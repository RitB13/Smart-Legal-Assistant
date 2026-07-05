"""
End-to-End Mediation Flow Test
================================
Tests the complete mediation pipeline via the live FastAPI server.

Prerequisites:
  1. Server running:  uvicorn app:app --reload --port 8000
  2. Two registered & verified accounts (or set USE_EXISTING=True and fill credentials)

Run:
    python src/data/mediation_training/test_e2e.py

The script prints a pass/fail result for each step and a final summary.
"""

import sys
import json
import time
import requests

BASE = "http://localhost:8000"
TIMEOUT = 15

# ─── Test credentials ─────────────────────────────────────────────────────────
# Use real emails you control so OTP verification actually arrives.
# Override via env vars: TEST_EMAIL_A, TEST_PASS_A, TEST_EMAIL_B, TEST_PASS_B
#
# Quick setup (one time, before running this test):
#   1. POST /auth/register with each email through Swagger UI or curl
#   2. Enter the OTP that arrives in your inbox via POST /auth/verify-otp
#   3. Then run this test — subsequent runs just login, no OTP needed
#
# Or: if you set TOKEN_A and TOKEN_B env vars to pre-obtained JWT tokens
#     the script skips login entirely.

import os as _os

PARTY_A = {
    "email":    _os.getenv("TEST_EMAIL_A", "party_a_test@example.com"),
    "password": _os.getenv("TEST_PASS_A",  "TestPass123!"),
    "name": "Rahul Sharma",
    "preferred_language": "en",
    "jurisdiction": "india",
}
PARTY_B = {
    "email":    _os.getenv("TEST_EMAIL_B", "party_b_test@example.com"),
    "password": _os.getenv("TEST_PASS_B",  "TestPass456!"),
    "name": "Priya Patel",
    "preferred_language": "en",
    "jurisdiction": "india",
}

# Optional: skip auth entirely if tokens are provided
PRESET_TOKEN_A = _os.getenv("TOKEN_A", "")
PRESET_TOKEN_B = _os.getenv("TOKEN_B", "")

RESULTS = []


def step(name):
    def _decorator(fn):
        def _wrapper(*args, **kwargs):
            try:
                result = fn(*args, **kwargs)
                RESULTS.append((name, "PASS", ""))
                print(f"  ✅ {name}")
                return result
            except AssertionError as e:
                RESULTS.append((name, "FAIL", str(e)))
                print(f"  ❌ {name}: {e}")
                return None
            except Exception as e:
                RESULTS.append((name, "ERROR", str(e)))
                print(f"  💥 {name}: {e}")
                return None
        return _wrapper
    return _decorator


