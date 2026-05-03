"""app/routes/leads.py — Saved leads CRUD."""
from flask import Blueprint, request, jsonify
from app.models import db, Lead
from app.utils.decorators import require_auth

leads_bp = Blueprint('leads', __name__, url_prefix='/leads')

@leads_bp.route('', methods=['GET'])
@require_auth
def list_leads():
    user = request.current_user
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    status_filter = request.args.get('status')

    query = Lead.query.filter_by(user_id=user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    paginated = query.order_by(Lead.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "leads": [l.to_dict() for l in paginated.items],
        "total": paginated.total,
        "page": page,
        "pages": paginated.pages,
    }), 200

@leads_bp.route('', methods=['POST'])
@require_auth
def save_lead():
    user = request.current_user
    data = request.json or {}

    username = data.get('username', '').strip()
    if not username:
        return jsonify({"error": "bad_request", "message": "username required"}), 400

    # Prevent duplicates
    existing = Lead.query.filter_by(user_id=user.id, username=username).first()
    if existing:
        return jsonify({"error": "duplicate", "message": "Lead already saved", "lead": existing.to_dict()}), 409

    lead = Lead(
        user_id=user.id,
        username=username,
        full_name=data.get('full_name', ''),
        followers=data.get('followers', 0),
        email=data.get('email', ''),
        bio=data.get('bio', ''),
        category=data.get('category', ''),
        location=data.get('location', ''),
        external_url=data.get('external_url', ''),
        profile_url=data.get('profile_url', ''),
        is_verified=data.get('is_verified', False),
        is_business=data.get('is_business', False),
        lead_score=data.get('lead_score', 0),
        high_intent=data.get('high_intent', False),
        influencer_tier=data.get('influencer_tier', ''),
        source_hashtag=data.get('source_hashtag', ''),
        status='new',
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify({"success": True, "lead": lead.to_dict()}), 201

@leads_bp.route('/<uuid:lead_id>', methods=['PATCH'])
@require_auth
def update_lead(lead_id):
    user = request.current_user
    lead = Lead.query.filter_by(id=lead_id, user_id=user.id).first_or_404()
    data = request.json or {}

    if 'status' in data:
        lead.status = data['status']
    if 'lead_score' in data:
        lead.lead_score = data['lead_score']
    if 'high_intent' in data:
        lead.high_intent = data['high_intent']

    db.session.commit()
    return jsonify({"success": True, "lead": lead.to_dict()}), 200

@leads_bp.route('/<uuid:lead_id>', methods=['DELETE'])
@require_auth
def delete_lead(lead_id):
    user = request.current_user
    lead = Lead.query.filter_by(id=lead_id, user_id=user.id).first_or_404()
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"success": True}), 200
