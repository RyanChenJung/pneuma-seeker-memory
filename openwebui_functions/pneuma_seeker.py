import asyncio
import json
import time
from typing import Callable

import websockets
from fastapi import Request
from pydantic import BaseModel


class Pipe:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()
        # Persistent connections keyed by (user_id, chat_id)
        self.connections: dict[
            tuple[str, str],
            websockets.WebSocketClientProtocol,
        ] = {}
        # Locks to ensure one recv at a time per connection
        self.locks: dict[tuple[str, str], asyncio.Lock] = {}

    def get_capabilities(self):
        return {
            "allow_file_upload": True,
            "allow_image_input": False,
            "allow_code_interpreter": False,
        }

    async def get_connection(
        self, user_id: str, chat_id: str
    ) -> websockets.WebSocketClientProtocol:
        key = (user_id, chat_id)
        if key not in self.connections or self.connections[key].closed:
            uri = f"ws://localhost:8000/ws/{user_id}/{chat_id}"
            self.connections[key] = await websockets.connect(
                uri, open_timeout=50, ping_interval=20, ping_timeout=20
            )
            self.locks[key] = asyncio.Lock()
        return self.connections[key]

    async def pipe(
        self,
        body: dict,
        __user__: dict,
        __request__: Request,
        __metadata__: dict,
        __event_emitter__: Callable,
    ):
        start = time.time()
        user_id = __metadata__["user_id"]
        chat_id = __metadata__["chat_id"]
        chat_messages = [i for i in body["messages"] if i["role"] != "system"]
        files = [i["url"] for i in (__metadata__.get("files") or [])]

        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Connecting to Pneuma Seeker...",
                    "done": False,
                    "hidden": False,
                },
            }
        )

        websocket = await self.get_connection(user_id, chat_id)
        lock = self.locks[(user_id, chat_id)]

        await websocket.send(
            json.dumps(
                {
                    "chat_messages": chat_messages,
                    "files": files,
                }
            )
        )

        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Processing input...",
                    "done": False,
                    "hidden": False,
                },
            }
        )

        async with lock:
            while True:
                try:
                    message = await websocket.recv()
                    message_data = json.loads(message)

                    if message_data["sender"] == "log":
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": message_data["text"][5:],
                                    "done": False,
                                    "hidden": False,
                                },
                            }
                        )
                    elif message_data["sender"] == "assistant":
                        await __event_emitter__(
                            {
                                "type": "chat:message:delta",
                                "data": {
                                    "content": message_data["text"].replace("~", "\\~")
                                },
                            }
                        )
                    elif message_data["sender"] == "done":
                        end = time.time()
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": f"Processing done in {end-start:.2f} seconds.",
                                    "done": True,
                                    "hidden": False,
                                },
                            }
                        )
                        break
                except websockets.ConnectionClosed:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "Processing done (connection closed).",
                                "done": True,
                                "hidden": False,
                            },
                        }
                    )
                    # Remove from dict to allow reconnect
                    self.connections.pop((user_id, chat_id), None)
                    self.locks.pop((user_id, chat_id), None)
                    break
