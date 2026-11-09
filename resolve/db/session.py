from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from resolve.config import get_settings
from resolve.db.models import Base

_engine = None
_SessionLocal = None
_schema_ready = False


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().database_url
        sqlite = url.startswith("sqlite")
        connect_args = {"check_same_thread": False, "timeout": 30} if sqlite else {}
        kwargs = {} if sqlite else {"pool_size": 10, "max_overflow": 10, "pool_pre_ping": True}
        _engine = create_engine(url, echo=False, connect_args=connect_args, **kwargs)
        if sqlite:
            @event.listens_for(_engine, "connect")
            def _pragmas(dbapi_conn, _):  # WAL: readers don't block the writer; NORMAL: fsync at checkpoint
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA synchronous=NORMAL")
                cur.close()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db() -> None:
    """Create tables once per process. It used to run on every session: ~58 ms of has_table() per ticket."""
    global _schema_ready
    if _schema_ready:
        return
    engine = get_engine()
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)
    _schema_ready = True


def _add_missing_columns(engine) -> None:
    """create_all() never alters existing tables. Add nullable columns introduced after a DB was created."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in have and col.nullable:
                ddl = col.type.compile(dialect=engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}'))


@contextmanager
def get_session() -> Iterator[Session]:
    init_db()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
