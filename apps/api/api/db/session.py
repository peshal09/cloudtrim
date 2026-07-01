"""Engine construction for the SQL store."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine


def make_engine(url: str) -> Engine:
    # SQLite (tests) needs check_same_thread off for the shared in-memory case.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)
