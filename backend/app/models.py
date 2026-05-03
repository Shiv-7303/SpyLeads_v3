"""
app/models.py — All SQLAlchemy models for SpyLeads.
Matches Phase 1 Database Models spec.
"""
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import UniqueConstraint
import bcrypt

db = SQLAlchemy()

# ─── System Config ────────────────────────────────────────────────────────────

class AppConfig(db.Model):
    __tablename__ = 'app_config'
    key = db.Column(db.String(50), primary_key=True)
    value_json = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(50), nullable=True)

# ─── Users & Auth ─────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identity
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Plan
    plan = db.Column(db.String(50), default='FREE')  # FREE | PRO | PRO_PLUS

    # Stripe
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    subscription_status = db.Column(db.String(20), default='active')  # active | cancelled | past_due
    subscription_end_date = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    daily_quotas = db.relationship('DailyQuota', backref='user', lazy=True)
    usage_logs = db.relationship('UsageLog', backref='user', lazy=True)
    extraction_requests = db.relationship('ExtractionRequest', backref='user', lazy=True)
    leads = db.relationship('Lead', backref='user', lazy=True)
    saved_lists = db.relationship('SavedList', backref='user', lazy=True)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "plan": self.plan,
            "status": self.subscription_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# ─── Quota & Usage Tracking ───────────────────────────────────────────────────

class DailyQuota(db.Model):
    __tablename__ = 'daily_quotas'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    daily_used = db.Column(db.Integer, default=0)
    monthly_used = db.Column(db.Integer, default=0)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_user_daily_quota'),
    )

class UsageLog(db.Model):
    """Extended UsageLog (combines previous UsageLog + ActorRun)"""
    __tablename__ = 'usage_logs'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    
    query = db.Column(db.String(255))
    query_type = db.Column(db.String(50))
    requested_results = db.Column(db.Integer)
    returned_results = db.Column(db.Integer)
    
    proxy_type = db.Column(db.String(50), default='datacenter')
    fallback_used = db.Column(db.Boolean, default=False)
    
    apify_run_id = db.Column(db.String(255), nullable=True)
    apify_cost_usd = db.Column(db.Float, nullable=True)
    apify_compute_units = db.Column(db.Float, nullable=True)
    residential_mb = db.Column(db.Float, nullable=True)
    datacenter_mb = db.Column(db.Float, nullable=True)
    
    from_cache = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50))  # success | failed | partial
    failure_reason = db.Column(db.String(255), nullable=True)
    runtime_seconds = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExtractionRequest(db.Model):
    """Tracks asynchronous extraction jobs"""
    __tablename__ = 'extraction_requests'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    query = db.Column(db.String(255))
    query_type = db.Column(db.String(50))
    filters_json = db.Column(db.JSON, nullable=True)
    requested_results = db.Column(db.Integer)
    
    status = db.Column(db.String(50), default='pending')  # pending | processing | completed | failed
    usage_log_id = db.Column(UUID(as_uuid=True), db.ForeignKey('usage_logs.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class HashtagCache(db.Model):
    __tablename__ = 'hashtag_cache'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hashtag = db.Column(db.String(255), unique=True, nullable=False)
    dataset = db.Column(db.JSON, nullable=False)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    access_count = db.Column(db.Integer, default=0)

# ─── CRM & Leads ──────────────────────────────────────────────────────────────

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    # Core data
    username = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    followers = db.Column(db.Integer, default=0)
    email = db.Column(db.String(255))
    bio = db.Column(db.Text)
    category = db.Column(db.String(255))
    location = db.Column(db.String(255))
    external_url = db.Column(db.String(500))
    profile_url = db.Column(db.String(500))
    
    is_verified = db.Column(db.Boolean, default=False)
    is_business = db.Column(db.Boolean, default=False)

    # CRM Fields
    lead_score = db.Column(db.Integer, default=0)
    high_intent = db.Column(db.Boolean, default=False)
    influencer_tier = db.Column(db.String(50))  # micro | mid | macro
    status = db.Column(db.String(50), default='new')  # new | qualified | contacted | replied | converted | closed
    source_hashtag = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead_tags = db.relationship('LeadTag', backref='lead', lazy=True, cascade='all, delete-orphan')
    lead_notes = db.relationship('LeadNote', backref='lead', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": str(self.id),
            "username": self.username,
            "full_name": self.full_name,
            "followers": self.followers,
            "email": self.email,
            "bio": self.bio,
            "category": self.category,
            "location": self.location,
            "external_url": self.external_url,
            "profile_url": self.profile_url,
            "is_verified": self.is_verified,
            "is_business": self.is_business,
            "lead_score": self.lead_score,
            "high_intent": self.high_intent,
            "influencer_tier": self.influencer_tier,
            "status": self.status,
            "source_hashtag": self.source_hashtag,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(20), nullable=True)

class LeadTag(db.Model):
    __tablename__ = 'lead_tags'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = db.Column(UUID(as_uuid=True), db.ForeignKey('leads.id'), nullable=False)
    tag_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tags.id'), nullable=False)
    
    tag = db.relationship('Tag')

class LeadNote(db.Model):
    __tablename__ = 'lead_notes'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = db.Column(UUID(as_uuid=True), db.ForeignKey('leads.id'), nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedList(db.Model):
    __tablename__ = 'saved_lists'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    list_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    list_leads = db.relationship('ListLead', backref='saved_list', lazy=True, cascade='all, delete-orphan')

class ListLead(db.Model):
    __tablename__ = 'list_leads'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = db.Column(UUID(as_uuid=True), db.ForeignKey('saved_lists.id'), nullable=False)
    lead_id = db.Column(UUID(as_uuid=True), db.ForeignKey('leads.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
