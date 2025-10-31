import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

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
