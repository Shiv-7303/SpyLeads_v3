"""app/routes/admin.py — Admin analytics endpoints."""
from flask import Blueprint, jsonify, request
from app.models import db, UsageLog
from app.utils.decorators import require_admin

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/proxy-cost', methods=['GET'])
@require_admin
def proxy_cost():
    total_runs = db.session.query(UsageLog).count()

    if total_runs == 0:
        return jsonify({
            "summary": {"total_runs": 0, "datacenter_runs": 0, "residential_runs": 0,
                        "fallback_rate_percent": 0.0, "total_actual_cost_usd": 0.0,
                        "status": "healthy", "alert": False},
            "recent_runs": []
        }), 200

    dc_runs = db.session.query(UsageLog).filter_by(proxy_type="datacenter").count()
    res_runs = db.session.query(UsageLog).filter_by(proxy_type="residential").count()
    fallback_rate = (res_runs / total_runs) * 100

    status = "healthy"
    if fallback_rate > 20:
        status = "critical"
    elif fallback_rate > 10:
        status = "warning"

    total_cost = db.session.query(db.func.sum(UsageLog.apify_cost_usd)).scalar() or 0.0

    recent = db.session.query(UsageLog).order_by(UsageLog.created_at.desc()).limit(20).all()
    history = [{
        "id": str(r.id),
        "run_id": r.apify_run_id,
        "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
        "proxy": r.proxy_type,
        "fallback": r.fallback_used,
        "requested": r.requested_results,
        "returned": r.returned_results,
        "cost_usd": r.apify_cost_usd or 0.0,
        "runtime": r.runtime_seconds,
    } for r in recent]

    return jsonify({
        "summary": {
            "total_runs": total_runs,
            "datacenter_runs": dc_runs,
            "residential_runs": res_runs,
            "fallback_rate_percent": round(fallback_rate, 2),
            "total_actual_cost_usd": round(total_cost, 4),
            "status": status,
            "alert": status in ["warning", "critical"]
        },
        "recent_runs": history
    }), 200

@admin_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    from app.models import User
    users = User.query.order_by(User.created_at.desc()).limit(50).all()
    return jsonify([u.to_dict() for u in users]), 200

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def stats():
    from app.models import User, UsageLog
    total_users = User.query.count()
    pro_users = User.query.filter_by(plan='PRO').count()
    pro_plus_users = User.query.filter_by(plan='PRO_PLUS').count()
    free_users = User.query.filter_by(plan='FREE').count()
    total_extractions = db.session.query(db.func.sum(UsageLog.returned_results)).scalar() or 0
    total_cost = db.session.query(db.func.sum(UsageLog.apify_cost_usd)).scalar() or 0.0

    return jsonify({
        "users": {"total": total_users, "free": free_users, "pro": pro_users, "pro_plus": pro_plus_users},
        "extractions": {"total_profiles": total_extractions},
        "cost": {"total_usd": round(total_cost, 4)}
    }), 200
