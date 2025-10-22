# backend: src/pneuma_seeker/server.py
import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from torch.backends import cudnn

from pneuma_seeker.core.chat_interface import ChatInterface
from pneuma_seeker.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.core.persistence import get_unique_user_chat_ids

import os
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


class Manager:
    def __init__(self, llm_path, embed_model_path, data_sources):
        self.llm_path = llm_path
        self.embed_model_path = embed_model_path
        self.data_sources = data_sources
        self.chat_interfaces = {}

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

manager = Manager(
    llm_path="o4-mini",
    embed_model_path="model/weight/bge-base",
    data_sources=["buysite"],
)


templates = Jinja2Templates(directory="template")


@app.get("/state/html/{user_id}/{chat_id}", response_class=HTMLResponse)
async def read_state_html(request: Request, user_id: str, chat_id: str):
    conductor = manager.get_chat_interface(user_id, chat_id).conductor
    state = conductor.info_need_state.get_current_state_instance()

    return templates.TemplateResponse(
        "index.html", {"request": request, "state": state}
    )


@app.get("/graph/html/{user_id}/{chat_id}", response_class=HTMLResponse)
async def read_graph_html(request: Request, user_id: str, chat_id: str):
    conductor = manager.get_chat_interface(user_id, chat_id).conductor
    prov_graph = conductor.prov_graph
    return prov_graph.get_graph_visualization()


@app.get("/combined/html/{user_id}/{chat_id}", response_class=HTMLResponse)
async def read_combined_html(request: Request, user_id: str, chat_id: str):
    conductor = manager.get_chat_interface(user_id, chat_id).conductor
    state = conductor.info_need_state.get_current_state_instance()
    prov_graph_html = conductor.prov_graph.get_graph_visualization()
    return templates.TemplateResponse(
        "index2.html",
        {"request": request, "state": state, "prov_graph_html": prov_graph_html},
    )


@app.get("/helper")
async def helper():
    res = get_unique_user_chat_ids()
    return {"data": res}


@app.post("/chat")
async def chat_endpoint(request: Request):
    """
    Handles chat requests with HTTP streaming instead of WebSockets.
    Streams logs and assistant messages in real time.
    """
    body = await request.json()
    user_id = body.get("user_id", "default_user")
    chat_id = body.get("chat_id", "default_chat")

    messages: list[dict[str, Any]] = body["messages"]
    files: list[str] = body.get("files", [])

    chat_interface = manager.get_chat_interface(user_id, chat_id)

    async def event_stream():
        start = datetime.now().timestamp()

        yield json.dumps({
            "sender": "log",
            "text": "Connecting to Pneuma Seeker...",
            "time_stamp": int(datetime.now().timestamp() * 1000)
        }) + "\n"

        await asyncio.sleep(0.1)

        yield json.dumps({
            "sender": "log",
            "text": "Processing input...",
            "time_stamp": int(datetime.now().timestamp() * 1000)
        }) + "\n"

        await asyncio.sleep(0.1)

        # Stream data from ChatInterface
        for msg in chat_interface.process_user_input(messages, files):
            if msg.startswith("LOG"):
                yield json.dumps({
                    "sender": "log",
                    "text": msg,
                    "time_stamp": int(datetime.now().timestamp() * 1000)
                }) + "\n"
            elif msg.startswith("DONE"):
                end = datetime.now().timestamp()
                yield json.dumps({
                    "sender": "done",
                    "text": f"Processing done in {end - start:.2f} seconds.",
                    "time_stamp": int(datetime.now().timestamp() * 1000)
                }) + "\n"
            else:
                yield json.dumps({
                    "sender": "assistant",
                    "text": msg,
                    "time_stamp": int(datetime.now().timestamp() * 1000)
                }) + "\n"

            await asyncio.sleep(0)  # yield control back to loop

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/state/{user_id}/{chat_id}")
def get_state(user_id: str, chat_id: str):
    """
    Returns the current (T,Q) pairs, along with the current retrieval results.
    """
    conductor = manager.get_chat_interface(user_id, chat_id).conductor

    state = conductor.info_need_state.get_current_state_instance()
    curr_retrieval_results = conductor.current_retrieval_results
    transformed_retrieval_results: dict[str, list[AbstractDocument]] = {}
    for retriever_type in curr_retrieval_results.keys():
        transformed_retrieval_results[retriever_type.value] = curr_retrieval_results[
            retriever_type
        ]

    state["curr_retrieval_results"] = transformed_retrieval_results
    return state
