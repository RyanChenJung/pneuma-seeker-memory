import json
import time
import websockets
import re

from fastapi import Request
from pydantic import BaseModel, Field
from typing import Callable


class Pipe:
    class Valves(BaseModel):
        NUM_ITERATION: int = Field(
            default=2,
            description="The number of exclamation points to add at the end of prompt.",
        )

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
        prompt: str = body.get("messages")[-1]["content"]
        prompt = re.sub(r"\{\{HTML_FILE_ID_.*\}\}$", "", prompt).strip()

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

        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"prompt": prompt}))

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

            # Listen for streamed messages
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
                        await __event_emitter__(
                            {
                                "type": "chat:completion",
                                "data": {
                                    "content": message_data["text"].replace("~", "\\~")
                                },
                            }
                        )
                        break
                except websockets.ConnectionClosed:
                    break
