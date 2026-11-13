from alembic import context
from backend.storage import Base, engine
from backend.config import settings
from sqlalchemy import create_engine

if settings.migration_database_url.get_secret_value():
    migration_url = settings.migration_database_url.get_secret_value().replace("postgresql://", "postgresql+psycopg://", 1).replace("postgres://", "postgresql+psycopg://", 1)
    engine = create_engine(migration_url, pool_pre_ping=True)

if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
