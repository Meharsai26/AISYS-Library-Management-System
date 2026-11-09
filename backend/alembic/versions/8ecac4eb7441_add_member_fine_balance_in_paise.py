"""add member fine balance in paise

Revision ID: 8ecac4eb7441
Revises: df1940331666
Create Date: 2026-11-09 12:36:17.363682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ecac4eb7441'
down_revision: Union[str, Sequence[str], None] = 'df1940331666'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add INR fine balance without rebuilding members."""
    op.add_column(
        "members",
        sa.Column(
            "fine_balance_paise",
            sa.Integer(),
            sa.CheckConstraint(
                "fine_balance_paise >= 0",
                name="ck_member_fine_nonnegative",
            ),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Remove the fine balance column."""
    op.drop_column("members", "fine_balance_paise")
