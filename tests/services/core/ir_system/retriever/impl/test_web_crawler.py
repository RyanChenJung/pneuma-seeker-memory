import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../src"))
)

import requests

from pneuma_seeker.services.core.ir_system.retriever.impl.web_crawler import WebCrawler
from pneuma_seeker.services.core.ir_system.data_model import RetrieverType, Text


class WebSearchTests(unittest.TestCase):
    def setUp(self):
        # Simple config object with a max char limit
        self.config = SimpleNamespace(WEB_CRAWL_MAX_CHARS=1000)
        self.models = None

    def _mock_response(self, status_code=200, text=""):
        mock = Mock()
        mock.status_code = status_code
        mock.text = text

        def raise_for_status():
            if not (200 <= status_code < 300):
                raise requests.HTTPError(f"status {status_code}")

        mock.raise_for_status = raise_for_status
        return mock

    @patch("requests.Session.get")
    def test_retrieve_success(self, mock_get):
        """When robots.txt is inaccessible (404) and page returns HTML, retrieve returns Text doc."""

        robots_resp = self._mock_response(status_code=404, text="")
        page_html = (
            "<html><body><h1>Example Domain</h1><p>This is example</p></body></html>"
        )
        page_resp = self._mock_response(status_code=200, text=page_html)

        # session.get will be called twice: once for robots.txt, once for the page
        mock_get.side_effect = [robots_resp, page_resp]

        crawler = WebCrawler(self.models, self.config)
        results = crawler.retrieve("http://www.example.com", [], 1, False)

        # Should return a list with one Text document
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        doc = results[0]
        self.assertIsInstance(doc, Text)
        self.assertEqual(doc.doc_id, "web_crawl")
        self.assertEqual(doc.retriever_type, RetrieverType.WEB_CRAWL)
        self.assertIn("Example Domain", doc.content)

    @patch("requests.Session.get")
    def test_retrieve_blocked_by_robots(self, mock_get):
        """When robots.txt disallows the path, retrieve returns a disallow message."""

        # robots.txt disallows everything
        robots_text = "User-agent: *\nDisallow: /"
        robots_resp = self._mock_response(status_code=200, text=robots_text)

        mock_get.return_value = robots_resp

        crawler = WebCrawler(self.models, self.config)
        out = crawler.retrieve("http://www.example.com/anypath", [], 1)

        # When disallowed, retrieve returns a string error message
        self.assertIsInstance(out, str)
        self.assertIn("disallowed by robots.txt", out)


if __name__ == "__main__":
    unittest.main()
