# SpyLeads — Complete Build Checklist (Production)
> Stack: Flask + Stripe + Apify + PostgreSQL + Render
> Payment: Stripe (no Gumroad)
> Monitoring: Real Apify cost data in Admin Dashboard
> Last Updated: May 2026

---

# ═══════════════════════════════════════════
# PHASE 0 — PROJECT FOUNDATION & SETUP
# ═══════════════════════════════════════════

## 0.1 Folder Structure

- [ ] Create project root folder: `spyleads-backend/`
- [ ] Create subfolder structure:
  ```
  spyleads-backend/
  ├── app/
  │   ├── __init__.py
  │   ├── models.py
  │   ├── routes/
  │   │   ├── __init__.py
  │   │   ├── auth.py
  │   │   ├── extract.py
  │   │   ├── leads.py
  │   │   ├── billing.py
  │   │   ├── export.py
  │   │   └── admin.py
  │   ├── services/
  │   │   ├── apify_service.py
  │   │   ├── stripe_service.py
  │   │   ├── quota_service.py
  │   │   ├── lead_scorer.py
  │   │   ├── cache_service.py
  │   │   └── export_service.py
  │   └── utils/
  │       ├── decorators.py
  │       └── helpers.py
  ├── migrations/
  ├── tests/
  │   ├── test_auth.py
  │   ├── test_extract.py
  │   ├── test_billing.py
  │   └── test_admin.py
  ├── config.py
  ├── run.py
  ├── requirements.txt
  ├── .env
  ├── .env.example
  └── Procfile
  ```

## 0.2 Environment Setup

- [ ] Create Python virtualenv: `python -m venv venv`
- [ ] Activate: `source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows)
- [ ] Install core dependencies:
  ```
  Flask==3.0.0
  Flask-SQLAlchemy==3.1.1
  Flask-Migrate==4.0.5
  Flask-Login==0.6.3
  Flask-CORS==4.0.0
  psycopg2-binary==2.9.9
  apify-client==1.7.1
  stripe==8.5.0
  python-dotenv==1.0.0
  bcrypt==4.1.2
  PyJWT==2.8.0
  requests==2.31.0
  pandas==2.1.4
  gunicorn==21.2.0
  ```
- [ ] Generate requirements.txt: `pip freeze > requirements.txt`

## 0.3 Environment Variables

- [ ] Create `.env` file with these keys:
  ```
  # Flask
  SECRET_KEY=your_secret_key_here
  FLASK_ENV=development
  DATABASE_URL=postgresql://user:pass@localhost/spyleads

  # Apify
  APIFY_TOKEN=your_apify_api_token
  APIFY_ACTOR_ID=your_username/spyleads-instagram-scraper

  # Stripe
  STRIPE_SECRET_KEY=sk_test_xxxxx
  STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
  STRIPE_WEBHOOK_SECRET=whsec_xxxxx
  STRIPE_PRO_PRICE_ID=price_xxxxx
  STRIPE_PRO_PLUS_PRICE_ID=price_xxxxx

  # Admin
  ADMIN_SECRET_KEY=your_admin_secret

  # Config
  KILL_SWITCH=false
  FREE_DAILY_LIMIT=10
  PRO_DAILY_LIMIT=50
  PRO_PLUS_DAILY_LIMIT=150
  ```
- [ ] Create `.env.example` (same keys, empty values — commit this)
- [ ] Add `.env` to `.gitignore`

## 0.4 Database Setup

- [ ] Install PostgreSQL locally for development
- [ ] Create local database: `createdb spyleads_dev`
- [ ] Test connection: `psql -d spyleads_dev`
- [ ] Initialize Flask-Migrate: `flask db init`

## 0.5 Git Setup

- [ ] Initialize repo: `git init`
- [ ] Create `.gitignore` (include: venv/, .env, __pycache__, *.pyc)
- [ ] First commit: `git commit -m "project structure initialized"`
- [ ] Push to GitHub: `spyleads-backend` repo

---

# MANUAL TESTING CHECKPOINT 0

```
Test: Environment boots correctly
Command: flask run
Expected: Server starts on http://127.0.0.1:5000
Pass: 200 on GET /health
Fail: Import errors or missing env vars
```

---

# ═══════════════════════════════════════════
# PHASE 1 — DATABASE MODELS
# ═══════════════════════════════════════════

## 1.1 Users Table

- [ ] Create `User` model with fields:
  ```python
  id               (UUID, primary key)
  email            (String, unique, not null)
  password_hash    (String, not null)
  plan             (String: 'free'/'pro'/'pro_plus', default 'free')
  stripe_customer_id    (String, nullable)
  stripe_subscription_id (String, nullable)
  subscription_status   (String: 'active'/'cancelled'/'past_due', nullable)
  subscription_end_date (DateTime, nullable)
  created_at       (DateTime, default now)
  is_active        (Boolean, default True)
  is_admin         (Boolean, default False)
  ```

## 1.2 Usage Logs Table

- [ ] Create `UsageLog` model:
  ```python
  id               (UUID, primary key)
  user_id          (FK → users.id)
  profiles_requested (Integer)
  profiles_returned  (Integer)
  hashtag          (String)
  extraction_mode  (String: 'fast'/'standard'/'full')
  proxy_type       (String: 'datacenter'/'residential'/'hybrid')
  apify_run_id     (String, nullable)
  apify_cost_usd   (Float, nullable)
  apify_compute_units (Float, nullable)
  apify_proxy_mb   (Float, nullable)
  apify_datacenter_mb (Float, nullable)
  apify_residential_mb (Float, nullable)
  duration_seconds (Integer)
  status           (String: 'success'/'failed'/'partial')
  created_at       (DateTime, default now)
  ```

## 1.3 Daily Quota Table

- [ ] Create `DailyQuota` model:
  ```python
  id               (UUID, primary key)
  user_id          (FK → users.id, unique per date)
  date             (Date, not null)
  profiles_used    (Integer, default 0)
  monthly_used     (Integer, default 0)
  last_reset       (DateTime)
  ```

## 1.4 Leads Table

- [ ] Create `Lead` model:
  ```python
  id               (UUID, primary key)
  user_id          (FK → users.id)
  username         (String, not null)
  followers        (Integer)
  bio              (Text)
  email            (String, nullable)
  external_url     (String, nullable)
  is_verified      (Boolean)
  category         (String, nullable)
  lead_score       (Integer, default 0)
  high_intent      (Boolean, default False)
  influencer_tier  (String: 'micro'/'mid'/'macro', nullable)
  status           (String: 'new'/'qualified'/'contacted'/'replied'/'converted'/'closed', default 'new')
  source_hashtag   (String)
  created_at       (DateTime, default now)
  updated_at       (DateTime)
  ```

## 1.5 Lead Tags Table

- [ ] Create `LeadTag` model:
  ```python
  id               (UUID, primary key)
  lead_id          (FK → leads.id)
  tag_name         (String)
  created_at       (DateTime)
  ```

## 1.6 Lead Notes Table

- [ ] Create `LeadNote` model:
  ```python
  id               (UUID, primary key)
  lead_id          (FK → leads.id)
  note_text        (Text)
  created_at       (DateTime)
  ```

## 1.7 Saved Lists Table

- [ ] Create `SavedList` model:
  ```python
  id               (UUID, primary key)
  user_id          (FK → users.id)
  list_name        (String)
  created_at       (DateTime)
  ```

## 1.8 List Leads Junction Table

- [ ] Create `ListLead` model:
  ```python
  id               (UUID, primary key)
  list_id          (FK → saved_lists.id)
  lead_id          (FK → leads.id)
  added_at         (DateTime)
  ```

## 1.9 Hashtag Cache Table

- [ ] Create `HashtagCache` model:
  ```python
  id               (UUID, primary key)
  hashtag          (String, unique)
  dataset          (JSON — list of profile objects)
  cached_at        (DateTime)
  expires_at       (DateTime)
  access_count     (Integer, default 0)
  ```

## 1.10 App Config Table

- [ ] Create `AppConfig` model:
  ```python
  key              (String, primary key)
  value            (String)
  updated_at       (DateTime)
  updated_by       (String)
  ```
  - [ ] Seed default config rows:
    ```
    kill_switch = false
    free_daily_limit = 10
    pro_daily_limit = 50
    pro_plus_daily_limit = 150
    free_monthly_cap = 200
    pro_monthly_cap = 1200
    pro_plus_monthly_cap = 4500
    cache_ttl_hours = 24
    ```

## 1.11 Run Migrations

- [ ] `flask db migrate -m "initial tables"`
- [ ] `flask db upgrade`
- [ ] Verify all tables created: `\dt` in psql

---

# MANUAL TESTING CHECKPOINT 1

```
Test 1: All tables exist
Command: psql -d spyleads_dev → \dt
Expected: 9 tables listed
Pass: All models visible

