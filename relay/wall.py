"""Serve the terminal wall. This is the only HTML in the project."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _index_pages(root: Path):
    # docs/index.html is the single copy (GitHub Pages and the local wall).
    # web/index.html remains a fallback for an older checkout.
    return (root / "docs" / "index.html", root / "web" / "index.html")


def web_root() -> Path:
    package_root = Path(__file__).resolve().parent.parent
    seen = set()
    for root in (package_root, Path.cwd()):
        key = str(root.resolve())
        if key in seen:
            continue
        seen.add(key)
        for candidate in _index_pages(root):
            if candidate.is_file():
                return candidate.parent
    raise FileNotFoundError("docs/index.html is missing")


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    directory = web_root()
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = make_server(host, port)
    bound_host, bound_port = server.server_address[:2]
    page = web_root() / "index.html"
    print(f"serving {page.parent.name}/index.html at http://{bound_host}:{bound_port}/")
    print("ctrl+c stops the wall. press f in the page for fullscreen.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nwall stopped")
    finally:
        server.server_close()
