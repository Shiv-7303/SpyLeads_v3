SPYLEADS — POST-BUILD CORRECTION & HARDENING CHECKLIST
(Apply AFTER MVP works end-to-end)

==================================================
SECTION 1 — APIFY ACTOR STABILITY LAYER
==================================================

Goal:
Prevent empty datasets, login redirects, selector failures,
and Instagram blocking issues.

Add login redirect detection:

If page_url contains:
instagram.com/accounts/login

Then return:

{
  error: "instagram_login_required"
}

instead of empty dataset.


Add retry system:

Retry actor run up to 2 times if dataset empty.

Logic:

run_actor()
if dataset_empty:
    retry_actor()


Add selector fallback system:

Primary selector fails → use backup selector.

Example:

selector_v1
selector_v2
selector_v3


Add timeout protection:

If actor runtime > 120 seconds:

terminate run
return timeout error


Add proxy rotation strategy:

FREE users:
shared proxy pool

PRO users:
rotating datacenter proxies

PRO PLUS users:
rotating residential proxies (later upgrade)


Add dataset validation rule:

Reject dataset if:

results < 3 AND requested > 20

Return:

low_confidence_dataset


==================================================
SECTION 2 — DATABASE STORAGE OPTIMIZATION
==================================================

Goal:
Prevent database from growing uncontrollably.

Do NOT store permanently:

bio text
external links
raw dataset JSON


Store only:

username
followers
email flag
lead_score
status
tags
saved_list_relation


Add dataset caching layer:

Cache extraction results for:

15 minutes

If same query repeated:

return cached dataset


Add duplicate detection index:

UNIQUE(user_id, username)


Prevents repeated inserts.


Add cleanup scheduler:

Daily job:

delete leads older than 30 days
if not tagged or saved


==================================================
SECTION 3 — GUMROAD SUBSCRIPTION SYNC SYSTEM
==================================================

Goal:
Prevent cancelled users from continuing extraction.

Add webhook endpoint:

POST /gumroad-webhook


Handle events:

subscription_cancelled
subscription_refunded
subscription_failed


Example logic:

if subscription_cancelled:

set license_status = inactive


Add daily license revalidation job:

cron job runs every 24 hours:

recheck Gumroad subscription status


==================================================
SECTION 4 — QUOTA SYSTEM HARDENING
==================================================

Goal:
Prevent quota bypass exploits.

Move quota tracking server-side only.

Never trust frontend counters.


Deduct quota only AFTER successful dataset return.


Add emergency quota freeze mode:

admin_config:

quota_freeze = true


Stops all extractions instantly.


Add per-request limit validation:

FREE:

maxResults <= 10

PRO:

maxResults <= 50

PRO PLUS:

maxResults <= 150


Reject larger requests automatically.


==================================================
SECTION 5 — APIFY COST PROTECTION LAYER
==================================================

Goal:
Prevent unexpected scraping bill spikes.

Add monthly extraction caps:

FREE:

200/month

PRO:

1200/month

PRO PLUS:

4500/month


Add actor runtime monitor:

Store:

runtime_seconds per extraction


Alert if:

runtime > 90 seconds


Add dataset size limiter:

Reject actor output if:

results > requested_results


Prevents accidental overscraping.


Add budget alert trigger:

If monthly_profiles_scraped > threshold:

send admin notification


==================================================
SECTION 6 — ERROR HANDLING STANDARDIZATION
==================================================

Goal:
Improve frontend reliability and UX clarity.

Standardize backend error responses:


invalid_license → 401

quota_exceeded → 429

monthly_cap_reached → 429

kill_switch_active → 503

actor_timeout → 504

instagram_login_required → 503

dataset_empty → 200


Return structured response:

{
  success: false,
  error_code: "quota_exceeded",
  message: "Daily quota reached"
}


==================================================
SECTION 7 — LEAD INTELLIGENCE ENGINE IMPROVEMENTS
==================================================

Goal:
Improve scoring accuracy over time.

Make scoring weights configurable via admin panel:

email_score = 30
website_score = 20
followers_score = 15
keyword_score = 10


Store scoring config in:

remote_config table


Allow live adjustment without redeploy.


Add keyword dictionary file:

intent_keywords.json


Example:

hire
dm
contact
consulting
agency
coach


Editable dynamically.


==================================================
SECTION 8 — CRM-LITE STORAGE OPTIMIZATION
==================================================

Goal:
Keep lead manager scalable.

Store notes separately from leads table.

Structure:

lead_notes table


Add indexing:

user_id
lead_id


Add soft-delete support:

deleted_at column


Allows recovery later.


