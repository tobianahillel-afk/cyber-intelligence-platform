from __future__ import annotations

from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, status

from cip.shared.config.settings import Settings, get_settings


def require_control_plane_access(
    x_cip_control_token: str | None = Header(default=None, alias="X-CIP-Control-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.control_plane_token
    if (
        not expected
        or x_cip_control_token is None
        or not compare_digest(x_cip_control_token, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="control-plane authentication required",
        )
