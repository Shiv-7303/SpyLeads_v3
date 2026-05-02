# SpyLeads — Complete Build Checklist
> Architecture: Cloud SaaS | Apify Actor | Flask Backend | CRM-lite Lead Manager
> Last Updated: May 2026

---

## PHASE 0 — FOUNDATION & SETUP
- [ ] Apify account created + actor deployed via CLI
- [ ] Actor test run successful (manual input from Apify console)
- [ ] Actor returns correct dataset structure (username, followers, bio, email, etc.)
- [ ] Flask project folder initialized (virtualenv + requirements.txt)
- [ ] Render account ready for Flask backend deploy
- [ ] Gumroad products created: PRO (₹499) + PRO PLUS (₹1199)
- [ ] Gumroad API key saved securely (env var)
- [ ] SQLite or PostgreSQL database initialized
- [ ] `.env` file created with all secrets (never committed to git)
- [ ] GitHub repo created for Flask backend

---

## PHASE 1 — BACKEND CORE (Flask API)

### License & Auth
- [ ] `POST /validate-license` — calls Gumroad API, returns plan + status
- [ ] License key stored in DB on first validation
- [ ] Plan detection working: FREE / PRO / PRO PLUS

### Quota Engine
- [ ] Daily quota check logic (10 / 50 / 150 by plan)
- [ ] Monthly cap check logic (200 / 1200 / 4500 by plan)
- [ ] `daily_used` resets at midnight IST
- [ ] `monthly_used` resets on 1st of month
- [ ] Quota deducted only after successful extraction
- [ ] `GET /quota` endpoint — returns remaining daily + monthly

### Kill Switch
- [ ] `GET /kill-switch` endpoint
- [ ] Kill switch flag stored in DB / config
- [ ] All extraction routes check kill switch before proceeding
- [ ] Admin can toggle via admin panel

### Remote Config
- [ ] `GET /config` endpoint
- [ ] Returns: daily_limits, monthly_caps, max_results_per_request, feature flags
- [ ] Config editable from admin without redeployment

---

## PHASE 2 — EXTRACTION ENGINE

### POST /extract
- [ ] Accepts: type, value, maxResults, filters (emailRequired, minFollowers, maxFollowers, bioKeyword)
- [ ] Validates license key (header or body)
- [ ] Checks daily quota
- [ ] Checks monthly cap
- [ ] Checks kill switch
- [ ] Validates maxResults against plan limits (FREE=10, PRO=50, PRO+=150)
- [ ] Triggers Apify actor with correct input
- [ ] Waits for actor run completion
- [ ] Fetches dataset from Apify
- [ ] Returns structured JSON response

### Error Handling
- [ ] `invalid_license` → 401
- [ ] `quota_exceeded` → 429
- [ ] `monthly_cap_reached` → 429
- [ ] `kill_switch_active` → 503
- [ ] `actor_timeout` → 504
- [ ] `dataset_empty` → 200 with empty array + message
- [ ] `instagram_block_detected` → 503

### Usage Logging
- [ ] Every extraction logged to `usage_logs` table
- [ ] Fields: license_key, timestamp, profiles_requested, profiles_returned
- [ ] Actor run_id stored in `actor_runs` table

---

## PHASE 3 — LEAD INTELLIGENCE ENGINE

### Lead Quality Scorer
- [ ] +30 if email present in bio
- [ ] +20 if website/link present
- [ ] +15 if followers > 5000
- [ ] +10 if service keyword in bio (coach, agency, hire, DM, consulting)
- [ ] +10 if category exists
- [ ] Score calculated per lead, stored as `lead_score` (0–100)

### Intent Detection
- [ ] Bio scanned for keywords: hire, DM, contact, services, agency, coach, consulting
- [ ] `high_intent: true/false` flag set per lead
- [ ] 🔥 High Intent badge shown in frontend

### Influencer Classification
- [ ] Micro-influencer: 1k–50k followers → badge shown
- [ ] Mid-tier: 50k–500k
- [ ] Macro: 500k+

### Auto-Tagging Engine
- [ ] email present → tag: "Hot"
- [ ] followers > 10k → tag: "Influencer"
- [ ] bio contains "coach" → tag: "Coach Lead"
- [ ] website present → tag: "Business Lead"
- [ ] Tags auto-applied after each extraction

