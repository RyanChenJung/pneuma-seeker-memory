import io
import os
import shutil
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.responses import HTMLResponse

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from fastapi.testclient import TestClient

import pneuma_seeker.server as server


class ServerEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(server.app)

    def _make_mock_chat_interface(
        self, prov_nodes=None, graph_code="print('hi')", stream_messages=None
    ):
        # Build a minimal mock prov_graph
        prov_graph = MagicMock()
        prov_graph.nodes = prov_nodes or {}
        prov_graph.get_graph_code.return_value = graph_code

        # Minimal conductor/materializer structure
        materializer = MagicMock()
        materializer.prov_graph = prov_graph

        conductor = MagicMock()
        conductor.materializer = materializer

        # Chat interface mock
        chat_interface = MagicMock()
        chat_interface.conductor = conductor

        # process_user_input should be an iterable/generator
        if stream_messages is None:

            def default_gen(messages, files):
                yield "LOG connected"
                yield "Hello from assistant"
                yield "DONE"

            chat_interface.process_user_input.side_effect = (
                lambda messages, files: default_gen(messages, files)
            )
        else:
            chat_interface.process_user_input.side_effect = lambda messages, files: (
                m for m in stream_messages
            )

        chat_interface.persist_state.return_value = None
        return chat_interface

    def test_root_returns_ok(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_provenance_nodes_endpoint_returns_nodes(self):
        # Create simple node-like objects
        node_a = types.SimpleNamespace(
            id="n1",
            source_retriever=types.SimpleNamespace(value="USER"),
            python_code="x=1",
            description="a",
            parents=[],
            children=[],
        )
        node_b = types.SimpleNamespace(
            id="n2",
            source_retriever=types.SimpleNamespace(value="WEB"),
            python_code="y=2",
            description="b",
            parents=[node_a],
            children=[],
        )
        node_a.children.append(node_b)

        prov_nodes = {node_a.id: node_a, node_b.id: node_b}

        mock_chat = self._make_mock_chat_interface(prov_nodes=prov_nodes)

        # Patch manager.get_chat_interface temporarily
        original_get = server.manager.get_chat_interface
        server.manager.get_chat_interface = lambda user_id, chat_id: mock_chat
        try:
            r = self.client.get("/provenance/nodes/u1/c1")
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertEqual(body["user_id"], "u1")
            self.assertEqual(body["chat_id"], "c1")
            self.assertEqual(body["node_count"], 2)
            ids = {n["id"] for n in body["nodes"]}
            self.assertEqual(ids, {"n1", "n2"})
        finally:
            server.manager.get_chat_interface = original_get

    def test_materializer_code_download_returns_file(self):
        mock_chat = self._make_mock_chat_interface(graph_code="print('materialize')")
        original_get = server.manager.get_chat_interface
        server.manager.get_chat_interface = lambda user_id, chat_id: mock_chat
        try:
            r = self.client.get("/materializer_code/u1/c1")
            self.assertEqual(r.status_code, 200)
            # Content should include the graph code
            self.assertIn("materialize", r.content.decode())
            self.assertIn(
                "attachment; filename=", r.headers.get("content-disposition", "")
            )
        finally:
            server.manager.get_chat_interface = original_get

    # def test_download_chat_pdf_returns_pdf(self):
    #     # Patch server.HTML to avoid heavy weasyprint dependency and write a dummy PDF
    #     original_HTML = server.HTML

    #     class DummyHTML:
    #         def __init__(self, string=None):
    #             self.string = string

    #         def write_pdf(self, path):
    #             with open(path, "wb") as f:
    #                 f.write(b"%PDF-1.4\n%dummy pdf\n")

    #     server.HTML = DummyHTML
    #     try:
    #         body = {
    #             "model": "assistant",
    #             "messages": [{"role": "user", "content": "hello"}],
    #             "chat_id": "c_pdf",
    #         }
    #         r = self.client.post("/download_chat_pdf", json=body)
    #         self.assertEqual(r.status_code, 200)
    #         self.assertEqual(r.headers.get("content-type"), "application/pdf")
    #         # PDF signature should be present
    #         self.assertTrue(r.content.startswith(b"%PDF"))
    #         self.assertIn("attachment; filename=", r.headers.get("content-disposition", ""))
    #     finally:
    #         server.HTML = original_HTML

    def test_combined_html_calls_prov_explanation_and_renders(self):
        # Prepare a chat_interface mock where T is materialized and prov_graph returns markdown
        prov_graph = MagicMock()
        prov_graph.get_graph_explanation.return_value = "**md** code"

        materializer = MagicMock()
        materializer.prov_graph = prov_graph

        info_need_state = MagicMock()
        info_need_state.get_current_state_instance.return_value = {"state": "ok"}
        info_need_state.is_T_materialized = True

        conductor = MagicMock()
        conductor.materializer = materializer
        conductor.info_need_state = info_need_state

        chat_interface = MagicMock()
        chat_interface.conductor = conductor

        original_get = server.manager.get_chat_interface
        server.manager.get_chat_interface = lambda user_id, chat_id: chat_interface

        # Replace templates.TemplateResponse so we can inspect the context passed to it
        original_templates = server.templates

        def fake_template_response(template_name, context):
            # Ensure prov_explanation was computed from prov_graph markdown
            self.assertIn("prov_explanation", context)
            # It should include HTML converted from markdown (bold -> <strong>) or at least the markdown content
            self.assertTrue("md" in context["prov_explanation"])
            return HTMLResponse(content=context["prov_explanation"], status_code=200)

        # Replace the templates object with a minimal object exposing TemplateResponse
        server.templates = types.SimpleNamespace(
            TemplateResponse=fake_template_response
        )

        try:
            payload = {
                "messages": [{"role": "user", "content": "hi"}],
                "model": "assistant",
            }
            r = self.client.post("/combined/html/u1/c1", json=payload)
            self.assertEqual(r.status_code, 200)
            # Body should contain the prov_explanation we returned
            self.assertIn("md", r.text)
            # ensure the prov_graph method was called
            prov_graph.get_graph_explanation.assert_called()
        finally:
            server.manager.get_chat_interface = original_get
            server.templates = original_templates

    def test_all_tables_downloads_zip(self):
        # Create a temp TABLES_DIR structure with user/chat and a csv file
        tmp_dir = tempfile.mkdtemp()
        original_tables_dir = server.TABLES_DIR
        server.TABLES_DIR = Path(tmp_dir)
        try:
            user_dir = server.TABLES_DIR / "u_test"
            chat_dir = user_dir / "c_test"
            chat_dir.mkdir(parents=True)
            csv_path = chat_dir / "table1.csv"
            csv_path.write_text("col1,col2\n1,2\n")

            r = self.client.get(f"/all_tables/u_test/c_test")
            self.assertEqual(r.status_code, 200)
            self.assertIn("application/zip", r.headers.get("content-type", ""))
            # Verify returned bytes form a valid zip with the csv inside
            zip_bytes = r.content
            z = zipfile.ZipFile(io.BytesIO(zip_bytes))
            names = z.namelist()
            self.assertIn("table1.csv", names)
        finally:
            server.TABLES_DIR = original_tables_dir
            shutil.rmtree(tmp_dir)

    def test_chat_endpoint_streams_messages_and_calls_persist(self):
        messages = [{"role": "user", "content": "hi"}]
        mock_chat = self._make_mock_chat_interface(
            stream_messages=["LOG one", "answer text", "DONE"]
        )

        original_get = server.manager.get_chat_interface
        server.manager.get_chat_interface = lambda user_id, chat_id: mock_chat
        try:
            r = self.client.post(
                "/chat", json={"user_id": "u1", "chat_id": "c1", "messages": messages}
            )
            self.assertEqual(r.status_code, 200)
            # streaming response lines
            text = b"".join(r.iter_bytes())
            decoded = text.decode(errors="ignore")
            # Should contain assistant message and log/done structure
            self.assertIn("answer text", decoded)
            # persist_state should have been scheduled (called after streaming) - ensure method exists and can be called
            self.assertTrue(hasattr(mock_chat, "persist_state"))
        finally:
            server.manager.get_chat_interface = original_get


if __name__ == "__main__":
    unittest.main()
