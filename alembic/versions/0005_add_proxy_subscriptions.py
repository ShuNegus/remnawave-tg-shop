"""add proxy_subscriptions table and product_type to payments

Revision ID: 0005_add_proxy_subscriptions
Revises: 0004_add_promo_bonus_gb
Create Date: 2026-04-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_add_proxy_subscriptions"
down_revision: Union[str, Sequence[str],
                     None] = "0004_add_promo_bonus_gb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proxy_subscriptions",
        sa.Column("proxy_sub_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.user_id"), nullable=False, index=True),
        sa.Column("secret", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("tg_proxy_link", sa.String(), nullable=True),
        sa.Column("traffic_limit_bytes", sa.BigInteger(), nullable=False),
        sa.Column("traffic_used_bytes", sa.BigInteger(), server_default="0"),
        sa.Column("start_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", index=True),
        sa.Column("is_promo", sa.Boolean(), server_default="false"),
        sa.Column("last_traffic_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column(
        "payments",
        sa.Column("product_type", sa.String(), nullable=False, server_default="vpn", index=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "product_type")
    op.drop_table("proxy_subscriptions")