Test 2: Insert a test user
Command: Flask shell → db.session.add(User(email='test@test.com'))
Expected: Row inserted
Pass: SELECT * FROM users returns 1 row

Test 3: Config table seeded
Command: SELECT * FROM app_config;
Expected: 8 rows with default values
Pass: kill_switch = 'false'
```

---

# ═══════════════════════════════════════════
# PHASE 2 — AUTHENTICATION SYSTEM
# ═══════════════════════════════════════════

## 2.1 Register Endpoint

- [ ] `POST /auth/register`
  - Accepts: `email`, `password`
  - Validates: email format, password min 8 chars
  - Checks: email not already registered
  - Hashes password with bcrypt (rounds=12)
  - Creates User row (plan='free')
  - Creates DailyQuota row for today
  - Returns: `{ success: true, token: "JWT_TOKEN", user: { email, plan } }`
  - Error cases:
    - `email_taken` → 409
    - `invalid_email` → 400
    - `weak_password` → 400

## 2.2 Login Endpoint

- [ ] `POST /auth/login`
  - Accepts: `email`, `password`
  - Checks: user exists, password matches bcrypt hash
  - Generates: JWT token (expires 7 days)
  - Returns: `{ success: true, token: "JWT_TOKEN", user: { email, plan, daily_remaining } }`
  - Error cases:
    - `invalid_credentials` → 401
    - `account_inactive` → 403

## 2.3 JWT Middleware

- [ ] Create `@require_auth` decorator in `utils/decorators.py`
  - Reads `Authorization: Bearer TOKEN` header
  - Decodes JWT
  - Injects `current_user` into route
  - Rejects expired/invalid tokens with 401

## 2.4 Admin Auth Middleware

- [ ] Create `@require_admin` decorator
  - Checks `current_user.is_admin = True`
  - OR checks `X-Admin-Key` header matches `ADMIN_SECRET_KEY` env var
  - Returns 403 if not admin

## 2.5 Get Current User

- [ ] `GET /auth/me`
  - Requires: `@require_auth`
  - Returns:
    ```json
    {
      "email": "user@email.com",
      "plan": "pro",
      "subscription_status": "active",
      "subscription_end_date": "2026-06-01",
      "daily_used": 12,
      "daily_limit": 50,
      "monthly_used": 340,
      "monthly_cap": 1200
    }
    ```

## 2.6 Change Password

- [ ] `POST /auth/change-password`
  - Requires: `@require_auth`
  - Accepts: `current_password`, `new_password`
  - Verifies current password
  - Updates hash

---

# MANUAL TESTING CHECKPOINT 2

```
Test 1: Register new user
Tool: Postman or curl
Request: POST /auth/register
Body: { "email": "test@test.com", "password": "Test1234!" }
Expected: 200 + JWT token
Pass: Token returned, row in DB

Test 2: Login
Request: POST /auth/login
Body: Same credentials
Expected: 200 + token
Pass: Token different from register token (new expiry)

Test 3: Wrong password
Body: { "email": "test@test.com", "password": "WrongPass" }
Expected: 401 + { "error": "invalid_credentials" }
Pass: Not logged in

Test 4: Protected route
Request: GET /auth/me
Header: Authorization: Bearer {token}
Expected: 200 + user object
Pass: Plan shows 'free'

Test 5: No token
Request: GET /auth/me (no header)
Expected: 401
Pass: Rejected
```

---

# ═══════════════════════════════════════════
# PHASE 3 — STRIPE BILLING SYSTEM
# ═══════════════════════════════════════════

## 3.1 Stripe Product Setup (Do This First in Stripe Dashboard)

- [ ] Login to dashboard.stripe.com
- [ ] Create Product: "SpyLeads PRO"
  - Price: ₹499/month (recurring)
  - Currency: INR
  - Copy Price ID → save as `STRIPE_PRO_PRICE_ID` in .env
- [ ] Create Product: "SpyLeads PRO PLUS"
  - Price: ₹1199/month (recurring)
  - Currency: INR
  - Copy Price ID → save as `STRIPE_PRO_PLUS_PRICE_ID` in .env
- [ ] Enable Indian payment methods:
  - Cards (Visa, Mastercard, Rupay)
  - UPI
  - Netbanking
- [ ] Setup webhook endpoint in Stripe Dashboard:
  - URL: `https://your-render-url.onrender.com/billing/webhook`
  - Events to listen:
    - `checkout.session.completed`
    - `customer.subscription.updated`
    - `customer.subscription.deleted`
    - `invoice.payment_failed`
    - `invoice.payment_succeeded`
  - Copy Webhook Secret → save as `STRIPE_WEBHOOK_SECRET`

## 3.2 Create Checkout Session

- [ ] `POST /billing/create-checkout`
  - Requires: `@require_auth`
  - Accepts: `plan` ('pro' or 'pro_plus')
  - Logic:
    - Get or create Stripe Customer for this user
      - `stripe.Customer.create(email=user.email)`
      - Save `stripe_customer_id` to user row
    - Create Checkout Session:
      ```python
      stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=['card', 'upi', 'netbanking'],
        line_items=[{ 'price': PRICE_ID, 'quantity': 1 }],
        mode='subscription',
        success_url='https://yoursite.com/dashboard?payment=success',
        cancel_url='https://yoursite.com/pricing?payment=cancelled',
        metadata={ 'user_id': str(user.id), 'plan': plan }
      )
      ```
    - Return: `{ "checkout_url": session.url }`
  - Frontend redirects user to Stripe checkout page

## 3.3 Stripe Webhook Handler

- [ ] `POST /billing/webhook`
  - NO auth required (Stripe calls this directly)
  - First verify signature:
    ```python
    stripe.Webhook.construct_event(
      payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
    ```
  - Handle events:

  ### `checkout.session.completed`
  - [ ] Get `user_id` from metadata
  - [ ] Get `plan` from metadata
  - [ ] Update user:
    - `plan = 'pro'` or `'pro_plus'`
    - `stripe_subscription_id = subscription_id`
    - `subscription_status = 'active'`
    - `subscription_end_date = current_period_end`
  - [ ] Log activation

  ### `customer.subscription.updated`
  - [ ] Get user by `stripe_customer_id`
  - [ ] Update `subscription_status`, `subscription_end_date`
  - [ ] If plan changed (upgrade/downgrade), update `plan`

  ### `customer.subscription.deleted`
  - [ ] Get user by `stripe_customer_id`
  - [ ] Set `plan = 'free'`
  - [ ] Set `subscription_status = 'cancelled'`
  - [ ] Set `subscription_end_date = now`

  ### `invoice.payment_failed`
  - [ ] Get user
  - [ ] Set `subscription_status = 'past_due'`
  - [ ] (Future: send email notification)

  ### `invoice.payment_succeeded`
  - [ ] Get user
  - [ ] Set `subscription_status = 'active'`
  - [ ] Extend `subscription_end_date` by 30 days

