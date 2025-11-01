"""
title: View/Hide Conductor's State
author: Luthfi Balaka
version: 0.0.1
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzNTMiIGhlaWdodD0iNTEyIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCI+CiAgPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNMjk5LjU5NiA0OTIuMjIzQzI2Ni44NTYgNTA0Ljk3NiAyMjMuNDk2IDUxMiAxNzcuNSA1MTJjLTQ1Ljk5NiAwLTg5LjM1Ny03LjAyNC0xMjIuMDk1LTE5Ljc3Ny0zNS4wODMtMTMuNjY3LTU0LjQwNC0zMi43NjYtNTQuNDA0LTUzLjc4VjczLjU1N2MwLTIxLjAxNCAxOS4zMjEtNDAuMTEzIDU0LjQwNC01My43OEM4OC4xNDQgNy4wMjQgMTMxLjUwNCAwIDE3Ny41IDBjNDUuOTk2IDAgODkuMzU2IDcuMDI0IDEyMi4wOTYgMTkuNzc4IDM1LjA2OSAxMy42NjEgNTQuMzg3IDMyLjc1MSA1NC40MDIgNTMuNzU2IDAgLjAwNy4wMDEuMDE0LjAwMS4wMjN2MzY0Ljg4NmMwIDIxLjAxNC0xOS4zMjEgNDAuMTEzLTU0LjQwMyA1My43OFpNMjkzLjg3MiAzNC40NEMyNjIuOTE0IDIyLjM4MSAyMjEuNTg1IDE1LjczOSAxNzcuNSAxNS43MzljLTQ0LjA4NSAwLTg1LjQxNCA2LjY0Mi0xMTYuMzcyIDE4LjcwMi0yOC4yIDEwLjk4NC00NC4zNzQgMjUuMjQzLTQ0LjM3NCAzOS4xMTYgMCAxMy44NzMgMTYuMTc0IDI4LjEzMSA0NC4zNzQgMzkuMTE2IDMwLjk1OCAxMi4wNTggNzIuMjg3IDE4LjcgMTE2LjM3MiAxOC43IDE2LjUzMiAwIDMyLjY3NS0uOTM0IDQ4LjAzMS0yLjczOCAyNS41OTItMy4wMDUgNDguOTkyLTguNDI1IDY4LjM0MS0xNS45NjMgMjguMTk5LTEwLjk4NSA0NC4zNzItMjUuMjQzIDQ0LjM3Mi0zOS4xMTYgMC0xMy44NzMtMTYuMTcyLTI4LjEzMS00NC4zNzItMzkuMTE2Wm00NC4zNzUgNzAuMzkzYy0uMDE1LjAxNC0uMDMxLjAyNy0uMDQ2LjA0MS0uMTMzLjEyMi0uMjc1LjI0NC0uNDEuMzY3LTEwLjkxMiA5LjkxLTI0LjU1NCAxNi43ODEtMzguMTk0IDIyLjA5NS0yMS40ODUgOC4zNjktNDcuNTQ0IDE0LjI3LTc1LjkyMSAxNy4zMzktMTQuODY1IDEuNjA4LTMwLjM2NCAyLjQzOC00Ni4xNzUgMi40MzgtNDUuOTk2IDAtODkuMzU3LTcuMDI0LTEyMi4wOTUtMTkuNzc3LTEzLjg5Ni01LjQxMy0yNy41ODctMTIuMjY2LTM4LjYxNC0yMi40NjktLjAxMi0uMDExLS4wMjQtLjAyMS0uMDM2LS4wMzJ2OTAuMzVjMCAxMy44NzIgMTYuMTczIDI4LjEzIDQ0LjM3MyAzOS4xMTUgMjYuMTIxIDEwLjE3NiA1OS42MjQgMTYuNDk1IDk1LjkzOCAxOC4yMjEgNi44MDUuMzI1IDEzLjYyLjQ4MiAyMC40MzQuNDgyIDQ4Ljc0MyAwIDEwNi4xODQtMy41ODIgMTQ2LjEzMi0zNC42OTIgNS4zMDctNC4xMzMgMTAuMjY0LTkuMDI0IDEyLjkzNi0xNS4zMDUgMS4wNDktMi40NiAxLjY3OC01LjEzOSAxLjY3OC03Ljgydi05MC4zNTNabS4wMDEgMTIxLjYyN2MtLjAxMi4wMDktLjAyNC4wMi0uMDM0LjAyOS0yLjUyOCAyLjMxOS01LjIwNCA0LjQ3NS03Ljk5OCA2LjQ2OS0xNy4zODMgMTIuNDEtMzguMjQ3IDE5LjY5NS01OC43ODggMjQuOTIyLTE2Ljk5NCA0LjMyNC0zNS43MDEgNy40MjQtNTUuNDA2IDkuMTc3LS4xNzIuMDE0LS4zNDMuMDMyLS41MTUuMDQ3LTYuNDg1LjU2OC0xMy4wNzcuOTg3LTE5Ljc0OSAxLjI2MS02LjAyNi4yNDgtMTIuMTE3LjM3Ny0xOC4yNTYuMzc3LTQ1Ljk5NiAwLTg5LjM1Ny03LjAyNC0xMjIuMDk1LTE5Ljc3Ny0xMy42NTItNS4zMTYtMjcuMjE3LTEyLjE0My0zOC4xMzktMjIuMDQ1LS4xNTUtLjE0MS0uMzE3LS4yNzktLjQ3MS0uNDIxLS4wMTMtLjAxMi0uMDI2LS4wMjQtLjA0LS4wMzZ2OTAuMzUyYzAgMTMuODczIDE2LjE3MyAyOC4xMzEgNDQuMzczIDM5LjExNiAzMC45NTggMTIuMDU5IDcyLjI4NyAxOC43MDEgMTE2LjM3MiAxOC43MDEgMTEuODgxIDAgMjMuNTU5LS40ODcgMzQuODktMS40MjkuODEzLS4wNjYgMS42MjUtLjEzNyAyLjQzMy0uMjA4IDI5Ljc2Ny0yLjY1NSA1Ny4wMzItOC40ODcgNzkuMDQ5LTE3LjA2NCAxMi4wMjgtNC42ODUgMjEuODU5LTkuOTY3IDI5LjE4OS0xNS41NTkgNi4xNzEtNC43MDggMTIuMjUtMTAuNjcxIDE0LjQzNi0xOC4zNDQuMDE1LS4wNTIuMDI0LS4xMDQuMDM5LS4xNTUuNDU4LTEuNjQ4LjcxLTMuMzQ4LjcxLTUuMDU5VjIyNi40NlptLjAwMiAxMjEuNjI4Yy0uMDEzLjAxMi0uMDI1LjAyMi0uMDM4LjAzNC0uMTcyLjE1OS0uMzU2LjMxNy0uNTMxLjQ3NS0yLjU1MiAyLjMwOS01LjI1NSA0LjQ0NS04LjA3MyA2LjQyLTkuMjYxIDYuNDg3LTE5LjQ5MiAxMS40OC0zMC4wMSAxNS41NzctMjguNTA4IDExLjEwMy02NS4wNyAxNy44NjEtMTA0LjQxMSAxOS40MjMtNS44MzkuMjMyLTExLjczOC4zNTItMTcuNjgzLjM1Mi00NS45OTYgMC04OS4zNTctNy4wMjQtMTIyLjA5NS0xOS43NzctMTMuNjg3LTUuMzMtMjcuMTI3LTEyLjA3MS0zOC4wODYtMjEuOTk3LS4xNzQtLjE1Ny0uMzU2LS4zMTQtLjUyOC0uNDcyLS4wMTMtLjAxMi0uMDI1LS4wMjItLjAzOC0uMDM0djkwLjM1MmMwIDEzLjg3MiAxNi4xNzMgMjguMTMgNDQuMzczIDM5LjExNSAzMC45NTkgMTIuMDYgNzIuMjg2IDE4LjcwMiAxMTYuMzcyIDE4LjcwMnM4NS40MTQtNi42NDIgMTE2LjM3My0xOC43MDJjMjguMTk5LTEwLjk4NSA0NC4zNzItMjUuMjQxIDQ0LjM3Mi0zOS4xMTVoLjAwM3YtOTAuMzUzWm0tMjguMTc0IDgwLjg4M2MtNy45NDkgMC0xNC4zOTMtNi40MzgtMTQuMzkzLTE0LjM4MSAwLTcuOTQyIDYuNDQ0LTE0LjM4MSAxNC4zOTMtMTQuMzgxIDcuOTUgMCAxNC4zOTQgNi40MzkgMTQuMzk0IDE0LjM4MSAwIDcuOTQzLTYuNDQ0IDE0LjM4MS0xNC4zOTQgMTQuMzgxWm0tNDkuOTU2IDE1LjA0N2MtNy45NDkgMC0xNC4zOTMtNi40MzgtMTQuMzkzLTE0LjM4MSAwLTcuOTQyIDYuNDQ0LTE0LjM4MSAxNC4zOTMtMTQuMzgxIDcuOTQ5IDAgMTQuMzk0IDYuNDM5IDE0LjM5NCAxNC4zODEgMCA3Ljk0My02LjQ0NSAxNC4zODEtMTQuMzk0IDE0LjM4MVptLTUzLjAxMiA4LjIzN2MtNy45NDkgMC0xNC4zOTMtNi40MzgtMTQuMzkzLTE0LjM4MSAwLTcuOTQyIDYuNDQ0LTE0LjM4MSAxNC4zOTMtMTQuMzgxIDcuOTQ5IDAgMTQuMzkzIDYuNDM5IDE0LjM5MyAxNC4zODEgMCA3Ljk0My02LjQ0NCAxNC4zODEtMTQuMzkzIDE0LjM4MVptMTAyLjk2OC0xNDMuODc3Yy03Ljk0OSAwLTE0LjM5My02LjQzOS0xNC4zOTMtMTQuMzgxIDAtNy45NDMgNi40NDQtMTQuMzgxIDE0LjM5My0xNC4zODEgNy45NSAwIDE0LjM5NCA2LjQzOCAxNC4zOTQgMTQuMzgxIDAgNy45NDItNi40NDQgMTQuMzgxLTE0LjM5NCAxNC4zODFabS00OS45NTYgMTUuMDU3Yy03Ljk0OSAwLTE0LjM5My02LjQzOS0xNC4zOTMtMTQuMzgxIDAtNy45NDMgNi40NDQtMTQuMzgxIDE0LjM5My0xNC4zODEgNy45NDkgMCAxNC4zOTQgNi40MzggMTQuMzk0IDE0LjM4MSAwIDcuOTQyLTYuNDQ1IDE0LjM4MS0xNC4zOTQgMTQuMzgxWm0tNTMuMDEyIDguMjM3Yy03Ljk0OSAwLTE0LjM5My02LjQzOS0xNC4zOTMtMTQuMzgxIDAtNy45NDMgNi40NDQtMTQuMzgxIDE0LjM5My0xNC4zODEgNy45NDkgMCAxNC4zOTMgNi40MzggMTQuMzkzIDE0LjM4MSAwIDcuOTQyLTYuNDQ0IDE0LjM4MS0xNC4zOTMgMTQuMzgxWm0xMDIuOTY4LTE0NS45ODZjLTcuOTQ5IDAtMTQuMzkzLTYuNDM4LTE0LjM5My0xNC4zODEgMC03Ljk0MiA2LjQ0NC0xNC4zODEgMTQuMzkzLTE0LjM4MSA3Ljk1IDAgMTQuMzk0IDYuNDM5IDE0LjM5NCAxNC4zODEgMCA3Ljk0My02LjQ0NCAxNC4zODEtMTQuMzk0IDE0LjM4MVptLTQ5Ljk1NiAxNS4wNTdjLTcuOTQ5IDAtMTQuMzkzLTYuNDM4LTE0LjM5My0xNC4zODEgMC03Ljk0MiA2LjQ0NC0xNC4zODEgMTQuMzkzLTE0LjM4MSA3Ljk0OSAwIDE0LjM5NCA2LjQzOSAxNC4zOTQgMTQuMzgxIDAgNy45NDMtNi40NDUgMTQuMzgxLTE0LjM5NCAxNC4zODFabS01My4wMTIgOC4yMzdjLTcuOTQ5IDAtMTQuMzkzLTYuNDM4LTE0LjM5My0xNC4zODEgMC03Ljk0MiA2LjQ0NC0xNC4zODEgMTQuMzkzLTE0LjM4MSA3Ljk0OSAwIDE0LjM5MyA2LjQzOSAxNC4zOTMgMTQuMzgxIDAgNy45NDMtNi40NDQgMTQuMzgxLTE0LjM5MyAxNC4zODFaIi8+Cjwvc3ZnPg==
"""

