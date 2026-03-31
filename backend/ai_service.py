"""
ai_service.py — SCIP Guardian AI Service
"""

import os
import re
import traceback
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

VULNERABILITY_RULES = [
    {
        'category': 'Remote Code Execution',
        'severity': 0.95,
        'patterns': [
            r'os\.system\s*\(',
            r'subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True',
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'compile\s*\(.*exec\)',
            r'__import__\s*\(',
        ],
    },
    {
        'category': 'Privilege Escalation',
        'severity': 0.90,
        'patterns': [
            r'os\.setuid\s*\(\s*0\s*\)',
            r'chmod\s+777',
            r'\/etc\/shadow',
            r'\/etc\/passwd',
        ],
    },
    {
        'category': 'SQL Injection',
        'severity': 0.85,
        'patterns': [
            r'execute\s*\(\s*["\']?\s*(SELECT|INSERT|UPDATE|DELETE).*\+',
            r'WHERE\s+\w+\s*=\s*["\']?\s*\+',
            r'f["\'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*\{',
            r'".*SELECT.*"\s*\+',
            r"'.*SELECT.*'\s*\+",
        ],
    },
    {
        'category': 'Hardcoded Secrets',
        'severity': 0.80,
        'patterns': [
            r'(DB_PASSWORD|DATABASE_PASSWORD)\s*=\s*["\'][^"\']{4,}["\']',
            r'(SECRET_KEY|APP_SECRET)\s*=\s*["\'][^"\']{4,}["\']',
            r'ghp_[a-zA-Z0-9]{36}',
            r'sk-[a-zA-Z0-9]{32,}',
            r'AKIA[0-9A-Z]{16}',
            r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
        ],
    },
    {
        'category': 'Dangerous File Operations',
        'severity': 0.80,
        'patterns': [
            r'rm\s+-rf\s+\/',
            r'shutil\.rmtree\s*\(',
        ],
    },
    {
        'category': 'Insecure Deserialization',
        'severity': 0.75,
        'patterns': [
            r'pickle\.loads\s*\(',
            r'marshal\.loads\s*\(',
        ],
    },
]


def run_pattern_detection(code_content: str) -> Dict[str, Any]:
    detected    = {}
    floor_score = 0.0
    for rule in VULNERABILITY_RULES:
        matched = []
        for pattern in rule['patterns']:
            found = re.findall(pattern, code_content, re.IGNORECASE | re.MULTILINE)
            if found:
                matched.extend([str(m) for m in found])
        if matched:
            detected[rule['category']] = {
                'severity': rule['severity'],
                'matches':  matched[:3],
            }
            floor_score = max(floor_score, rule['severity'])
    return {'detected': detected, 'floor_score': floor_score}