## 3.4 Get Subscription Status

- [ ] `GET /billing/status`
  - Requires: `@require_auth`
  - Returns:
    ```json
    {
      "plan": "pro",
      "status": "active",
      "renewal_date": "2026-06-01",
      "monthly_cost": 499,
      "currency": "INR"
    }
    ```

## 3.5 Cancel Subscription

- [ ] `POST /billing/cancel`
  - Requires: `@require_auth`
  - Calls: `stripe.Subscription.modify(sub_id, cancel_at_period_end=True)`
  - Updates: `subscription_status = 'cancelling'`
  - Returns: `{ "message": "Subscription will cancel at end of billing period", "end_date": "..." }`

## 3.6 Upgrade/Downgrade Plan

- [ ] `POST /billing/change-plan`
  - Requires: `@require_auth`
  - Accepts: `new_plan` ('pro' or 'pro_plus')
  - Calls:
    ```python
    stripe.Subscription.modify(
      sub_id,
      items=[{ 'id': item_id, 'price': NEW_PRICE_ID }],
      proration_behavior='always_invoice'
    )
    ```
  - Updates user plan after webhook confirmation

## 3.7 Customer Portal

- [ ] `POST /billing/portal`
  - Requires: `@require_auth`
  - Creates Stripe Customer Portal session
  - User can manage card, cancel, download invoices
  - Returns: `{ "portal_url": "..." }`

---

# MANUAL TESTING CHECKPOINT 3

```
Test 1: Create checkout session (PRO)
Request: POST /billing/create-checkout
Body: { "plan": "pro" }
Header: Authorization: Bearer {token}
Expected: { "checkout_url": "https://checkout.stripe.com/..." }
Pass: URL is valid Stripe checkout

Test 2: Complete test payment
Action: Visit checkout_url in browser
Use: Stripe test card 4000 0035 6000 0008 (India)
Expected: Redirect to /dashboard?payment=success
Pass: User plan updated to 'pro' in DB

Test 3: Webhook received
Check: Stripe Dashboard → Webhooks → Recent deliveries
Expected: checkout.session.completed event = 200 OK
Pass: No failed webhook calls

Test 4: Verify plan upgrade in DB
Command: SELECT plan, subscription_status FROM users WHERE email='test@test.com'
Expected: plan='pro', subscription_status='active'
Pass: DB updated

Test 5: Cancel subscription
Request: POST /billing/cancel
Expected: 200 + cancellation message
Stripe dashboard: Subscription shows "Cancels on [date]"

Test 6: Failed payment simulation
Stripe test card: 4000 0000 0000 0341
Expected: invoice.payment_failed webhook fires
DB: subscription_status = 'past_due'

Test 7: Customer portal
Request: POST /billing/portal
Expected: { "portal_url": "..." }
Pass: Opens Stripe portal with user's invoices
```

---

# ═══════════════════════════════════════════
# PHASE 4 — QUOTA ENGINE
# ═══════════════════════════════════════════

## 4.1 Quota Service (quota_service.py)

- [ ] Function: `get_daily_limit(user)`
  ```python
  FREE = 10
  PRO = 50
  PRO PLUS = 150
  Returns limit based on user.plan
  ```

- [ ] Function: `get_monthly_cap(user)`
  ```python
  FREE = 200
  PRO = 1200
  PRO PLUS = 4500
  Returns cap based on user.plan
  ```

- [ ] Function: `get_or_create_quota(user_id, date)`
  - Finds or creates DailyQuota row for user+date
  - Resets `profiles_used = 0` if date changed

- [ ] Function: `check_quota(user, requested_count)`
  - Gets today's quota row
  - Gets this month's total from usage_logs
  - Checks: `daily_used + requested > daily_limit`
  - Checks: `monthly_total + requested > monthly_cap`
  - Returns: `{ allowed: bool, reason: str, daily_remaining: int, monthly_remaining: int }`

- [ ] Function: `deduct_quota(user_id, profiles_extracted)`
  - Called AFTER successful extraction
  - Increments `daily_used` in DailyQuota
  - Does NOT deduct on failure

- [ ] Function: `get_quota_status(user)`
  - Returns full quota object for frontend:
    ```json
    {
      "plan": "pro",
      "daily_used": 12,
      "daily_limit": 50,
      "daily_remaining": 38,
      "monthly_used": 340,
      "monthly_cap": 1200,
      "monthly_remaining": 860,
      "resets_at": "2026-06-01"
    }
    ```

## 4.2 Midnight Reset Logic

- [ ] Function: `reset_daily_quotas()`
  - Called at midnight IST via scheduler
  - Resets all `DailyQuota.profiles_used = 0` for today
  - (Use APScheduler or Render cron)

## 4.3 Monthly Reset Logic

- [ ] Function: `reset_monthly_quotas()`
  - Called on 1st of each month
  - (Monthly total is calculated dynamically from usage_logs, not stored)
  - Ensure usage_logs has `created_at` for month filtering

## 4.4 Kill Switch Check

- [ ] Function: `is_kill_switch_active()`
  - Reads `AppConfig` table where `key='kill_switch'`
  - Returns `True` if value is 'true'
  - Cached in memory for 60 seconds (avoid DB hit every request)

---

# MANUAL TESTING CHECKPOINT 4

```
Test 1: Quota check - FREE user
Create user with plan='free'
Call check_quota(user, 5)
Expected: { allowed: true, daily_remaining: 5 }

Test 2: Quota exceeded
Manually set daily_used=10 for free user
Call check_quota(user, 1)
Expected: { allowed: false, reason: 'daily_limit_exceeded' }

Test 3: Monthly cap exceeded
Create 200 usage_log rows for free user this month
Call check_quota(user, 1)
Expected: { allowed: false, reason: 'monthly_cap_exceeded' }

Test 4: Kill switch
SET kill_switch = 'true' in app_config table
Call is_kill_switch_active()
Expected: True
SET back to 'false'
Expected: False

Test 5: Quota deduction
Call deduct_quota(user_id, 10)
Check DailyQuota row
Expected: profiles_used increased by 10
```

---

# ═══════════════════════════════════════════
# PHASE 5 — APIFY ACTOR INTEGRATION
# ═══════════════════════════════════════════

## 5.1 Apify Service (apify_service.py)

- [ ] Function: `trigger_actor(query, max_results, proxy_tier, filters)`
  - Calls Apify API using `apify-client`:
    ```python
    from apify_client import ApifyClient
    client = ApifyClient(APIFY_TOKEN)
    run = client.actor(ACTOR_ID).call(
      run_input={
        "query": query,
        "type": "hashtag",
        "maxResults": max_results,
        "proxyTier": proxy_tier,  # 'datacenter'/'residential'/'hybrid'
        "filters": filters
      }
    )
    ```
  - Returns: `run` object (contains run_id, defaultDatasetId)

- [ ] Function: `fetch_dataset(run_id, dataset_id)`
  - Fetches results from Apify dataset
  - Returns: list of profile dicts

- [ ] Function: `get_run_stats(run_id)`
  - Calls Apify API to get run details:
    ```python
    run_info = client.run(run_id).get()
    ```
  - Extracts and returns:
    ```python
    {
      "run_id": run_id,
      "status": run_info["status"],
      "duration_seconds": run_info["stats"]["durationMillis"] / 1000,
      "compute_units": run_info["stats"]["computeUnits"],
      "total_cost_usd": run_info["usageTotalUsd"],
      "proxy_traffic_mb": run_info["stats"].get("proxyUsedBytes", 0) / (1024 * 1024),
      "residential_mb": extract_residential_mb(run_info),
      "datacenter_mb": extract_datacenter_mb(run_info),
      "memory_mb_used": run_info["stats"]["memUsedMbytes"],
      "pages_crawled": run_info["stats"].get("requestsFinished", 0),
      "retries": run_info["stats"].get("requestsRetried", 0)
    }
    ```