from pydantic import BaseModel, Field
from typing import Optional
from fastapi.requests import Request
import logging
import re
import httpx

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Action:
    START_COMMENT = "<!-- PNEUMA_STATE_START -->"
    END_COMMENT = "<!-- PNEUMA_STATE_END -->"

    class Valves(BaseModel):
        show_status: bool = Field(
            default=True, description="Show status of the action."
        )

    class UserValves(BaseModel):
        show_status: bool = Field(
            default=True, description="Show status of the action."
        )

    def __init__(self):
        self.valves = self.Valves()

    def _strip_all_placeholders(self, messages: list, pattern: str) -> None:
        """Remove matching placeholders from every message, tidy whitespace."""
        for msg in messages:
            content = msg.get("content", "") or ""
            content = re.sub(pattern, "", content)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()
            msg["content"] = content

    async def _fetch_launcher_html(self, user_id: str, chat_id: str, body: dict) -> str:
        url = f"http://127.0.0.1:8000/combined/html/{user_id}/{chat_id}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                html = resp.text
                html = html.replace("<body", '<body style="min-height:800px;"')
                return html
        except httpx.ReadTimeout:
            return "<h1>Backend timed out</h1><p>Please try again later.</p>"
        except Exception as e:
            return f"<h1>Error fetching HTML</h1><p>{e}</p>"

    async def action(
        self,
        body: dict,
        __request__: Request = None,
        __user__=None,
        __event_emitter__=None,
        __metadata__=None,
        __event_call__=None,
    ) -> Optional[dict]:
        user_valves = (__user__ or {}).get("valves") or self.UserValves()

        # pattern to detect the fenced html block that contains the start/end comments
        block_pattern = rf"```html\s*{re.escape(self.START_COMMENT)}.*?{re.escape(self.END_COMMENT)}\s*```"

        try:
            messages = body.get("messages") or []
            if not messages:
                return body

            last_msg = messages[-1]
            last_content = last_msg.get("content", "") or ""

            block_shown = bool(re.search(block_pattern, last_content, flags=re.DOTALL))

            if __event_emitter__ and user_valves.show_status:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": (
                                "Hiding State…" if block_shown else "Opening State…"
                            ),
                            "done": False,
                        },
                    }
                )

            if block_shown:
                # Toggle OFF → remove the fenced html block (including comments)
                last_msg["content"] = re.sub(
                    block_pattern, "", last_content, flags=re.DOTALL
                ).strip()
            else:
                # Toggle ON → fetch HTML and insert WITH the markers inside the code fence
                user_id = (__user__ or {}).get("id", "anonymous")
                launcher_html = await self._fetch_launcher_html(
                    user_id, body["chat_id"], body
                )

                # Escape triple backticks in the fetched HTML so the fence doesn't break
                launcher_html = launcher_html.replace("```", "`\u200b``")

                # Put the HTML comments inside the fenced code block
                html_block = (
                    "```html\n"
                    f"{self.START_COMMENT}\n"
                    f"{launcher_html}\n"
                    f"{self.END_COMMENT}\n"
                    "```"
                )

                if last_content.strip():
                    last_msg["content"] += "\n\n" + html_block
                else:
                    last_msg["content"] = html_block

            if __event_emitter__ and user_valves.show_status:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": (
                                "State Hidden." if block_shown else "State Opened."
                            ),
                            "done": True,
                        },
                    }
                )

        except Exception as e:
            logger.exception("Error in State View Action")
            if messages:
                last_msg = messages[-1]
                last_msg["content"] = (
                    last_msg.get("content", "") or ""
                ) + f"\n\nError: {e}"
            if __event_emitter__ and user_valves.show_status:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Error during toggle", "done": True},
                    }
                )

        return body
