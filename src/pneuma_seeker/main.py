# src/pneuma_seeker/main.py
import asyncio
import io
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any

import markdown
import markdown2
from anyio import to_thread
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from pneuma_seeker.session_manager import SessionManager
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.logger import setup_logger
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage


app = FastAPI(title="Pneuma-Seeker")
logger = setup_logger("Core Service")
config = Config("../../.env")
session_manager = SessionManager(
    config,
    logger,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = (
    Path(__file__).resolve().parents[2]
)  # go up from /src/pneuma_seeker/main.py → project root
TABLES_DIR = BASE_DIR / "data_src" / "target_tables"

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

# Helper functions
def now_ms() -> int:
    """Returns the current time in milliseconds."""
    return int(datetime.now().timestamp() * 1000)


def stream_payload(sender: str, text: str) -> str:
    """Formats a message payload for streaming responses."""
    return (
        json.dumps(
            {
                "sender": sender,
                "text": text,
                "time_stamp": now_ms(),
            }
        )
        + "\n"
    )

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/provenance/nodes/{user_id}/{chat_id}", response_class=JSONResponse)
async def get_provenance_nodes(request: Request, user_id: str, chat_id: str):
    """
    Return all nodes of the provenance graph for a given user and chat.
    """
    # Get the provenance graph instance
    chat_session = session_manager.get_chat_session(user_id, chat_id)
    prov_graph = chat_session.conductor.materializer.prov_graph

    # Convert all nodes to JSON-serializable format
    nodes_json = []
    for node in prov_graph.nodes.values():
        nodes_json.append(
            {
                "id": node.id,
                "source_retriever": getattr(
                    node.source_retriever, "value", str(node.source_retriever)
                ),
                "python_code": node.python_code,
                "description": node.description,
                "parents": [p.id for p in node.parents],
                "children": [c.id for c in node.children],
            }
        )

    return JSONResponse(
        content={
            "user_id": user_id,
            "chat_id": chat_id,
            "node_count": len(nodes_json),
            "nodes": nodes_json,
        }
    )


@app.post("/download_chat_pdf")
async def download_chat_pdf(data: dict):
    from weasyprint import HTML

    model = data["model"]
    messages = data["messages"]
    chat_id = data["chat_id"]

    html_messages = ""
    for msg in messages:
        role = "User" if msg["role"] == "user" else model.capitalize()
        color = "#f2f2f2" if msg["role"] == "user" else "#e8f0fe"
        content_html = markdown2.markdown(msg["content"])
        html_messages += f"""
            <div style="margin-bottom: 16px; padding: 10px; border-radius: 10px; background-color: {color}">
                <strong>{role}:</strong><br>{content_html}
            </div>
        """

    full_html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: sans-serif;
                    margin: 40px;
                    background-color: #ffffff;
                }}
                h1 {{
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <h2>Chat Transcript</h2>
            <h3>Chat ID: {chat_id}</h3>
            {html_messages}
        </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        HTML(string=full_html).write_pdf(tmp_file.name)
        return FileResponse(
            tmp_file.name, filename=f"chat_{chat_id}.pdf", media_type="application/pdf"
        )


@app.post("/combined/html/{user_id}/{chat_id}", response_class=HTMLResponse)
async def read_combined_html(request: Request, user_id: str, chat_id: str, data: dict):
    conductor = session_manager.get_chat_session(user_id, chat_id).conductor
    state = conductor.info_need_state.get_current_state_instance()

    base_url = str(request.base_url).rstrip("/")
    script_download_link = f"{base_url}/materializer_code/{user_id}/{chat_id}"

    prov_explanation = "<strong>T</strong> is not materialized yet."
    if conductor.info_need_state.is_T_materialized:
        prov_explanation_markdown = (
            conductor.materializer.prov_graph.get_graph_explanation(
                script_download_link=script_download_link
            )
        )
        prov_explanation = markdown.markdown(
            prov_explanation_markdown, extensions=["fenced_code"]
        )

    messages = data.get("messages", [])
    model = data.get("model", "assistant")

    return templates.TemplateResponse(
        "state_view.html",
        {
            "request": request,
            "state": state,
            "prov_explanation": prov_explanation,
            "user_id": user_id,
            "chat_id": chat_id,
            "model": model,
            "messages": messages,
        },
    )


@app.post("/chat")
async def chat(request: Request):
    body: dict[str, Any] = await request.json()
    user_id: str = body.get("user_id", "default_user")
    chat_id: str = body.get("chat_id", "default_chat")
    messages = body.get("messages", [])
    files = body.get("files", [])

    llm_messages: list[LLMMessage] = []
    for msg in messages:
        llm_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

    chat_session = session_manager.get_chat_session(user_id, chat_id)

    async def event_stream():
        start = datetime.now().timestamp()

        yield stream_payload("log", "Pneuma connected. Starting processing...")
        await asyncio.sleep(0)

        response_queue: Queue[str | None] = Queue()

        def run_chat():
            try:
                for msg in chat_session.chat(llm_messages, files):
                    response_queue.put(msg)
            finally:
                response_queue.put(None)

        producer = asyncio.create_task(
            to_thread.run_sync(run_chat, abandon_on_cancel=True)
        )

        try:
            while True:
                try:
                    response = await to_thread.run_sync(response_queue.get)

                    if response is None:
                        break

                    if response.startswith("LOG"):
                        payload = stream_payload("log", response)
                    elif response.startswith("DONE"):
                        payload = stream_payload(
                            "done",
                            f"Processing done in {datetime.now().timestamp() - start:.2f}s.",
                        )
                    else:
                        payload = stream_payload("assistant", response)

                    yield payload
                    await asyncio.sleep(0)
                except Exception as e:
                    break
        finally:
            chat_session.persist_session()
            producer.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@app.get("/all_tables/{user_id}/{chat_id}")
def download_all_tables(user_id: str, chat_id: str):
    """
    Download all tables (CSV files) for a given user and chat as a ZIP file.
    Example: /tables/u123/c45/all
    """
    user_dir = TABLES_DIR / user_id
    chat_dir = user_dir / chat_id

    # Check existence of user and chat directories
    if not user_dir.exists():
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    if not chat_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Chat '{chat_id}' not found for user '{user_id}'"
        )

    # Gather all CSV files
    csv_files = list(chat_dir.glob("*.csv"))
    if not csv_files:
        raise HTTPException(status_code=404, detail="No tables found for this chat")

    # Create a ZIP file in memory (no temp file needed)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for csv_path in csv_files:
            # The arcname ensures zip has clean folder structure (just filenames)
            zipf.write(csv_path, arcname=csv_path.name)

    zip_buffer.seek(0)

    # Stream the zip file to the client
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={user_id}_{chat_id}_tables.zip"
        },
    )


@app.get("/materializer_code/{user_id}/{chat_id}")
def download_materializer_code(user_id: str, chat_id: str):
    """
    Downloads Materializer code (.py) generated for a given user and chat.
    """
    chat_session = session_manager.get_chat_session(user_id, chat_id)
    materializer_code = (
        chat_session.conductor.materializer.prov_graph.get_graph_code()
    )

    file_stream = io.BytesIO()
    file_stream.write(materializer_code.encode("utf-8"))
    file_stream.seek(0)

    filename = f"materializer_{user_id}_{chat_id}.py"
    return StreamingResponse(
        file_stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