- [ ] Function: `extract_residential_mb(run_info)`
  - Parse `usageUsd.proxyResidential` and `usageUsd.proxySerp`
  - Convert back to MB using ₹670/GB rate

- [ ] Function: `extract_datacenter_mb(run_info)`
  - Parse `usageUsd.proxyDatacenter`
  - Convert to MB

## 5.2 Proxy Tier Selection

- [ ] Function: `determine_proxy_tier(user_plan, filters_active)`
  ```python
  if user_plan == 'free':
    return 'datacenter'  # Never use residential for free users
  elif user_plan == 'pro':
    return 'hybrid'      # Datacenter for hashtag, residential for profiles
  elif user_plan == 'pro_plus':
    return 'residential' # Full residential
  ```

## 5.3 Extraction Mode Selection

- [ ] Function: `determine_extraction_mode(filters)`
  ```python
  if not filters.get('emailRequired') and not filters.get('websiteRequired') and not filters.get('bioKeyword'):
    return 'fast'      # Hashtag page only, skip profile visits
  elif filters.get('emailRequired') or filters.get('websiteRequired'):
    return 'full'      # Visit every profile
  else:
    return 'standard'  # Visit profiles only if needed
  ```

---

# MANUAL TESTING CHECKPOINT 5

```
Test 1: Actor trigger - 5 profiles
Function: trigger_actor("fitness", 5, "hybrid", {})
Expected: run object returned, status not 'FAILED'
Check Apify Console: New run visible in Runs tab

Test 2: Fetch dataset
After run completes:
Function: fetch_dataset(run_id, dataset_id)
Expected: List of 5 profile dicts with username, followers

Test 3: Run stats fetch
Function: get_run_stats(run_id)
Expected: {
  compute_units: 0.03,
  total_cost_usd: 0.05,
  proxy_traffic_mb: 45,
  residential_mb: 40,
  datacenter_mb: 5
}
Compare with Apify Console → same run → Usage section
Should match

Test 4: Proxy tier selection
determine_proxy_tier('free', False) → 'datacenter'
determine_proxy_tier('pro', True) → 'hybrid'
determine_proxy_tier('pro_plus', False) → 'residential'

Test 5: Extraction mode
determine_extraction_mode({}) → 'fast'
determine_extraction_mode({'emailRequired': True}) → 'full'
```

---

# ═══════════════════════════════════════════
# PHASE 6 — EXTRACTION ENDPOINT
# ═══════════════════════════════════════════

## 6.1 POST /extract

- [ ] Full extraction flow with all checks:

  **Step 1 — Auth check**
  - `@require_auth` decorator
  - Reject if no token: 401

  **Step 2 — Parse input**
  - Accept:
    ```json
    {
      "query": "fitness",
      "type": "hashtag",
      "maxResults": 50,
      "filters": {
        "emailRequired": false,
        "websiteRequired": false,
        "minFollowers": 1000,
        "maxFollowers": 50000,
        "bioKeyword": "",
        "microInfluencerOnly": false
      }
    }
    ```
  - Validate: query not empty, type is valid, maxResults > 0

  **Step 3 — Cap maxResults by plan**
  - FREE: max 10
  - PRO: max 50
  - PRO PLUS: max 150
  - If requested > plan max → use plan max silently

  **Step 4 — Kill switch check**
  - `if is_kill_switch_active(): return 503 { "error": "service_unavailable" }`

  **Step 5 — Quota check**
  - `quota = check_quota(user, maxResults)`
  - `if not quota.allowed: return 429 { "error": quota.reason, "daily_remaining": ..., "monthly_remaining": ... }`

  **Step 6 — Cache check**
  - `cached = check_hashtag_cache(query)`
  - If cache exists and not expired:
    - Apply filters to cached dataset
    - Return immediately (no Apify call)
    - Log: `apify_cost_usd = 0, status = 'cache_hit'`
    - Deduct quota

  **Step 7 — Determine proxy tier + extraction mode**
  - Based on user.plan and filters

  **Step 8 — Trigger Apify actor**
  - `run = trigger_actor(query, maxResults * 1.3, proxy_tier, filters)`
    - Note: request 30% more profiles for ranking later
  - Handle timeout: if run fails, return 504

  **Step 9 — Fetch dataset**
  - `raw_profiles = fetch_dataset(run.run_id, run.dataset_id)`
  - If empty: return `{ "error": "dataset_empty", "profiles": [] }`

  **Step 10 — Get run stats from Apify**
  - `stats = get_run_stats(run.run_id)`

  **Step 11 — Apply filters locally**
  - Filter by minFollowers, maxFollowers
  - Filter by emailRequired (has email in bio)
  - Filter by websiteRequired
  - Filter by bioKeyword (bio contains keyword)
  - Filter by microInfluencerOnly (followers 1k–50k)

  **Step 12 — Score and rank**
  - Run `lead_scorer.score(profile)` on each profile
  - Sort by score DESC
  - Slice top `maxResults`

  **Step 13 — Save leads to DB**
  - Bulk insert all profiles as `Lead` rows for this user
  - Skip duplicates (same username for same user)

  **Step 14 — Store in cache**
  - `store_hashtag_cache(query, raw_profiles)`

  **Step 15 — Log extraction**
  - Create `UsageLog` row with ALL Apify stats:
    ```
    user_id, profiles_requested, profiles_returned,
    hashtag, extraction_mode, proxy_type,
    apify_run_id, apify_cost_usd, apify_compute_units,
    apify_proxy_mb, apify_datacenter_mb, apify_residential_mb,
    duration_seconds, status
    ```

  **Step 16 — Deduct quota**
  - `deduct_quota(user.id, len(returned_profiles))`
  - Only deduct what was returned, not what was requested

  **Step 17 — Return response**
  ```json
  {
    "success": true,
    "profiles_returned": 47,
    "quota_remaining": 38,
    "extraction_mode": "hybrid",
    "profiles": [...],
    "run_stats": {
      "cost_usd": 0.07,
      "duration_seconds": 142,
      "from_cache": false
    }
  }
  ```

## 6.2 Error Response Format

- [ ] All errors return consistent format:
  ```json
  {
    "success": false,
    "error": "error_code",
    "message": "Human readable message",
    "details": {}
  }
  ```
- [ ] Error codes:
  - `unauthorized` → 401
  - `daily_limit_exceeded` → 429
  - `monthly_cap_exceeded` → 429
  - `service_unavailable` → 503 (kill switch)
  - `actor_timeout` → 504
  - `dataset_empty` → 200 (not an error, empty result)
  - `instagram_blocked` → 503
  - `invalid_input` → 400

---

# MANUAL TESTING CHECKPOINT 6

