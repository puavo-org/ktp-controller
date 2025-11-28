# Standard library imports
import logging.config
import os
import sys

# Third-party imports
import alembic.context  # type: ignore
import sqlalchemy
import sqlalchemy.pool

# Internal imports
from ktp_controller.api.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = alembic.context.config

# configure sqlalchemy.url from environment
if not 'KTP_CONTROLLER_DB_PATH' in os.environ:
    raise Exception('KTP_CONTROLLER_DB_PATH not set in environment')
config.set_main_option('sqlalchemy.url',
                       'sqlite:///%s' % os.environ['KTP_CONTROLLER_DB_PATH'])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    logging.config.fileConfig(config.config_file_name)

# for 'alembic autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to alembic.context.execute() here emit the given string to
    the script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    alembic.context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = sqlalchemy.engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=sqlalchemy.pool.NullPool,
    )

    with connectable.connect() as connection:
        alembic.context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with alembic.context.begin_transaction():
            alembic.context.run_migrations()


if alembic.context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
