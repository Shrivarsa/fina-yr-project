"""
custom_model.py — SCIP Guardian Custom Security Risk Model

A local ML model trained on OpenRouter-labeled examples.
Uses TF-IDF + Gradient Boosting to predict risk scores from code content.

Training data is collected by querying OpenRouter with diverse code samples,
then storing the labeled results to build a local dataset.

Usage:
    from custom_model import CustomSecurityModel
    model = CustomSecurityModel()
    score = model.predict(code_content)  # returns float 0.0–1.0
"""

import os
import re
import json
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import cross_val_score

# ── paths ───────────────────────────────────────────────────────────────────
MODEL_DIR  = Path(os.getenv("SCIP_MODEL_DIR", "models"))
MODEL_PATH = MODEL_DIR / "security_model.pkl"
DATA_PATH  = MODEL_DIR / "training_data.jsonl"
STATS_PATH = MODEL_DIR / "model_stats.json"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── hand-crafted pattern features ───────────────────────────────────────────

CRITICAL_PATTERNS = [
    (r'os\.system\s*\(',                                         "rce_os_system",         0.95),
    (r'subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True',    "rce_subprocess_shell",  0.95),
    (r'\beval\s*\(',                                             "rce_eval",              0.95),
    (r'\bexec\s*\(',                                             "rce_exec",              0.90),
    (r'compile\s*\(.*exec\)',                                    "dynamic_compile",       0.90),
    (r'__import__\s*\(',                                         "dynamic_import",        0.70),
    (r'pickle\.loads\s*\(',                                      "deser_pickle",          0.75),
    (r'marshal\.loads\s*\(',                                     "deser_marshal",         0.75),
    (r'os\.setuid\s*\(\s*0\s*\)',                                "priv_setuid",           0.90),
    (r'chmod\s+777',                                             "chmod777",              0.85),
    (r'\/etc\/shadow',                                           "shadow_access",         0.85),
    (r'execute\s*\(\s*["\']?\s*(SELECT|INSERT|UPDATE|DELETE).*\+', "sqli_concat",         0.85),
    (r'f["\'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*\{',           "sqli_fstring",         0.85),
    (r'(DB_PASSWORD|DATABASE_PASSWORD)\s*=\s*["\'][^"\']{4,}["\']', "hc_dbpass",         0.80),
    (r'(SECRET_KEY|APP_SECRET)\s*=\s*["\'][^"\']{4,}["\']',     "hc_secret",            0.80),
    (r'ghp_[a-zA-Z0-9]{36}',                                    "hc_github_token",       0.80),
    (r'sk-[a-zA-Z0-9]{32,}',                                    "hc_openai_key",         0.80),
    (r'AKIA[0-9A-Z]{16}',                                       "hc_aws_key",            0.80),
    (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',                  "hc_private_key",        0.80),
    (r'rm\s+-rf\s+\/',                                           "rm_rf",                0.80),
    (r'shutil\.rmtree\s*\(',                                     "rmtree",               0.75),
    (r'requests\.(get|post)\s*\(.*verify\s*=\s*False',           "ssl_no_verify",        0.55),
    (r'DEBUG\s*=\s*True',                                        "debug_mode",           0.30),
    (r'password\s*=\s*["\'][^"\']{3,}["\']',                    "plaintext_password",    0.60),
    (r'base64\.b64decode\s*\(.*\)',                              "b64_decode",           0.45),
]


def extract_numeric_features(code: str) -> np.ndarray:
    """Extract hand-crafted numeric features from code."""
    max_severity = 0.0
    hit_count = 0
    for pattern, name, severity in CRITICAL_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
            hit_count += 1
            max_severity = max(max_severity, severity)

    lines = code.splitlines()
    comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
    imports = re.findall(r'^(?:import|from)\s+(\w+)', code, re.MULTILINE)
    risky_imports = {'os', 'subprocess', 'pickle', 'marshal', 'ctypes', 'socket'}
    risky_count = sum(1 for i in imports if i in risky_imports)
    long_strings = re.findall(r'["\'][A-Za-z0-9+/=]{40,}["\']', code)
    net_calls = len(re.findall(r'requests\.(get|post|put|delete)|urllib|socket\.', code, re.I))

    return np.array([
        max_severity,
        min(hit_count / 5.0, 1.0),
        min(len(lines) / 500.0, 1.0),
        min(len(code) / 10000.0, 1.0),
        comment_lines / max(len(lines), 1),
        min(risky_count / 3.0, 1.0),
        min(len(long_strings) / 3.0, 1.0),
        min(net_calls / 5.0, 1.0),
    ], dtype=np.float32)


def code_to_text_tokens(code: str) -> str:
    """Normalise code to token string for TF-IDF."""
    code = re.sub(r'"[^"]*"', ' STRING_LITERAL ', code)
    code = re.sub(r"'[^']*'", ' STRING_LITERAL ', code)
    code = re.sub(r'\b\d+\b', ' NUMBER ', code)
    code = re.sub(r'([a-z])([A-Z])', r'\1 \2', code)
    code = code.replace('_', ' ')
    return code.lower()


class CustomSecurityModel:
    """
    Local ML security risk model.

    Architecture:
        TF-IDF(code tokens)  ─┐
                               ├─► GradientBoostingRegressor → risk score ∈ [0,1]
        Numeric features ──────┘

    Workflow:
        1. ModelTrainer queries OpenRouter with diverse code snippets
        2. Each (code, risk_score) pair is saved to training_data.jsonl
        3. Once MIN_TRAIN_SAMPLES are collected, call model.train()
        4. SCIP Orchestrator then routes all analysis through this model
        5. OpenRouter is still used as the "teacher" to keep improving it
    """

    MIN_TRAIN_SAMPLES = 20
    VERSION = "1.0.0"

    def __init__(self):
        self.tfidf_pipeline: Optional[Pipeline] = None
        self.regressor: Optional[GradientBoostingRegressor] = None
        self.scaler: Optional[MinMaxScaler] = None
        self._loaded = False
        self._stats: Dict = {}
        self._load()

    # ── public API ──────────────────────────────────────────────────────────

    def predict(self, code: str) -> float:
        """Return a risk score in [0, 1]."""
        if not self._loaded:
            return self._heuristic_predict(code)

        try:
            import scipy.sparse as sp
            tfidf_feat = self.tfidf_pipeline.transform([code_to_text_tokens(code)])
            num_feat   = extract_numeric_features(code).reshape(1, -1)
            num_scaled = self.scaler.transform(num_feat)
            combined   = sp.hstack([tfidf_feat, sp.csr_matrix(num_scaled)])

            raw_score     = float(self.regressor.predict(combined)[0])
            pattern_floor = float(extract_numeric_features(code)[0])   # worst pattern severity
            score = max(raw_score, pattern_floor)
            return round(min(max(score, 0.0), 1.0), 4)

        except Exception as e:
            print(f"[CustomModel] Prediction error: {e} — heuristic fallback")
            return self._heuristic_predict(code)

    def is_trained(self) -> bool:
        return self._loaded

    def sample_count(self) -> int:
        return self._stats.get("sample_count", 0)

    def add_training_example(self, code: str, risk_score: float,
                              source: str = "openrouter") -> bool:
        """
        Save a labeled example. Returns True if it was new (not a duplicate).
        Call model.train() after collecting enough samples.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        existing = set()
        if DATA_PATH.exists():
            with open(DATA_PATH) as f:
                for line in f:
                    try:
                        existing.add(json.loads(line).get("hash", ""))
                    except Exception:
                        pass

        if code_hash in existing:
            return False

        with open(DATA_PATH, "a") as f:
            f.write(json.dumps({
                "hash":       code_hash,
                "code":       code,
                "risk_score": round(float(risk_score), 4),
                "source":     source,
            }) + "\n")
        return True

    def train(self, force: bool = False) -> Dict[str, Any]:
        """Train/retrain on all stored examples."""
        import scipy.sparse as sp
        examples = self._load_training_data()
        n = len(examples)

        if n < self.MIN_TRAIN_SAMPLES and not force:
            return {
                "status":       "skipped",
                "reason":       f"Only {n} samples — need at least {self.MIN_TRAIN_SAMPLES}",
                "sample_count": n,
            }

        print(f"[CustomModel] Training on {n} samples …")
        codes  = [ex["code"] for ex in examples]
        labels = np.array([ex["risk_score"] for ex in examples], dtype=np.float32)

        # TF-IDF
        tokens = [code_to_text_tokens(c) for c in codes]
        self.tfidf_pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=8000,
                sublinear_tf=True,
                min_df=1,
            ))
        ])
        tfidf_feat = self.tfidf_pipeline.fit_transform(tokens)

        # Numeric
        num_feat   = np.vstack([extract_numeric_features(c) for c in codes])
        self.scaler = MinMaxScaler()
        num_scaled = self.scaler.fit_transform(num_feat)

        X = sp.hstack([tfidf_feat, sp.csr_matrix(num_scaled)])

        # Regressor
        self.regressor = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.85,
            min_samples_leaf=2,
            random_state=42,
        )
        self.regressor.fit(X, labels)

        cv_k = min(5, max(2, n // 4))
        cv   = cross_val_score(self.regressor, X, labels, cv=cv_k,
                               scoring="neg_mean_absolute_error")
        mae  = float(-cv.mean())

        import datetime
        self._stats = {
            "sample_count": n,
            "mae":          round(mae, 4),
            "trained_at":   datetime.datetime.utcnow().isoformat(),
            "version":      self.VERSION,
        }
        self._save()
        self._loaded = True
        print(f"[CustomModel] Done — MAE: {mae:.4f}")
        return {"status": "trained", **self._stats}

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "loaded": self._loaded, "version": self.VERSION}

    # ── internal ────────────────────────────────────────────────────────────

    def _heuristic_predict(self, code: str) -> float:
        feats = extract_numeric_features(code)
        score = feats[0] * 0.7 + feats[1] * 0.3
        return round(float(min(max(score, 0.0), 1.0)), 4)

    def _save(self):
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({
                "tfidf_pipeline": self.tfidf_pipeline,
                "regressor":      self.regressor,
                "scaler":         self.scaler,
                "stats":          self._stats,
                "version":        self.VERSION,
            }, f)
        with open(STATS_PATH, "w") as f:
            json.dump(self._stats, f, indent=2)
        print(f"[CustomModel] Saved → {MODEL_PATH}")

    def _load(self):
        if not MODEL_PATH.exists():
            print("[CustomModel] No saved model — using heuristics until trained.")
            return
        try:
            with open(MODEL_PATH, "rb") as f:
                d = pickle.load(f)
            self.tfidf_pipeline = d["tfidf_pipeline"]
            self.regressor      = d["regressor"]
            self.scaler         = d["scaler"]
            self._stats         = d.get("stats", {})
            self._loaded        = True
            print(f"[CustomModel] Loaded — {self._stats.get('sample_count','?')} samples, "
                  f"MAE: {self._stats.get('mae','?')}")
        except Exception as e:
            print(f"[CustomModel] Load failed: {e}")

    def _load_training_data(self) -> List[Dict]:
        if not DATA_PATH.exists():
            return []
        data = []
        with open(DATA_PATH) as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except Exception:
                    pass
        return data