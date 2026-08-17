from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from cip.modules.provider_onboarding.application.federated_authorization import (
    pkce_s256_challenge,
)

PORT = 18777
BASE = f"http://127.0.0.1:{PORT}"
CLIENT_ID = "cip-controlled-public-client"
AUTH_CODE = "controlled-one-time-authorization-code"
ACCESS_TOKEN = "controlled-l17-access-token"


class FixtureState:
    state = ""
    redirect_uri = ""
    code_challenge = ""
    approvals = 0
    token_posts = 0
    private_hits = 0
    code_consumed = False


def reset_fixture() -> None:
    FixtureState.state = ""
    FixtureState.redirect_uri = ""
    FixtureState.code_challenge = ""
    FixtureState.approvals = 0
    FixtureState.token_posts = 0
    FixtureState.private_hits = 0
    FixtureState.code_consumed = False


def create_server() -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", PORT), ControlledOAuthHandler)


class ControlledOAuthHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/oauth/authorize":
            self._authorize(parse_qs(parsed.query, keep_blank_values=True))
            return
        if parsed.path == "/oauth/approve":
            self._approve()
            return
        if parsed.path == "/oauth/callback":
            self._html(HTTPStatus.OK, "<div id='oauth-complete'>approved</div>")
            return
        if parsed.path == "/private":
            self._private()
            return
        self._text(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/oauth/token":
            self._text(HTTPStatus.NOT_FOUND, "not found")
            return
        FixtureState.token_posts += 1
        values = self._form_values()
        verifier = values.get("code_verifier", [""])[0]
        valid = (
            values.get("grant_type", [""])[0] == "authorization_code"
            and values.get("code", [""])[0] == AUTH_CODE
            and values.get("client_id", [""])[0] == CLIENT_ID
            and values.get("redirect_uri", [""])[0] == FixtureState.redirect_uri
            and pkce_s256_challenge(verifier) == FixtureState.code_challenge
            and not FixtureState.code_consumed
        )
        if not valid:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_grant"})
            return
        FixtureState.code_consumed = True
        self._json(
            HTTPStatus.OK,
            {
                "access_token": ACCESS_TOKEN,
                "token_type": "Bearer",
                "scope": "read",
                "expires_in": 3600,
            },
        )

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _authorize(self, values: dict[str, list[str]]) -> None:
        state = values.get("state", [""])[0]
        redirect_uri = values.get("redirect_uri", [""])[0]
        challenge = values.get("code_challenge", [""])[0]
        valid = (
            values.get("response_type", [""])[0] == "code"
            and values.get("client_id", [""])[0] == CLIENT_ID
            and values.get("scope", [""])[0] == "read"
            and values.get("code_challenge_method", [""])[0] == "S256"
            and redirect_uri == f"{BASE}/oauth/callback"
            and len(state) >= 16
            and bool(challenge)
        )
        if not valid:
            self._text(HTTPStatus.BAD_REQUEST, "invalid authorization request")
            return
        FixtureState.state = state
        FixtureState.redirect_uri = redirect_uri
        FixtureState.code_challenge = challenge
        self._html(
            HTTPStatus.OK,
            "<html><body><h1>Controlled OAuth consent</h1>"
            "<a id='approve' href='/oauth/approve'>Approve access</a>"
            "</body></html>",
        )

    def _approve(self) -> None:
        if not FixtureState.state or not FixtureState.redirect_uri:
            self._text(HTTPStatus.BAD_REQUEST, "authorization context missing")
            return
        FixtureState.approvals += 1
        query = urlencode({"code": AUTH_CODE, "state": FixtureState.state})
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"{FixtureState.redirect_uri}?{query}")
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def _private(self) -> None:
        if self.headers.get("Authorization") != f"Bearer {ACCESS_TOKEN}":
            self._text(HTTPStatus.UNAUTHORIZED, "unauthorized")
            return
        FixtureState.private_hits += 1
        self._json(HTTPStatus.OK, {"status": "authorized"})

    def _form_values(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        return parse_qs(payload, keep_blank_values=True)

    def _html(self, status: HTTPStatus, body: str) -> None:
        self._send(status, body.encode(), "text/html; charset=utf-8")

    def _text(self, status: HTTPStatus, body: str) -> None:
        self._send(status, body.encode(), "text/plain; charset=utf-8")

    def _json(self, status: HTTPStatus, body: dict[str, object]) -> None:
        self._send(status, json.dumps(body).encode(), "application/json")

    def _send(self, status: HTTPStatus, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
