import json
import time
import websockets

from fastapi import Request
from pydantic import BaseModel
from typing import Callable


class Pipe:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    def get_capabilities(self):
        return {
            "allow_file_upload": False,
            "allow_image_input": False,
            "allow_code_interpreter": False,
        }

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

        uri = f"ws://localhost:8000/ws/{user_id}/{chat_id}"
        files = []
        if __metadata__ is not None and __metadata__["files"] is not None:
            files = [i["url"] for i in __metadata__["files"]]

        async with websockets.connect(uri, open_timeout=30) as websocket:
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

            user_buffer = ""
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
                    else:
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
                                "description": f"Processing done.",
                                "done": True,
                                "hidden": False,
                            },
                        }
                    )
                    break
