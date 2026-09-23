"""値引き企画はすべて会員限定にする（members_only 列を削除）

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("promotion") as batch:
        batch.drop_column("members_only")


def downgrade() -> None:
    with op.batch_alter_table("promotion") as batch:
        batch.add_column(sa.Column("members_only", sa.Boolean(), nullable=False, server_default=sa.true()))
