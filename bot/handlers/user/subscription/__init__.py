from aiogram import Router

from . import core
from . import payments

router = Router(name="user_subscription_router")

# Include sub-routers
router.include_router(core.router)
router.include_router(payments.router)

# Re-export commonly used entrypoints for backward compatibility
from .core import display_subscription_options, my_subscription_command_handler, my_devices_command_handler  # noqa: E402,F401
