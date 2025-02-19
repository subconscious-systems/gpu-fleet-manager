from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import your models
from src.models.base import Base
from src.models.job import Job
from src.models.gpu import GPU

# this is the Alembic Config object
config = context.config

# Setup logging
fileConfig(config.config_file_name)

# Set the database URL in the alembic.ini file
section = config.config_ini_section
config.set_section_option(section, "DATABASE_URL",
                         os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/gpu_fleet"))

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