Add tag normalization table:

tags table

instead of storing raw strings repeatedly.


==================================================
SECTION 9 — SECURITY HARDENING
==================================================

Goal:
Prevent scraping abuse and API misuse.

Add request signature verification:

X-API-KEY header required


Add per-IP rate limiting:

max 30 requests per minute


Add extraction cooldown window:

minimum 5 seconds between extractions


Add admin route protection:

token-based authentication


==================================================
SECTION 10 — PERFORMANCE OPTIMIZATION
==================================================

Goal:
Keep response times fast under load.

Add async actor polling system:

Instead of:

wait_for_actor_completion

Use:

poll_status_every_2_seconds


Add background task queue:

Celery or lightweight worker


Add dataset pagination:

return first 50 results immediately


Load rest lazily.


==================================================
SECTION 11 — ADMIN MONITORING UPGRADES
==================================================

Goal:
Detect misuse early.

Track:

top users by extraction volume

failed actor runs

quota abuse attempts

empty dataset frequency


Display inside admin dashboard.


Add suspicious activity trigger:

if user runs >10 extractions/hour:

flag account


==================================================
SECTION 12 — DEPLOYMENT RELIABILITY FIXES
==================================================

Goal:
Prevent downtime surprises.

Add health endpoint:

GET /health

Returns:

status: ok


Add environment validation on startup:

check:

APIFY_TOKEN exists
DB connected
GUMROAD_KEY exists


Fail startup if missing.


Add logging system:

store:

actor errors
quota errors
license errors


Rotate logs weekly.


SPYLEADS — POST-BUILD CORRECTION CHECKLIST (PART 2)
ADVANCED PRODUCTION HARDENING LAYER

==================================================
SECTION 13 — ACTOR FAILURE AUTO-RECOVERY SYSTEM
==================================================

Goal:
Prevent extraction failures from impacting users.

Add actor failure retry tiers:

retry_1 → same actor rerun
retry_2 → fallback selector mode
retry_3 → fallback proxy pool


If still failed:

return:

{
  error: "extraction_temporarily_unavailable"
}


Track failure reason types:

login_redirect
selector_missing
timeout
proxy_blocked
dataset_empty


Store inside:

actor_failures table


Use for debugging patterns later.


==================================================
SECTION 14 — SELECTOR VERSION CONTROL SYSTEM
==================================================

Goal:
Handle Instagram DOM changes safely.

Create selector config file:

selectors.json


Example:

{
  "username_selector": "h2",
  "bio_selector": "div.bio",
  "followers_selector": "span.followers"
}


Load dynamically inside actor.


If selector breaks:

update JSON

no redeploy required.


==================================================
SECTION 15 — QUERY CACHE SYSTEM
==================================================

Goal:
Reduce APify cost and response time.

Cache structure:

query_hash
timestamp
dataset_reference


Example:

hash("fitnesscoach_50_email=true")


Cache TTL:

15 minutes


If identical request arrives:

return cached dataset


Skip actor run.


==================================================
SECTION 16 — EXTRACTION PRIORITY QUEUE
==================================================

Goal:
Improve experience for PRO PLUS users.

Queue logic:

FREE users → normal queue

PRO users → medium priority queue

PRO PLUS users → high priority queue


Example implementation:

queue_priority:

FREE = 1
PRO = 2
PRO_PLUS = 3


Sort actor runs before execution.


==================================================
SECTION 17 — USER BEHAVIOR ANALYTICS ENGINE
==================================================

Goal:
Understand usage patterns.

Track:

search types used
avg results requested
filters used
export frequency
tag usage frequency


Store inside:

analytics_events table


Example:

{
  user_id: 82,
  event: "extract_hashtag",
  value: "fitnesscoach"
}


Used later for:

feature roadmap
pricing optimization
conversion improvement


==================================================
SECTION 18 — SMART ABUSE DETECTION SYSTEM
==================================================

Goal:
Detect automation misuse early.

Flag account if:

>15 extractions/hour

or

>3 identical queries/minute

or

>dataset requests without export activity


Set:

risk_score += 20


If risk_score > threshold:

auto-disable extraction temporarily


==================================================
SECTION 19 — DATASET SIZE PROTECTION SYSTEM
==================================================

Goal:
Prevent accidental overscraping.

Before returning dataset:

if dataset_size > requested_size:

truncate dataset


Example:

requested = 50
returned = 80

keep only first 50


Avoid quota miscalculation.


==================================================
SECTION 20 — LEAD RELEVANCE BOOST ENGINE
==================================================

Goal:
Improve perceived dataset quality.