### Smart Filter Engine
- [ ] Filter by: emailRequired, websiteRequired, minFollowers, maxFollowers, bioKeyword
- [ ] Filter by: business accounts only, active accounts only (last post < 30 days)
- [ ] Filter by: micro-influencer toggle
- [ ] All filters applied server-side before returning results

---

## PHASE 4 — CRM-LITE LEAD MANAGEMENT

### Lead Storage
- [ ] Extracted leads stored per user in DB
- [ ] Duplicate detection by username (no repeat leads in same list)
- [ ] `GET /leads` — paginated lead list for user
- [ ] `GET /leads/:id` — single lead detail

### Tags System
- [ ] `POST /leads/:id/tags` — add tag
- [ ] `DELETE /leads/:id/tags/:tag` — remove tag
- [ ] `GET /leads?tag=Hot` — filter by tag
- [ ] Tag filter panel functional in UI

### Notes System
- [ ] `POST /leads/:id/notes` — add note
- [ ] `GET /leads/:id/notes` — get all notes
- [ ] Free-text notes per lead

### Workflow Status
- [ ] Status options: New / Qualified / Contacted / Replied / Converted / Closed
- [ ] `PATCH /leads/:id/status` — update status
- [ ] Color-coded labels in UI

### Saved Lists
- [ ] `POST /lists` — create named list (e.g. "Fitness Influencers Mumbai")
- [ ] `POST /lists/:id/leads` — add lead to list
- [ ] `GET /lists` — all user lists
- [ ] `GET /lists/:id/leads` — leads in a list
- [ ] `DELETE /lists/:id` — delete list

---

## PHASE 5 — EXPORT ENGINE

### CSV Export
- [ ] `GET /export/csv?list_id=X` — download CSV
- [ ] Selective export: Hot Leads, Influencers, Email Leads, Contacted
- [ ] CSV columns: username, followers, email, website, bio, tags, status, lead_score

### Google Sheets Export
- [ ] Google OAuth flow implemented
- [ ] Token stored securely per user
- [ ] `POST /export/sheets` — appends rows to user's sheet
- [ ] Sheet columns match CSV structure
- [ ] Handles token refresh automatically

---

## PHASE 6 — FRONTEND WEBSITE

### Landing Page
- [ ] Hero: "Find 150 targeted Instagram leads daily in minutes"
- [ ] How It Works section (3-step visual)
- [ ] Use Cases: Agencies, Coaches, Freelancers, Brands
- [ ] Feature comparison table (FREE vs PRO vs PRO PLUS)
- [ ] Pricing section (₹499 / ₹1199 + Free tier)
- [ ] CTA buttons → Gumroad checkout links
- [ ] Mobile responsive

### Pricing Page
- [ ] 3 plan cards: FREE / PRO / PRO PLUS
- [ ] Feature list per plan
- [ ] Buy Now → Gumroad

### Dashboard (Post-login)
- [ ] Quota remaining: X / 50 today
- [ ] Monthly cap remaining
- [ ] Recent extractions list
- [ ] Saved lists summary
- [ ] Hot leads count
- [ ] Influencers found count

### Extraction Panel
- [ ] Search type selector: Hashtag / Location / Competitor / Post Likers
- [ ] Input field for hashtag/handle
- [ ] Advanced filters accordion: follower range, email required, bio keyword, micro-influencer toggle
- [ ] Max results slider (capped by plan)
- [ ] Extract button
- [ ] Real-time progress indicator
- [ ] Results table with lead scores + badges

### Lead Manager
- [ ] Searchable + filterable lead table
- [ ] Tag filter panel (Hot, Influencer, Contacted, etc.)
- [ ] Inline status update
- [ ] Add to saved list button
- [ ] Notes modal per lead
- [ ] Bulk select + bulk tag/export

### Saved Lists Panel
- [ ] All user lists displayed
- [ ] Click list → view leads
- [ ] Rename / delete list
- [ ] Export list as CSV

### Export Center
- [ ] Export by list
- [ ] Export by tag / status filter
- [ ] Google Sheets connect button
- [ ] Download CSV button

### Account Settings
- [ ] License key input + verify
- [ ] Plan displayed
- [ ] Usage stats
- [ ] Reset/logout

---

## PHASE 7 — ADMIN PANEL

