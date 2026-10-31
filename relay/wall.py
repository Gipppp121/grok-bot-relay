"""Serve the terminal wall. This is the only HTML in the project."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def web_root() -> Path:
    package_root = Path(__file__).resolve().parent.parent
    candidate = package_root / "web" / "index.html"
    if candidate.exists():
        return candidate.parent
    cwd_candidate = Path.cwd() / "web" / "index.html"
    if cwd_candidate.exists():
        return cwd_candidate.parent
    raise FileNotFoundError("web/index.html is missing")


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    directory = web_root()
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = make_server(host, port)
    bound_host, bound_port = server.server_address[:2]
    print(f"serving web/index.html at http://{bound_host}:{bound_port}/")
    print("ctrl+c stops the wall. press f in the page for fullscreen.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nwall stopped")
    finally:
        server.server_close()