```
Test 1: Full extraction - 5 profiles, no filters
POST /extract
Body: { "query": "yoga", "maxResults": 5 }
Expected: 200 + 5 profiles + run_stats
Check: UsageLog row created with Apify stats
Check: Lead rows created in DB
Check: Daily quota decremented by 5

Test 2: Kill switch active
Set app_config: kill_switch = 'true'
POST /extract
Expected: 503 { "error": "service_unavailable" }
Reset kill_switch to 'false'

Test 3: Daily limit exceeded (FREE user)
Set daily_used = 10 for free user
POST /extract with free user token
Expected: 429 { "error": "daily_limit_exceeded" }

Test 4: Cache hit
Extract #yoga once (populates cache)
Extract #yoga again immediately
Expected: Second call returns same data faster (no new Apify run)
Check: UsageLog shows apify_cost_usd = 0 on second call

Test 5: Filter - emailRequired
POST /extract with { "filters": { "emailRequired": true } }
Expected: Only profiles with email in bio returned
Verify: All returned profiles have non-null email field

Test 6: Plan limit enforcement
PRO user requests maxResults=200
Expected: Actually queries 50 (PRO cap)
Response: profiles_returned ≤ 50

Test 7: Quota deduction accuracy
User has 50 quota
Request 50 profiles
Actor returns 43 (some filtered out)
Expected: daily_used incremented by 43 (not 50)
```

---

# ═══════════════════════════════════════════
# PHASE 7 — LEAD INTELLIGENCE ENGINE
# ═══════════════════════════════════════════

## 7.1 Lead Scorer (lead_scorer.py)

- [ ] Function: `score_lead(profile)` → returns 0–100
  ```python
  score = 0

  # Email present in bio
  if profile.get('email'): score += 30

  # Website/external link present
  if profile.get('external_url'): score += 20

  # Follower count tiers
  followers = profile.get('followers', 0)
  if followers > 100000: score += 20
  elif followers > 10000: score += 15
  elif followers > 1000: score += 10

  # Service keywords in bio
  service_keywords = ['coach', 'agency', 'hire', 'consulting',
                      'services', 'dm', 'contact', 'business',
                      'founder', 'studio']
  bio = profile.get('bio', '').lower()
  if any(kw in bio for kw in service_keywords): score += 10

  # Category exists
  if profile.get('category'): score += 10

  # Verified account
  if profile.get('is_verified'): score += 5

  return min(score, 100)
  ```

## 7.2 Intent Detector

- [ ] Function: `detect_intent(profile)` → returns bool
  ```python
  high_intent_keywords = ['hire me', 'dm for', 'collab', 'available for',
                          'book now', 'contact for', 'open to work',
                          'inquiries', 'partnerships', 'sponsorship']
  bio = profile.get('bio', '').lower()
  return any(kw in bio for kw in high_intent_keywords)
  ```

## 7.3 Influencer Classifier

- [ ] Function: `classify_influencer(profile)` → returns tier string
  ```python
  followers = profile.get('followers', 0)
  if 1000 <= followers <= 50000: return 'micro'
  elif 50001 <= followers <= 500000: return 'mid'
  elif followers > 500000: return 'macro'
  return None
  ```

## 7.4 Auto-Tagger

- [ ] Function: `auto_tag(profile)` → returns list of tags
  ```python
  tags = []
  if profile.get('email'): tags.append('Hot')
  if profile.get('followers', 0) > 10000: tags.append('Influencer')
  if 'coach' in profile.get('bio', '').lower(): tags.append('Coach Lead')
  if profile.get('external_url'): tags.append('Business Lead')
  if classify_influencer(profile) == 'micro': tags.append('Micro-Influencer')
  if detect_intent(profile): tags.append('High Intent')
  return tags
  ```

## 7.5 Email Extractor

- [ ] Function: `extract_email_from_bio(bio)` → returns email or None
  ```python
  import re
  pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
  match = re.search(pattern, bio or '')
  return match.group(0) if match else None
  ```

---

# MANUAL TESTING CHECKPOINT 7

```
Test 1: Score lead with email + website
profile = { email: "test@gmail.com", external_url: "site.com", followers: 15000 }
Expected score: 30 + 20 + 15 = 65

Test 2: Score lead minimal
profile = { followers: 500 }
Expected score: 0

Test 3: Intent detection
profile = { bio: "DM for brand deals and sponsorship" }
detect_intent(profile) → True

Test 4: Influencer classification
classify_influencer({ followers: 25000 }) → 'micro'
classify_influencer({ followers: 200000 }) → 'mid'
classify_influencer({ followers: 1500000 }) → 'macro'

Test 5: Auto-tagging
profile = { email: "x@y.com", followers: 25000, bio: "fitness coach" }
auto_tag(profile) → ['Hot', 'Influencer', 'Coach Lead', 'Micro-Influencer']

Test 6: Email extraction
extract_email_from_bio("reach me at hello@brand.com for collab")
Expected: "hello@brand.com"
extract_email_from_bio("no email here")
Expected: None
```

---

# ═══════════════════════════════════════════
# PHASE 8 — CRM-LITE LEAD MANAGEMENT
# ═══════════════════════════════════════════

## 8.1 Get Leads

- [ ] `GET /leads`
  - Requires: `@require_auth`
  - Query params:
    - `page` (default 1)
    - `per_page` (default 25, max 100)
    - `tag` (filter by tag name)
    - `status` (filter by status)
    - `min_score` (filter by lead_score ≥ N)
    - `has_email` (true/false)
    - `hashtag` (filter by source hashtag)
  - Returns paginated leads with tags included

## 8.2 Get Single Lead

- [ ] `GET /leads/:id`
  - Requires: `@require_auth`
  - Verifies lead belongs to current_user
  - Returns lead + all tags + all notes

## 8.3 Update Lead Status

- [ ] `PATCH /leads/:id/status`
  - Requires: `@require_auth`
  - Accepts: `{ "status": "contacted" }`
  - Valid statuses: new / qualified / contacted / replied / converted / closed
  - Updates `updated_at`

## 8.4 Add Tag

- [ ] `POST /leads/:id/tags`
  - Requires: `@require_auth`
  - Accepts: `{ "tag": "Hot" }`
  - Creates LeadTag row
  - Skip if already exists (no duplicates)

## 8.5 Remove Tag

- [ ] `DELETE /leads/:id/tags/:tag`
  - Requires: `@require_auth`
  - Deletes LeadTag row

## 8.6 Add Note

- [ ] `POST /leads/:id/notes`
  - Requires: `@require_auth`
  - Accepts: `{ "note": "Interested in collab, DM sent on May 3" }`
  - Creates LeadNote row

## 8.7 Get Notes

- [ ] `GET /leads/:id/notes`
  - Requires: `@require_auth`
  - Returns all notes sorted by created_at DESC

## 8.8 Delete Lead

- [ ] `DELETE /leads/:id`
  - Requires: `@require_auth`
  - Soft delete (set is_active = False) OR hard delete
  - Also removes from all saved lists

## 8.9 Bulk Operations

- [ ] `POST /leads/bulk/tag`
  - Accepts: `{ "lead_ids": [...], "tag": "Hot" }`
  - Adds tag to multiple leads at once

- [ ] `POST /leads/bulk/status`
  - Accepts: `{ "lead_ids": [...], "status": "contacted" }`

- [ ] `POST /leads/bulk/delete`
  - Accepts: `{ "lead_ids": [...] }`

## 8.10 Saved Lists

- [ ] `POST /lists` — Create new list
  - Accepts: `{ "name": "Fitness Coaches Mumbai" }`

- [ ] `GET /lists` — Get all user's lists
  - Returns: lists with lead count

- [ ] `GET /lists/:id/leads` — Get leads in a list

- [ ] `POST /lists/:id/leads` — Add lead(s) to list
  - Accepts: `{ "lead_ids": [...] }`

- [ ] `DELETE /lists/:id/leads/:lead_id` — Remove lead from list

- [ ] `DELETE /lists/:id` — Delete list (not the leads)

- [ ] `PATCH /lists/:id` — Rename list

---

# MANUAL TESTING CHECKPOINT 8

