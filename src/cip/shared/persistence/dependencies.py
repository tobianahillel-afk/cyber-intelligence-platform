from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from cip.shared.config.settings import get_settings
from cip.shared.persistence.session import create_database_engine, create_session_factory


@lru_cache(maxsize=8)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_database_engine(database_url))


def get_database_session() -> Iterator[Session]:
    factory = _session_factory(get_settings().database_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
