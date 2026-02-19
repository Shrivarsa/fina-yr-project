import os
import re
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# PATTERN DETECTION — sets a FLOOR score only
# OpenRouter AI still analyzes everything
# Patterns prevent AI from scoring critical issues too low
# ============================================================
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
        ]
    },
    {
        'category': 'Privilege Escalation',
        'severity': 0.90,
        'patterns': [
            r'os\.setuid\s*\(\s*0\s*\)',
            r'chmod\s+777',
            r'\/etc\/shadow',
            r'\/etc\/passwd',
        ]
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
        ]
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
        ]
    },
    {
        'category': 'Dangerous File Operations',
        'severity': 0.80,
        'patterns': [
            r'rm\s+-rf\s+\/',
            r'shutil\.rmtree\s*\(',
        ]
    },
    {
        'category': 'Insecure Deserialization',
        'severity': 0.75,
        'patterns': [
            r'pickle\.loads\s*\(',
            r'marshal\.loads\s*\(',
        ]
    },
]

# Soft patterns — these are WARNING level only, should NOT force high scores
# These are common in legitimate code so AI should make the final call
SOFT_PATTERNS = [
    r'\bpassword\b',      # variable named password is fine
    r'\bsecret\b',        # secret config key is fine
    r'\btoken\b',         # token variable is fine
    r'\bapi_key\b',       # api_key variable is fine
    r'\bquery\b',         # SQL query variable is fine
]


def run_pattern_detection(code_content: str) -> Dict[str, Any]:
    """
    Run pattern detection to establish a risk floor.
    Only definitive critical patterns set the floor — not soft indicators.
    """
    detected = {}
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
                'matches': matched[:3],  # cap at 3 examples
            }
            floor_score = max(floor_score, rule['severity'])

    return {
        'detected': detected,
        'floor_score': floor_score,
    }


