import json
import time
import websockets
import re

from fastapi import Request
from pydantic import BaseModel, Field
from typing import Callable


class Pipe:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(
        self,
        body: dict,
        __user__: dict,
        __request__: Request,
        __metadata__: dict,
        __event_emitter__: Callable,
    ):
        filtered_messages = [i for i in body["messages"] if i["role"] != "system"]
        filtered_files = []
        if __metadata__ is not None and __metadata__["files"] is not None:
            filtered_files = [i["url"] for i in __metadata__["files"]]
        print(f"DEBUGGY: messages: {filtered_messages}")
        print(f"DEBUGGY: files: {filtered_files}")

        yield "DONE!"

        await __event_emitter__(
            {
                "type": "chat:title",
                "data": "Market Analysis",
            }
        )

        # return "DONE!"
