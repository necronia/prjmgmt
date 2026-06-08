"""Postgres 연결 풀 + pgvector 등록. 단순 psycopg3 ConnectionPool 사용."""
from contextlib import contextmanager

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

from .config import settings

_pool: ConnectionPool | None = None


def _configure(conn):
    register_vector(conn)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            configure=_configure,
            open=True,
        )
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    with pool.connection() as conn:
        yield conn