```
Test 1: Get leads after extraction
GET /leads (after extracting 10 profiles)
Expected: 10 leads, paginated

Test 2: Filter by tag
GET /leads?tag=Hot
Expected: Only leads tagged 'Hot'

Test 3: Update status
PATCH /leads/{id}/status
Body: { "status": "contacted" }
Expected: 200, status updated
GET /leads/{id} → status: "contacted"

Test 4: Add/remove tag
POST /leads/{id}/tags { "tag": "VIP" }
Expected: Tag added
DELETE /leads/{id}/tags/VIP
Expected: Tag removed

Test 5: Notes
POST /leads/{id}/notes { "note": "Very responsive, follow up Friday" }
GET /leads/{id}/notes
Expected: Note visible

Test 6: Saved list
POST /lists { "name": "Hot Fitness Leads" }
POST /lists/{id}/leads { "lead_ids": ["id1", "id2"] }
GET /lists/{id}/leads
Expected: 2 leads in list

Test 7: Bulk tag
POST /leads/bulk/tag { "lead_ids": ["id1","id2","id3"], "tag": "Priority" }
Expected: All 3 leads get Priority tag
```

---

# ═══════════════════════════════════════════
# PHASE 9 — EXPORT ENGINE
# ═══════════════════════════════════════════

## 9.1 CSV Export

- [ ] `GET /export/csv`
  - Requires: `@require_auth`
  - Query params (filters):
    - `list_id` — export specific list
    - `tag` — export by tag
    - `status` — export by status
    - `has_email` — only email leads
  - Process:
    - Query leads with filters
    - Create pandas DataFrame
    - Columns: username, followers, email, external_url, bio, tags, status, lead_score, source_hashtag, created_at
    - Export to CSV string
    - Return as file download:
      ```python
      return Response(
        csv_string,
        mimetype='text/csv',
        headers={ "Content-Disposition": "attachment; filename=spyleads_export.csv" }
      )
      ```
  - Log: export count in usage metrics

## 9.2 Google Sheets Export (Phase 2 — After MVP)

- [ ] Setup Google OAuth2 credentials in Google Cloud Console
- [ ] `GET /export/google/auth` — Start OAuth flow
- [ ] `GET /export/google/callback` — Handle OAuth callback
- [ ] `POST /export/google/sheets` — Push leads to sheet
  - Creates new sheet named "SpyLeads Export {date}"
  - Appends rows
  - Returns sheet URL

---

# MANUAL TESTING CHECKPOINT 9

```
Test 1: CSV export all leads
GET /export/csv
Expected: File download dialog
Open CSV: 10 rows, all columns present

Test 2: CSV export by tag
GET /export/csv?tag=Hot
Expected: Only Hot leads in CSV

Test 3: CSV export by list
GET /export/csv?list_id={id}
Expected: Only leads in that list

Test 4: CSV with email filter
GET /export/csv?has_email=true
Expected: All rows have non-empty email column

Test 5: Empty export
GET /export/csv?tag=NonExistentTag
Expected: CSV with headers only (0 rows)
Should not error
```

---

# ═══════════════════════════════════════════
# PHASE 10 — APIFY COST MONITORING (ADMIN DASHBOARD)
# ═══════════════════════════════════════════

## 10.1 Admin: Apify Cost Overview

- [ ] `GET /admin/apify/cost-summary`
  - Requires: `@require_admin`
  - Returns:
    ```json
    {
      "today": {
        "total_runs": 42,
        "total_cost_usd": 3.45,
        "total_cost_inr": 288.47,
        "total_profiles_extracted": 1840,
        "total_proxy_mb": 1240,
        "residential_mb": 980,
        "datacenter_mb": 260,
        "compute_units": 1.82,
        "avg_cost_per_profile_inr": 0.16,
        "cache_hits": 8,
        "cache_savings_usd": 0.56
      },
      "this_month": {
        "total_runs": 1340,
        "total_cost_usd": 98.40,
        "total_cost_inr": 8,223.84,
        "total_profiles_extracted": 52000,
        "total_proxy_mb": 38000,
        "residential_mb": 29000,
        "datacenter_mb": 9000,
        "compute_units": 56.4,
        "avg_cost_per_profile_inr": 0.16,
        "cache_hit_rate_percent": 18.5,
        "estimated_savings_inr": 1520
      }
    }
    ```
  - Source: Aggregate from `usage_logs` table (your DB, not Apify API)

## 10.2 Admin: Per-Run Cost Breakdown

- [ ] `GET /admin/apify/runs`
  - Requires: `@require_admin`
  - Query params: `page`, `per_page`, `date_from`, `date_to`, `user_id`
  - Returns table of every run:
    ```json
    [
      {
        "run_id": "abc123",
        "user_email": "user@email.com",
        "plan": "pro",
        "hashtag": "fitness",
        "profiles_requested": 50,
        "profiles_returned": 47,
        "extraction_mode": "hybrid",
        "proxy_type": "hybrid",
        "cost_usd": 0.07,
        "cost_inr": 5.85,
        "compute_units": 0.04,
        "proxy_mb_total": 65,
        "residential_mb": 50,
        "datacenter_mb": 15,
        "duration_seconds": 142,
        "status": "success",
        "from_cache": false,
        "created_at": "2026-05-03 14:23:00"
      }
    ]
    ```

## 10.3 Admin: Cost Per User

- [ ] `GET /admin/apify/cost-by-user`
  - Requires: `@require_admin`
  - Returns cost aggregated per user this month:
    ```json
    [
      {
        "user_email": "highuser@test.com",
        "plan": "pro_plus",
        "total_profiles": 3200,
        "total_cost_inr": 682,
        "revenue_inr": 1199,
        "profit_inr": 517,
        "margin_percent": 43.1,
        "avg_cost_per_profile": 0.21,
        "residential_mb": 9600,
        "datacenter_mb": 2400,
        "cache_hits": 12
      }
    ]
    ```

## 10.4 Admin: Proxy Usage Breakdown

- [ ] `GET /admin/apify/proxy-breakdown`
  - Returns detailed proxy usage:
    ```json
    {
      "this_month": {
        "residential": {
          "total_mb": 29000,
          "total_gb": 28.32,
          "cost_usd": 226.56,
          "cost_inr": 18,929,
          "percent_of_total": 76.3
        },
        "datacenter": {
          "total_mb": 9000,
          "total_gb": 8.79,
          "cost_usd": 4.40,
          "cost_inr": 368,
          "percent_of_total": 23.7
        }
      },
      "by_plan": {
        "free": { "datacenter_mb": 3000, "residential_mb": 0, "cost_inr": 123 },
        "pro": { "datacenter_mb": 4500, "residential_mb": 12000, "cost_inr": 4521 },
        "pro_plus": { "datacenter_mb": 1500, "residential_mb": 17000, "cost_inr": 14673 }
      }
    }
    ```

## 10.5 Admin: Cache Efficiency Report

- [ ] `GET /admin/apify/cache-stats`
  - Returns:
    ```json
    {
      "total_searches_this_month": 1340,
      "cache_hits": 248,
      "cache_hit_rate_percent": 18.5,
      "saved_runs": 248,
      "estimated_savings_usd": 17.36,
      "estimated_savings_inr": 1450,
      "top_cached_hashtags": [
        { "hashtag": "fitness", "hit_count": 42, "last_cached": "..." },
        { "hashtag": "realestate", "hit_count": 31, "last_cached": "..." }
      ]
    }
    ```

## 10.6 Admin: Live Dashboard Stats

