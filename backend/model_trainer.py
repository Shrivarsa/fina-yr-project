"""
model_trainer.py — SCIP Guardian Model Trainer

Generates labeled training data via OpenRouter and trains the local model.

Usage (CLI):
    python model_trainer.py check     # validate OpenRouter connection FIRST
    python model_trainer.py seed      # generate samples and train
    python model_trainer.py train     # retrain on existing data only
    python model_trainer.py stats     # show model stats
"""

import os
import re
import sys
import json
import time
import argparse
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from custom_model import CustomSecurityModel

OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL    = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
HTTP_REFERER        = os.getenv("OPENROUTER_HTTP_REFERER", "https://scip-guardian.com")

SEED_DESCRIPTIONS = [
    # CLEAN (0.00–0.15)
    ("a Python function that adds two integers",                         "clean"),
    ("a class that reads a CSV file with pandas",                        "clean"),
    ("a Flask route that returns a JSON health check",                   "clean"),
    ("a function that sorts a list of strings alphabetically",           "clean"),
    ("a Python decorator that measures function execution time",         "clean"),
    ("a dataclass for a User with name and email fields",                "clean"),
    ("a simple linked list implementation in Python",                    "clean"),
    ("a function that paginates a list of items",                        "clean"),
    # LOW RISK (0.16–0.35)
    ("a Flask route that reads a query param without validation",        "low"),
    ("a function that catches all exceptions with bare except",          "low"),
    ("code that stores a session token in a plain dict",                 "low"),
    ("a function that logs user input to stdout without sanitising",     "low"),
    # MODERATE (0.36–0.55)
    ("a function that builds a URL from user input without sanitising",  "moderate"),
    ("a login that compares passwords with == instead of hmac",          "moderate"),
    ("code that disables SSL cert verification with verify=False",       "moderate"),
    ("a Flask debug server with debug=True exposed publicly",            "moderate"),
    ("a function that accepts a filename from user input and opens it",  "moderate"),
    # HIGH (0.56–0.74)
    ("code with a SQL query built by string concatenation",              "high"),
    ("code that stores a hardcoded database password in source",         "high"),
    ("a function that deserialises untrusted data with pickle.loads",    "high"),
    ("code with a GitHub personal access token hardcoded",               "high"),
    ("code with an AWS access key hardcoded in source",                  "high"),
    ("a function that runs rm -rf on a user-supplied path",              "high"),
    # CRITICAL (0.75–1.0)
    ("code that passes user input directly to eval()",                   "critical"),
    ("code that uses os.system() with unsanitised user input",           "critical"),
    ("code with subprocess shell=True and user-controlled command",      "critical"),
    ("code that escalates privileges with os.setuid(0)",                 "critical"),
    ("code that reads /etc/shadow and returns its contents",             "critical"),
    ("code with SQL injection via f-string in a SELECT query",           "critical"),
    ("a backdoor that opens a reverse shell to a remote server",         "critical"),
    ("code that exfiltrates /etc/passwd over HTTP to an attacker",       "critical"),
]

RISK_TIER_RANGE = {
    "clean":    (0.00, 0.15),
    "low":      (0.16, 0.35),
    "moderate": (0.36, 0.55),
    "high":     (0.56, 0.74),
    "critical": (0.75, 1.00),
}


