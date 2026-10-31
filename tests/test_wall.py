"""The wall is the only HTML, served from docs/index.html."""

from __future__ import annotations

import threading
import unittest
import urllib.request
from pathlib import Path

from relay.adapters.github import GitHubHook
from relay.adapters.seeded import SeededRepo
from relay.adapters.x_search import XSearchHook
from relay.demo_data import IDEAS
from relay.wall import make_server

REPO = Path(__file__).resolve().parents[1]


class WallTests(unittest.TestCase):
    def test_pages_copy_matches_and_server_returns_it(self) -> None:
        docs = (REPO / "docs" / "index.html").read_bytes()
        self.assertFalse((REPO / "web" / "index.html").exists())
        self.assertIn(b"<title>grok bot</title>", docs)
        png = (REPO / "assets" / "wall.png").read_bytes()
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        server = make_server("127.0.0.1", 0)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
                body = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(body, docs)
        finally:
            server.shutdown()
            server.server_close()

    def test_network_hooks_fail_closed(self) -> None:
        with self.assertRaises(RuntimeError):
            XSearchHook().search("launch", 5)
        with self.assertRaises(RuntimeError):
            GitHubHook().merge(1)
        with self.assertRaises(RuntimeError):
            SeededRepo().merge(1)
        plan = SeededRepo().plan(IDEAS[0])
        self.assertFalse(plan["merge"])
        self.assertTrue(plan["branch"].startswith("relay/idea-01-"))


class TextHygieneTests(unittest.TestCase):
    def test_no_em_or_en_dash(self) -> None:
        bad = []
        for path in REPO.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() in {".png", ".pyc"}:
                continue
            data = path.read_bytes()
            if b"\xe2\x80\x94" in data or b"\xe2\x80\x93" in data:
                bad.append(str(path.relative_to(REPO)))
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
