#!/usr/bin/env python3
"""
Tiny static file server for local preview.

    python3 scripts/serve.py [port]     ->  http://localhost:4173

Serves the project root explicitly rather than the working directory, because
`python3 -m http.server` resolves its default from os.getcwd() at import time,
which some sandboxes refuse.
"""

import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4173


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Always hit disk while developing, so edits show up on reload.
        self.send_header("Cache-Control", "no-store")
        SimpleHTTPRequestHandler.end_headers(self)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    os.chdir(os.sep)  # keep os.getcwd() off any restricted path
    handler = partial(Handler, directory=ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    sys.stderr.write("serving %s on http://localhost:%d\n" % (ROOT, PORT))
    server.serve_forever()


if __name__ == "__main__":
    main()