Add ranking logic:

sort by:

email_present DESC
followers DESC
lead_score DESC


Return highest-quality leads first.


Users see:

better leads faster


==================================================
SECTION 21 — EXPORT HISTORY TRACKER
==================================================

Goal:
Add traceability.

Store:

export_type
timestamp
list_id
filters_used


Example:

{
  export: "csv",
  tag: "Hot Leads"
}


Allows:

usage insights
export analytics
future billing upgrades


==================================================
SECTION 22 — FEATURE FLAG SYSTEM
==================================================

Goal:
Enable gradual rollout of features.

Create:

feature_flags table


Example:

enable_competitor_mode = true
enable_micro_influencer_mode = true
enable_google_sheets_export = false


Loaded via:

GET /config


Allows silent testing.


==================================================
SECTION 23 — BACKGROUND CLEANUP WORKERS
==================================================

Goal:
Maintain system performance.

Daily cron tasks:

delete stale datasets

remove unused cached queries

compress logs

remove orphan tags


Weekly cron:

archive inactive users


==================================================
SECTION 24 — USER SESSION MANAGEMENT
==================================================

Goal:
Secure dashboard access.

Add:

JWT-based session tokens


Expiration:

24 hours


Refresh token support:

enabled


Logout invalidates session.


==================================================
SECTION 25 — PLAN UPGRADE DETECTION ENGINE
==================================================

Goal:
Instantly unlock features after payment.

On each request:

recheck cached plan status


If upgrade detected:

update quota immediately


No relogin required.


==================================================
SECTION 26 — ACTOR HEALTH MONITOR
==================================================

Goal:
Detect scraping instability early.

Track:

avg runtime

success_rate

empty_dataset_rate


Alert admin if:

success_rate < 85%


==================================================
SECTION 27 — API RESPONSE TIME OPTIMIZER
==================================================

Goal:
Improve frontend speed perception.

Return immediately:

job_started: true


Then poll:

GET /job-status/:id


Instead of waiting synchronously.


==================================================
SECTION 28 — LEAD DUPLICATE GLOBAL INDEX
==================================================

Goal:
Prevent repeated datasets across sessions.

Create global table:

global_usernames


Structure:

username
first_seen_timestamp


Avoid storing duplicates repeatedly.


==================================================
SECTION 29 — LIGHTWEIGHT EVENT LOGGING SYSTEM
==================================================

Goal:
Enable debugging without heavy infra.

Log:

actor_errors

quota_failures

license_failures

empty_results


Store last 7 days only.


==================================================
SECTION 30 — COST FORECAST ENGINE
==================================================

Goal:
Predict APify billing risk.

Daily compute:

profiles_scraped_today


Estimate:

monthly_projection


Example:

today = 12k profiles

projection = 360k/month


Trigger alert if above safe threshold.


SPYLEADS — FINAL SYSTEM MATURITY STATE (AFTER FULL HARDENING)

==================================================
PRODUCT CATEGORY TRANSFORMATION
==================================================

SpyLeads is no longer:

❌ Instagram scraper
❌ CSV export tool
❌ hashtag extractor

SpyLeads becomes:

✅ Instagram Lead Intelligence Platform
✅ Competitor Audience Discovery Engine
✅ Micro-Influencer Finder
✅ Outreach Workflow Organizer (CRM-lite)
✅ Dataset Scoring & Qualification System


==================================================
CORE PLATFORM CAPABILITIES (FINAL STATE)
==================================================

Lead Discovery Engine

Supports:

Hashtag search
Competitor followers extraction
Post likers extraction (optional phase 2)
Keyword-filtered bio discovery


Lead Qualification Engine

Each lead enriched with:

lead_score (0–100)
intent_flag
email_presence_flag
website_presence_flag
business_indicator
activity_indicator
influencer_tier


Lead Ranking Engine

Datasets automatically sorted by:

email availability
followers
intent keywords
lead score priority


CRM-lite Lead Manager

Each lead supports:

tags
status workflow
notes
saved lists
duplicate protection


Workflow Pipeline States

New
Qualified
Contacted
Replied
Converted
Closed


==================================================
AUTOMATION & INTELLIGENCE LAYER
==================================================

Auto-tagging engine assigns:

Hot
Influencer
Coach Lead
Business Lead
High Intent


Intent Detection Engine

Bio scanned for:

hire
contact
consulting
agency
DM
services


Micro-Influencer Classifier

Automatically labels:

1k–50k followers


Activity Filter Engine

Detects:

recent posting accounts


Lead Quality Score Engine

Weighted scoring:

email presence
website presence
follower threshold
service keywords
category metadata