class AIService:
    """
    Security analysis service using OpenRouter AI as primary analyzer.
    Pattern detection sets a minimum floor — AI does the real analysis.
    If no API key is set, falls back to pattern-only scoring.
    """

    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.enabled = bool(self.api_key)

        if self.enabled:
            print(f"[AIService] OpenRouter enabled — model: {self.model}")
        else:
            print("[AIService] No OPENROUTER_API_KEY found — using pattern detection only.")

    def analyze_code_security(self, code_content: str) -> Dict[str, Any]:
        """
        Primary analysis flow:
        1. Run pattern detection to get floor score + detected issues
        2. Always send to OpenRouter for full AI analysis (if key set)
        3. Take the HIGHER of AI score vs pattern floor — never lower
        4. Fall back to pattern-only scoring if no API key
        """
        # Step 1: Pattern detection (floor only)
        pattern_result = run_pattern_detection(code_content)
        floor_score = pattern_result['floor_score']
        detected = pattern_result['detected']

        # Step 2: AI analysis (primary scorer)
        if self.enabled:
            try:
                ai_result = self._call_openrouter(code_content, detected)

                # Step 3: Enforce floor — AI cannot score BELOW what patterns found
                final_score = max(ai_result['risk_score'], floor_score)
                ai_result['risk_score'] = round(final_score, 4)

                # Merge pattern findings into vulnerabilities list
                if detected:
                    pattern_vulns = [
                        f"[Pattern Match] {cat}: {', '.join(info['matches'])}"
                        for cat, info in detected.items()
                    ]
                    # Prepend pattern findings, keep AI findings after
                    ai_result['vulnerabilities'] = pattern_vulns + [
                        v for v in ai_result.get('vulnerabilities', [])
                        if v not in pattern_vulns
                    ]

                ai_result['analysis_mode'] = 'openrouter_ai'
                return ai_result

            except Exception as e:
                print(f"[AIService] OpenRouter call failed: {e}. Falling back to pattern scoring.")

        # Step 4: Pattern-only fallback (no API key or API failure)
        return self._pattern_only_result(code_content, floor_score, detected)

    def predict_risk_score(self, code_content: str) -> float:
        return self.analyze_code_security(code_content)['risk_score']

    def _call_openrouter(self, code_content: str, detected: Dict) -> Dict[str, Any]:
        """Call OpenRouter API for AI-powered analysis."""

        # Tell the AI what patterns were already found
        pattern_context = ""
        if detected:
            found_cats = ', '.join(detected.keys())
            pattern_context = (
                f"\n\nNote: The following vulnerability categories were already detected "
                f"by static analysis: {found_cats}. Factor these into your score."
            )

        prompt = f"""You are a strict security code auditor. Analyze the following code carefully.

Code to analyze:
```python
{code_content}
```
{pattern_context}

Scoring rules — be precise:
- 0.00–0.15: Clean code, no security issues
- 0.16–0.35: Minor style issues, no real vulnerabilities
- 0.36–0.55: Low risk — weak patterns but no direct exploit path
- 0.56–0.74: Moderate risk — unvalidated input, weak auth, minor info leak
- 0.75–0.89: High risk — SQL injection, hardcoded secrets, insecure deserialization
- 0.90–1.00: Critical — RCE (eval/exec/os.system/shell=True), privilege escalation

Important:
- Variables merely NAMED "password", "token", "api_key", or "secret" are NOT vulnerabilities unless they contain actual hardcoded values
- Parameterized SQL queries are SAFE — do not flag them
- Only flag real, exploitable issues

Respond EXACTLY in this format:
RISK_SCORE: [0.00-1.00]
REASONING: [one paragraph explanation]
VULNERABILITIES:
- [issue 1]
- [issue 2]
- [write "None" if no issues found]"""

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv('OPENROUTER_HTTP_REFERER', 'https://scip-guardian.com'),
                "X-Title": "SCIP Guardian"
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise security auditor. You flag only real, "
                            "exploitable vulnerabilities. You never flag safe code as "
                            "malicious just because it uses common variable names like "
                            "'password', 'token', or 'api_key'. You score accurately."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=30
        )

        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return self._parse_ai_response(content)

    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """Parse structured AI response."""
        risk_match = re.search(r'RISK_SCORE:\s*([0-9.]+)', content, re.IGNORECASE)
        risk_score = float(risk_match.group(1)) if risk_match else 0.5
        risk_score = max(0.0, min(1.0, risk_score))

        reasoning_match = re.search(
            r'REASONING:\s*(.+?)(?=VULNERABILITIES:|$)', content, re.IGNORECASE | re.DOTALL
        )
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Analysis completed"

        vuln_match = re.search(r'VULNERABILITIES:\s*(.+?)$', content, re.IGNORECASE | re.DOTALL)
        vulnerabilities_text = vuln_match.group(1).strip() if vuln_match else "None"
        vulnerabilities = [
            v.strip().lstrip('-').strip()
            for v in vulnerabilities_text.split('\n')
            if v.strip() and v.strip() not in ['-', 'None', 'none']
            and len(v.strip()) > 2
        ]

        return {
            'risk_score': round(risk_score, 4),
            'reasoning': reasoning,
            'vulnerabilities': vulnerabilities or ["No vulnerabilities identified"],
        }

    def _pattern_only_result(self, code_content: str, floor_score: float, detected: Dict) -> Dict[str, Any]:
        """Fallback result when OpenRouter is unavailable."""
        if not detected:
            return {
                'risk_score': 0.05,
                'reasoning': "No critical patterns detected. Set OPENROUTER_API_KEY for full AI analysis.",
                'vulnerabilities': ["No vulnerabilities detected"],
                'analysis_mode': 'pattern_only',
            }

        vuln_list = [
            f"[CRITICAL] {cat}: {', '.join(info['matches'])}"
            for cat, info in detected.items()
        ]

        categories = ', '.join(detected.keys())
        return {
            'risk_score': round(floor_score, 4),
            'reasoning': (
                f"Pattern detection found critical issues in: {categories}. "
                f"Add OPENROUTER_API_KEY to backend/.env for full AI analysis."
            ),
            'vulnerabilities': vuln_list,
            'analysis_mode': 'pattern_only',
        }

    def is_enabled(self) -> bool:
        return self.enabled