- [ ] `GET /admin/stats`
  - Returns all key metrics in one call:
    ```json
    {
      "users": {
        "total": 45,
        "free": 28,
        "pro": 14,
        "pro_plus": 3,
        "active_today": 12
      },
      "extractions": {
        "today": { "count": 42, "profiles": 1840 },
        "this_month": { "count": 1340, "profiles": 52000 }
      },
      "revenue": {
        "mrr_inr": 12588,
        "pro_subscribers": 14,
        "pro_plus_subscribers": 3
      },
      "costs": {
        "today_inr": 288,
        "this_month_inr": 8224,
        "cost_revenue_ratio": 0.65
      },
      "apify": {
        "total_cost_usd_today": 3.45,
        "total_cost_usd_month": 98.40,
        "compute_units_today": 1.82,
        "residential_mb_today": 980,
        "datacenter_mb_today": 260,
        "cache_hit_rate": 18.5
      },
      "kill_switch": false
    }
    ```

## 10.7 Admin: Kill Switch Control

- [ ] `POST /admin/kill-switch`
  - Requires: `@require_admin`
  - Accepts: `{ "enabled": true }`
  - Updates `AppConfig` where key='kill_switch'
  - Clears in-memory cache immediately
  - Returns current status

## 10.8 Admin: Remote Config Editor

- [ ] `GET /admin/config` — Get all config values
- [ ] `PATCH /admin/config` — Update config values
  - Accepts: `{ "key": "pro_daily_limit", "value": "60" }`
  - Updates `AppConfig` table
  - Takes effect on next request (no restart needed)

## 10.9 Admin: User Management

- [ ] `GET /admin/users` — List all users with stats
- [ ] `GET /admin/users/:id` — Single user detail
- [ ] `POST /admin/users/:id/reset-quota` — Reset daily quota manually
- [ ] `POST /admin/users/:id/ban` — Set is_active = False
- [ ] `POST /admin/users/:id/upgrade` — Manually set plan
- [ ] `GET /admin/users/:id/runs` — All extraction runs for user

---

# MANUAL TESTING CHECKPOINT 10

```
Test 1: Cost summary today
GET /admin/apify/cost-summary
(After running 5+ extractions)
Expected: Populated today object with real numbers
Verify: Total cost matches sum of usage_logs.apify_cost_usd

Test 2: Per-run breakdown
GET /admin/apify/runs
Expected: Table with each extraction run
Check: All fields populated (cost, mb, CU, proxy type)

Test 3: Proxy breakdown
GET /admin/apify/proxy-breakdown
Expected: Residential vs Datacenter MB separated
Verify: Higher residential for pro/pro_plus, datacenter for free

Test 4: Kill switch via admin
POST /admin/kill-switch { "enabled": true }
Then: POST /extract (with valid user)
Expected: 503 error
POST /admin/kill-switch { "enabled": false }
Then: POST /extract
Expected: Works normally

Test 5: Remote config change
PATCH /admin/config { "key": "pro_daily_limit", "value": "25" }
Verify: Pro user now gets 25 limit (not 50)
Reset back to 50

Test 6: Cost-by-user
GET /admin/apify/cost-by-user
Expected: Each user with revenue vs cost vs profit
Verify: Users with more usage have higher cost

Test 7: Quota reset
POST /admin/users/{id}/reset-quota
Check: DailyQuota.profiles_used = 0 for that user

Test 8: Cache stats
(After repeated #fitness searches)
GET /admin/apify/cache-stats
Expected: fitness shows multiple hits
Verify: estimated_savings > 0
```

---

# ═══════════════════════════════════════════
# PHASE 11 — COST EFFICIENCY OPTIMIZATIONS
# ═══════════════════════════════════════════

## 11.1 Image Blocking in Actor

- [ ] In `spyleads-actor/src/main.js` — add to both crawlers:
  ```javascript
  await page.route(
    '**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,mp4,webp,ico}',
    route => route.abort()
  );
  ```
  Expected: Page download drops from 3 MB → ~400 KB per page

## 11.2 Hybrid Proxy in Actor

- [ ] Accept `proxyTier` in actor input schema
- [ ] In Phase 1 (hashtag crawl): Use `DATACENTER` proxy group
- [ ] In Phase 2 (profile visits): Use `RESIDENTIAL` proxy group
- [ ] Map input:
  ```javascript
  const proxyConfig = await Actor.createProxyConfiguration({
    groups: input.proxyTier === 'datacenter' ? ['DATACENTER'] : ['RESIDENTIAL']
  });
  ```

## 11.3 Memory Optimization

- [ ] Set actor default memory to 256 MB in `.actor/actor.json`:
  ```json
  "defaultRunOptions": {
    "memoryMbytes": 256
  }
  ```
- [ ] Expected: CU cost drops 75% compared to 1 GB default

## 11.4 Conditional Profile Visits

- [ ] Accept `extractionMode` in actor input
- [ ] In `fast` mode: Parse from hashtag page only, skip profile visits
- [ ] In `standard` mode: Visit profiles only if emailRequired
- [ ] In `full` mode: Visit all profiles

## 11.5 Cache Service (cache_service.py)

- [ ] Function: `check_hashtag_cache(hashtag)`
  - Query HashtagCache where hashtag = value AND expires_at > now
  - Increment access_count
  - Return dataset or None

- [ ] Function: `store_hashtag_cache(hashtag, dataset)`
  - Upsert into HashtagCache
  - Set expires_at = now + 24 hours
  - For popular hashtags (access_count > 5): extend to 72 hours

## 11.6 Scroll Depth Limit in Actor

- [ ] In Phase 1: Request `maxResults × 1.3` instead of `maxResults`
- [ ] Stop scrolling once 1.3× profiles collected
- [ ] Rank and return top `maxResults`

---

# MANUAL TESTING CHECKPOINT 11

```
Test 1: Image blocking reduces MB
Run extraction without image blocking → note proxy_mb in usage_log
Add image blocking to actor → run same hashtag
Expected: proxy_mb should drop significantly (target: 60-80% reduction)
Compare usage_logs for both runs

Test 2: Hybrid proxy works
Extract with PRO user (hybrid mode)
Check usage_log: datacenter_mb > 0 AND residential_mb > 0
Both should have values (not just one)

Test 3: Memory usage
Check actor run in Apify Console
Expected: Peak memory < 300 MB (we set 256 MB)
If crashing: increase to 512 MB

Test 4: Cache hit
Extract #fitness twice in 24 hours
Second call usage_log: apify_cost_usd = 0
Check HashtagCache table: access_count incremented

Test 5: Extraction mode
fast mode: No profile page visits (check Apify run pages_crawled = 1)
full mode: 50 profile visits (pages_crawled ≈ 51)
```

---

# ═══════════════════════════════════════════
# PHASE 12 — DEPLOYMENT
# ═══════════════════════════════════════════

## 12.1 Render Setup

- [ ] Create Render account
- [ ] Create new Web Service
  - Connect GitHub → `spyleads-backend` repo
  - Runtime: Python 3
  - Build command: `pip install -r requirements.txt && flask db upgrade`
  - Start command: `gunicorn run:app`
  - Plan: Starter ($7/month) for MVP

- [ ] Set all environment variables in Render Dashboard:
  - All vars from `.env` file
  - `DATABASE_URL` → from Render PostgreSQL

- [ ] Create Render PostgreSQL database
  - Plan: Free for MVP
  - Copy Internal Database URL → set as `DATABASE_URL`

- [ ] Create `Procfile`:
  ```
  web: gunicorn run:app --workers 2 --bind 0.0.0.0:$PORT
  ```

## 12.2 Stripe Webhook Update

- [ ] After Render deploys, go to Stripe Dashboard
- [ ] Update webhook URL to: `https://your-app.onrender.com/billing/webhook`
- [ ] Copy new Webhook Secret → update `STRIPE_WEBHOOK_SECRET` in Render env vars

## 12.3 CORS Configuration

- [ ] In Flask app:
  ```python
  from flask_cors import CORS
  CORS(app, origins=[
    "https://yourfrontend.com",
    "http://localhost:3000"  # Dev only
  ])
  ```

## 12.4 Health Check