- [ ] Protected route (admin password / token)
- [ ] View all active users + plans
- [ ] Daily / monthly extraction counts per user
- [ ] Apify credit usage monitor
- [ ] Blacklist a license key
- [ ] Manually reset user quota
- [ ] Toggle global kill switch
- [ ] View suspicious activity (high frequency users)
- [ ] Remote config editor (change quotas live)

---

## PHASE 8 — DEPLOYMENT

### Backend (Render)
- [ ] Flask app deployed to Render
- [ ] Environment variables set on Render (APIFY_TOKEN, GUMROAD_KEY, SECRET_KEY, DB_URL)
- [ ] Database connected (Render PostgreSQL or SQLite for MVP)
- [ ] Health check endpoint: `GET /health` → `{"status": "ok"}`
- [ ] CORS configured for frontend domain

### Frontend
- [ ] Hosted on Vercel / Netlify / Render static
- [ ] Custom domain connected (spyleads.in or .com)
- [ ] HTTPS enabled
- [ ] API base URL pointing to Render backend

### Apify Actor
- [ ] Actor deployed + latest build live
- [ ] Actor tested end-to-end with real hashtag
- [ ] APIFY_TOKEN in Render env vars

---

## PHASE 9 — TESTING & QA

- [ ] Full extraction flow tested: hashtag → dataset → scored leads → UI
- [ ] FREE plan quota limit enforced correctly
- [ ] PRO plan quota limit enforced correctly
- [ ] PRO PLUS quota limit enforced correctly
- [ ] Monthly caps enforced
- [ ] Kill switch disables extraction globally
- [ ] Invalid license returns 401
- [ ] CSV export downloads correctly with all columns
- [ ] Google Sheets export appends rows correctly
- [ ] Lead tags + notes persist across sessions
- [ ] Saved lists work correctly
- [ ] Admin panel actions work (blacklist, quota reset, kill switch)
- [ ] Mobile responsiveness tested on landing page + dashboard

---

## PHASE 10 — LAUNCH

- [ ] Privacy Policy page live (required for Gumroad + Google OAuth)
- [ ] Terms of Service page live
- [ ] Gumroad webhook configured (for license activation on purchase)
- [ ] Test purchase flow end-to-end (buy → license email → enter key → upgrade to PRO)
- [ ] Error monitoring set up (Sentry or basic logging)
- [ ] First 3 beta users onboarded
- [ ] Feedback loop established

---

## QUICK REFERENCE — API ENDPOINTS

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /validate-license | Validate Gumroad license |
| GET | /quota | Get remaining quota |
| POST | /extract | Trigger extraction |
| GET | /leads | Get all leads (paginated) |
| PATCH | /leads/:id/status | Update lead status |
| POST | /leads/:id/tags | Add tag to lead |
| POST | /leads/:id/notes | Add note to lead |
| POST | /lists | Create saved list |
| GET | /lists | Get all saved lists |
| GET | /export/csv | Download CSV |
| POST | /export/sheets | Export to Google Sheets |
| GET | /config | Remote config |
| GET | /kill-switch | Kill switch status |
| GET | /health | Health check |

---

## QUICK REFERENCE — DATABASE TABLES

| Table | Key Fields |
|-------|-----------|
| users | id, email, license_key, plan, expiry_date |
| usage_logs | user_id, profiles_extracted, timestamp |
| actor_runs | run_id, license_key, profiles_requested, profiles_returned |
| leads | id, user_id, username, followers, email, bio, lead_score, status |
| lead_tags | lead_id, tag_name |
| lead_notes | lead_id, note_text, created_at |
| saved_lists | id, user_id, list_name |
| list_leads | list_id, lead_id |

---

## PROGRESS TRACKER

Phase 0 — Foundation         [ ] Not Started
Phase 1 — Backend Core       [ ] Not Started
Phase 2 — Extraction Engine  [ ] Not Started
Phase 3 — Intelligence Engine[ ] Not Started
Phase 4 — CRM-lite           [ ] Not Started
Phase 5 — Export Engine      [ ] Not Started
Phase 6 — Frontend           [ ] Not Started
Phase 7 — Admin Panel        [ ] Not Started
Phase 8 — Deployment         [ ] In Progress (Actor deployed)
Phase 9 — Testing            [ ] Not Started
Phase 10 — Launch            [ ] Not Started