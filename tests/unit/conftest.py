from __future__ import annotations

import socket
from collections.abc import Generator
from typing import NoReturn

import pytest


@pytest.fixture(autouse=True)
def forbid_live_network_in_unit_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    def blocked_connect(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        raise AssertionError(
            "Unit tests must not open network connections; use a fake client or MockTransport"
        )

    monkeypatch.setattr(socket, "create_connection", blocked_connect)
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
    yield
