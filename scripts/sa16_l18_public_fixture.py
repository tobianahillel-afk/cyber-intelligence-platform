from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import urlsplit

FIXTURE_HOST = "sa16-l18-public.example"
ETAG = '"sa16-l18-v1"'
REPORT = b"SA16 L18 controlled document\npublic evidence pipeline\n"
ARTIFACT_REPORT = b"SA16 L18 browser download\nquarantine projection proof\n"
_LOCK = Lock()


class FixtureState:
    requests = 0
    not_modified = 0
    json_hits = 0
    xhr_hits = 0
    document_hits = 0
    artifact_download_hits = 0

    @classmethod
    def reset(cls) -> None:
        with _LOCK:
            cls.requests = 0
            cls.not_modified = 0
            cls.json_hits = 0
            cls.xhr_hits = 0
            cls.document_hits = 0
            cls.artifact_download_hits = 0


class FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        with _LOCK:
            FixtureState.requests += 1
        if path == "/robots.txt":
            self._send(
                (
                    "User-agent: *\n"
                    "Allow: /\n"
                    f"Sitemap: {self.origin}sitemap.xml\n"
                ).encode(),
                "text/plain; charset=utf-8",
            )
            return
        if path == "/sitemap.xml":
            self._send(_sitemap_index(self.origin), "application/xml")
            return
        if path == "/sitemap-pages.xml":
            self._send(_sitemap_pages(self.origin), "application/xml")
            return
        if path == "/feed.xml":
            self._send(_feed(self.origin), "application/rss+xml")
            return
        if path == "/.well-known/security.txt":
            self._send(
                (
                    f"Contact: mailto:security@{FIXTURE_HOST}\n"
                    "Expires: 2030-01-01T00:00:00Z\n"
                ).encode(),
                "text/plain; charset=utf-8",
            )
            return
        if path == "/manifest.webmanifest":
            self._send_json({"name": "SA16 L18 Fixture", "start_url": "/"})
            return
        if path == "/api/app.json":
            with _LOCK:
                FixtureState.json_hits += 1
            self._send_json(
                {
                    "provider": "sa16-l18",
                    "technology": "rendered-fetch",
                    "accessToken": "must-drop",
                    "region": "eu",
                }
            )
            return
        if path == "/api/xhr":
            with _LOCK:
                FixtureState.xhr_hits += 1
            self._send_json(
                {
                    "provider": "sa16-l18",
                    "transport": "xhr",
                    "sessionId": "must-drop",
                    "evidence": {"kind": "public-json"},
                }
            )
            return
        if path == "/documents/report.txt":
            with _LOCK:
                FixtureState.document_hits += 1
            self._send_versioned(REPORT, "text/plain; charset=utf-8")
            return
        if path == "/artifact-download.txt":
            with _LOCK:
                FixtureState.artifact_download_hits += 1
            self._send(ARTIFACT_REPORT, "text/plain; charset=utf-8")
            return
        if path == "/artifact":
            self._send(_artifact_page().encode(), "text/html; charset=utf-8")
            return
        if path == "/gone":
            self._send(b"gone", "text/plain; charset=utf-8", status=HTTPStatus.GONE)
            return
        if path == "/":
            self._send_versioned(_home(self.origin).encode(), "text/html; charset=utf-8")
            return
        if path == "/static":
            self._send_versioned(_static_page().encode(), "text/html; charset=utf-8")
            return
        if path == "/app":
            self._send_versioned(_app_page().encode(), "text/html; charset=utf-8")
            return
        if path == "/feed-item":
            self._send_versioned(_feed_item().encode(), "text/html; charset=utf-8")
            return
        self._send(b"not found", "text/plain; charset=utf-8", status=HTTPStatus.NOT_FOUND)

    @property
    def origin(self) -> str:
        return f"http://{FIXTURE_HOST}:{self.server.server_address[1]}/"

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _send_versioned(self, body: bytes, content_type: str) -> None:
        if self.headers.get("If-None-Match") == ETAG:
            with _LOCK:
                FixtureState.not_modified += 1
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", ETAG)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send(body, content_type, extra_headers=(("ETag", ETAG),))

    def _send_json(self, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self._send(body, "application/json")

    def _send(
        self,
        body: bytes,
        content_type: str,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        if status != HTTPStatus.NOT_MODIFIED:
            self.wfile.write(body)
            self.wfile.flush()


@contextmanager
def serve_fixture() -> Iterator[str]:
    FixtureState.reset()
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{FIXTURE_HOST}:{server.server_address[1]}/"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _home(origin: str) -> str:
    json_ld = (
        '{"@context":"https://schema.org","@type":"Organization",'
        '"name":"SA16 L18 Fixture"}'
    )
    embedded = (
        '{"company":"SA16 L18 Fixture","technology":"static-json",'
        '"password":"must-drop"}'
    )
    return f"""<!doctype html><html><head>
<title>SA16 L18 Public Composite</title>
<meta name="description" content="Controlled organization research fixture">
<meta property="og:title" content="SA16 L18 Composite">
<link rel="canonical" href="{origin}">
<link rel="alternate" hreflang="fr" href="{origin}static">
<link rel="alternate" type="application/rss+xml" href="{origin}feed.xml">
<link rel="stylesheet" href="{origin}assets/site.css">
<link rel="manifest" href="{origin}manifest.webmanifest">
<script src="{origin}assets/site.js"></script>
<script type="application/ld+json">{json_ld}</script>
<script type="application/json">{embedded}</script>
</head><body><main><h1>Controlled organization research</h1>
<p>{'bounded public evidence ' * 20}</p></main>
<a href="{origin}static">Static evidence</a>
<a href="{origin}app">Rendered evidence</a>
<a href="{origin}documents/report.txt">Public report</a>
<a href="{origin}gone">Historical removed resource</a>
<form action="{origin}search" method="get"><input name="q"><button>Search</button></form>
<img src="{origin}media/logo.png" alt="fixture logo">
</body></html>"""


def _static_page() -> str:
    return (
        "<!doctype html><html><head><title>Static Evidence</title></head><body>"
        "<h1>Static evidence</h1><p>" + "stable evidence " * 40 + "</p></body></html>"
    )


def _app_page() -> str:
    return """<!doctype html><html><head><title>Rendered App</title></head><body>
<div id="app">loading</div><script>
window.__INITIAL_STATE__ = {
  company:"SA16 L18 Fixture", region:"eu", accessToken:"must-drop"
};
fetch("/api/app.json").then(r => r.json()).then(v => {
  document.querySelector("#app").textContent = "rendered " + v.technology;
});
const xhr = new XMLHttpRequest();
xhr.open("GET", "/api/xhr");
xhr.send();
</script></body></html>"""


def _artifact_page() -> str:
    return """<!doctype html><html><head><title>Artifact Evidence</title></head><body>
<main id="evidence"><h1>Controlled artifact evidence</h1><p>safe screenshot content</p></main>
<a id="download" href="/artifact-download.txt">Download controlled report</a>
</body></html>"""


def _feed_item() -> str:
    return (
        "<!doctype html><html><body><h1>Feed evidence</h1>"
        "<p>controlled feed item</p></body></html>"
    )


def _sitemap_index(origin: str) -> bytes:
    return (
        '<?xml version="1.0"?><sitemapindex '
        'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<sitemap><loc>{origin}sitemap-pages.xml</loc></sitemap></sitemapindex>"
    ).encode()


def _sitemap_pages(origin: str) -> bytes:
    urls = (
        origin,
        f"{origin}static",
        f"{origin}app",
        f"{origin}documents/report.txt",
        f"{origin}gone",
    )
    body = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return (
        '<?xml version="1.0"?><urlset '
        'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}</urlset>"
    ).encode()


def _feed(origin: str) -> bytes:
    return (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>SA16 L18 Feed</title>'
        f"<link>{origin}</link><item><title>Feed item</title><link>{origin}feed-item</link></item>"
        "</channel></rss>"
    ).encode()
