from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
import sys
from pathlib import Path
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_target_metadata():
    # Import models metadata lazily to avoid app import side effects
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "apps" / "yuqing-sentiment" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from yuqing.models.database_models import Base as YuqingBase  # type: ignore

    return YuqingBase.metadata


def run_migrations_offline():
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=get_target_metadata(),
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL", configuration.get("sqlalchemy.url"))

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_target_metadata(),
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
