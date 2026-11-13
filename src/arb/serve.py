"""Serves the site folder at /jkm-ttf-arbitrage/, the path GitHub Pages uses: python -m arb.serve [port]"""

from __future__ import annotations

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import params

PREFIX = "/jkm-ttf-arbitrage"


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        if not path.startswith(PREFIX + "/"):
            return "/nonexistent"                 # anything outside the prefix is a 404, as on Pages
        return super().translate_path(path[len(PREFIX):])

    def do_GET(self):
        if self.path == PREFIX:
            self.send_response(301)
            self.send_header("Location", PREFIX + "/")
            self.end_headers()
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(params.ROOT / "site")))
    print("http://localhost:%d%s/" % (port, PREFIX))
    server.serve_forever()
