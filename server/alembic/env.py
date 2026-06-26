import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

import app.models.attendance  # noqa: F401 — регистрирует AttendanceRecord в Base.metadata
import app.models.employee  # noqa: F401 — регистрирует Employee в Base.metadata
import app.models.finance  # noqa: F401 — регистрирует ExpenseCategory, OrderPayment, OrderExpense
import app.models.order  # noqa: F401 — регистрирует ProductionStage, Order, OrderStatusHistory
from alembic import context
from app.models.base import Base

config = context.config

# Если URL не был передан программно (например, из conftest), берём из окружения
if not config.get_main_option("sqlalchemy.url"):
    if "DATABASE_URL" not in os.environ:
        load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
