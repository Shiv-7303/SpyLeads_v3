"""app/routes/auth.py — Register, Login, Profile endpoints."""
import jwt
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from app.models import db, User
from app.utils.decorators import require_auth
from app.services.quota_service import get_quota_info, seed_default_config, get_daily_quota
from app.utils.helpers import get_ist_now

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

def _generate_token(user: User) -> str:
    expiry_hours = current_app.config.get("JWT_EXPIRY_HOURS", 168)
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "plan": user.plan,
        "exp": datetime.utcnow() + timedelta(hours=expiry_hours)
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "bad_request", "message": "Email and password required"}), 400
    
    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "invalid_email", "message": "Invalid email format"}), 400

    if len(password) < 8:
        return jsonify({"error": "weak_password", "message": "Password must be at least 8 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email_taken", "message": "Email already registered"}), 409

    # 1. Create User
    user = User(
        email=email, 
        plan='FREE', 
        subscription_status='active',
        is_admin=False
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush() # Get user.id

    # 2. Create DailyQuota for today
    now = get_ist_now().replace(tzinfo=None)
    get_daily_quota(user.id, now.date())

    db.session.commit()

    seed_default_config()
    token = _generate_token(user)

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "email": user.email,
            "plan": user.plan
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid_credentials", "message": "Invalid email or password"}), 401

    if user.subscription_status not in ('active', 'past_due'):
        return jsonify({"error": "account_inactive", "message": f"Account is {user.subscription_status}"}), 403

    token = _generate_token(user)
    quota = get_quota_info(user)

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "email": user.email,
            "plan": user.plan,
            "daily_remaining": quota["daily_remaining"]
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    user = request.current_user
    q = get_quota_info(user)
    
    return jsonify({
        "email": user.email,
        "plan": user.plan,
        "subscription_status": user.subscription_status,
        "subscription_end_date": user.subscription_end_date.strftime("%Y-%m-%d") if user.subscription_end_date else None,
        "daily_used": q["daily_used"],
        "daily_limit": q["daily_limit"],
        "monthly_used": q["monthly_used"],
        "monthly_cap": q["monthly_limit"]
    }), 200

@auth_bp.route('/quota', methods=['GET'])
@require_auth
def quota():
    user = request.current_user
    return jsonify(get_quota_info(user)), 200

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    user = request.current_user
    data = request.json or {}
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"error": "bad_request", "message": "Both current and new passwords required"}), 400
    
    if not user.check_password(current_password):
        return jsonify({"error": "invalid_credentials", "message": "Incorrect current password"}), 401
    
    if len(new_password) < 8:
        return jsonify({"error": "weak_password", "message": "New password must be at least 8 characters"}), 400
        
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Password updated successfully"}), 200
