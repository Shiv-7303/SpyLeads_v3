"""app/services/quota_service.py — Quota reset and limit checking."""
import json
from datetime import datetime
from sqlalchemy import extract, func
from app.utils.helpers import get_ist_now

DEFAULT_CONFIG = {
    "kill_switch": False,
    "daily_limits":  {"FREE": 10,  "PRO": 50,  "PRO_PLUS": 150},
    "monthly_caps":  {"FREE": 200, "PRO": 1200, "PRO_PLUS": 4500},
    "max_results_per_request": {"FREE": 10, "PRO": 50, "PRO_PLUS": 150},
}

def get_system_config() -> dict:
    """Returns parsed system config from DB, falls back to defaults."""
    from app.models import AppConfig
    record = AppConfig.query.filter_by(key='main_config').first()
    if record and record.value_json:
        try:
            return record.value_json
        except Exception:
            pass
    return DEFAULT_CONFIG

def seed_default_config():
    """Inserts default system config if not present."""
    from app.models import db, AppConfig
    if not AppConfig.query.filter_by(key='main_config').first():
        record = AppConfig(
            key='main_config',
            value_json=DEFAULT_CONFIG,
            updated_by='system'
        )
        db.session.add(record)
        db.session.commit()

def get_daily_quota(user_id, today_date):
    """Gets or creates the DailyQuota record for the user and date."""
    from app.models import db, DailyQuota
    quota = DailyQuota.query.filter_by(user_id=user_id, date=today_date).first()
    if not quota:
        # Calculate monthly_used so far for the current month
        month_start = today_date.replace(day=1)
        monthly_used_so_far = db.session.query(func.sum(DailyQuota.daily_used)).filter(
            DailyQuota.user_id == user_id,
            DailyQuota.date >= month_start,
            DailyQuota.date < today_date
        ).scalar() or 0

        quota = DailyQuota(
            user_id=user_id,
            date=today_date,
            daily_used=0,
            monthly_used=monthly_used_so_far
        )
        db.session.add(quota)
        db.session.commit()
    return quota

def increment_quota(user_id, amount: int):
    """Increments the daily and monthly usage."""
    from app.models import db
    now = get_ist_now().replace(tzinfo=None)
    today = now.date()
    quota = get_daily_quota(user_id, today)
    quota.daily_used += amount
    quota.monthly_used += amount
    db.session.commit()

def check_quota(user) -> tuple[bool, dict]:
    """
    Returns (allowed: bool, error_response: dict | None).
    Checks kill switch, daily limit, and monthly cap.
    """
    config = get_system_config()

    if config.get("kill_switch"):
        return False, {"error": "kill_switch", "message": "Service temporarily unavailable."}

    plan = user.plan
    daily_limit = config["daily_limits"].get(plan, 0)
    monthly_cap = config["monthly_caps"].get(plan, 0)

    now = get_ist_now().replace(tzinfo=None)
    quota = get_daily_quota(user.id, now.date())

    if quota.daily_used >= daily_limit:
        return False, {
            "error": "quota_exceeded",
            "message": f"Daily quota of {daily_limit} reached for {plan} plan",
            "daily_used": quota.daily_used,
            "daily_limit": daily_limit
        }

    if quota.monthly_used >= monthly_cap:
        return False, {
            "error": "monthly_cap_reached",
            "message": f"Monthly cap of {monthly_cap} reached for {plan} plan",
            "monthly_used": quota.monthly_used,
            "monthly_limit": monthly_cap
        }

    return True, None

def get_quota_info(user) -> dict:
    config = get_system_config()
    plan = user.plan
    daily_limit = config.get("daily_limits", {}).get(plan, 0)
    monthly_cap = config.get("monthly_caps", {}).get(plan, 0)
    
    now = get_ist_now().replace(tzinfo=None)
    quota = get_daily_quota(user.id, now.date())
    
    return {
        "plan": plan,
        "daily_used": quota.daily_used,
        "daily_limit": daily_limit,
        "daily_remaining": max(0, daily_limit - quota.daily_used),
        "monthly_used": quota.monthly_used,
        "monthly_limit": monthly_cap,
        "monthly_remaining": max(0, monthly_cap - quota.monthly_used),
    }
