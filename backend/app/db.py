"""SQLite engine + FastAPI dependency for sessions."""
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# check_same_thread=False is required for SQLite with FastAPI's threadpool
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables. Idempotent — safe to call on every startup."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency — yields a session scoped to one request."""
    with Session(engine) as session:
        yield session