"""add bonus_gb column to promo_codes

Revision ID: 0004_add_promo_bonus_gb
Revises: 0003_promo_curr_act_not_null
Create Date: 2026-03-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_add_promo_bonus_gb"
down_revision: Union[str, Sequence[str],
                     None] = "0003_promo_curr_act_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("promo_codes", sa.Column("bonus_gb", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("promo_codes", "bonus_gb")
