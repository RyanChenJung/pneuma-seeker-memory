# backend: src/pneuma_seeker/server.py
import json
import os

import asyncio
from typing import Any

from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from torch.backends import cudnn

from pneuma_seeker.core.conductor.chat_interface import ChatInterface
from pneuma_seeker.core.conductor import persistence
from pneuma_seeker.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.model.llm_message import LLMMessage


# enforce more deterministic behavior
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
cudnn.deterministic = True
cudnn.benchmark = False

app = FastAPI(title="Pneuma-Seeker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


FRONTEND_PATH = "http://localhost:8080"


class ConnectionManager:
    def __init__(self, llm_path: str, embed_model_path: str, data_sources: list[str]):
        self.llm_path = llm_path
        self.embed_model_path = embed_model_path
        self.data_sources = data_sources

        self.active_connections: dict[tuple[str, str], list[WebSocket]] = {}
        # TODO: Handle concurrency issue in the future!
        self.chat_interfaces: dict[tuple[str, str], ChatInterface] = {}

    def get_chat_interface(self, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        if key not in self.chat_interfaces:
            self.chat_interfaces[key] = ChatInterface(
                llm_path=self.llm_path,
                embed_model_path=self.embed_model_path,
                user_id=user_id,
                chat_id=chat_id,
                data_sources=self.data_sources,
                env_path="../../.env",
            )
        return self.chat_interfaces[key]

    async def connect(self, websocket: WebSocket, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)

        if key not in self.chat_interfaces:
            self.chat_interfaces[key] = ChatInterface(
                llm_path=self.llm_path,
                embed_model_path=self.embed_model_path,
                user_id=user_id,
                chat_id=chat_id,
                data_sources=self.data_sources,
                env_path="../../.env",
            )

    def disconnect(self, websocket: WebSocket, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        if key in self.active_connections:
            self.active_connections[key].remove(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]

    async def send_personal_message(
        self,
        user_id: str,
        chat_id: str,
        role: str,
        log_message: str,
        log_message_ts: int,
    ):
        key = (user_id, chat_id)
        for conn in self.active_connections.get(key, []):
            message = {
                "sender": role,
                "text": log_message,
                "time_stamp": log_message_ts,
            }
            await conn.send_json(message)

    def delete_chat(self, user_id: str, chat_id: str):
        key = (user_id, chat_id)

        # Close active connections for this chat
        if key in self.active_connections:
            for ws in self.active_connections[key]:
                # Ideally close websocket connections gracefully
                import asyncio

                asyncio.create_task(ws.close())
            del self.active_connections[key]

        # Remove conductor
        if key in self.chat_interfaces:
            del self.chat_interfaces[key]


manager = ConnectionManager(
    llm_path="o4-mini",
    embed_model_path="model/weight/bge-base",
    data_sources=["environment"],
)


templates = Jinja2Templates(directory="template")


@app.get("/state/html/{user_id}/{chat_id}", response_class=HTMLResponse)
async def read_state_html(request: Request, user_id: str, chat_id: str):
    conductor = manager.get_chat_interface(user_id, chat_id).llm_conductor
    state = conductor.info_need_state.get_current_state_instance()

    return templates.TemplateResponse(
        "index.html", {"request": request, "state": state}
    )


@app.get("/graph/html/{user_id}/{chat_id}", response_class=HTMLResponse)
async def read_graph_html(request: Request, user_id: str, chat_id: str):
    conductor = manager.get_chat_interface(user_id, chat_id).llm_conductor
    prov_graph = conductor.prov_graph
    return prov_graph.get_graph_visualization()


@app.get("/helper")
async def helper():
    res = persistence.get_unique_user_chat_ids()
    return {"data": res}


@app.websocket("/ws/{user_id}/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, chat_id: str):
    await manager.connect(websocket, user_id, chat_id)
    await websocket.accept()
    try:
        while True:
            # Receive the prompt from frontend
            data_from_frontend: dict[str, Any] = json.loads(
                await websocket.receive_text()
            )
            chat_messages: list[LLMMessage] = data_from_frontend["chat_messages"]
            url_paths: list[str] = [data_from_frontend["file_url_paths"]]

            # Normalize paths
            for idx, url_path in enumerate(url_paths):
                if not url_path.startswith("/"):
                    url_paths[idx] = f"/{url_path}"

            file_urls = [f"{FRONTEND_PATH}{i}" for i in url_paths]
            conductor = manager.get_chat_interface(user_id, chat_id)

            loop = asyncio.get_running_loop()

            # Run the blocking generator in a separate thread
            def run_generator():
                for log_message in conductor.process_user_input(
                    chat_messages, file_urls
                ):
                    actual_message = log_message
                    role = "assistant"
                    if log_message.startswith("LOG"):
                        role = "log"
                    elif log_message.startswith("DONE"):
                        role = "done"
                        actual_message = ""
                    # Schedule sending messages back to the websocket asynchronously
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message(
                            user_id,
                            chat_id,
                            role,
                            actual_message,
                            int(datetime.now().timestamp() * 1000),
                        ),
                        loop,
                    )

            await asyncio.to_thread(run_generator)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, chat_id)


@app.get("/state/{user_id}/{chat_id}")
def get_state(user_id: str, chat_id: str):
    """
    Returns the current (T,Q) pairs, along with the current retrieval results.
    """
    conductor = manager.get_chat_interface(user_id, chat_id).llm_conductor

    state = conductor.info_need_state.get_current_state_instance()
    curr_retrieval_results = conductor.current_retrieval_results
    transformed_retrieval_results: dict[str, list[AbstractDocument]] = {}
    for retriever_type in curr_retrieval_results.keys():
        transformed_retrieval_results[retriever_type.value] = curr_retrieval_results[
            retriever_type
        ]

    state["curr_retrieval_results"] = transformed_retrieval_results
    return state
