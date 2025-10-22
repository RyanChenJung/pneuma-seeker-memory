# frontend: OpenWebUI Pipe (Python side)
import json
import time
import httpx
from typing import Callable
from fastapi import Request
from pydantic import BaseModel


class Pipe:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    def get_capabilities(self):
        return {
            "allow_file_upload": True,
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
        user_id = __metadata__.get("user_id", "default_user")
        chat_id = __metadata__.get("chat_id", "default_chat")
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

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            async with client.stream(
                "POST",
                "http://localhost:8000/chat",
                json={
                    "messages": chat_messages,
                    "files": files,
                    "user_id": user_id,
                    "chat_id": chat_id,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        message_data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    sender = message_data.get("sender")
                    text = message_data.get("text", "")

                    if sender == "log":
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": (
                                        text[5:] if text.startswith("LOG: ") else text
                                    ),
                                    "done": False,
                                    "hidden": False,
                                },
                            }
                        )
                    elif sender == "assistant":
                        await __event_emitter__(
                            {
                                "type": "chat:message:delta",
                                "data": {"content": text.replace("~", "\\~")},
                            }
                        )
                    elif sender == "done":
                        end = time.time()
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": f"{text}",
                                    "done": True,
                                    "hidden": False,
                                },
                            }
                        )
                        break
