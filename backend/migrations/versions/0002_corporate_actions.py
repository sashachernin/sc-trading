"""Auditable corporate action adjustments."""

from alembic import op
from app.models import CorporateAction

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    CorporateAction.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    CorporateAction.__table__.drop(op.get_bind())
