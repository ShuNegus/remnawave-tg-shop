from aiogram import Router

from .core import router as core_router
from .purchase import router as purchase_router

router = Router(name="user_proxy_router")
router.include_router(core_router)
router.include_router(purchase_router)