def post(path, data=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.post(f"{BASE}{path}", json=data, headers=headers, timeout=TIMEOUT)
    return r


def get(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(f"{BASE}{path}", headers=headers, timeout=TIMEOUT)
    return r


# ─── Step definitions ─────────────────────────────────────────────────────────

@step("Server health check")
def test_health():
    r = get("/health")
    assert r.status_code == 200, f"Got {r.status_code}"
    data = r.json()
    assert data.get("status") == "ok", f"Unexpected body: {data}"
    return True


@step("Register Party A")
def test_register_a():
    r = post("/auth/register", PARTY_A)
    if r.status_code == 400 and "already registered" in r.text:
        print("    (already registered — continuing)")
        return True
    if r.status_code == 500 and "verification email" in r.text:
        print(f"    ⚠  Account created but OTP email failed (fake email address?).")
        print(f"    →  Use Swagger to call POST /auth/resend-otp with email={PARTY_A['email']}")
        print(f"       then POST /auth/verify-otp to complete verification.")
        return True
    assert r.status_code == 201, f"Got {r.status_code}: {r.text[:200]}"
    print(f"    Account created — check {PARTY_A['email']} for OTP.")
    return True


@step("Register Party B")
def test_register_b():
    r = post("/auth/register", PARTY_B)
    if r.status_code == 400 and "already registered" in r.text:
        print("    (already registered — continuing)")
        return True
    if r.status_code == 500 and "verification email" in r.text:
        print(f"    ⚠  Account created but OTP email failed (fake email address?).")
        print(f"    →  Use Swagger to call POST /auth/resend-otp with email={PARTY_B['email']}")
        print(f"       then POST /auth/verify-otp to complete verification.")
        return True
    assert r.status_code == 201, f"Got {r.status_code}: {r.text[:200]}"
    print(f"    Account created — check {PARTY_B['email']} for OTP.")
    return True


def get_token_for(user, otp_override=None):
    """
    Try logging in. If unverified, prompt for OTP (or use override).
    Returns JWT token string.
    """
    r = post("/auth/login", {"email": user["email"], "password": user["password"]})
    if r.status_code == 200:
        return r.json()["access_token"]

    if r.status_code == 403 and "not verified" in r.text.lower():
        if otp_override:
            otp = otp_override
        else:
            otp = input(f"    Enter OTP sent to {user['email']}: ").strip()
        rv = post("/auth/verify-otp", {"email": user["email"], "otp_code": otp})
        assert rv.status_code == 200, f"OTP verify failed: {rv.text[:200]}"
        return rv.json()["access_token"]

    raise AssertionError(f"Login failed {r.status_code}: {r.text[:200]}")


@step("Login Party A")
def test_login_a():
    token = get_token_for(PARTY_A)
    assert token and len(token) > 10
    return token


@step("Login Party B")
def test_login_b():
    token = get_token_for(PARTY_B)
    assert token and len(token) > 10
    return token


@step("GET /auth/me — Party A")
def test_me(token_a):
    r = get("/auth/me", token=token_a)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body["email"] == PARTY_A["email"]
    return True


@step("Create dispute (Party A)")
def test_create_dispute(token_a):
    payload = {
        "case_description": (
            "I rented a flat in Bangalore for 11 months and paid a security deposit of Rs. 75,000. "
            "Upon vacating the premises in good condition on the agreed date, my landlord refused to "
            "return the deposit claiming damages that were pre-existing and unrelated to my tenancy."
        ),
        "case_type": "property",
        "jurisdiction": "India/Karnataka",
        "state": "Karnataka",
        "language": "en",
    }
    r = post("/mediation/create", payload, token=token_a)
    assert r.status_code == 201, f"Got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "dispute_id" in body
    assert "invite_code" in body
    assert len(body["invite_code"]) >= 6
    print(f"    dispute_id={body['dispute_id']}, invite_code={body['invite_code']}")
    return body["dispute_id"], body["invite_code"]


@step("Join dispute (Party B)")
def test_join_dispute(invite_code, token_b):
    r = post("/mediation/join", {"invite_code": invite_code}, token=token_b)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("status") == "pending_statements"
    return True


@step("Submit statement — Party A")
def test_submit_a(dispute_id, token_a):
    payload = {
        "statement": (
            "I am the tenant. Pursuant to the rental agreement dated March 2024, I paid a security "
            "deposit of Rs. 75,000 via NEFT (transaction ID TXN2024XYZ). The agreement clearly states "
            "that the deposit shall be refunded within 15 days of vacating if no damage is caused. "
            "I vacated on February 28, 2026 and handed over the keys. The flat was in the same condition "
            "as when I moved in. The landlord has not returned the deposit or provided any written "
            "communication about damages despite two weeks having passed."
        ),
        "supporting_points": [
            "Bank transfer receipt for Rs. 75,000 available",
            "Rental agreement clause 8 specifies 15-day refund",
            "WhatsApp messages confirming vacating date",
        ],
        "language": "en",
    }
    r = post(f"/mediation/{dispute_id}/submit", payload, token=token_a)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "status" in body
    return True


@step("Submit statement — Party B (triggers analysis)")
def test_submit_b(dispute_id, token_b):
    payload = {
        "statement": (
            "I am the landlord. The tenant caused significant damage to the flat including "
            "broken bathroom tiles worth Rs. 20,000 and a damaged kitchen exhaust fan worth Rs. 8,000. "
            "Additionally the tenant left without settling the outstanding electricity bill of Rs. 5,000. "
            "I am willing to return the remaining Rs. 42,000 after deducting legitimate repair costs. "
            "Photos of the damage were sent to the tenant on WhatsApp."
        ),
        "supporting_points": [
            "Repair estimate from contractor dated March 2026",
            "Electricity bill copy",
            "Photos of damage sent via WhatsApp",
        ],
        "language": "en",
    }
    r = post(f"/mediation/{dispute_id}/submit", payload, token=token_b)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("status") == "analysis_running", f"Expected analysis_running, got: {body}"
    print(f"    Analysis triggered. Polling status...")
    return True


@step("Poll status until completed (max 90s)")
def test_poll_status(dispute_id, token_a):
    for i in range(18):
        time.sleep(5)
        r = get(f"/mediation/{dispute_id}/status", token=token_a)
        assert r.status_code == 200, f"Poll failed {r.status_code}"
        status = r.json().get("status")
        print(f"    [{i*5+5}s] status={status}")
        if status == "completed":
            return True
        if status == "failed":
            raise AssertionError("Analysis failed")
    raise AssertionError("Timed out waiting for analysis to complete (90s)")


@step("GET result — validate report structure")
def test_get_result(dispute_id, token_a):
    r = get(f"/mediation/{dispute_id}/result", token=token_a)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body["status"] == "completed", f"Status: {body['status']}"
    report = body.get("report")
    assert report is not None, "report is null"

    # Validate required fields
    assert "proposed_settlement" in report and report["proposed_settlement"], "Missing proposed_settlement"
    assert "fairness_audit" in report, "Missing fairness_audit"
    assert "settlement_range" in report, "Missing settlement_range"
    assert "points_of_agreement" in report, "Missing points_of_agreement"
    assert "points_of_conflict" in report, "Missing points_of_conflict"

    fa = report["fairness_audit"]
    print(f"    Fairness: A={fa.get('party_a_privilege_score'):.3f}, B={fa.get('party_b_privilege_score'):.3f}, bias={fa.get('bias_detected')}")

    sr = report["settlement_range"]
    print(f"    Settlement range: ₹{sr.get('low')} – ₹{sr.get('high')} (confidence={sr.get('confidence')}, basis={sr.get('basis')})")

    prec = report.get("similar_precedents", [])
    print(f"    Similar precedents: {len(prec)} returned")
    if prec:
        print(f"    First: {prec[0][:100]}")

    print(f"    model_version: {report.get('model_version')}")
    print(f"    Proposed: {report.get('proposed_settlement', '')[:120]}")
    return True


@step("GET result — Party B also sees same report")
def test_get_result_b(dispute_id, token_b):
    r = get(f"/mediation/{dispute_id}/result", token=token_b)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["report"] is not None
    return True


@step("Submit feedback (Party A)")
def test_feedback(dispute_id, token_a):
    r = post(
        f"/mediation/{dispute_id}/feedback",
        {"rating": 4, "accepted_settlement": True, "comment": "Fair and quick resolution."},
        token=token_a,
    )
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
    return True


@step("GET /mediation/my/disputes — Party A")
def test_my_disputes(token_a):
    r = get("/mediation/my/disputes", token=token_a)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert "disputes" in body
    assert body["total"] >= 1
    print(f"    Party A has {body['total']} dispute(s)")
    return True


@step("Access denied — third party cannot see dispute")
def test_access_denied(dispute_id):
    # Unauthenticated request should get 401
    r = get(f"/mediation/{dispute_id}/status")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    return True


# ─── Runner ───────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Smart Legal Assistant — Mediation E2E Test")
    print("=" * 60)

    # Health
    test_health()

    # Auth setup
    if PRESET_TOKEN_A and PRESET_TOKEN_B:
        print("  ℹ  Using pre-set TOKEN_A / TOKEN_B — skipping registration and login.")
        token_a, token_b = PRESET_TOKEN_A, PRESET_TOKEN_B
        RESULTS.append(("Register Party A", "PASS", "skipped (preset token)"))
        RESULTS.append(("Register Party B", "PASS", "skipped (preset token)"))
        RESULTS.append(("Login Party A",    "PASS", "skipped (preset token)"))
        RESULTS.append(("Login Party B",    "PASS", "skipped (preset token)"))
    else:
        test_register_a()
        test_register_b()
        token_a = test_login_a()
        token_b = test_login_b()

    if not token_a or not token_b:
        print("\n⛔ Cannot continue without auth tokens.")
        sys.exit(1)

    test_me(token_a)

    # Mediation flow
    create_result = test_create_dispute(token_a)
    if not create_result:
        print("\n⛔ Cannot continue without dispute_id.")
        sys.exit(1)
    dispute_id, invite_code = create_result

    test_join_dispute(invite_code, token_b)
    test_submit_a(dispute_id, token_a)
    test_submit_b(dispute_id, token_b)
    test_poll_status(dispute_id, token_a)
    test_get_result(dispute_id, token_a)
    test_get_result_b(dispute_id, token_b)
    test_feedback(dispute_id, token_a)
    test_my_disputes(token_a)
    test_access_denied(dispute_id)

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    failed = sum(1 for _, s, _ in RESULTS if s in ("FAIL", "ERROR"))
    print(f"  Results: {passed}/{len(RESULTS)} passed, {failed} failed")
    if failed:
        print("\n  Failed steps:")
        for name, status, err in RESULTS:
            if status != "PASS":
                print(f"    [{status}] {name}: {err}")
    print("=" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
