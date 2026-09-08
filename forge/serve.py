"""Forge HTTP surface — the two health boards over stdlib HTTP, token-gated.

  GET /                  landing with links to both boards
  GET /project           project board (HTML)
  GET /project.json      project board (machine JSON)
  GET /ecosystem         ecosystem board (HTML)
  GET /ecosystem.json    ecosystem board (machine JSON)
  GET /healthz           liveness (200, no token required)

Fail-closed design (mirrors the dashboards themselves):
  * NO random broadcast. The server binds the address passed at construction
    time; the CLI defaults to loopback and requires an explicit --host to
    expose on a tailnet/LAN address. 0.0.0.0 is refused.
  * Bearer auth is mandatory for every content route. The expected token is
    fixed at construction (from FORGE_TOKEN); a server configured without a
    token refuses to start rather than serving open. Comparisons use
    hmac.compare_digest (no timing oracle).
  * A board that refuses to build surfaces the reason as HTTP 503 with the
    refusal text — never a guess.

Pure stdlib: http.server + ssl not required (tailnet transport). Offline.
"""

from __future__ import annotations

import argparse
import hmac
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .dash import DashRefusal, _md_ecosystem, _md_project, ecosystem_board, project_board


class ServeRefusal(Exception):
    """Raised when the server cannot start or a route cannot be served."""


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _html_shell(title: str, body: str) -> bytes:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{_esc(title)}</title>"
        "<style>"
        "body{font-family:system-ui,sans-serif;margin:2rem auto;max-width:52rem;"
        "line-height:1.5;color:#1a1a1a;background:#fafafa}"
        "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left;font-size:.9rem}"
        "th{background:#eef1f4}code{background:#f0f0f0;padding:.1rem .3rem;border-radius:3px}"
        ".bad{color:#b00020}.ok{color:#187a2f}.muted{color:#777}"
        "nav a{margin-right:1rem}"
        "footer{margin-top:3rem;color:#777;font-size:.8rem;border-top:1px solid #ddd;padding-top:1rem}"
        "</style></head><body>"
        f"{body}<footer>forge {_esc(__import__('forge').__version__)} · "
        "bastion-host · token-gated</footer></body></html>"
    ).encode("utf-8")


def _html_project(board: dict) -> bytes:
    t, c = board["tasks"], board["corpus"]
    by = t["by_status"]
    integrity = "ok" if board["journal_integrity"] is True else str(board["journal_integrity"])
    body = [
        "<h1>Forge Project Board</h1>",
        f"<p class='muted'>Journal <code>{_esc(board['journal'])}</code> · "
        f"integrity <code>{_esc(integrity)}</code></p>",
        "<table><tr><th>metric</th><th>value</th></tr>",
        f"<tr><td>tasks total</td><td>{t['total']}</td></tr>",
        f"<tr><td>merged</td><td>{t['merged']} ({t['merged_pct']}%)</td></tr>",
        f"<tr><td>queued</td><td>{by['queued']}</td></tr>",
        f"<tr><td>retrieving</td><td>{by['retrieving']}</td></tr>",
        f"<tr><td>building</td><td>{by['building']}</td></tr>",
        f"<tr><td>reviewing</td><td>{by['reviewing']}</td></tr>",
        f"<tr><td>changes_requested</td><td>{by['changes_requested']}</td></tr>",
        f"<tr><td>blocked</td><td>{by['blocked']}</td></tr>",
        "</table>",
    ]
    if t["blockeds_with_reason"]:
        body.append("<h2>Blocked (never resurrect, reason required)</h2><ul>")
        for b in t["blockeds_with_reason"]:
            body.append(f"<li><code>{_esc(b['id'])}</code> <span class='muted'>"
                        f"[{_esc(b['repo'])}]</span> — {_esc(b['reason'])}</li>")
        body.append("</ul>")
    if c["loaded"]:
        vc = "n/a (no repo-root)" if c["verified_citations"] is None else c["verified_citations"]
        body.append(f"<h2>Builder corpus</h2><p>{c['patterns']} patterns, "
                    f"{_esc(vc)} citations proof-read</p>")
    else:
        body.append("<h2>Builder corpus</h2><p class='muted'>not loaded (path absent)</p>")
    return _html_shell("Forge Project Board", "\n".join(body))


def _html_ecosystem(board: dict) -> bytes:
    rows = ["<table><tr><th>repo</th><th>head</th><th>signed</th><th>version</th>"
            "<th>top sections</th><th>problems</th></tr>"]
    for r in board["repos"]:
        signed = "G" if r["signed"] == "G" else (r["signed"] or "n/a")
        cls = "" if r["signed"] == "G" else "bad"
        probs = "none" if not r["problems"] else "; ".join(r["problems"])
        rows.append(
            f"<tr><td>{_esc(r['name'])}</td><td><code>{_esc(r['head'] or 'n/a')}</code></td>"
            f"<td class='{cls}'>{_esc(signed)}</td><td>{_esc(r['version'] or '—')}</td>"
            f"<td>{_esc(r['top_release_sections'] or '—')}</td>"
            f"<td class='{'bad' if r['problems'] else 'ok'}'>{_esc(probs)}</td></tr>"
        )
    rows.append("</table>")
    body = [
        "<h1>Forge Ecosystem Board</h1>",
        "<p class='muted'>Read from each repo's own pristine CHANGELOG.md "
        "(documentation doctrine).</p>",
        "\n".join(rows),
    ]
    return _html_shell("Forge Ecosystem Board", "\n".join(body))