class AIService:
    def __init__(self):
        self.api_key  = os.getenv('OPENROUTER_API_KEY', '').strip()
        self.model    = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini').strip()
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').strip()
        self.enabled  = bool(self.api_key)

        # ── Custom local model ──────────────────────────────────────────────
        self.custom_model = None
        try:
            from custom_model import CustomSecurityModel
            self.custom_model = CustomSecurityModel()
            print(f"[AIService] Custom model loaded — "
                  f"trained={self.custom_model.is_trained()}, "
                  f"samples={self.custom_model.sample_count()}")
        except ImportError:
            print("[AIService] custom_model.py not found — skipping.")
        except Exception as e:
            print(f"[AIService] Custom model init error: {e}")

        # ── ModelTrainer (online learning) ──────────────────────────────────
        self.trainer = None
        if self.enabled:
            try:
                from model_trainer import ModelTrainer
                self.trainer = ModelTrainer()
                print("[AIService] ModelTrainer ready.")
            except ImportError:
                print("[AIService] model_trainer.py not found — online learning disabled.")
            except RuntimeError as e:
                # No API key etc — non-fatal
                print(f"[AIService] ModelTrainer skipped: {e}")
            except Exception as e:
                print(f"[AIService] ModelTrainer init error: {e}")

        if self.enabled:
            print(f"[AIService] OpenRouter ENABLED — model: {self.model}")
            print(f"[AIService] Base URL: {self.base_url}")
        else:
            print("[AIService] OpenRouter DISABLED — no OPENROUTER_API_KEY in .env")

    # ── Public entry points ─────────────────────────────────────────────────

    def analyze_code_security(self, code_content: str) -> Dict[str, Any]:
        """Full pipeline: patterns + custom model + OpenRouter."""
        pat         = run_pattern_detection(code_content)
        floor_score = pat['floor_score']
        detected    = pat['detected']

        custom_score  = 0.0
        custom_active = False
        if self.custom_model and self.custom_model.is_trained():
            custom_score  = self.custom_model.predict(code_content)
            custom_active = True
            print(f"[AIService] Custom model score: {custom_score:.4f}")

        if self.enabled:
            try:
                ai_result = self._call_openrouter(code_content, detected)
                ai_score  = ai_result['risk_score']

                # Online learning
                if self.trainer:
                    try:
                        self.trainer.learn_from_commit(code_content, ai_score)
                    except Exception as te:
                        print(f"[AIService] Trainer learn error: {te}")

                final_score = max(ai_score, custom_score, floor_score)
                ai_result['risk_score'] = round(final_score, 4)

                if detected:
                    pattern_vulns = [
                        f"[Pattern Match] {cat}: {', '.join(info['matches'])}"
                        for cat, info in detected.items()
                    ]
                    ai_result['vulnerabilities'] = pattern_vulns + [
                        v for v in ai_result.get('vulnerabilities', [])
                        if v not in pattern_vulns
                    ]

                ai_result['analysis_mode']      = (
                    'custom_model+openrouter_ai' if custom_active else 'openrouter_ai'
                )
                ai_result['custom_model_score'] = round(custom_score, 4)
                print(f"[AIService] Final score: {ai_result['risk_score']} "
                      f"(ai={ai_score}, custom={custom_score}, floor={floor_score})")
                return ai_result

            except requests.exceptions.HTTPError as e:
                # Log the full response body — most useful for 4xx errors
                body = ""
                try:
                    body = e.response.text[:500]
                except Exception:
                    pass
                print(f"[AIService] OpenRouter HTTP {e.response.status_code}: {body}")
                print(f"[AIService] Falling back to local analysis.")

            except requests.exceptions.ConnectionError as e:
                print(f"[AIService] OpenRouter connection error: {e}")
                print(f"[AIService] Falling back to local analysis.")

            except requests.exceptions.Timeout:
                print("[AIService] OpenRouter request timed out — falling back.")

            except Exception as e:
                print(f"[AIService] OpenRouter unexpected error: {type(e).__name__}: {e}")
                print(traceback.format_exc())
                print("[AIService] Falling back to local analysis.")

        return self.analyze_code_security_local_only(code_content)

    def analyze_code_security_local_only(self, code_content: str) -> Dict[str, Any]:
        """Local-only: custom model + pattern detection. No OpenRouter call."""
        pat         = run_pattern_detection(code_content)
        floor_score = pat['floor_score']
        detected    = pat['detected']

        custom_score  = 0.0
        custom_active = False
        if self.custom_model and self.custom_model.is_trained():
            custom_score  = self.custom_model.predict(code_content)
            custom_active = True

        final_score = max(custom_score, floor_score)

        vulns = (
            [
                f"[Pattern Match] {cat}: {', '.join(info['matches'])}"
                for cat, info in detected.items()
            ]
            if detected
            else ["No vulnerabilities detected by pattern analysis"]
        )

        if custom_active:
            reasoning = (
                f"Local custom model score: {custom_score:.2f}. "
                f"Pattern floor: {floor_score:.2f}. "
                "OpenRouter skipped (token budget conserved)."
            )
            mode = 'custom_model_only'
        else:
            reasoning = (
                f"Pattern floor score: {floor_score:.2f}. "
                "Custom model not yet trained. OpenRouter skipped (token budget conserved)."
            )
            mode = 'pattern_only'

        return {
            'risk_score':         round(final_score, 4),
            'reasoning':          reasoning,
            'vulnerabilities':    vulns,
            'analysis_mode':      mode,
            'custom_model_score': round(custom_score, 4),
        }

    def predict_risk_score(self, code_content: str) -> float:
        return self.analyze_code_security(code_content)['risk_score']

    def is_enabled(self) -> bool:
        return self.enabled

    # ── OpenRouter ──────────────────────────────────────────────────────────

    def _call_openrouter(self, code_content: str, detected: Dict) -> Dict[str, Any]:
        pattern_context = ""
        if detected:
            cats = ', '.join(detected.keys())
            pattern_context = (
                f"\n\nNote: Static analysis already detected: {cats}. "
                "Factor these into your score."
            )

        prompt = f"""You are a strict security code auditor. Analyze the following code carefully.

Code to analyze:
```python
{code_content}
```
{pattern_context}

Scoring rules:
- 0.00-0.15: Clean code, no security issues
- 0.16-0.35: Minor style issues, no real vulnerabilities
- 0.36-0.55: Low risk - weak patterns but no direct exploit path
- 0.56-0.74: Moderate risk - unvalidated input, weak auth, minor info leak
- 0.75-0.89: High risk - SQL injection, hardcoded secrets, insecure deserialization
- 0.90-1.00: Critical - RCE (eval/exec/os.system/shell=True), privilege escalation

Important:
- Variables merely NAMED "password", "token", "api_key" are NOT vulnerabilities unless hardcoded
- Parameterized SQL queries are SAFE
- Only flag real, exploitable issues

Respond EXACTLY in this format:
RISK_SCORE: [0.00-1.00]
REASONING: [one paragraph]
VULNERABILITIES:
- [issue 1]
- [write "None" if no issues]"""

        print(f"[AIService] Calling OpenRouter ({self.model}) ...")
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  os.getenv('OPENROUTER_HTTP_REFERER', 'https://scip-guardian.com'),
                "X-Title":       "SCIP Guardian",
            },
            json={
                "model":    self.model,
                "messages": [
                    {
                        "role":    "system",
                        "content": (
                            "You are a precise security auditor. Flag only real, exploitable "
                            "vulnerabilities. Never flag safe code just because it uses common "
                            "variable names like 'password', 'token', or 'api_key'."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens":  1000,
            },
            timeout=30,
        )
        resp.raise_for_status()
        print(f"[AIService] OpenRouter responded OK (status {resp.status_code})")
        content = resp.json()['choices'][0]['message']['content']
        return self._parse_ai_response(content)

    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        risk_match = re.search(r'RISK_SCORE:\s*([0-9.]+)', content, re.IGNORECASE)
        risk_score = float(risk_match.group(1)) if risk_match else 0.5
        risk_score = max(0.0, min(1.0, risk_score))

        reason_match = re.search(
            r'REASONING:\s*(.+?)(?=VULNERABILITIES:|$)', content, re.IGNORECASE | re.DOTALL
        )
        reasoning = reason_match.group(1).strip() if reason_match else "Analysis completed."

        vuln_match = re.search(r'VULNERABILITIES:\s*(.+?)$', content, re.IGNORECASE | re.DOTALL)
        vuln_text  = vuln_match.group(1).strip() if vuln_match else "None"
        vulns = [
            v.strip().lstrip('-').strip()
            for v in vuln_text.split('\n')
            if v.strip() and v.strip() not in ['-', 'None', 'none'] and len(v.strip()) > 2
        ]

        return {
            'risk_score':      round(risk_score, 4),
            'reasoning':       reasoning,
            'vulnerabilities': vulns or ["No vulnerabilities identified"],
        }