def _check_connection() -> Dict[str, Any]:
    """Validate OpenRouter config. Returns dict with 'ok' bool and 'error' string."""
    if not OPENROUTER_API_KEY:
        return {"ok": False, "error": "OPENROUTER_API_KEY is not set in .env"}

    print(f"  API key : {OPENROUTER_API_KEY[:8]}...{OPENROUTER_API_KEY[-4:]}")
    print(f"  Base URL: {OPENROUTER_BASE_URL}")
    print(f"  Model   : {OPENROUTER_MODEL}")

    # Step 1 — quick reachability check (auth only, no strict model validation)
    # NOTE: We skip strict model-list matching because :free suffix models
    # (e.g. mistralai/mistral-7b-instruct:free) are valid but won't appear
    # in /models exactly. The completion test below is the real validator.
    try:
        ping = requests.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=10,
        )
        if ping.status_code == 401:
            return {"ok": False, "error": "API key is invalid or expired (401 Unauthorized)"}
        elif ping.status_code == 404:
            return {
                "ok": False,
                "error": (
                    f"Base URL returned 404: {OPENROUTER_BASE_URL}\n"
                    "  OPENROUTER_BASE_URL in .env should be: https://openrouter.ai/api/v1"
                ),
            }
        elif ping.status_code == 200:
            available = [m["id"] for m in ping.json().get("data", [])]
            print(f"  Models available on account: {len(available)}")
            # Only warn — don't block. :free variants won't be in this list exactly.
            if OPENROUTER_MODEL not in available:
                print(f"  Note: '{OPENROUTER_MODEL}' not in model list (OK for :free variants)")
                print(f"  Running completion test to verify ...")
        else:
            print(f"  /models returned {ping.status_code} — proceeding to completion test")
    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "error": (
                f"Cannot connect to {OPENROUTER_BASE_URL}\n"
                "  Check internet connection or OPENROUTER_BASE_URL in .env"
            ),
        }
    except Exception as e:
        print(f"  Warning: model list check failed ({e}) — trying completion test anyway")

    # Step 2 — test actual completion
    try:
        test = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  HTTP_REFERER,
                "X-Title":       "SCIP Guardian",
            },
            json={
                "model":      OPENROUTER_MODEL,
                "messages":   [{"role": "user", "content": "Say READY and nothing else."}],
                "max_tokens": 5,
            },
            timeout=20,
        )
        if test.status_code == 200:
            reply = test.json()["choices"][0]["message"]["content"].strip()
            return {"ok": True, "test_reply": reply}
        else:
            body = test.text[:400]
            return {"ok": False, "error": f"Completion test failed ({test.status_code}): {body}"}
    except Exception as e:
        return {"ok": False, "error": f"Completion test exception: {e}"}


