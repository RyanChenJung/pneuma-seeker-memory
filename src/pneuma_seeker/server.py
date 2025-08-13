# backend: src/pneuma_seeker/server.py
import json
import os

import asyncio

from dotenv import load_dotenv
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from torch.backends import cudnn

from pneuma_seeker.core.conductor.chat_interface import ChatInterface
from pneuma_seeker.core.ir_system.data_model import AbstractDocument

load_dotenv("../../.env")

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


@app.websocket("/ws/{user_id}/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, chat_id: str):
    await manager.connect(websocket, user_id, chat_id)
    await websocket.accept()
    try:
        while True:
            # Receive the prompt from frontend
            data = json.loads(await websocket.receive_text())["prompt"]
            conductor = manager.get_chat_interface(user_id, chat_id)

            loop = asyncio.get_running_loop()

            # Run the blocking generator in a separate thread
            def run_generator():
                for log_message in conductor.process_user_input(data):
                    # Schedule sending messages back to the websocket asynchronously
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message(
                            user_id,
                            chat_id,
                            "log" if log_message.startswith("LOG") else "assistant",
                            log_message,
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
