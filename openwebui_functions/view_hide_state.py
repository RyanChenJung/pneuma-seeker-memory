"""
title: Open Random HelloWorld Page
author: Luthfi Balaka
version: 0.1.0
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzNTMiIGhlaWdodD0iNTEyIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCI+CiAgPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNMjk5LjU5NiA0OTIuMjIzQzI2Ni44NTYgNTA0Ljk3NiAyMjMuNDk2IDUxMiAxNzcuNSA1MTJjLTQ1Ljk5NiAwLTg5LjM1Ny03LjAyNC0xMjIuMDk1LTE5Ljc3Ny0zNS4wODMtMTMuNjY3LTU0LjQwNC0zMi43NjYtNTQuNDA0LTUzLjc4VjczLjU1N2MwLTIxLjAxNCAxOS4zMjEtNDAuMTEzIDU0LjQwNC01My43OEM4OC4xNDQgNy4wMjQgMTMxLjUwNCAwIDE3Ny41IDBjNDUuOTk2IDAgODkuMzU2IDcuMDI0IDEyMi4wOTYgMTkuNzc4IDM1LjA2OSAxMy42NjEgNTQuMzg3IDMyLjc1MSA1NC40MDIgNTMuNzU2IDAgLjAwNy4wMDEuMDE0LjAwMS4wMjN2MzY0Ljg4NmMwIDIxLjAxNC0xOS4zMjEgNDAuMTEzLTU0LjQwMyA1My43OFpNMjkzLjg3MiAzNC40NEMyNjIuOTE0IDIyLjM4MSAyMjEuNTg1IDE1LjczOSAxNzcuNSAxNS43MzljLTQ0LjA4NSAwLTg1LjQxNCA2LjY0Mi0xMTYuMzcyIDE4LjcwMi0yOC4yIDEwLjk4NC00NC4zNzQgMjUuMjQzLTQ0LjM3NCAzOS4xMTYgMCAxMy44NzMgMTYuMTc0IDI4LjEzMSA0NC4zNzQgMzkuMTE2IDMwLjk1OCAxMi4wNTggNzIuMjg3IDE4LjcgMTE2LjM3MiAxOC43IDE2LjUzMiAwIDMyLjY3NS0uOTM0IDQ4LjAzMS0yLjczOCAyNS41OTItMy4wMDUgNDguOTkyLTguNDI1IDY4LjM0MS0xNS45NjMgMjguMTk5LTEwLjk4NSA0NC4zNzItMjUuMjQzIDQ0LjM3Mi0zOS4xMTYgMC0xMy44NzMtMTYuMTcyLTI4LjEzMS00NC4zNzItMzkuMTE2Wm00NC4zNzUgNzAuMzkzYy0uMDE1LjAxNC0uMDMxLjAyNy0uMDQ2LjA0MS0uMTMzLjEyMi0uMjc1LjI0NC0uNDEuMzY3LTEwLjkxMiA5LjkxLTI0LjU1NCAxNi43ODEtMzguMTk0IDIyLjA5NS0yMS40ODUgOC4zNjktNDcuNTQ0IDE0LjI3LTc1LjkyMSAxNy4zMzktMTQuODY1IDEuNjA4LTMwLjM2NCAyLjQzOC00Ni4xNzUgMi40MzgtNDUuOTk2IDAtODkuMzU3LTcuMDI0LTEyMi4wOTUtMTkuNzc3LTEzLjg5Ni01LjQxMy0yNy41ODctMTIuMjY2LTM4LjYxNC0yMi40NjktLjAxMi0uMDExLS4wMjQtLjAyMS0uMDM2LS4wMzJ2OTAuMzVjMCAxMy44NzIgMTYuMTczIDI4LjEzIDQ0LjM3MyAzOS4xMTUgMjYuMTIxIDEwLjE3NiA1OS42MjQgMTYuNDk1IDk1LjkzOCAxOC4yMjEgNi44MDUuMzI1IDEzLjYyLjQ4MiAyMC40MzQuNDgyIDQ4Ljc0MyAwIDEwNi4xODQtMy41ODIgMTQ2LjEzMi0zNC42OTIgNS4zMDctNC4xMzMgMTAuMjY0LTkuMDI0IDEyLjkzNi0xNS4zMDUgMS4wNDktMi40NiAxLjY3OC01LjEzOSAxLjY3OC03Ljgydi05MC4zNTNabS4wMDEgMTIxLjYyN2MtLjAxMi4wMDktLjAyNC4wMi0uMDM0LjAyOS0yLjUyOCAyLjMxOS01LjIwNCA0LjQ3NS03Ljk5OCA2LjQ2OS0xNy4zODMgMTIuNDEtMzguMjQ3IDE5LjY5NS01OC43ODggMjQuOTIyLTE2Ljk5NCA0LjMyNC0zNS43MDEgNy40MjQtNTUuNDA2IDkuMTc3LS4xNzIuMDE0LS4zNDMuMDMyLS41MTUuMDQ3LTYuNDg1LjU2OC0xMy4wNzcuOTg3LTE5Ljc0OSAxLjI2MS02LjAyNi4yNDgtMTIuMTE3LjM3Ny0xOC4yNTYuMzc3LTQ1Ljk5NiAwLTg5LjM1Ny03LjAyNC0xMjIuMDk1LTE5Ljc3Ny0xMy42NTItNS4zMTYtMjcuMjE3LTEyLjE0My0zOC4xMzktMjIuMDQ1LS4xNTUtLjE0MS0uMzE3LS4yNzktLjQ3MS0uNDIxLS4wMTMtLjAxMi0uMDI2LS4wMjQtLjA0LS4wMzZ2OTAuMzUyYzAgMTMuODczIDE2LjE3MyAyOC4xMzEgNDQuMzczIDM5LjExNiAzMC45NTggMTIuMDU5IDcyLjI4NyAxOC43MDEgMTE2LjM3MiAxOC43MDEgMTEuODgxIDAgMjMuNTU5LS40ODcgMzQuODktMS40MjkuODEzLS4wNjYgMS42MjUtLjEzNyAyLjQzMy0uMjA4IDI5Ljc2Ny0yLjY1NSA1Ny4wMzItOC40ODcgNzkuMDQ5LTE3LjA2NCAxMi4wMjgtNC42ODUgMjEuODU5LTkuOTY3IDI5LjE4OS0xNS41NTkgNi4xNzEtNC43MDggMTIuMjUtMTAuNjcxIDE0LjQzNi0xOC4zNDQuMDE1LS4wNTIuMDI0LS4xMDQuMDM5LS4xNTUuNDU4LTEuNjQ4LjcxLTMuMzQ4LjcxLTUuMDU5VjIyNi40NlptLjAwMiAxMjEuNjI4Yy0uMDEzLjAxMi0uMDI1LjAyMi0uMDM4LjAzNC0uMTcyLjE1OS0uMzU2LjMxNy0uNTMxLjQ3NS0yLjU1MiAyLjMwOS01LjI1NSA0LjQ0NS04LjA3MyA2LjQyLTkuMjYxIDYuNDg3LTE5LjQ5MiAxMS40OC0zMC4wMSAxNS41NzctMjguNTA4IDExLjEwMy02NS4wNyAxNy44NjEtMTA0LjQxMSAxOS40MjMtNS44MzkuMjMyLTExLjczOC4zNTItMTcuNjgzLjM1Mi00NS45OTYgMC04OS4zNTctNy4wMjQtMTIyLjA5NS0xOS43NzctMTMuNjg3LTUuMzMtMjcuMTI3LTEyLjA3MS0zOC4wODYtMjEuOTk3LS4xNzQtLjE1Ny0uMzU2LS4zMTQtLjUyOC0uNDcyLS4wMTMtLjAxMi0uMDI1LS4wMjItLjAzOC0uMDM0djkwLjM1MmMwIDEzLjg3MiAxNi4xNzMgMjguMTMgNDQuMzczIDM5LjExNSAzMC45NTkgMTIuMDYgNzIuMjg2IDE4LjcwMiAxMTYuMzcyIDE4LjcwMnM4NS40MTQtNi42NDIgMTE2LjM3My0xOC43MDJjMjguMTk5LTEwLjk4NSA0NC4zNzItMjUuMjQxIDQ0LjM3Mi0zOS4xMTVoLjAwM3YtOTAuMzUzWm0tMjguMTc0IDgwLjg4M2MtNy45NDkgMC0xNC4zOTMtNi40MzgtMTQuMzkzLTE0LjM4MSAwLTcuOTQyIDYuNDQ0LTE0LjM4MSAxNC4zOTMtMTQuMzgxIDcuOTUgMCAxNC4zOTQgNi40MzkgMTQuMzk0IDE0LjM4MSAwIDcuOTQzLTYuNDQ0IDE0LjM4MS0xNC4zOTQgMTQuMzgxWm0tNDkuOTU2IDE1LjA0N2MtNy45NDkgMC0xNC4zOTMtNi40MzgtMTQuMzkzLTE0LjM4MSAwLTcuOTQyIDYuNDQ0LTE0LjM4MSAxNC4zOTMtMTQuMzgxIDcuOTQ5IDAgMTQuMzk0IDYuNDM5IDE0LjM5NCAxNC4zODEgMCA3Ljk0My02LjQ0NSAxNC4zODEtMTQuMzk0IDE0LjM4MVptLTUzLjAxMiA4LjIzN2MtNy45NDkgMC0xNC4zOTMtNi40MzgtMTQuMzkzLTE0LjM4MSAwLTcuOTQyIDYuNDQ0LTE0LjM4MSAxNC4zOTMtMTQuMzgxIDcuOTQ5IDAgMTQuMzkzIDYuNDM5IDE0LjM5MyAxNC4zODEgMCA3Ljk0My02LjQ0NCAxNC4zODEtMTQuMzkzIDE0LjM4MVptMTAyLjk2OC0xNDMuODc3Yy03Ljk0OSAwLTE0LjM5My02LjQzOS0xNC4zOTMtMTQuMzgxIDAtNy45NDMgNi40NDQtMTQuMzgxIDE0LjM5My0xNC4zODEgNy45NSAwIDE0LjM5NCA2LjQzOCAxNC4zOTQgMTQuMzgxIDAgNy45NDItNi40NDQgMTQuMzgxLTE0LjM5NCAxNC4zODFabS00OS45NTYgMTUuMDU3Yy03Ljk0OSAwLTE0LjM5My02LjQzOS0xNC4zOTMtMTQuMzgxIDAtNy45NDMgNi40NDQtMTQuMzgxIDE0LjM5My0xNC4zODEgNy45NDkgMCAxNC4zOTQgNi40MzggMTQuMzk0IDE0LjM4MSAwIDcuOTQyLTYuNDQ1IDE0LjM4MS0xNC4zOTQgMTQuMzgxWm0tNTMuMDEyIDguMjM3Yy03Ljk0OSAwLTE0LjM5My02LjQzOS0xNC4zOTMtMTQuMzgxIDAtNy45NDMgNi40NDQtMTQuMzgxIDE0LjM5My0xNC4zODEgNy45NDkgMCAxNC4zOTMgNi40MzggMTQuMzkzIDE0LjM4MSAwIDcuOTQyLTYuNDQ0IDE0LjM4MS0xNC4zOTMgMTQuMzgxWm0xMDIuOTY4LTE0NS45ODZjLTcuOTQ5IDAtMTQuMzkzLTYuNDM4LTE0LjM5My0xNC4zODEgMC03Ljk0MiA2LjQ0NC0xNC4zODEgMTQuMzkzLTE0LjM4MSA3Ljk1IDAgMTQuMzk0IDYuNDM5IDE0LjM5NCAxNC4zODEgMCA3Ljk0My02LjQ0NCAxNC4zODEtMTQuMzk0IDE0LjM4MVptLTQ5Ljk1NiAxNS4wNTdjLTcuOTQ5IDAtMTQuMzkzLTYuNDM4LTE0LjM5My0xNC4zODEgMC03Ljk0MiA2LjQ0NC0xNC4zODEgMTQuMzkzLTE0LjM4MSA3Ljk0OSAwIDE0LjM5NCA2LjQzOSAxNC4zOTQgMTQuMzgxIDAgNy45NDMtNi40NDUgMTQuMzgxLTE0LjM5NCAxNC4zODFabS01My4wMTIgOC4yMzdjLTcuOTQ5IDAtMTQuMzkzLTYuNDM4LTE0LjM5My0xNC4zODEgMC03Ljk0MiA2LjQ0NC0xNC4zODEgMTQuMzkzLTE0LjM4MSA3Ljk0OSAwIDE0LjM5MyA2LjQzOSAxNC4zOTMgMTQuMzgxIDAgNy45NDMtNi40NDQgMTQuMzgxLTE0LjM5MyAxNC4zODFaIi8+Cjwvc3ZnPg==
required_open_webui_version: 0.5.0
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from fastapi.requests import Request
from pathlib import Path
import os
import uuid
import time
import logging
import re
import httpx

from open_webui.models.files import FilesTable, FileForm

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Action:
    class Valves(BaseModel):
        show_status: bool = Field(
            default=True, description="Show status of the action."
        )
        target_url: str = Field(default="/hello", description="URL to open in new tab")
        html_filename_suffix: str = Field(default="hello_launcher.html")

    class UserValves(BaseModel):
        show_status: bool = Field(
            default=True, description="Show status of the action."
        )

    def __init__(self):
        self.valves = self.Valves()

    def _build_launcher_html(self) -> str:
        # Simple random HTML + JS that opens target_url in new tab
        url = self.valves.target_url
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Hello World Launcher</title>
</head>
<body>
  <h1>Hello World!</h1>
  <p>Opening {url} in a new tab...</p>
  <p><a href="{url}" target="_blank">Click here if nothing happens</a></p>
  <script>
    try {{
      window.open("{url}", "_blank", "noopener,noreferrer");
    }} catch(e) {{
      console.warn("window.open blocked:", e);
    }}
  </script>
</body>
</html>"""

    def _write_launcher_file(self, user_id: str, html_content: str) -> str:
        directory = "action_embed"
        base_path = os.path.join("uploads", directory)
        os.makedirs(base_path, exist_ok=True)

        # --- Clean up old files ---
        for f in Path(base_path).glob("*"):
            try:
                f.unlink()
            except Exception as e:
                print(f"Warning: could not delete old file {f}: {e}")

        # --- Create new file ---
        filename = f"{int(time.time()*1000)}_{self.valves.html_filename_suffix}"
        file_path = os.path.join(base_path, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        meta = {
            "source": file_path,
            "title": "Hello World Launcher",
            "content_type": "text/html",
            "size": os.path.getsize(file_path),
            "path": file_path,
        }

        # Create FileForm and insert via FilesTable
        form_data = FileForm(
            id=str(uuid.uuid4()),
            filename=f"{directory}/{user_id}/{filename}",
            path=file_path,
            meta=meta,
            data={},
        )

        new_file = FilesTable().insert_new_file(user_id, form_data)
        if not new_file:
            raise Exception("Failed to insert new file")

        return new_file.id

    def _replace_or_append_placeholder(self, content: str, new_file_id: str) -> str:
        new_tag = f"{{{{HTML_FILE_ID_{new_file_id}}}}}"
        # Try replacing an existing placeholder, otherwise append
        replaced, count = re.subn(r"\{\{HTML_FILE_ID_[^}]+\}\}", new_tag, content)
        if count > 0:
            return replaced
        else:
            return content + "\n\n" + new_tag

    def _toggle_placeholder(self, content: str, new_file_id: str) -> str:
        # Regex for any existing HTML_FILE_ID placeholder
        pattern = r"\{\{HTML_FILE_ID_[^}]+\}\}"
        if re.search(pattern, content):
            # ✅ If exists → remove it
            return re.sub(pattern, "", content).strip()
        else:
            # ✅ If not exists → append a new one
            new_tag = f"{{{{HTML_FILE_ID_{new_file_id}}}}}"
            return content + ("\n\n" if content.strip() else "") + new_tag

    def _toggle_global_placeholder(self, messages: list, new_file_id: str) -> list:
        """
        Remove all existing placeholders across all messages.
        Then toggle on/off in the last message only.
        """
        pattern = r"\{\{HTML_FILE_ID_[^}]+\}\}"

        # --- Remove all placeholders globally ---
        for msg in messages:
            msg["content"] = re.sub(pattern, "", msg["content"]).strip()

        # --- Toggle last message ---
        if not messages:
            return messages

        last_msg = messages[-1]
        if re.search(pattern, last_msg["content"]):
            # If last message had it → already removed in cleanup → stays off
            pass
        else:
            # If it didn’t → add a fresh one
            new_tag = f"{{{{HTML_FILE_ID_{new_file_id}}}}}"
            if last_msg["content"].strip():
                last_msg["content"] += "\n\n" + new_tag
            else:
                last_msg["content"] = new_tag

        return messages

    def _strip_all_placeholders(self, messages: list, pattern: str) -> None:
        """Remove all HTML_FILE_ID placeholders from every message, tidy whitespace."""
        for msg in messages:
            content = msg.get("content", "") or ""
            content = re.sub(pattern, "", content)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()
            msg["content"] = content

    async def _fetch_launcher_html(self, user_id: str, chat_id: str) -> str:
        url = f"http://127.0.0.1:8000/state/html/{user_id}/{chat_id}"
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0)
            ) as client:  # 30s timeout
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text
        except httpx.ReadTimeout:
            # fallback HTML if the backend is too slow
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
        chat_id = body["chat_id"]
        user_id = __user__["id"]
        user_valves = (__user__ or {}).get("valves") or self.UserValves()
        pattern = r"\{\{HTML_FILE_ID_[^}]+\}\}"

        try:
            # Determine ON vs OFF based on whether the last message *currently* has a placeholder
            messages = body.get("messages") or []
            if not messages:
                return body

            last_msg = messages[-1]
            last_content_before = last_msg.get("content", "") or ""
            last_had_before = bool(re.search(pattern, last_content_before))

            # Status: on/off intent
            if __event_emitter__ and user_valves.show_status:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": (
                                "Hiding HelloWorld page…"
                                if last_had_before
                                else "Opening HelloWorld page…"
                            ),
                            "done": False,
                        },
                    }
                )

            # 1) Remove ALL placeholders across ALL messages
            self._strip_all_placeholders(messages, pattern)

            # 2) If last had one → toggle OFF (do nothing further)
            #    If last did not → toggle ON (create new file + insert only in last message)
            if not last_had_before:
                user_id = (__user__ or {}).get("id", "anonymous")
                launcher_html = await self._fetch_launcher_html(user_id, chat_id)
                file_id = self._write_launcher_file(user_id, launcher_html)

                new_tag = f"{{{{HTML_FILE_ID_{file_id}}}}}"
                if last_msg["content"].strip():
                    last_msg["content"] += "\n\n" + new_tag
                else:
                    last_msg["content"] = new_tag

            if __event_emitter__ and user_valves.show_status:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Done." if last_had_before else "Launched.",
                            "done": True,
                        },
                    }
                )

        except Exception as e:
            logger.exception("Error in HelloWorld Action")
            if body.get("messages"):
                body["messages"][-1]["content"] = (
                    body["messages"][-1].get("content", "") or ""
                ) + f"\n\nError: {e}"
            if __event_emitter__ and user_valves.show_status:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Error during toggle", "done": True},
                    }
                )

        return body
