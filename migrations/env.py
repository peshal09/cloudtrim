"""Alembic environment — targets Postgres via CLOUDTRIM_DATABASE_URL."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the app packages importable when alembic runs from the repo root.
_ROOT = Path(__file__).resolve().parents[1]
for _p in ("apps/api", "packages/engine", "packages/ai"):
    sys.path.insert(0, str(_ROOT / _p))

from api.db.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_URL = os.getenv("CLOUDTRIM_DATABASE_URL")


def run_migrations_offline() -> None:
    context.configure(url=_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    if _URL:
        section["sqlalchemy.url"] = _URL
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
