from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401 — registers all ORM models in metadata before engine use
from app.core.config import settings

engine: Engine = create_engine(settings.database_url)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
