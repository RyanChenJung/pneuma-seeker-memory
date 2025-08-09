from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pneuma_seeker.core.interaction_conductor.chat_interface import ChatInterface

import os

# from dotenv import load_dotenv
from torch.backends import cudnn

from pneuma_seeker.core.ir_system.ir_data_model import AbstractDocument

# enforce more deterministic behavior
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
cudnn.deterministic = True
cudnn.benchmark = False

app = FastAPI(title="Pneuma-Seeker")

# List of allowed origins (your Next.js frontend URL)
origins = [
    "http://localhost:3000",  # Next.js dev server
    # Add your production URL when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],  # ["GET", "POST", ...] if you want to restrict
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()
pneuma_seeker = ChatInterface(
    llm_path="model/weight/qwen3-8b",
    embed_model_path="model/weight/bge-base",
    user_id="single_user",
    data_sources=["environment"],
)


# Input model for API requests
class UserInput(BaseModel):
    message: str


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # If you expect incoming messages
            data = await websocket.receive_text()
            await manager.broadcast(f"Message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/chat/")
def chat(user_input: UserInput):
    """
    Handle chat input from the user and return the system's response.
    """
    response = pneuma_seeker.process_user_input(user_input.message)
    return {"response": response}


@app.get("/state/")
def get_state():
    """
    Returns the current SQLs and target schemas.
    """
    state = pneuma_seeker.llm_conductor.info_need_state.get_current_state_instance()
    curr_retrieval_results = pneuma_seeker.llm_conductor.current_retrieval_results
    transformed_retrieval_results: dict[str, list[AbstractDocument]] = {}
    for retriever_type in curr_retrieval_results.keys():
        transformed_retrieval_results[retriever_type.value] = curr_retrieval_results[
            retriever_type
        ]

    state["curr_retrieval_results"] = transformed_retrieval_results
    return state
