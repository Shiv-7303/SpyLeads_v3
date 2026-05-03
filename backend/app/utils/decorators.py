"""app/utils/decorators.py — Route decorators for JWT and admin auth."""
import os
from functools import wraps
import jwt
from flask import request, jsonify, current_app
from app.models import User

def require_auth(f):
    """Protects a route — expects Authorization: Bearer <token>."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "unauthorized", "message": "Missing token"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token_expired", "message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid_token", "message": "Invalid token"}), 401

        user = User.query.get(payload.get("user_id"))
        if not user:
            return jsonify({"error": "user_not_found"}), 401
        
        if user.subscription_status not in ("active", "past_due") and not user.is_admin:
            return jsonify({
                "error": "account_inactive", 
                "message": f"Account is {user.subscription_status}"
            }), 403

        request.current_user = user
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """
    Protects admin routes.
    Checks for X-Admin-Key OR checks if current_user.is_admin is True.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Check for Admin API Key (direct access)
        admin_key = current_app.config.get("ADMIN_API_KEY", "")
        provided = request.headers.get("X-ADMIN-KEY") or request.args.get("key")
        if admin_key and provided == admin_key:
            return f(*args, **kwargs)

        # 2. Check for User Session + Admin Flag
        # This requires the route to also use require_auth or have token manually checked
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
                user = User.query.get(payload.get("user_id"))
                if user and user.is_admin:
                    request.current_user = user
                    return f(*args, **kwargs)
            except:
                pass

        return jsonify({"error": "unauthorized", "message": "Admin access required"}), 403
    return decorated

# Alias for backward compatibility if needed
require_jwt = require_auth
