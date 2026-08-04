from __future__ import annotations

from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.service import sync_source_portfolio
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.config.settings import Settings
from cip.shared.kernel.time import utc_now


def ensure_source_portfolio(session: Session, settings: Settings) -> None:
    entries = load_source_portfolio(settings.source_portfolio_path)
    sync_source_portfolio(session, entries, now=utc_now())


def require_control_plane(
    settings: Settings,
    token: Annotated[str | None, Header(alias="X-CIP-Control-Token")] = None,
) -> None:
    if token is None or not compare_digest(token, settings.control_plane_token):
        raise HTTPException(status_code=401, detail="control-plane authentication required")
