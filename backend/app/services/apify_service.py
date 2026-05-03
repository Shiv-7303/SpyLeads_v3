"""app/services/apify_service.py — Apify Actor trigger and dataset logic."""
import os
from apify_client import ApifyClient
from flask import current_app

INSTAGRAM_BLOCK_KEYWORDS = [
    "challenge_required", "checkpoint_required",
    "login_required", "rate_limit", "too many requests", "blocked"
]


def build_actor_input(extract_type: str, value: str, max_results: int,
                      filters: dict, proxy_mode: str = "datacenter") -> dict:
    if not value:
        raise ValueError("'value' cannot be empty")

    if extract_type == "hashtag":
        query = value.lstrip("#")
    elif extract_type == "competitor":
        query = value.lstrip("@")
    elif extract_type in ("location", "post_likers"):
        query = value
    else:
        raise ValueError(f"Unknown extract_type: {extract_type}")

    actor_input = {
        "query": query,
        "type": extract_type,
        "maxResults": max_results,
        "phase1ProxyType": proxy_mode
    }

    session_cookie = current_app.config.get("IG_SESSION_COOKIE")
    if session_cookie:
        actor_input["sessionCookie"] = session_cookie

    if filters.get("minFollowers"):
        actor_input["minFollowers"] = int(filters["minFollowers"])
    if filters.get("maxFollowers"):
        actor_input["maxFollowers"] = int(filters["maxFollowers"])

    return actor_input


def trigger_actor_and_wait(actor_input: dict, timeout_secs: int = 300) -> tuple:
    """Returns (run_id, dataset_id, status, cost_usd)."""
    token = current_app.config.get("APIFY_TOKEN")
    actor_id = current_app.config.get("APIFY_ACTOR_ID")

    if not token or not actor_id:
        raise RuntimeError("APIFY_TOKEN or APIFY_ACTOR_ID not configured.")

    client = ApifyClient(token)
    run = client.actor(actor_id).call(run_input=actor_input, timeout_secs=timeout_secs)

    if not run:
        raise TimeoutError("Actor run timed out or failed to start.")

    run_id = run.get("id")
    status = run.get("status")
    dataset_id = run.get("defaultDatasetId")
    cost_usd = run.get("usageTotalUsd") or 0.0

    if status != "SUCCEEDED":
        raise RuntimeError(f"Actor run ended with status: {status}")

    return run_id, dataset_id, status, cost_usd


def fetch_dataset(dataset_id: str) -> list:
    token = current_app.config.get("APIFY_TOKEN")
    client = ApifyClient(token)
    return list(client.dataset(dataset_id).iterate_items())


def detect_instagram_block(items: list) -> bool:
    for item in items:
        if isinstance(item, dict) and item.get("error") == "phase1_failed":
            return True
        item_str = str(item).lower()
        for keyword in INSTAGRAM_BLOCK_KEYWORDS:
            if keyword in item_str:
                return True
    return False


def normalize_profile(raw: dict) -> dict:
    from app.utils.helpers import extract_email_from_bio
    bio = raw.get("bio") or raw.get("biography") or ""
    username = raw.get("username") or raw.get("userName") or ""
    return {
        "username": username,
        "full_name": raw.get("fullName") or raw.get("full_name") or username,
        "followers": raw.get("followers") or raw.get("followersCount") or 0,
        "following": raw.get("following") or raw.get("followingCount") or 0,
        "bio": bio,
        "email": raw.get("email") or extract_email_from_bio(bio),
        "website": raw.get("website") or raw.get("externalUrl") or "",
        "is_business": raw.get("isBusinessAccount") or bool(raw.get("category")),
        "category": raw.get("category") or raw.get("businessCategoryName") or "",
        "profile_url": raw.get("profile_url") or f"https://instagram.com/{username}",
        "post_count": raw.get("postsCount") or raw.get("mediaCount") or 0,
        "location": raw.get("location") or "",
        "is_verified": raw.get("is_verified") or False,
    }


def apply_filters(profiles: list, filters: dict) -> list:
    result = []
    for p in profiles:
        if filters.get("emailRequired") and not p.get("email"):
            continue
        if filters.get("minFollowers") and (p.get("followers") or 0) < int(filters["minFollowers"]):
            continue
        if filters.get("maxFollowers") and (p.get("followers") or 0) > int(filters["maxFollowers"]):
            continue
        if filters.get("bioKeyword"):
            if filters["bioKeyword"].lower() not in (p.get("bio") or "").lower():
                continue
        result.append(p)
    return result
