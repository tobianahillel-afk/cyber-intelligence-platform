from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from cip.modules.provider_onboarding.application.runtime_secrets import (
    resolve_connected_provider_secret,
)
from cip.modules.provider_onboarding.application.secrets import LocalSecretValueResolver
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.session import session_scope


def connected_secret_supplier(
    factory: sessionmaker[Session],
    *,
    source_id: str,
    secret_name: str,
) -> Callable[[], str | None]:
    resolver = LocalSecretValueResolver()

    def resolve() -> str | None:
        with session_scope(factory) as session:
            return resolve_connected_provider_secret(
                session,
                source_id,
                secret_name,
                resolver=resolver,
                now=utc_now(),
            )

    return resolve
