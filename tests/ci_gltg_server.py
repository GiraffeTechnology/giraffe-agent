"""Standalone GLTG mock server for CI E2E scripts.

Serves the GLTG HTTP API on localhost using the deterministic `route()` from
`tests.gltg_fake`, so CI scripts that exercise GLTG-backed code (feasibility,
rollup, RFQ flows) work without the real GLTG service or any secrets.

This is CI/test infrastructure only -- not product code, not a runtime fallback.
Production always talks to the real standalone GLTG service.

Usage:
    python tests/ci_gltg_server.py [port]   # default 8090
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")
from tests.gltg_fake import route  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        status, payload = route("GET", self.path, None)
        self._send(status, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode() or "{}")
        status, payload = route("POST", self.path, body)
        self._send(status, payload)

    def log_message(self, *args) -> None:  # silence access logs
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    print(f"CI GLTG mock server listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
