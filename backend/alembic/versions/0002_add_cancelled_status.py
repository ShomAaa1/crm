"""add cancelled status to request_status enum

Revision ID: 0002_add_cancelled
Revises: 0fe8f6c38823
Create Date: 2026-05-17
"""

from alembic import op
from sqlalchemy import text

revision = "0002_add_cancelled"
down_revision = "0fe8f6c38823"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG требует AUTOCOMMIT для ALTER TYPE ... ADD VALUE
    conn = op.get_bind()
    conn.execute(text("COMMIT"))
    conn.execute(
        text("ALTER TYPE request_status ADD VALUE IF NOT EXISTS 'cancelled'")
    )


def downgrade() -> None:
    # Удаление значения из PG enum нетривиально — оставляем no-op.
    pass
