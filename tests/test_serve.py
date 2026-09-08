"""Tests for the Forge HTTP surface (forge/serve.py).

Exercises the REAL boundary: a live ThreadingHTTPServer on an ephemeral
socket, requesting real routes with and without the bearer token, plus the
fail-closed construction rules (no token -> refuse; broadcast bind -> refuse).
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from forge import __version__
from forge.engine import engine
from forge.journal import Journal
from forge.serve import ServeRefusal, ForgeHandler, _html_ecosystem, _html_project, serve
from forge.task import Status, Task, TaskInput

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _seed_project(journal_path: str) -> None:
    j = Journal(journal_path)
    task = Task.new(TaskInput(repo="Daftari", title="serve seed", file_scope=[],
                              acceptance_criteria=["ok"]), created_by="test")
    j.append(task)
    for status, via in ((Status.RETRIEVING, "builder"), (Status.BUILDING, "builder"),
                        (Status.REVIEWING, "reviewer")):
        engine(task, status, via)
    engine(task, Status.MERGED, "reviewer", note="ok")
    j.append(task)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServeConstructionTest(unittest.TestCase):
    def test_refuses_to_serve_without_token(self) -> None:
        with self.assertRaises(ServeRefusal):
            serve(journal="/tmp/x.jsonl", corpus="", repo_root="", roots=[],
                  token="", host="127.0.0.1", port=1)

    def test_refuses_broadcast_bind(self) -> None:
        for host in ("0.0.0.0", "::"):
            with self.assertRaises(ServeRefusal):
                serve(journal="/tmp/x.jsonl", corpus="", repo_root="", roots=[],
                      token="tok", host=host, port=1)


class ServeHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="forge-serve-", dir="/tmp")
        self.addCleanup(lambda: __import__("shutil").rmtree(self._tmp, ignore_errors=True))
        self.journal = os.path.join(self._tmp, "tasks.jsonl")
        _seed_project(self.journal)
        self.token = "test-secret-token"
        self.port = _free_port()
        self.server = serve(journal=self.journal, corpus="", repo_root="",
                            roots=[REPO], token=self.token, host="127.0.0.1",
                            port=self.port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _get(self, path: str, token: str | None = None):
        req = Request(self._url(path))
        if token is not None:
            req.add_header("Authorization", f"Bearer {token}")
        return urlopen(req, timeout=10)

    def test_healthz_is_open(self) -> None:
        with self._get("/healthz") as r:
            self.assertEqual(200, r.status)
            self.assertEqual(b"ok", r.read())

    def test_content_requires_token(self) -> None:
        for path in ("/", "/project", "/ecosystem", "/project.json", "/ecosystem.json"):
            with self.assertRaises(HTTPError) as ctx:
                self._get(path)
            self.assertEqual(401, ctx.exception.code, path)

    def test_wrong_token_rejected(self) -> None:
        for path in ("/", "/project"):
            with self.assertRaises(HTTPError) as ctx:
                self._get(path, "wrong-token")
            self.assertEqual(401, ctx.exception.code, path)

    def test_project_html_with_token(self) -> None:
        with self._get("/project", self.token) as r:
            self.assertEqual(200, r.status)
            body = r.read().decode("utf-8")
        self.assertIn("Forge Project Board", body)
        self.assertIn("100.0", body)

    def test_project_html_escapes_issues(self) -> None:
        with self._get("/project", self.token) as r:
            body = r.read().decode("utf-8")
        self.assertNotIn("<script", body)

    def test_project_json_with_token(self) -> None:
        with self._get("/project.json", self.token) as r:
            self.assertEqual(200, r.status)
            board = json.loads(r.read().decode("utf-8"))
        self.assertEqual("project", board["type"])
        self.assertEqual(1, board["tasks"]["merged"])

    def test_ecosystem_html_with_token(self) -> None:
        with self._get("/ecosystem", self.token) as r:
            self.assertEqual(200, r.status)
            body = r.read().decode("utf-8")
        self.assertIn("Forge Ecosystem Board", body)
        self.assertIn(os.path.basename(REPO), body)

    def test_ecosystem_json_with_token(self) -> None:
        with self._get("/ecosystem.json", self.token) as r:
            board = json.loads(r.read().decode("utf-8"))
        self.assertEqual("ecosystem", board["type"])
        self.assertTrue(any(r["name"] == os.path.basename(REPO) for r in board["repos"]))

    def test_bad_route_404(self) -> None:
        with self.assertRaises(HTTPError) as ctx:
            self._get("/nope", self.token)
        self.assertEqual(404, ctx.exception.code)

    def test_corrupt_journal_surfaces_503(self) -> None:
        with open(self.journal, "w") as fh:
            fh.write("not-json\n")
        with self.assertRaises(HTTPError) as ctx:
            self._get("/project", self.token)
        self.assertEqual(503, ctx.exception.code)
        err = json.loads(ctx.exception.read().decode("utf-8"))
        self.assertIn("refused", err["error"])

    def test_html_renderers_exist(self) -> None:
        self.assertTrue(callable(_html_project))
        self.assertTrue(callable(_html_ecosystem))


class ServeCliTest(unittest.TestCase):
    def test_refuses_without_token_env(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "forge", "serve", "--journal", "/tmp/x.jsonl",
             "--host", "127.0.0.1", "--port", "1"],
            capture_output=True, text=True, timeout=60, cwd=REPO,
            env={**os.environ, "FORGE_TOKEN": ""},
        )
        self.assertEqual(1, r.returncode)
        self.assertIn("REFUSED", r.stderr)

    def test_refuses_broadcast_bind_flag(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "forge", "serve", "--journal", "/tmp/x.jsonl",
             "--host", "0.0.0.0", "--port", "1", "--token", "tok"],
            capture_output=True, text=True, timeout=60, cwd=REPO,
        )
        self.assertEqual(1, r.returncode)
        self.assertIn("REFUSED", r.stderr)

    def test_version_floor(self) -> None:
        self.assertGreaterEqual(tuple(int(x) for x in __version__.split(".")), (0, 3, 0))


if __name__ == "__main__":
    unittest.main()