"""app/routes/billing.py — Stripe integration endpoints."""
from flask import Blueprint, request, jsonify, current_app
from app.models import db, User
from app.utils.decorators import require_auth
import stripe

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/checkout', methods=['POST'])
@require_auth
def create_checkout():
    user = request.current_user
    plan_type = request.json.get('plan') # PRO | PRO_PLUS
    
    if plan_type not in ('PRO', 'PRO_PLUS'):
        return jsonify({"error": "invalid_plan"}), 400

    price_id = current_app.config.get(f"STRIPE_{plan_type}_PRICE_ID")
    if not price_id:
        return jsonify({"error": "billing_not_configured"}), 503

    try:
        # This is a stub for now
        return jsonify({
            "sessionId": "cs_test_stub",
            "url": "https://checkout.stripe.com/pay/stub"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    # Stub for Stripe webhook
    return jsonify({"status": "received"}), 200

@billing_bp.route('/portal', methods=['POST'])
@require_auth
def billing_portal():
    user = request.current_user
    if not user.stripe_customer_id:
        return jsonify({"error": "no_active_subscription"}), 400
        
    return jsonify({"url": "https://billing.stripe.com/portal/stub"}), 200

@billing_bp.route('/status', methods=['GET'])
@require_auth
def billing_status():
    user = request.current_user
    return jsonify({
        "plan": user.plan,
        "status": user.subscription_status,
        "end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None
    }), 200
