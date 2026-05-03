"""app/services/stripe_service.py — Stripe billing integration."""
import stripe
from flask import current_app


def get_stripe():
    stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")
    return stripe


def create_checkout_session(user, price_id: str, success_url: str, cancel_url: str) -> str:
    """Creates a Stripe Checkout session and returns the URL."""
    s = get_stripe()

    # Create or retrieve Stripe customer
    if user.stripe_customer_id:
        customer_id = user.stripe_customer_id
    else:
        customer = s.Customer.create(email=user.email, metadata={"user_id": user.id})
        customer_id = customer.id
        from app.models import db
        user.stripe_customer_id = customer_id
        db.session.commit()

    session = s.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user.id},
    )
    return session.url


def create_portal_session(user, return_url: str) -> str:
    """Creates a Stripe Customer Portal session."""
    s = get_stripe()
    session = s.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Parses and handles Stripe webhook events. Returns event dict."""
    s = get_stripe()
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
    try:
        event = s.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid webhook signature")

    return _process_event(event)


def _process_event(event: dict) -> dict:
    """Routes Stripe events to the appropriate handler."""
    from app.models import db, User

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.updated":
        _sync_subscription(data)
    elif event_type == "customer.subscription.deleted":
        _cancel_subscription(data)
    elif event_type == "invoice.payment_failed":
        _mark_past_due(data)

    return {"handled": event_type}


def _sync_subscription(subscription):
    from app.models import db, User
    customer_id = subscription.get("customer")
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    status = subscription.get("status")
    price_id = subscription["items"]["data"][0]["price"]["id"] if subscription.get("items") else None

    price_to_plan = {
        current_app.config.get("STRIPE_PRO_PRICE_ID"): "PRO",
        current_app.config.get("STRIPE_PRO_PLUS_PRICE_ID"): "PRO_PLUS",
    }

    user.plan = price_to_plan.get(price_id, "FREE")
    user.status = "active" if status == "active" else status
    user.stripe_subscription_id = subscription.get("id")
    db.session.commit()


def _cancel_subscription(subscription):
    from app.models import db, User
    customer_id = subscription.get("customer")
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if user:
        user.plan = "FREE"
        user.status = "active"
        user.stripe_subscription_id = None
        db.session.commit()


def _mark_past_due(invoice):
    from app.models import db, User
    customer_id = invoice.get("customer")
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if user:
        user.status = "past_due"
        db.session.commit()
