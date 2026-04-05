from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ProxySubscription


async def create_proxy_subscription(
    session: AsyncSession,
    user_id: int,
    secret: str,
    tg_proxy_link: str,
    traffic_limit_bytes: int,
    end_date: datetime,
    is_promo: bool = False,
) -> ProxySubscription:
    sub = ProxySubscription(
        user_id=user_id,
        secret=secret,
        tg_proxy_link=tg_proxy_link,
        traffic_limit_bytes=traffic_limit_bytes,
        end_date=end_date,
        is_promo=is_promo,
    )
    session.add(sub)
    await session.flush()
    return sub


async def get_active_proxy_subscription(
    session: AsyncSession, user_id: int
) -> Optional[ProxySubscription]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(ProxySubscription)
        .where(
            ProxySubscription.user_id == user_id,
            ProxySubscription.is_active == True,
            ProxySubscription.end_date > now,
        )
        .order_by(ProxySubscription.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_all_active_proxy_subscriptions(
    session: AsyncSession,
) -> List[ProxySubscription]:
    now = datetime.now(timezone.utc)
    stmt = select(ProxySubscription).where(
        ProxySubscription.is_active == True,
        ProxySubscription.end_date > now,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_proxy_subscription_by_secret(
    session: AsyncSession, secret: str
) -> Optional[ProxySubscription]:
    stmt = select(ProxySubscription).where(ProxySubscription.secret == secret)
    result = await session.execute(stmt)
    return result.scalars().first()


async def update_proxy_traffic(
    session: AsyncSession, proxy_sub_id: int, traffic_used_bytes: int
):
    stmt = (
        update(ProxySubscription)
        .where(ProxySubscription.proxy_sub_id == proxy_sub_id)
        .values(
            traffic_used_bytes=traffic_used_bytes,
            last_traffic_sync=datetime.now(timezone.utc),
        )
    )
    await session.execute(stmt)


async def deactivate_proxy_subscription(
    session: AsyncSession, proxy_sub_id: int
):
    stmt = (
        update(ProxySubscription)
        .where(ProxySubscription.proxy_sub_id == proxy_sub_id)
        .values(is_active=False)
    )
    await session.execute(stmt)


async def has_proxy_promo(session: AsyncSession, user_id: int) -> bool:
    stmt = select(ProxySubscription.proxy_sub_id).where(
        ProxySubscription.user_id == user_id,
        ProxySubscription.is_promo == True,
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first() is not None


async def has_any_subscription(session: AsyncSession, user_id: int) -> bool:
    """Check if user has ever had any VPN subscription (for promo eligibility)."""
    from db.models import Subscription
    stmt = select(Subscription.subscription_id).where(
        Subscription.user_id == user_id,
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first() is not None
