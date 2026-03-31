"""
diagnose.py — Run this from D:\SCIP12\backend to find the exact 500 error.

Usage:
    python diagnose.py YOUR_EMAIL YOUR_PASSWORD

It will:
1. Test login
2. Test analyze with a tiny safe code snippet
3. Test analyze with custom_model.py
4. Print the exact error detail from the server
"""

import sys
import json
import requests

BASE_URL = "http://localhost:5000"


def main():
    if len(sys.argv) < 3:
        print("Usage: python diagnose.py YOUR_EMAIL YOUR_PASSWORD")
        sys.exit(1)

    email    = sys.argv[1]
    password = sys.argv[2]

    # ── Step 1: Login ────────────────────────────────────────────────────────
    print("\n[1] Testing login...")
    r = requests.post(f"{BASE_URL}/api/login", json={"email": email, "password": password})
    print(f"    Status: {r.status_code}")
    if r.status_code != 200:
        print(f"    Error: {r.text}")
        sys.exit(1)

    token = r.json().get("access_token", "")
    print(f"    OK — token starts with: {token[:20]}...")

    headers = {"Authorization": f"Bearer {token}"}

    # ── Step 2: Health check ─────────────────────────────────────────────────
    print("\n[2] Health check...")
    r = requests.get(f"{BASE_URL}/health")
    print(f"    Status: {r.status_code}")
    try:
        print(f"    {json.dumps(r.json(), indent=4)}")
    except Exception:
        print(f"    {r.text}")

    # ── Step 3: Analyze tiny safe code ──────────────────────────────────────
    print("\n[3] Testing analyze with tiny safe code...")
    tiny_code = "def add(a, b):\n    return a + b\n"
    r = requests.post(
        f"{BASE_URL}/api/analyze_commit",
        headers=headers,
        json={"code_content": tiny_code},
    )
    print(f"    Status: {r.status_code}")
    try:
        data = r.json()
        if r.status_code == 200:
            print(f"    risk_score:     {data.get('risk_score')}")
            print(f"    status:         {data.get('status')}")
            print(f"    analysis_mode:  {data.get('analysis_mode')}")
            print(f"    openrouter_called: {data.get('openrouter_called')}")
        else:
            print(f"    ERROR: {data.get('error')}")
            detail = data.get("detail", "")
            if detail:
                print(f"\n    TRACEBACK:\n{detail}")
    except Exception as e:
        print(f"    Could not parse response: {e}")
        print(f"    Raw: {r.text[:500]}")

    # ── Step 4: Analyze custom_model.py ─────────────────────────────────────
    print("\n[4] Testing analyze with custom_model.py...")
    try:
        with open("custom_model.py", "r", encoding="utf-8") as f:
            code = f.read()
        print(f"    File size: {len(code)} chars, {code.count(chr(10))} lines")
    except FileNotFoundError:
        print("    custom_model.py not found in current directory — trying full path")
        try:
            with open(r"D:\SCIP12\backend\custom_model.py", "r", encoding="utf-8") as f:
                code = f.read()
        except FileNotFoundError:
            print("    Could not find custom_model.py — skipping")
            code = None

    if code:
        r = requests.post(
            f"{BASE_URL}/api/analyze_commit",
            headers=headers,
            json={"code_content": code},
        )
        print(f"    Status: {r.status_code}")
        try:
            data = r.json()
            if r.status_code == 200:
                print(f"    risk_score:        {data.get('risk_score')}")
                print(f"    status:            {data.get('status')}")
                print(f"    analysis_mode:     {data.get('analysis_mode')}")
                print(f"    openrouter_called: {data.get('openrouter_called')}")
                print(f"    openrouter_reason: {data.get('openrouter_reason')}")
                print(f"    vulnerabilities:   {data.get('vulnerabilities', [])[:3]}")
            else:
                print(f"    ERROR: {data.get('error')}")
                detail = data.get("detail", "")
                if detail:
                    print(f"\n    TRACEBACK:\n{detail}")
                else:
                    print(f"\n    Full response: {json.dumps(data, indent=4)}")
        except Exception as e:
            print(f"    Could not parse response: {e}")
            print(f"    Raw: {r.text[:1000]}")

    # ── Step 5: Import chain test ────────────────────────────────────────────
    print("\n[5] Testing local import chain...")
    imports_to_test = [
        ("custom_model", "CustomSecurityModel"),
        ("model_trainer", "ModelTrainer"),
        ("model_routes",  "register_model_routes"),
        ("ai_service",    "AIService"),
    ]
    for module, cls in imports_to_test:
        try:
            m = __import__(module)
            getattr(m, cls)
            print(f"    {module}.{cls}: OK")
        except ImportError as e:
            print(f"    {module}: MISSING — {e}")
        except AttributeError as e:
            print(f"    {module}.{cls}: ATTRIBUTE MISSING — {e}")
        except RuntimeError as e:
            print(f"    {module}: RuntimeError (likely missing API key, OK) — {e}")
        except Exception as e:
            print(f"    {module}: UNEXPECTED ERROR — {type(e).__name__}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()