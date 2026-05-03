"""
tests/test_auth.py — Auth and core endpoint tests for Phase 2.
Run: .\venv\Scripts\python tests\test_auth.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from app import create_app
from app.models import db, User

app = create_app()

def client():
    return app.test_client()

def setup():
    with app.app_context():
        db.drop_all()
        db.create_all()
        from app.services.quota_service import seed_default_config
        seed_default_config()

def t(label, status_expected, res):
    ok = "PASS" if res.status_code == status_expected else "FAIL"
    data = res.get_json()
    print(f"{ok} [{res.status_code}] {label}: {json.dumps(data, indent=None)[:120]}")
    return data

def run_tests():
    setup()
    c = client()

    print("\n=== AUTH TESTS (PHASE 2) ===")

    # 1. Register - Invalid Email
    res = c.post('/auth/register', json={"email": "not-an-email", "password": "password123"})
    t("register invalid email -> 400", 400, res)

    # 2. Register - Weak Password
    res = c.post('/auth/register', json={"email": "test@spyleads.io", "password": "weak"})
    t("register weak password -> 400", 400, res)

    # 3. Register Success
    res = c.post('/auth/register', json={"email": "test@spyleads.io", "password": "password123"})
    data = t("register success", 201, res)
    token = data.get("token")

    # 4. Register Duplicate
    res = c.post('/auth/register', json={"email": "test@spyleads.io", "password": "password123"})
    t("register duplicate -> 409", 409, res)

    # 5. Login Success
    res = c.post('/auth/login', json={"email": "test@spyleads.io", "password": "password123"})
    data = t("login success", 200, res)
    token = data.get("token")

    # 6. Login Wrong Password
    res = c.post('/auth/login', json={"email": "test@spyleads.io", "password": "wrongpass"})
    t("login wrong password -> 401", 401, res)

    # 7. GET /auth/me
    res = c.get('/auth/me', headers={"Authorization": f"Bearer {token}"})
    me_data = t("/auth/me", 200, res)
    # Check if flat format is correct
    if "daily_used" in me_data and "plan" in me_data:
        print("PASS: /auth/me has correct flat schema")
    else:
        print("FAIL: /auth/me schema incorrect")

    # 8. Change Password
    res = c.post('/auth/change-password', json={
        "current_password": "password123",
        "new_password": "newpassword123"
    }, headers={"Authorization": f"Bearer {token}"})
    t("change password success", 200, res)

    # 9. Login with new password
    res = c.post('/auth/login', json={"email": "test@spyleads.io", "password": "newpassword123"})
    data = t("login with new password", 200, res)
    token = data.get("token")

    print("\n=== ADMIN TESTS (PHASE 2) ===")

    # 10. Admin via Key
    res = c.get('/admin/proxy-cost?key=spyleads_admin_k7x9m2v4p8q1w3')
    t("admin access via key", 200, res)

    # 11. Admin via is_admin flag (unauthorized first)
    res = c.get('/admin/stats', headers={"Authorization": f"Bearer {token}"})
    t("regular user admin stats -> 403", 403, res)

    # Promote user to admin in DB
    with app.app_context():
        user = User.query.filter_by(email="test@spyleads.io").first()
        user.is_admin = True
        db.session.commit()
    
    # 12. Admin via is_admin flag (authorized now)
    res = c.get('/admin/stats', headers={"Authorization": f"Bearer {token}"})
    t("admin user stats -> 200", 200, res)

    print("\n=== LEADS TESTS ===")
    res = c.post('/leads', json={
        "username": "testuser", "full_name": "Test User",
        "followers": 5000, "email": "test@email.com", "bio": "Fitness coach"
    }, headers={"Authorization": f"Bearer {token}"})
    lead_data = t("save lead", 201, res)
    lead_id = lead_data.get("lead", {}).get("id")

    res = c.get('/export/csv', headers={"Authorization": f"Bearer {token}"})
    ok = "PASS" if res.status_code == 200 and b"testuser" in res.data else "FAIL"
    print(f"{ok} [200] export CSV check")

    print("\n=== DONE ===")

if __name__ == '__main__':
    run_tests()
