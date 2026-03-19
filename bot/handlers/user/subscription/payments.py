from aiogram import Router

from .payments_stars import router as stars_router
from .payments_subscription import router as subscription_selection_router

router = Router(name="user_subscription_payments_router")

router.include_router(subscription_selection_router)
router.include_router(stars_router)

__all__ = ["router"]