- [ ] Create `GET /health` endpoint:
  ```python
  @app.route('/health')
  def health():
    return { "status": "ok", "version": "1.0.0" }
  ```

---

# MANUAL TESTING CHECKPOINT 12

```
Test 1: Render deployment
Visit: https://your-app.onrender.com/health
Expected: { "status": "ok" }

Test 2: DB connection on Render
Run: flask db upgrade (check Render deploy logs)
Expected: No migration errors

Test 3: Stripe webhook live
Do test purchase on production Stripe
Check: Render logs show webhook received
Check: User plan updated in production DB

Test 4: CORS
From browser console (your frontend URL):
fetch('https://your-app.onrender.com/health')
Expected: No CORS error

Test 5: Environment variables
GET /auth/me with valid token on production
Expected: Works correctly
If error: Check Render env vars are set
```

---

# ═══════════════════════════════════════════
# PHASE 13 — FINAL INTEGRATION TESTING
# ═══════════════════════════════════════════

## Full End-to-End Tests

### Test Suite A: New User Journey
```
1. Register: POST /auth/register → get token
2. Check plan: GET /auth/me → plan='free', daily_remaining=10
3. Extract: POST /extract { query: "yoga", maxResults: 5 }
   Expected: 5 leads returned, quota=5 remaining
4. View leads: GET /leads → 5 rows
5. Add tag: POST /leads/{id}/tags { tag: "Hot" }
6. Export: GET /export/csv → file download with 5 rows
7. Quota check: POST /extract { maxResults: 10 }
   Expected: 429 (only 5 remaining, requested 10)
   Actually: Should work (5 remaining = return 5)
   Test: POST /extract { maxResults: 6 } after 5 used
   Expected: Returns 5 (remaining), deducts 5
```

### Test Suite B: PRO User Upgrade Flow
```
1. Start as FREE user
2. POST /billing/create-checkout { plan: 'pro' }
3. Complete Stripe test payment
4. GET /auth/me → plan='pro', daily_remaining=50
5. POST /extract { maxResults: 50 } → full PRO extraction
6. Verify: UsageLog has proxy costs
7. Verify: Admin dashboard shows this user's cost
```

### Test Suite C: Admin Cost Verification
```
1. Run 10 extractions with different users
2. GET /admin/apify/cost-summary → today shows N runs
3. GET /admin/apify/runs → all 10 visible
4. GET /admin/apify/cost-by-user → each user's cost shown
5. GET /admin/apify/proxy-breakdown → residential vs datacenter split
6. Compare: Sum of usage_logs.apify_cost_usd = admin total cost
   They MUST match exactly
```

### Test Suite D: Kill Switch
```
1. POST /admin/kill-switch { enabled: true }
2. POST /extract → 503 error
3. GET /admin/stats → kill_switch: true
4. POST /admin/kill-switch { enabled: false }
5. POST /extract → works normally
```

### Test Suite E: Stripe Subscription Lifecycle
```
1. Subscribe with test card
2. GET /billing/status → active
3. Simulate invoice.payment_failed webhook
4. GET /billing/status → past_due
5. POST /billing/cancel
6. Stripe dashboard shows cancel_at_period_end
7. When subscription ends, webhook fires
8. GET /auth/me → plan = 'free'
```

---

# ═══════════════════════════════════════════
# QUICK REFERENCE
# ═══════════════════════════════════════════

## All API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | /auth/register | None | Register new user |
| POST | /auth/login | None | Login + get JWT |
| GET | /auth/me | JWT | Get current user + quota |
| POST | /auth/change-password | JWT | Change password |
| POST | /billing/create-checkout | JWT | Start Stripe checkout |
| POST | /billing/webhook | None (Stripe sig) | Stripe events |
| GET | /billing/status | JWT | Subscription status |
| POST | /billing/cancel | JWT | Cancel subscription |
| POST | /billing/change-plan | JWT | Upgrade/downgrade |
| POST | /billing/portal | JWT | Stripe customer portal |
| POST | /extract | JWT | Main extraction |
| GET | /leads | JWT | Get all leads |
| GET | /leads/:id | JWT | Single lead |
| PATCH | /leads/:id/status | JWT | Update status |
| POST | /leads/:id/tags | JWT | Add tag |
| DELETE | /leads/:id/tags/:tag | JWT | Remove tag |
| POST | /leads/:id/notes | JWT | Add note |
| GET | /leads/:id/notes | JWT | Get notes |
| DELETE | /leads/:id | JWT | Delete lead |
| POST | /leads/bulk/tag | JWT | Bulk tag |
| POST | /leads/bulk/status | JWT | Bulk status update |
| POST | /lists | JWT | Create list |
| GET | /lists | JWT | Get all lists |
| GET | /lists/:id/leads | JWT | Leads in list |
| POST | /lists/:id/leads | JWT | Add to list |
| DELETE | /lists/:id/leads/:id | JWT | Remove from list |
| DELETE | /lists/:id | JWT | Delete list |
| GET | /export/csv | JWT | CSV download |
| GET | /admin/stats | Admin | Dashboard stats |
| GET | /admin/apify/cost-summary | Admin | Apify cost overview |
| GET | /admin/apify/runs | Admin | Per-run table |
| GET | /admin/apify/cost-by-user | Admin | Cost by user |
| GET | /admin/apify/proxy-breakdown | Admin | Proxy usage split |
| GET | /admin/apify/cache-stats | Admin | Cache efficiency |
| POST | /admin/kill-switch | Admin | Toggle kill switch |
| GET | /admin/config | Admin | Get config |
| PATCH | /admin/config | Admin | Update config |
| GET | /admin/users | Admin | All users |
| POST | /admin/users/:id/reset-quota | Admin | Reset quota |
| POST | /admin/users/:id/ban | Admin | Ban user |
| GET | /health | None | Health check |

---

## Database Tables Summary

| Table | Purpose |
|-------|---------|
| users | Auth, plan, Stripe IDs |
| daily_quota | Per-user per-day usage tracking |
| usage_logs | Every extraction with full Apify cost data |
| leads | All extracted profiles |
| lead_tags | Tags per lead |
| lead_notes | Notes per lead |
| saved_lists | User-created collections |
| list_leads | Which leads in which list |
| hashtag_cache | Cached extraction results |
| app_config | Kill switch, limits, feature flags |

---

## Apify Cost Fields Stored in usage_logs

| Field | What It Is |
|-------|-----------|
| apify_run_id | Run ID from Apify API |
| apify_cost_usd | Total cost in USD |
| apify_compute_units | CU consumed |
| apify_proxy_mb | Total proxy bandwidth MB |
| apify_datacenter_mb | Datacenter proxy MB used |
| apify_residential_mb | Residential proxy MB used |
| duration_seconds | How long actor ran |
| proxy_type | 'datacenter'/'hybrid'/'residential' |
| extraction_mode | 'fast'/'standard'/'full' |

---

## PROGRESS TRACKER

Phase 0  — Foundation & Setup          [ ] Not Started
Phase 1  — Database Models             [ ] Not Started
Phase 2  — Authentication              [ ] Not Started
Phase 3  — Stripe Billing              [ ] Not Started
Phase 4  — Quota Engine                [ ] Not Started
Phase 5  — Apify Integration           [ ] Not Started
Phase 6  — Extraction Endpoint         [ ] Not Started
Phase 7  — Lead Intelligence           [ ] Not Started
Phase 8  — CRM-Lite Management         [ ] Not Started
Phase 9  — Export Engine               [ ] Not Started
Phase 10 — Apify Cost Monitoring       [ ] Not Started
Phase 11 — Cost Optimizations          [ ] Not Started
Phase 12 — Deployment                  [ ] Not Started
Phase 13 — Final Integration Testing   [ ] Not Started

Actor Deploy: ✅ Done