==================================================
DATA PROTECTION & COST CONTROL SYSTEM
==================================================

Quota Protection Layer

FREE      10/day
PRO       50/day
PRO PLUS  150/day


Monthly Caps

FREE      200/month
PRO       1200/month
PRO PLUS  4500/month


Query Cache System

Duplicate queries avoided
Actor calls minimized
Response speed improved


Dataset Validation Engine

Rejects low-confidence extraction outputs


Actor Runtime Monitor

Detects:

timeouts
selector failure
proxy blocks
login redirects


==================================================
SCRAPING RESILIENCE LAYER
==================================================

Selector Version Control

Selectors stored in JSON
Hot-patchable without redeploy


Fallback Selector Chains

Primary selector
Secondary selector
Tertiary selector


Proxy Rotation Strategy

Shared pool (FREE)
Rotating datacenter (PRO)
Rotating residential (future PRO PLUS upgrade)


Retry Engine

Auto reruns failed actor jobs


Login Redirect Detection

Stops empty dataset responses


==================================================
PERFORMANCE OPTIMIZATION LAYER
==================================================

Priority Queue System

FREE users → standard queue
PRO users → accelerated queue
PRO PLUS users → priority queue


Async Extraction Engine

job_started response returned immediately

frontend polls:

GET /job-status/:id


Partial Dataset Streaming

first 50 leads returned instantly
remaining appended asynchronously


Short-term Dataset Cache

15 minute reuse window


==================================================
CRM-LITE WORKFLOW ENGINE
==================================================

Saved Lead Lists

User-defined collections:

Fitness Influencers
Dubai Realtors
Salon Owners Mumbai
Startup Founders


Lead Notes System

Free-text annotations per lead


Tag Filtering Engine

Filter by:

Hot
Influencer
Contacted
Converted


Export by Segment

Export:

Hot leads
Influencers
Email leads
Status-based lists


==================================================
EXPORT & INTEGRATION LAYER
==================================================

CSV Export Engine

Selective column export
Selective tag export
Selective status export


Google Sheets Sync Engine (Phase 2)

OAuth integration
Row append automation
Token refresh support


Future Integrations (ready architecture)

Zapier
Webhook exports
Notion sync
HubSpot sync


==================================================
SECURITY & ABUSE PREVENTION LAYER
==================================================

License Validation Engine

Gumroad API verification
Daily revalidation cron


Subscription Sync Webhook

Handles:

refund
cancellation
payment failure


API Protection Layer

X-API-KEY validation
JWT sessions
rate limiting


Suspicious Activity Detector

Triggers if:

>15 extractions/hour
duplicate query spam
non-export scraping behavior


Auto Temporary Suspension Engine

Risk-score threshold enforcement


==================================================
ADMIN CONTROL PANEL CAPABILITIES
==================================================

Live user monitoring

Extraction activity dashboards

Quota reset controls

License blacklist system

Kill switch toggle

Remote config editor

Actor health metrics

APify cost projections


==================================================
REMOTE CONFIG CONTROL SYSTEM
==================================================

Dynamic control over:

daily limits
monthly caps
feature toggles
selector versions
scoring weights


No redeploy required


==================================================
COST FORECAST ENGINE
==================================================

Tracks:

profiles_scraped_today

Predicts:

monthly scraping volume

Triggers:

admin alerts before cost spikes


==================================================
ANALYTICS & PRODUCT INTELLIGENCE LAYER
==================================================

Tracks:

search types used
filter usage frequency
export behavior
tag usage patterns


Used for:

pricing optimization
feature roadmap planning
conversion funnel tuning


==================================================
SYSTEM SCALABILITY READINESS
==================================================

Supports safely:

100 users → immediately

500 users → with proxy scaling

1000 users → with queue separation

3000 users → with actor parallelization layer


==================================================
BUSINESS POSITIONING AFTER COMPLETION
==================================================

SpyLeads competes against:

PhantomBuster (simplified alternative)
TexAu (lightweight replacement)
Inflact (lead discovery subset)
Apify actors (user-friendly wrapper)


Unique positioning:

Affordable Instagram Lead Intelligence SaaS
for agencies, freelancers, outreach teams


==================================================
FINAL ARCHITECTURE MATURITY LEVEL
==================================================

Infrastructure maturity:

Tier 1 Indie SaaS

Operational readiness:

Production capable

Scaling readiness:

Early-stage commercial SaaS

Failure resilience:

Selector-safe
proxy-safe
quota-safe
billing-safe


SpyLeads becomes a deployable, monetizable,
and scalable lead intelligence platform.