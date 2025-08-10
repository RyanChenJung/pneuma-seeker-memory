import os

# from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from torch.backends import cudnn

from pneuma_seeker.core.interaction_conductor.chat_interface import ChatInterface
from pneuma_seeker.core.ir_system.ir_data_model import AbstractDocument

# enforce more deterministic behavior
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
cudnn.deterministic = True
cudnn.benchmark = False

app = FastAPI(title="Pneuma-Seeker")
origins = [
    "http://localhost:3000",  # Next.js dev server
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],  # ["GET", "POST", ...] if you want to restrict
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self, llm_path: str, embed_model_path: str, data_sources: list[str]):
        self.llm_path = llm_path
        self.embed_model_path = embed_model_path
        self.data_sources = data_sources

        self.active_connections: dict[tuple[str, str], list[WebSocket]] = {}
        # TODO: Handle concurrency issue in the future!
        self.conductors: dict[tuple[str, str], ChatInterface] = {}
    
    def get_conductor(self, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        if key not in self.conductors:
            self.conductors[key] = ChatInterface(
                llm_path=self.llm_path,
                embed_model_path=self.embed_model_path,
                user_id=user_id,
                data_sources=self.data_sources,
            )
        return self.conductors[key]

    async def connect(self, websocket: WebSocket, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)

        if key not in self.conductors:
            self.conductors[key] = ChatInterface(
                llm_path=self.llm_path,
                embed_model_path=self.embed_model_path,
                user_id=user_id,
                data_sources=self.data_sources,
            )

    def disconnect(self, websocket: WebSocket, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        if key in self.active_connections:
            self.active_connections[key].remove(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]

    async def send_personal_message(self, message: str, user_id: str, chat_id: str):
        key = (user_id, chat_id)
        for conn in self.active_connections.get(key, []):
            await conn.send_text(message)

manager = ConnectionManager(
    llm_path="model/weight/qwen3-8b",
    embed_model_path="model/weight/bge-base",
    data_sources=["environment"]
)

@app.websocket("/ws/{user_id}/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, chat_id: str):
    await manager.connect(websocket, user_id, chat_id)
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            conductor = manager.get_conductor(user_id, chat_id)
            for log_message in conductor.process_user_input(data):
                await manager.send_personal_message(log_message, user_id, chat_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, chat_id)


# @app.get("/state/")
# def get_state():
#     """
#     Returns the current SQLs and target schemas.
#     """
#     state = pneuma_seeker.llm_conductor.info_need_state.get_current_state_instance()
#     curr_retrieval_results = pneuma_seeker.llm_conductor.current_retrieval_results
#     transformed_retrieval_results: dict[str, list[AbstractDocument]] = {}
#     for retriever_type in curr_retrieval_results.keys():
#         transformed_retrieval_results[retriever_type.value] = curr_retrieval_results[
#             retriever_type
#         ]

#     state["curr_retrieval_results"] = transformed_retrieval_results
#     return state
