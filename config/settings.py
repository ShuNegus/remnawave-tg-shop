import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError, computed_field, field_validator, model_validator
from typing import Optional, List, Dict, Any


class Settings(BaseSettings):
    BOT_TOKEN: str
    TELEGRAM_PROXY_URL: Optional[str] = None
    ADMIN_IDS_STR: str = Field(
        default="",
        alias="ADMIN_IDS",
        description="Comma-separated list of admin Telegram User IDs")

    POSTGRES_USER: str = Field(default="user")
    POSTGRES_PASSWORD: str = Field(default="password")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="vpn_shop_db")

    DEFAULT_LANGUAGE: str = Field(default="ru")

    SUPPORT_LINK: Optional[str] = Field(default=None)
    SERVER_STATUS_URL: Optional[str] = Field(default=None)
    TERMS_OF_SERVICE_URL: Optional[str] = Field(default=None)
    REQUIRED_CHANNEL_SUBSCRIBE_TO_USE: bool = Field(
        default=False,
        description="Require users to subscribe to REQUIRED_CHANNEL_ID before using the bot",
    )
    REQUIRED_CHANNEL_ID: Optional[int] = Field(
        default=None,
        description="Telegram channel ID the user must join to access the bot")
    REQUIRED_CHANNEL_LINK: Optional[str] = Field(
        default=None,
        description="Public username or invite link to the required channel for join button")

    # Legacy payment provider fields kept for DB compatibility but no longer used
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None
    YOOKASSA_RETURN_URL: Optional[str] = None
    YOOKASSA_DEFAULT_RECEIPT_EMAIL: Optional[str] = Field(default=None)
    YOOKASSA_VAT_CODE: int = Field(default=1)
    YOOKASSA_TAX_SYSTEM_CODE: Optional[int] = Field(default=None)
    YOOKASSA_PAYMENT_MODE: Optional[str] = Field(default=None)
    YOOKASSA_PAYMENT_SUBJECT: Optional[str] = Field(default=None)
    YOOKASSA_AUTOPAYMENTS_ENABLED: bool = Field(default=False)
    YOOKASSA_AUTOPAYMENTS_REQUIRE_CARD_BINDING: bool = Field(default=False)
    LKNPD_INN: Optional[str] = Field(default=None, alias="NALOGO_INN")
    LKNPD_PASSWORD: Optional[str] = Field(default=None, alias="NALOGO_PASSWORD")
    LKNPD_API_URL: str = Field(default="https://lknpd.nalog.ru/api", alias="NALOGO_API_URL")
    LKNPD_RECEIPT_NAME_SUBSCRIPTION: str = Field(default="subscription {months} months", alias="NALOGO_RECEIPT_NAME_SUBSCRIPTION")
    LKNPD_RECEIPT_NAME_TRAFFIC: str = Field(default="traffic package {gb} GB", alias="NALOGO_RECEIPT_NAME_TRAFFIC")

    WEBHOOK_BASE_URL: Optional[str] = None
    TELEGRAM_WEBHOOK_PATH: str = Field(
        default="/webhook/telegram",
        description="Relative path for Telegram webhook endpoint",
    )
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="Secret token for Telegram webhook header validation",
    )

    # Legacy payment provider fields (kept for compatibility, not used)
    CRYPTOPAY_TOKEN: Optional[str] = None
    CRYPTOPAY_NETWORK: str = Field(default="mainnet")
    CRYPTOPAY_CURRENCY_TYPE: str = Field(default="fiat")
    CRYPTOPAY_ASSET: str = Field(default="RUB")
    CRYPTOPAY_ENABLED: bool = Field(default=False)
    PLATEGA_ENABLED: bool = Field(default=False)
    PLATEGA_BASE_URL: str = Field(default="https://app.platega.io")
    PLATEGA_MERCHANT_ID: Optional[str] = None
    PLATEGA_SECRET: Optional[str] = None
    PLATEGA_PAYMENT_METHOD: int = Field(default=2)
    PLATEGA_RETURN_URL: Optional[str] = Field(default=None)
    PLATEGA_FAILED_URL: Optional[str] = Field(default=None)
    FREEKASSA_ENABLED: bool = Field(default=False)
    FREEKASSA_MERCHANT_ID: Optional[str] = None
    FREEKASSA_FIRST_SECRET: Optional[str] = None
    FREEKASSA_SECOND_SECRET: Optional[str] = None
    FREEKASSA_PAYMENT_URL: str = Field(default="https://pay.freekassa.ru/")
    FREEKASSA_API_KEY: Optional[str] = None
    FREEKASSA_PAYMENT_IP: Optional[str] = None
    FREEKASSA_PAYMENT_METHOD_ID: Optional[int] = None
    SEVERPAY_ENABLED: bool = Field(default=False)
    SEVERPAY_MID: Optional[int] = None
    SEVERPAY_TOKEN: Optional[str] = None
    SEVERPAY_RETURN_URL: Optional[str] = None
    SEVERPAY_BASE_URL: str = Field(default="https://severpay.io/api/merchant")
    SEVERPAY_LIFETIME_MINUTES: Optional[int] = Field(default=None)
    YOOKASSA_ENABLED: bool = Field(default=False)

    # Only Telegram Stars payment
    STARS_ENABLED: bool = Field(default=True)
    STARS_PROVIDER_TOKEN: Optional[str] = Field(default="")
    PAYMENT_METHODS_ORDER: Optional[str] = Field(default="stars")

    # Legacy monthly subscription fields (kept for compatibility)
    MONTH_1_ENABLED: bool = Field(default=False, alias="1_MONTH_ENABLED")
    MONTH_3_ENABLED: bool = Field(default=False, alias="3_MONTHS_ENABLED")
    MONTH_6_ENABLED: bool = Field(default=False, alias="6_MONTHS_ENABLED")
    MONTH_12_ENABLED: bool = Field(default=False, alias="12_MONTHS_ENABLED")
    RUB_PRICE_1_MONTH: Optional[int] = Field(default=None)
    RUB_PRICE_3_MONTHS: Optional[int] = Field(default=None)
    RUB_PRICE_6_MONTHS: Optional[int] = Field(default=None)
    RUB_PRICE_12_MONTHS: Optional[int] = Field(default=None)
    STARS_PRICE_1_MONTH: Optional[int] = Field(default=None)
    STARS_PRICE_3_MONTHS: Optional[int] = Field(default=None)
    STARS_PRICE_6_MONTHS: Optional[int] = Field(default=None)
    STARS_PRICE_12_MONTHS: Optional[int] = Field(default=None)
    PANEL_WEBHOOK_SECRET: Optional[str] = Field(default=None)

    # Traffic packages: "GB:stars_price:days" e.g. "15:100:15,50:200:30,120:400:30,250:700:60"
    TRAFFIC_PACKAGES: Optional[str] = Field(
        default=None,
        description="Comma-separated traffic packages: '<GB>:<stars_price>:<days>', e.g. '15:100:15,50:200:30'",
    )
    # Legacy field kept for compatibility
    STARS_TRAFFIC_PACKAGES: Optional[str] = Field(default=None)

    SUBSCRIPTION_NOTIFICATIONS_ENABLED: bool = Field(default=True)
    SUBSCRIPTION_NOTIFY_ON_EXPIRE: bool = Field(default=True)
    SUBSCRIPTION_NOTIFY_AFTER_EXPIRE: bool = Field(default=True)
    SUBSCRIPTION_NOTIFY_DAYS_BEFORE: int = Field(default=3)

    # Traffic usage notifications
    TRAFFIC_NOTIFICATION_THRESHOLD: float = Field(
        default=0.9,
        description="Send notification when traffic usage reaches this fraction (0.9 = 90%)",
    )
    TRAFFIC_NOTIFICATION_CHECK_INTERVAL_MINUTES: int = Field(
        default=60,
        description="How often to check traffic usage (minutes)",
    )

    # Referral bonuses (GB-based)
    REFERRAL_INVITER_BONUS_GB: float = Field(default=3.0)
    REFERRAL_INVITER_BONUS_DAYS: int = Field(default=7)
    REFERRAL_REFEREE_BONUS_GB: float = Field(default=3.0)
    REFERRAL_REFEREE_BONUS_DAYS: int = Field(default=7)

    # Legacy referral fields (kept for compatibility)
    REFERRAL_BONUS_DAYS_INVITER_1_MONTH: Optional[int] = Field(
        default=None, alias="REFERRAL_BONUS_DAYS_1_MONTH")
    REFERRAL_BONUS_DAYS_INVITER_3_MONTHS: Optional[int] = Field(
        default=None, alias="REFERRAL_BONUS_DAYS_3_MONTHS")
    REFERRAL_BONUS_DAYS_INVITER_6_MONTHS: Optional[int] = Field(
        default=None, alias="REFERRAL_BONUS_DAYS_6_MONTHS")
    REFERRAL_BONUS_DAYS_INVITER_12_MONTHS: Optional[int] = Field(
        default=None, alias="REFERRAL_BONUS_DAYS_12_MONTHS")
    REFERRAL_BONUS_DAYS_REFEREE_1_MONTH: Optional[int] = Field(
        default=None, alias="REFEREE_BONUS_DAYS_1_MONTH")
    REFERRAL_BONUS_DAYS_REFEREE_3_MONTHS: Optional[int] = Field(
        default=None, alias="REFEREE_BONUS_DAYS_3_MONTHS")
    REFERRAL_BONUS_DAYS_REFEREE_6_MONTHS: Optional[int] = Field(
        default=None, alias="REFEREE_BONUS_DAYS_6_MONTHS")
    REFERRAL_BONUS_DAYS_REFEREE_12_MONTHS: Optional[int] = Field(
        default=None, alias="REFEREE_BONUS_DAYS_12_MONTHS")

    # Referral program configuration
    REFERRAL_ONE_BONUS_PER_REFEREE: bool = Field(
        default=True,
        description="When true, referral bonuses (for inviter and referee) are applied only once per invited user - on their first successful payment."
    )
    REFERRAL_ENABLED: bool = Field(
        default=True,
        description="Enable referral links, referral menu and referral bonuses",
    )
    LEGACY_REFS: bool = Field(
        default=True,
        description="Allow legacy referral links like ref_<telegram_id> to continue working. Defaults to True when unset."
    )

    PANEL_API_URL: Optional[str] = None
    PANEL_API_KEY: Optional[str] = None
    USER_TRAFFIC_LIMIT_GB: Optional[float] = Field(default=0.0)
    USER_TRAFFIC_STRATEGY: str = Field(default="NO_RESET")
    USER_SQUAD_UUIDS: Optional[str] = Field(
        default=None,
        description=
        "Comma-separated UUIDs of internal squads to assign to new panel users")
    USER_EXTERNAL_SQUAD_UUID: Optional[str] = Field(
        default=None,
        description=
        "UUID of the external squad to assign to new panel users (optional)")

    TRIAL_ENABLED: bool = Field(default=True)
    TRIAL_DURATION_DAYS: int = Field(default=2)
    TRIAL_TRAFFIC_LIMIT_GB: Optional[float] = Field(default=1.0)

    CRYPT4_ENABLED: bool = Field(default=False, description="Enable happ crypt4 encryption for subscription URLs")
    CRYPT4_REDIRECT_URL: Optional[str] = Field(default=None, description="Base redirect URL used for the connect button when crypt4 is enabled")

    WEB_SERVER_HOST: str = Field(default="0.0.0.0")
    WEB_SERVER_PORT: int = Field(default=8080)
    LOGS_PAGE_SIZE: int = Field(default=10)

    SUBSCRIPTION_MINI_APP_URL: Optional[str] = Field(default=None)

    START_COMMAND_DESCRIPTION: Optional[str] = Field(default=None)
    DISABLE_WELCOME_MESSAGE: bool = Field(default=False, description="Disable welcome message on /start command")

    MY_DEVICES_SECTION_ENABLED: bool = Field(
        default=False,
        description="Enable the My Devices section in the subscription menu"
    )
    USER_HWID_DEVICE_LIMIT: Optional[int] = Field(
        default=None,
        description="Default hardware device limit for panel users (0 = unlimited)"
    )
    
    # Inline mode thumbnail URLs
    INLINE_REFERRAL_THUMBNAIL_URL: str = Field(default="https://cdn-icons-png.flaticon.com/512/1077/1077114.png")
    INLINE_USER_STATS_THUMBNAIL_URL: str = Field(default="https://cdn-icons-png.flaticon.com/512/681/681494.png")
    INLINE_FINANCIAL_STATS_THUMBNAIL_URL: str = Field(default="https://cdn-icons-png.flaticon.com/512/2769/2769339.png")
    INLINE_SYSTEM_STATS_THUMBNAIL_URL: str = Field(default="https://cdn-icons-png.flaticon.com/512/2920/2920277.png")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @computed_field
    @property
    def ADMIN_IDS(self) -> List[int]:
        if self.ADMIN_IDS_STR:
            try:
                return [
                    int(admin_id.strip())
                    for admin_id in self.ADMIN_IDS_STR.split(',')
                    if admin_id.strip().isdigit()
                ]
            except ValueError:
                logging.error(
                    f"Invalid ADMIN_IDS_STR format: '{self.ADMIN_IDS_STR}'. Expected comma-separated integers."
                )
                return []
        return []

    @computed_field
    @property
    def PRIMARY_ADMIN_ID(self) -> Optional[int]:
        ids = self.ADMIN_IDS
        return ids[0] if ids else None

    @computed_field
    @property
    def trial_traffic_limit_bytes(self) -> int:
        if self.TRIAL_TRAFFIC_LIMIT_GB is None or self.TRIAL_TRAFFIC_LIMIT_GB <= 0:
            return 0
        return int(self.TRIAL_TRAFFIC_LIMIT_GB * (1024**3))

    @computed_field
    @property
    def user_traffic_limit_bytes(self) -> int:
        if self.USER_TRAFFIC_LIMIT_GB is None or self.USER_TRAFFIC_LIMIT_GB <= 0:
            return 0
        return int(self.USER_TRAFFIC_LIMIT_GB * (1024**3))

    @computed_field
    @property
    def parsed_user_squad_uuids(self) -> Optional[List[str]]:
        if self.USER_SQUAD_UUIDS:
            return [
                uuid.strip()
                for uuid in self.USER_SQUAD_UUIDS.split(',')
                if uuid.strip()
            ]
        return None

    @computed_field
    @property
    def parsed_user_external_squad_uuid(self) -> Optional[str]:
        if self.USER_EXTERNAL_SQUAD_UUID:
            cleaned = self.USER_EXTERNAL_SQUAD_UUID.strip()
            if cleaned:
                return cleaned
        return None

    @computed_field
    @property
    def telegram_webhook_path(self) -> str:
        path = (self.TELEGRAM_WEBHOOK_PATH or "").strip() or "/webhook/telegram"
        if not path.startswith("/"):
            path = f"/{path}"
        return path

    @computed_field
    @property
    def telegram_full_webhook_url(self) -> Optional[str]:
        base = self.WEBHOOK_BASE_URL
        if base:
            return f"{base.rstrip('/')}{self.telegram_webhook_path}"
        return None

    # Legacy webhook paths (kept for compatibility)
    @computed_field
    @property
    def yookassa_webhook_path(self) -> str:
        return "/webhook/yookassa"

    @computed_field
    @property
    def yookassa_full_webhook_url(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def panel_webhook_path(self) -> str:
        return "/webhook/panel"

    @computed_field
    @property
    def panel_full_webhook_url(self) -> Optional[str]:
        base = self.WEBHOOK_BASE_URL
        if base:
            return f"{base.rstrip('/')}{self.panel_webhook_path}"
        return None

    @computed_field
    @property
    def cryptopay_webhook_path(self) -> str:
        return "/webhook/cryptopay"

    @computed_field
    @property
    def cryptopay_full_webhook_url(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def freekassa_webhook_path(self) -> str:
        return "/webhook/freekassa"

    @computed_field
    @property
    def freekassa_full_webhook_url(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def severpay_webhook_path(self) -> str:
        return "/webhook/severpay"

    @computed_field
    @property
    def severpay_full_webhook_url(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def platega_webhook_path(self) -> str:
        return "/webhook/platega"

    @computed_field
    @property
    def platega_full_webhook_url(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def yk_receipt_payment_mode(self) -> str:
        return "full_prepayment"

    @computed_field
    @property
    def yk_receipt_payment_subject(self) -> str:
        return "payment"

    @computed_field
    @property
    def subscription_options(self) -> Dict[int, float]:
        options: Dict[int, float] = {}

        if self.MONTH_1_ENABLED and self.RUB_PRICE_1_MONTH is not None:
            options[1] = float(self.RUB_PRICE_1_MONTH)
        if self.MONTH_3_ENABLED and self.RUB_PRICE_3_MONTHS is not None:
            options[3] = float(self.RUB_PRICE_3_MONTHS)
        if self.MONTH_6_ENABLED and self.RUB_PRICE_6_MONTHS is not None:
            options[6] = float(self.RUB_PRICE_6_MONTHS)
        if self.MONTH_12_ENABLED and self.RUB_PRICE_12_MONTHS is not None:
            options[12] = float(self.RUB_PRICE_12_MONTHS)
        return options

    @computed_field
    @property
    def stars_subscription_options(self) -> Dict[int, int]:
        options: Dict[int, int] = {}
        if self.STARS_ENABLED and self.MONTH_1_ENABLED and self.STARS_PRICE_1_MONTH is not None:
            options[1] = self.STARS_PRICE_1_MONTH
        if self.STARS_ENABLED and self.MONTH_3_ENABLED and self.STARS_PRICE_3_MONTHS is not None:
            options[3] = self.STARS_PRICE_3_MONTHS
        if self.STARS_ENABLED and self.MONTH_6_ENABLED and self.STARS_PRICE_6_MONTHS is not None:
            options[6] = self.STARS_PRICE_6_MONTHS
        if self.STARS_ENABLED and self.MONTH_12_ENABLED and self.STARS_PRICE_12_MONTHS is not None:
            options[12] = self.STARS_PRICE_12_MONTHS
        return options

    @computed_field
    @property
    def traffic_packages_parsed(self) -> List[Dict]:
        """
        Parsed traffic packages: list of {gb: float, price: int, days: int}.
        Format: "GB:stars_price:days" e.g. "15:100:15,50:200:30"
        """
        packages: List[Dict] = []
        raw = (self.TRAFFIC_PACKAGES or "").strip()
        if not raw:
            return packages
        for part in raw.split(","):
            chunk = part.strip()
            if not chunk:
                continue
            parts = chunk.split(":")
            if len(parts) != 3:
                logging.warning("Invalid TRAFFIC_PACKAGES entry (need GB:price:days): %s", chunk)
                continue
            try:
                size_gb = float(parts[0].strip())
                price = int(float(parts[1].strip()))
                days = int(parts[2].strip())
                if size_gb > 0 and price >= 0 and days > 0:
                    packages.append({"gb": size_gb, "price": price, "days": days})
            except ValueError:
                logging.warning("Invalid TRAFFIC_PACKAGES entry skipped: %s", chunk)
                continue
        return packages

    @computed_field
    @property
    def traffic_packages(self) -> Dict[float, float]:
        """Legacy compat: GB → price mapping."""
        return {p["gb"]: float(p["price"]) for p in self.traffic_packages_parsed}

    @computed_field
    @property
    def stars_traffic_packages(self) -> Dict[float, int]:
        """GB → stars price mapping (from new unified format)."""
        return {p["gb"]: p["price"] for p in self.traffic_packages_parsed}

    @computed_field
    @property
    def traffic_sale_mode(self) -> bool:
        """When true, the bot sells traffic packages instead of time-based subscriptions."""
        return bool(self.traffic_packages_parsed)

    @computed_field
    @property
    def referral_bonus_inviter(self) -> Dict[str, Any]:
        """Inviter bonus: {gb: float, days: int}"""
        return {"gb": self.REFERRAL_INVITER_BONUS_GB, "days": self.REFERRAL_INVITER_BONUS_DAYS}

    @computed_field
    @property
    def referral_bonus_referee(self) -> Dict[str, Any]:
        """Referee bonus: {gb: float, days: int}"""
        return {"gb": self.REFERRAL_REFEREE_BONUS_GB, "days": self.REFERRAL_REFEREE_BONUS_DAYS}

    def get_traffic_package(self, gb: float) -> Optional[Dict]:
        """Get package details by GB amount."""
        for p in self.traffic_packages_parsed:
            if p["gb"] == gb:
                return p
        return None

    @computed_field
    @property
    def yookassa_autopayments_active(self) -> bool:
        """Autopay features are available only when YooKassa itself is enabled."""
        return False

    @computed_field
    @property
    def payment_methods_order(self) -> List[str]:
        """
        Ordered list of payment providers to show in the subscription payment keyboard.
        """
        default_order = [
            "freekassa",
            "platega",
            "severpay",
            "yookassa",
            "stars",
            "cryptopay",
        ]
        if not self.PAYMENT_METHODS_ORDER:
            return default_order
        methods = []
        for item in self.PAYMENT_METHODS_ORDER.split(","):
            slug = item.strip().lower()
            if slug:
                methods.append(slug)
        return methods or default_order
    
    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_CHAT_ID: Optional[int] = Field(default=None, description="Telegram chat/group ID for sending notifications")
    LOG_THREAD_ID: Optional[int] = Field(default=None, description="Thread ID for supergroup messages (optional)")
    LOG_STORE_MESSAGE_CONTENT: bool = Field(
        default=False,
        description="Store message/callback content in message logs",
    )
    LOG_STORE_RAW_UPDATES: bool = Field(
        default=False,
        description="Store raw update previews in message logs",
    )
    LOG_EXPORT_INCLUDE_SENSITIVE: bool = Field(
        default=False,
        description="Include content/raw update fields in admin CSV export",
    )
    
    LOG_ADMIN_HIDE: bool = Field(
        default=False,
        description="Hide admin-generated events from admin logs UI and CSV export",
    )

    @field_validator('LOG_LEVEL', mode='before')
    @classmethod
    def normalize_log_level(cls, v):
        if isinstance(v, str):
            v = v.strip().upper()
        if not v:
            return "INFO"
        return v

    @model_validator(mode='before')
    @classmethod
    def drop_comment_placeholder_values(cls, values: Any):
        """
        dotenv parses lines like `KEY=  # comment` as `"# comment"`.
        Treat such values as unset so defaults/optionals work as expected.
        """
        if not isinstance(values, dict):
            return values

        sanitized: Dict[str, Any] = {}
        for key, value in values.items():
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed == "#" or trimmed.startswith("# "):
                    continue
            sanitized[key] = value
        return sanitized

    @field_validator(
        'TELEGRAM_WEBHOOK_PATH',
        mode='before',
    )
    @classmethod
    def normalize_webhook_path(cls, v):
        if not isinstance(v, str):
            return "/webhook/telegram"
        cleaned = v.strip()
        if not cleaned:
            return "/webhook/telegram"
        if not cleaned.startswith("/"):
            cleaned = f"/{cleaned}"
        return cleaned

    @field_validator(
        'REQUIRED_CHANNEL_LINK',
        'PLATEGA_RETURN_URL',
        'PLATEGA_FAILED_URL',
        'SEVERPAY_RETURN_URL',
        'CRYPT4_REDIRECT_URL',
        'TELEGRAM_WEBHOOK_SECRET',
        'PANEL_WEBHOOK_SECRET',
        'TELEGRAM_PROXY_URL',
        mode='before',
    )
    @classmethod
    def sanitize_optional_link(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v
    
    @field_validator(
        'REQUIRED_CHANNEL_ID',
        'FREEKASSA_PAYMENT_METHOD_ID',
        'USER_HWID_DEVICE_LIMIT',
        'SEVERPAY_MID',
        'SEVERPAY_LIFETIME_MINUTES',
        'LOG_CHAT_ID',
        'LOG_THREAD_ID',
        'YOOKASSA_TAX_SYSTEM_CODE',
        mode='before'
    )
    @classmethod
    def validate_optional_int(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator('YOOKASSA_PAYMENT_MODE', 'YOOKASSA_PAYMENT_SUBJECT', mode='before')
    @classmethod
    def normalize_optional_yookassa_receipt_fields(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator('YOOKASSA_TAX_SYSTEM_CODE')
    @classmethod
    def validate_yookassa_tax_system_code(cls, v):
        if v is None:
            return None
        if not 1 <= v <= 6:
            raise ValueError("YOOKASSA_TAX_SYSTEM_CODE must be an integer from 1 to 6.")
        return v
    
    # Notification types
    LOG_NEW_USERS: bool = Field(default=True, description="Send notifications for new user registrations")
    LOG_PAYMENTS: bool = Field(default=True, description="Send notifications for successful payments")
    LOG_PROMO_ACTIVATIONS: bool = Field(default=True, description="Send notifications for promo code activations")
    LOG_TRIAL_ACTIVATIONS: bool = Field(default=True, description="Send notifications for trial activations")
    LOG_SUSPICIOUS_ACTIVITY: bool = Field(default=True, description="Send notifications for suspicious promo attempts")
    DISCOUNT_PROMO_PAYMENT_TIMEOUT_MINUTES: int = Field(
        default=10,
        description="How long a discount promo reservation is kept before user payment",
    )

    model_config = SettingsConfigDict(env_file='.env',
                                      env_file_encoding='utf-8',
                                      extra='ignore',
                                      populate_by_name=True)


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
            if not _settings_instance.ADMIN_IDS:
                logging.warning(
                    "CRITICAL: ADMIN_IDS not set or contains no valid integer IDs in .env. "
                    "Admin functionality will be restricted.")

            if not _settings_instance.PANEL_API_URL:
                logging.warning(
                    "CRITICAL: PANEL_API_URL is not set. Panel integration will not work."
                )
            if _settings_instance.WEBHOOK_BASE_URL and not _settings_instance.TELEGRAM_WEBHOOK_SECRET:
                logging.warning(
                    "WARNING: TELEGRAM_WEBHOOK_SECRET is empty while webhook mode is enabled. "
                    "Set TELEGRAM_WEBHOOK_SECRET to validate X-Telegram-Bot-Api-Secret-Token header."
                )
            if not _settings_instance.traffic_packages_parsed:
                logging.warning(
                    "WARNING: TRAFFIC_PACKAGES is not set. Users will not see any packages to buy."
                )

        except ValidationError as e:
            logging.critical(
                f"Pydantic validation error while loading settings: {e}")

            raise SystemExit(
                f"CRITICAL SETTINGS ERROR: {e}. Please check your .env file and Settings model."
            )
    return _settings_instance