def _render_raw(text: str) -> bytes:
    return ("<pre>" + html.escape(text, quote=False) + "</pre>").encode("utf-8")


class ForgeHandler(BaseHTTPRequestHandler):
    """Token-gated HTTP handler. The expected token + board configs are pinned
    on the instance by serve() before the thread starts."""

    expected_token: str = ""
    journal: str = ""
    corpus: str = ""
    repo_root: str = ""
    roots: list[str] = []

    server_version = "forge"
    sys_version = ""

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def _authorized(self) -> bool:
        auth = self.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        return bool(token) and hmac.compare_digest(token, self.expected_token)

    def _send(self, status: int, ctype: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, "application/json", json.dumps(payload).encode("utf-8"))

    def _deny(self, status: int, reason: str) -> None:
        self._json(status, {"error": reason})

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/healthz":
            self._send(200, "text/plain", b"ok")
            return
        if not self._authorized():
            self._deny(401, "bearer token required")
            return

        if self.path in ("/", "/project", "/ecosystem"):
            if self.path == "/ecosystem":
                board = self._ecosystem()
                if not isinstance(board, dict):
                    return
                self._send(200, "text/html; charset=utf-8", _html_ecosystem(board))
                return
            if self.path == "/project":
                board = self._project()
                if not isinstance(board, dict):
                    return
                self._send(200, "text/html; charset=utf-8", _html_project(board))
                return
            links = ("<nav><a href='/project'>Project board</a>"
                     "<a href='/ecosystem'>Ecosystem board</a></nav>")
            self._send(200, "text/html; charset=utf-8",
                       _html_shell("Forge", f"<h1>Forge</h1>{links}"))
            return

        if self.path in ("/project.json", "/ecosystem.json"):
            if self.path == "/ecosystem.json":
                board = self._ecosystem()
                if not isinstance(board, dict):
                    return
                self._json(200, board)
                return
            board = self._project()
            if not isinstance(board, dict):
                return
            self._json(200, board)
            return

        self._deny(404, f"no route: {self.path}")

    def _project(self) -> dict:
        try:
            return project_board(self.journal, self.corpus, self.repo_root)
        except (OSError, ValueError, DashRefusal) as exc:
            self._deny(503, f"board refused: {exc}")
            return {}

    def _ecosystem(self) -> dict:
        try:
            return ecosystem_board(self.roots)
        except (OSError, DashRefusal) as exc:
            self._deny(503, f"board refused: {exc}")
            return {}


def serve(journal: str, corpus: str, repo_root: str, roots: list[str],
          token: str, host: str = "127.0.0.1", port: int = 8443) -> ThreadingHTTPServer:
    """Start the forge HTTP surface. Refuses (ServeRefusal) on: missing token,
    or a 0.0.0.0/:: broadcast bind."""
    if not token:
        raise ServeRefusal("FORGE_TOKEN is not set — refusing to serve without auth")
    if host in ("0.0.0.0", "::"):
        raise ServeRefusal(f"refusing to bind broadcast address {host!r}; "
                           "bind a specific interface (loopback or tailnet IP)")

    ForgeHandler.expected_token = token
    ForgeHandler.journal = journal
    ForgeHandler.corpus = corpus
    ForgeHandler.repo_root = repo_root
    ForgeHandler.roots = roots

    srv = ThreadingHTTPServer((host, port), ForgeHandler)
    srv.daemon_threads = True
    return srv


def cmd_serve(args: argparse.Namespace) -> int:
    token = args.token or os.environ.get("FORGE_TOKEN", "")
    journal = args.journal or os.environ.get("FORGE_JOURNAL",
                                             os.path.expanduser("~/.forge/tasks.jsonl"))
    host = args.host or "127.0.0.1"
    try:
        srv = serve(journal=journal, corpus=args.corpus, repo_root=args.repo_root,
                    roots=args.roots or [], token=token, host=host, port=args.port)
    except ServeRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    bound = srv.server_address[0]
    print(f"forge http on http://{bound}:{srv.server_address[1]} "
          f"(root /, project /project, ecosystem /ecosystem, healthz /healthz)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="forge serve", description="Serve the forge boards over HTTP")
    p.add_argument("--journal", help="path to tasks.jsonl (default FORGE_JOURNAL or ~/.forge)")
    p.add_argument("--corpus", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs/corpus/builder-corpus.json"),
        help="builder corpus path")
    p.add_argument("--repo-root", help="repo checkout for citation proof-read (optional)")
    p.add_argument("--roots", nargs="+", help="repo checkouts for the ecosystem board")
    p.add_argument("--token", help="bearer token (default FORGE_TOKEN env)")
    p.add_argument("--host", default="127.0.0.1", help="bind address (default loopback)")
    p.add_argument("--port", type=int, default=8443)
    return cmd_serve(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())