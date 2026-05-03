import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///spyleads.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "168"))  # 7 days

    # Apify
    APIFY_TOKEN = os.getenv("APIFY_TOKEN")
    APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID")

    # Stripe
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
    STRIPE_PRO_PLUS_PRICE_ID = os.getenv("STRIPE_PRO_PLUS_PRICE_ID", "")

    # Admin
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

    # Instagram session
    IG_SESSION_COOKIE = os.getenv("IG_SESSION_COOKIE", "")

    # Kill switch + Quota defaults (overridden by DB config)
    KILL_SWITCH = os.getenv("KILL_SWITCH", "false").lower() == "true"
    FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "10"))
    PRO_DAILY_LIMIT = int(os.getenv("PRO_DAILY_LIMIT", "50"))
    PRO_PLUS_DAILY_LIMIT = int(os.getenv("PRO_PLUS_DAILY_LIMIT", "150"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
