from __future__ import annotations

import uvicorn

from cip.shared.config.settings import get_settings


def run_api() -> None:
    settings = get_settings()
    uvicorn.run(
        "cip.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
