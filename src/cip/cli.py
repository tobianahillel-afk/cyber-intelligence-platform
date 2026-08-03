from __future__ import annotations

import logging

import uvicorn

from cip.modules.collection_orchestration.application.runtime import (
    run_scheduler_forever,
    run_worker_forever,
)
from cip.shared.config.settings import Settings, get_settings


def run_api() -> None:
    settings = get_settings()
    _configure_logging(settings)
    uvicorn.run(
        "cip.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )


def run_scheduler() -> None:
    settings = get_settings()
    _configure_logging(settings)
    run_scheduler_forever(settings)


def run_worker() -> None:
    settings = get_settings()
    _configure_logging(settings)
    run_worker_forever(settings)


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
