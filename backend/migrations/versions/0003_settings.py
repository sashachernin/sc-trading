"""Audited operator setting versions."""

from alembic import op
from app.models import SettingVersion

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    SettingVersion.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    SettingVersion.__table__.drop(op.get_bind())
