"""app/routes/export.py — CSV export endpoints."""
import csv
import io
from flask import Blueprint, request, jsonify, Response
from app.models import db, Lead
from app.utils.decorators import require_auth

export_bp = Blueprint('export', __name__, url_prefix='/export')

@export_bp.route('/csv', methods=['GET'])
@require_auth
def export_csv():
    user = request.current_user
    status_filter = request.args.get('status')

    query = Lead.query.filter_by(user_id=user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    leads = query.order_by(Lead.created_at.desc()).all()

    if not leads:
        return jsonify({"error": "no_data", "message": "No leads to export"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Username", "Full Name", "Followers", "Email", "Bio",
        "Category", "Location", "External URL", "Profile URL",
        "Verified", "Business", "Lead Score", "High Intent", "Tier", "Source", "Status", "Saved At"
    ])
    for lead in leads:
        writer.writerow([
            lead.username, lead.full_name, lead.followers, lead.email,
            lead.bio, lead.category, lead.location, lead.external_url,
            lead.profile_url, lead.is_verified, lead.is_business,
            lead.lead_score, lead.high_intent, lead.influencer_tier, lead.source_hashtag, lead.status,
            lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else ""
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=spyleads_export.csv"}
    )
