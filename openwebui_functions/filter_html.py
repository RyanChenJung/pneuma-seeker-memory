from pydantic import BaseModel
from typing import Optional
import re


class Filter:
    START_COMMENT = "<!-- PNEUMA_STATE_START -->"
    END_COMMENT = "<!-- PNEUMA_STATE_END -->"

    class Valves(BaseModel):
        enabled: Optional[bool] = True

    def __init__(self):
        self.valves = self.Valves()

        # Pattern matches the entire ```html ... ``` block that contains your markers
        self.block_pattern = re.compile(
            rf"```html\s*{re.escape(self.START_COMMENT)}.*?{re.escape(self.END_COMMENT)}\s*```",
            re.DOTALL,
        )

    def _clean_content(self, content: str) -> str:
        if not content:
            return content
        cleaned = self.block_pattern.sub("", content)
        # collapse excessive blank lines, trim edges
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned

    def inlet(self, body: dict) -> dict:
        """Clean user input before it reaches backend."""
        if "messages" in body:
            for msg in body["messages"]:
                if "content" in msg and isinstance(msg["content"], str):
                    msg["content"] = self._clean_content(msg["content"])
        return body

    def stream(self, event: dict) -> dict:
        """Clean streamed model tokens as they are generated."""
        if "content" in event and isinstance(event["content"], str):
            event["content"] = self._clean_content(event["content"])
        return event

    def outlet(self, body: dict) -> dict:
        """Clean model outputs before they are sent to frontend."""
        if "messages" in body:
            for msg in body["messages"]:
                if "content" in msg and isinstance(msg["content"], str):
                    msg["content"] = self._clean_content(msg["content"])
        elif "message" in body and "content" in body["message"]:
            body["message"]["content"] = self._clean_content(body["message"]["content"])
        return body
