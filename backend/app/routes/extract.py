"""app/routes/extract.py — /extract endpoint with JWT auth."""
import time
from flask import Blueprint, request, jsonify
from app.models import db, UsageLog, ExtractionRequest
from app.utils.decorators import require_auth
from app.services.quota_service import (
    check_quota, get_quota_info, get_system_config, increment_quota
)
from app.services.apify_service import (
    build_actor_input, trigger_actor_and_wait, fetch_dataset,
    detect_instagram_block, normalize_profile, apply_filters
)

extract_bp = Blueprint('extract', __name__)

@extract_bp.route('/extract', methods=['POST'])
@require_auth
def extract():
    user = request.current_user
    data = request.json or {}

    # ── 1. Quota check ───────────────────────────────────────────────────────
    allowed, quota_error = check_quota(user)
    if not allowed:
        return jsonify(quota_error), 429

    # ── 2. Validate request params ───────────────────────────────────────────
    extract_type = data.get('type')
    value = (data.get('value') or '').strip()
    max_results = int(data.get('maxResults', 10))
    filters = data.get('filters', {})

    if not extract_type or not value:
        return jsonify({"error": "bad_request", "message": "'type' and 'value' are required"}), 400
    if extract_type not in ('hashtag', 'location', 'competitor', 'post_likers'):
        return jsonify({"error": "bad_request", "message": f"Unknown type '{extract_type}'"}), 400

    # ── 3. Clamp max_results to plan limits ──────────────────────────────────
    config = get_system_config()
    plan = user.plan
    plan_max = config.get("max_results_per_request", {}).get(plan, 10)
    
    # Calculate daily_remaining from get_quota_info to ensure it's exact
    quota_info = get_quota_info(user)
    daily_remaining = quota_info["daily_remaining"]
    monthly_remaining = quota_info["monthly_remaining"]
    max_results = max(1, min(max_results, plan_max, daily_remaining, monthly_remaining))

    # ── 4. Create ExtractionRequest ──────────────────────────────────────────
    ext_req = ExtractionRequest(
        user_id=user.id,
        query=value,
        query_type=extract_type,
        filters_json=filters,
        requested_results=max_results,
        status='processing'
    )
    db.session.add(ext_req)
    db.session.commit()

    # ── 5. Run actor (with datacenter → residential fallback) ────────────────
    start_time = time.time()
    proxy_mode = "datacenter"
    fallback_used = False
    failure_reason = None
    total_cost_usd = 0.0

    try:
        actor_input = build_actor_input(extract_type, value, max_results, filters, proxy_mode)
    except ValueError as e:
        ext_req.status = 'failed'
        db.session.commit()
        return jsonify({"error": "bad_request", "message": str(e)}), 400

    try:
        run_id, dataset_id, run_status, cost_usd = trigger_actor_and_wait(actor_input)
        total_cost_usd += cost_usd
        raw_items = fetch_dataset(dataset_id)

        is_blocked = detect_instagram_block(raw_items)
        if extract_type == "hashtag" and (is_blocked or len(raw_items) < (max_results * 0.3)):
            fallback_used = True
            failure_reason = "ip_blocked" if is_blocked else "low_results"
            proxy_mode = "residential"
            actor_input["phase1ProxyType"] = proxy_mode
            run_id, dataset_id, run_status, cost_usd = trigger_actor_and_wait(actor_input)
            total_cost_usd += cost_usd
            raw_items = fetch_dataset(dataset_id)

    except TimeoutError:
        ext_req.status = 'failed'
        db.session.commit()
        return jsonify({"error": "actor_timeout", "message": "Extraction timed out. Please try again."}), 504
    except RuntimeError as e:
        ext_req.status = 'failed'
        db.session.commit()
        return jsonify({"error": "actor_error", "message": str(e)}), 503
    except Exception as e:
        ext_req.status = 'failed'
        db.session.commit()
        return jsonify({"error": "internal_error", "message": str(e)}), 503

    runtime_seconds = int(time.time() - start_time)

    # ── 6. Block detection after run ─────────────────────────────────────────
    if detect_instagram_block(raw_items):
        _log_usage(user, ext_req, value, extract_type, max_results, 0, proxy_mode,
                   fallback_used, run_id, total_cost_usd, "failed",
                   "blocked_after_fallback", runtime_seconds)
        return jsonify({"error": "instagram_block_detected",
                        "message": "Instagram blocked the scraper. Try again later."}), 503

    # ── 7. Empty dataset ─────────────────────────────────────────────────────
    if not raw_items:
        _log_usage(user, ext_req, value, extract_type, max_results, 0, proxy_mode,
                   fallback_used, run_id, total_cost_usd, "success",
                   "empty_dataset", runtime_seconds)
        return jsonify({"success": True, "message": "No profiles found.", "profiles": [], "count": 0}), 200

    # ── 8. Normalise + filter ────────────────────────────────────────────────
    profiles = [normalize_profile(item) for item in raw_items]
    profiles = apply_filters(profiles, filters)
    returned_count = len(profiles)

    # ── 9. Deduct quota ──────────────────────────────────────────────────────
    increment_quota(user.id, returned_count)

    # ── 10. Log ──────────────────────────────────────────────────────────────
    _log_usage(user, ext_req, value, extract_type, max_results, returned_count,
               proxy_mode, fallback_used, run_id, total_cost_usd, "success",
               None, runtime_seconds)

    return jsonify({
        "success": True,
        "plan": plan,
        "profiles": profiles,
        "count": returned_count,
        "quota": get_quota_info(user)
    }), 200


def _log_usage(user, ext_req, query, query_type, requested, returned, proxy_type,
               fallback_used, run_id, cost_usd, status, failure_reason, runtime_seconds):
    from datetime import datetime
    
    log = UsageLog(
        user_id=user.id,
        query=query,
        query_type=query_type,
        requested_results=requested,
        returned_results=returned,
        proxy_type=proxy_type,
        fallback_used=fallback_used,
        apify_run_id=run_id,
        apify_cost_usd=cost_usd,
        status=status,
        failure_reason=failure_reason,
        runtime_seconds=runtime_seconds
    )
    db.session.add(log)
    db.session.flush() # get log.id
    
    ext_req.status = 'completed' if status == 'success' else 'failed'
    ext_req.usage_log_id = log.id
    ext_req.completed_at = datetime.utcnow()
    
    db.session.commit()
