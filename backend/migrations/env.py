from alembic import context
from app.models import Base, connect
from app.config import Settings

config = context.config
engine, _ = connect(Settings())
with engine.connect() as connection:
    context.configure(
        connection=connection, target_metadata=Base.metadata, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()