def _call_openrouter(messages: List[Dict], max_tokens: int = 800) -> Optional[str]:
    """Single OpenRouter API call. Returns text or None on failure."""
    try:
        resp = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  HTTP_REFERER,
                "X-Title":       "SCIP Guardian Trainer",
            },
            json={
                "model":       OPENROUTER_MODEL,
                "messages":    messages,
                "temperature": 0.3,
                "max_tokens":  max_tokens,
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        body = e.response.text[:300] if e.response else ""
        print(f"  [OpenRouter] HTTP {code}: {body}")
        if code == 404:
            print(f"  [OpenRouter] 404 = wrong model name '{OPENROUTER_MODEL}' or wrong base URL")
            print(f"  [OpenRouter] Run: python model_trainer.py check")
        return None
    except Exception as e:
        print(f"  [OpenRouter] {e}")
        return None


def _generate_code(description: str, tier: str) -> Optional[str]:
    lo, hi = RISK_TIER_RANGE[tier]
    content = _call_openrouter([
        {
            "role": "system",
            "content": (
                "You are a code generator for a security training dataset. "
                "Output ONLY raw Python code. No explanations. No markdown fences."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a realistic Python snippet (20–60 lines) that: {description}.\n"
                f"Target security risk score: {lo:.2f}–{hi:.2f} out of 1.0.\n"
                "Output ONLY the raw Python code."
            ),
        },
    ], max_tokens=600)

    if not content:
        return None
    content = re.sub(r"^```[\w]*\n?", "", content)
    content = re.sub(r"\n?```$", "", content)
    return content.strip() or None


def _score_with_openrouter(code: str) -> Optional[float]:
    content = _call_openrouter([
        {
            "role": "system",
            "content": (
                "You are a security auditor. "
                "Respond with ONLY a decimal number 0.00–1.00. Nothing else."
            ),
        },
        {
            "role": "user",
            "content": (
                "Score this Python code for security risk (0.00=safe, 1.00=critical).\n"
                "0.00–0.15 clean | 0.16–0.35 minor | 0.36–0.55 low | "
                "0.56–0.74 moderate | 0.75–0.89 high | 0.90–1.00 critical\n\n"
                f"Code:\n{code}\n\n"
                "Numeric score only:"
            ),
        },
    ], max_tokens=10)

    if not content:
        return None
    m = re.search(r"([0-9]\.[0-9]+|[01])", content.strip())
    if not m:
        return None
    return round(min(max(float(m.group(1)), 0.0), 1.0), 4)


class ModelTrainer:
    def __init__(self):
        self.model = CustomSecurityModel()
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set in backend/.env"
            )

    def check(self) -> Dict[str, Any]:
        print("[Trainer] Checking OpenRouter connection …")
        result = _check_connection()
        if result["ok"]:
            print(f"  OK — test reply: '{result.get('test_reply', '')}'")
        else:
            print(f"  FAILED: {result['error']}")
        return result

    def seed(self, descriptions: Optional[List] = None,
             delay: float = 0.5) -> Dict[str, Any]:
        # Always validate first — avoids 31 silent failures
        print("[Trainer] Validating OpenRouter connection …")
        check = _check_connection()
        if not check["ok"]:
            print(f"\n[Trainer] Aborting seed — connection check failed:")
            print(f"  {check['error']}")
            print("\nFix your .env then run: python model_trainer.py check")
            return {
                "seeded": 0, "failed": 0,
                "error": check["error"],
                "training": {"status": "skipped", "reason": "connection_failed"},
            }

        print(f"  OK. Seeding with model: {OPENROUTER_MODEL}\n")
        descriptions = descriptions or SEED_DESCRIPTIONS
        added = failed = 0

        for desc, tier in descriptions:
            try:
                print(f"[Trainer] {desc} ({tier}) …")
                code = _generate_code(desc, tier)
                if not code:
                    print("  → generation failed")
                    failed += 1
                    continue

                score = _score_with_openrouter(code)
                if score is None:
                    print("  → scoring failed")
                    failed += 1
                    continue

                is_new = self.model.add_training_example(code, score, source="openrouter_seed")
                print(f"  → score: {score:.2f}  [{'saved' if is_new else 'duplicate'}]")
                if is_new:
                    added += 1
                time.sleep(delay)

            except Exception as e:
                print(f"  ERROR: {e}")
                failed += 1

        print(f"\n[Trainer] Done — {added} new samples, {failed} failures")
        return {"seeded": added, "failed": failed, "training": self.model.train()}

    def learn_from_commit(self, code: str, openrouter_score: float) -> bool:
        is_new = self.model.add_training_example(
            code, openrouter_score, source="live_commit"
        )
        if is_new:
            count = self.model.sample_count()
            if count > 0 and count % 50 == 0:
                print(f"[Trainer] Auto-retraining at {count} samples …")
                self.model.train()
        return is_new

    def retrain(self) -> Dict[str, Any]:
        return self.model.train(force=True)

    def stats(self) -> Dict[str, Any]:
        return self.model.get_stats()


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCIP Guardian Model Trainer")
    parser.add_argument(
        "command", choices=["check", "seed", "train", "stats"],
        help="check | seed | train | stats",
    )
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    if args.command == "check":
        try:
            trainer = ModelTrainer()
            result  = trainer.check()
        except RuntimeError as e:
            result = {"ok": False, "error": str(e)}
            print(f"[Trainer] {e}")

        if not result.get("ok"):
            avail = result.get("available_models", [])
            if avail:
                print("\nModels available on your OpenRouter account:")
                for m in sorted(avail)[:40]:
                    print(f"  {m}")
                print("\nPick one and set it as OPENROUTER_MODEL in backend/.env")
            sys.exit(1)
        else:
            print("\nConnection is working. Run: python model_trainer.py seed")

    elif args.command == "seed":
        try:
            trainer = ModelTrainer()
            result  = trainer.seed(delay=args.delay)
            print(json.dumps(result, indent=2))
        except RuntimeError as e:
            print(f"[Trainer] {e}")
            sys.exit(1)

    elif args.command == "train":
        try:
            trainer = ModelTrainer()
            result  = trainer.retrain()
            print(json.dumps(result, indent=2))
        except RuntimeError as e:
            print(f"[Trainer] {e}")
            sys.exit(1)

    elif args.command == "stats":
        result = CustomSecurityModel().get_stats()
        print(json.dumps(result, indent=2))