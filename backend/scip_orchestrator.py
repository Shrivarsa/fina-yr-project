from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import hashlib
import os
import sys
import random
from datetime import datetime
from typing import Tuple
from dotenv import load_dotenv
from supabase import create_client, Client

# Import services
from ai_service import AIService
from s3_service import S3Service

# Import model routes (optional — only if model_routes.py exists in backend/)
try:
    from model_routes import register_model_routes
    _model_routes_available = True
except ImportError:
    _model_routes_available = False
    print("[Orchestrator] model_routes.py not found — /api/model/* endpoints disabled.")

# Import blockchain bridge (from parent blockchain folder)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'blockchain'))
from web3_bridge import DLTBridge

load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Supabase configuration ───────────────────────────────────────────────────
SUPABASE_URL         = os.getenv('VITE_SUPABASE_URL') or os.getenv('SUPABASE_URL')
SUPABASE_KEY         = os.getenv('VITE_SUPABASE_ANON_KEY') or os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

RISK_THRESHOLD = 0.75

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and key must be set via environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_KEY)

# ── Custom model token budget ────────────────────────────────────────────────
# Controls how often OpenRouter is called vs. the local custom model.
#
# CUSTOM_MODEL_CONFIDENCE_THRESHOLD (float 0.0–1.0, default 0.85)
#   If the custom model's confidence is >= this value, skip OpenRouter entirely.
#   Lower = trust custom model more often → fewer OpenRouter calls.
#   Higher = send more commits to OpenRouter for validation → more accurate but costs tokens.
#
# OPENROUTER_CALL_BUDGET (int, default 200)
#   Hard cap on OpenRouter API calls per server session.
#   Once reached, all analysis falls back to custom model + pattern detection.
#   Reset by restarting the server. Set to 0 to disable OpenRouter entirely.
#
# OPENROUTER_SAMPLING_RATE (float 0.0–1.0, default 0.2)
#   Even when the custom model is confident, send this fraction of commits to
#   OpenRouter anyway so the model keeps learning from live data.
#   0.2 = 1 in every 5 confident commits still goes to OpenRouter.
#   Set to 0.0 to stop all background sampling once model is confident.

CUSTOM_MODEL_CONFIDENCE_THRESHOLD = float(os.getenv('CUSTOM_MODEL_CONFIDENCE_THRESHOLD', '0.85'))
OPENROUTER_CALL_BUDGET            = int(os.getenv('OPENROUTER_CALL_BUDGET', '200'))
OPENROUTER_SAMPLING_RATE          = float(os.getenv('OPENROUTER_SAMPLING_RATE', '0.2'))

# Session-level counter (resets on restart; use Redis/DB for persistence)
_openrouter_calls_this_session = 0


def _should_call_openrouter(custom_score: float, custom_trained: bool) -> Tuple[bool, str]:
    """
    Decide whether to call OpenRouter for this commit.

    Returns (should_call: bool, reason: str)

    Decision logic:
      1. If OpenRouter budget is exhausted → skip
      2. If custom model is not yet trained → always call (we need training data)
      3. If custom model score is in the ambiguous middle band (0.35–0.70) → call
         (these are the hardest cases; AI judgment adds most value here)
      4. If custom model is confident (score < 0.35 or > 0.70) AND
         random sampling rate check passes → call for background learning
      5. Otherwise → skip, trust the custom model
    """
    global _openrouter_calls_this_session

    # 1. Hard budget cap
    if OPENROUTER_CALL_BUDGET > 0 and _openrouter_calls_this_session >= OPENROUTER_CALL_BUDGET:
        return False, f"budget_exhausted ({_openrouter_calls_this_session}/{OPENROUTER_CALL_BUDGET})"

    # 2. Model not trained yet — always call to build training data
    if not custom_trained:
        return True, "model_not_trained"

    # 3. Ambiguous middle band — AI adds most value here
    if 0.35 <= custom_score <= 0.70:
        return True, "ambiguous_score_band"

    # 4. Confident score — only sample a fraction for background learning
    if random.random() < OPENROUTER_SAMPLING_RATE:
        return True, "background_learning_sample"

    # 5. Trust the custom model
    return False, "custom_model_confident"


# ── Initialize services ──────────────────────────────────────────────────────
ai_service  = AIService()
s3_service  = S3Service()
dlt_bridge  = DLTBridge()

# Register model management routes (/api/model/stats, /api/model/train, /api/model/seed)
if _model_routes_available:
    register_model_routes(app, supabase)


# ── Auth routes ──────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user via Supabase Auth."""
    try:
        data     = request.json
        email    = data.get('email', '').strip()
        password = data.get('password', '')
        username = data.get('username', '').strip()

        if not email or not password or not username:
            return jsonify({'error': 'Email, password, and username are required'}), 400

        auth_response = supabase.auth.sign_up({'email': email, 'password': password})
        user_id = auth_response.user.id if auth_response.user else None

        if not user_id:
            return jsonify({'error': 'Failed to create user'}), 500

        try:
            supabase.table('users').insert({
                'id':       user_id,
                'email':    email,
                'username': username,
            }).execute()
        except Exception as e:
            return jsonify({'error': f'Failed to create user profile: {str(e)}'}), 500

        return jsonify({
            'user_id':  user_id,
            'email':    email,
            'username': username,
            'message':  'Registration successful',
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Login user via Supabase Auth."""
    try:
        data     = request.json
        email    = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        try:
            auth_response = supabase.auth.sign_in_with_password({
                'email':    email,
                'password': password,
            })
        except Exception as auth_error:
            return jsonify({'error': str(auth_error) or 'Invalid credentials'}), 401

        user    = auth_response.user
        session = auth_response.session

        user_profile_response = (
            supabase.table('users').select('*').eq('id', user.id).limit(1).execute()
        )
        user_profile = user_profile_response.data[0] if user_profile_response.data else None

        return jsonify({
            'user_id':       user.id,
            'email':         user.email,
            'username':      user_profile['username'] if user_profile else email,
            'access_token':  session.access_token,
            'refresh_token': session.refresh_token,
            'message':       'Login successful',
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 401


# ── Core analysis route ──────────────────────────────────────────────────────

@app.route('/api/analyze_commit', methods=['POST'])
def analyze_commit():
    """
    Analyze code commit for security risks.

    Token-saving flow:
      1. Run pattern detection (free, instant)
      2. Run custom local model (free, instant)
      3. Decide whether to call OpenRouter based on budget + confidence
      4. Merge all scores → take the highest
    """
    global _openrouter_calls_this_session

    try:
        # ── Authenticate ────────────────────────────────────────────────────
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id if user_response.user else None

        if not user_id:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        # ── Get code ─────────────────────────────────────────────────────────
        data         = request.json
        code_content = data.get('code_content', '')

        if not code_content.strip():
            return jsonify({'error': 'Code content is required'}), 400

        commit_hash = hashlib.sha256(code_content.encode()).hexdigest()[:16]

        # ── Step 1: Custom model pre-check (free) ────────────────────────────
        custom_score   = 0.0
        custom_trained = False

        try:
            from custom_model import CustomSecurityModel
            cm = CustomSecurityModel()
            custom_trained = cm.is_trained()
            if custom_trained:
                custom_score = cm.predict(code_content)
        except Exception as cm_err:
            print(f"[Orchestrator] Custom model error: {cm_err}")

        # ── Step 2: Decide whether to call OpenRouter ────────────────────────
        use_openrouter, openrouter_reason = _should_call_openrouter(
            custom_score, custom_trained
        )

        print(
            f"[Orchestrator] commit={commit_hash} "
            f"custom_score={custom_score:.2f} trained={custom_trained} "
            f"use_openrouter={use_openrouter} reason={openrouter_reason} "
            f"budget_used={_openrouter_calls_this_session}/{OPENROUTER_CALL_BUDGET}"
        )

        # ── Step 3: Run analysis ─────────────────────────────────────────────
        if use_openrouter:
            # Full AI analysis (OpenRouter + patterns + custom model floor)
            analysis = ai_service.analyze_code_security(code_content)
            _openrouter_calls_this_session += 1
            analysis['openrouter_called'] = True
            analysis['openrouter_reason'] = openrouter_reason
        else:
            # Custom model + pattern detection only (no OpenRouter call)
            # Falls back to analyze_code_security() if local_only method doesn't exist
            if hasattr(ai_service, 'analyze_code_security_local_only'):
                analysis = ai_service.analyze_code_security_local_only(code_content)
            else:
                analysis = ai_service.analyze_code_security(code_content)
            analysis['openrouter_called'] = False
            analysis['openrouter_reason'] = openrouter_reason

        risk_score      = analysis['risk_score']
        risk_percentage = risk_score * 100
        status          = 'Accepted' if risk_score < RISK_THRESHOLD else 'Rollback Enforced'

        # ── Step 4: Log to blockchain ────────────────────────────────────────
        dlt_tx_hash = dlt_bridge.log_commit_data(commit_hash, risk_percentage, status)

        # ── Step 5: Upload to S3 (optional) ──────────────────────────────────
        s3_code_key = None
        if s3_service.is_enabled():
            s3_code_key = s3_service.upload_code_content(commit_hash, code_content, user_id)
            analysis_data = {
                'commit_hash':  commit_hash,
                'risk_score':   risk_percentage,
                'status':       status,
                'reasoning':    analysis.get('reasoning', ''),
                'vulnerabilities': analysis.get('vulnerabilities', []),
                'dlt_tx_hash':  dlt_tx_hash,
                'timestamp':    datetime.now().isoformat(),
            }
            s3_service.upload_analysis_result(commit_hash, analysis_data, user_id)

        # ── Step 6: Save to Supabase ─────────────────────────────────────────
        try:
            commit_response = supabase.table('commits').insert({
                'user_id':      user_id,
                'commit_hash':  commit_hash,
                'risk_score':   risk_percentage,
                'status':       status,
                'code_content': code_content,
                'dlt_tx_hash':  dlt_tx_hash,
            }).execute()

            commit_data = commit_response.data[0] if commit_response.data else {}

        except Exception as db_error:
            error_str = str(db_error)
            if '23505' in error_str:
                print(f"[Orchestrator] Duplicate commit {commit_hash} — returning existing record.")
                try:
                    existing = (
                        supabase.table('commits')
                        .select('*')
                        .eq('commit_hash', commit_hash)
                        .limit(1)
                        .execute()
                    )
                    commit_data = existing.data[0] if existing.data else {}
                except Exception as fe:
                    print(f"[Orchestrator] Could not fetch existing commit: {fe}")
                    commit_data = {}
            else:
                return jsonify({'error': f'Failed to save commit: {error_str}'}), 500

        # ── Step 7: Build response ────────────────────────────────────────────
        response_data = {
            'commit_id':        commit_data.get('id'),
            'commit_hash':      commit_hash,
            'risk_score':       risk_percentage,
            'status':           status,
            'timestamp':        commit_data.get('created_at', datetime.now().isoformat()),
            'dlt_tx_hash':      dlt_tx_hash,
            'reasoning':        analysis.get('reasoning', ''),
            'vulnerabilities':  analysis.get('vulnerabilities', []),
            'analysis_mode':    analysis.get('analysis_mode', 'unknown'),
            'openrouter_called': analysis.get('openrouter_called', False),
            'openrouter_reason': analysis.get('openrouter_reason', ''),
            'custom_model_score': round(custom_score * 100, 2),
            'token_budget': {
                'used':      _openrouter_calls_this_session,
                'limit':     OPENROUTER_CALL_BUDGET,
                'remaining': max(0, OPENROUTER_CALL_BUDGET - _openrouter_calls_this_session),
            },
            'duplicate': commit_data.get('id') is None,
        }

        if s3_code_key:
            response_data['s3_code_key'] = s3_code_key

        return jsonify(response_data), 200

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[Orchestrator] analyze_commit ERROR:\n{tb}")
        return jsonify({'error': str(e), 'detail': tb}), 500


# ── Logs & commit detail routes ──────────────────────────────────────────────

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get commit logs for authenticated user."""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id if user_response.user else None

        if not user_id:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        commits_response = (
            supabase.table('commits')
            .select('*, users(username, email)')
            .eq('user_id', user_id)
            .order('created_at', desc=True)
            .limit(50)
            .execute()
        )
        commits = commits_response.data or []

        logs = [
            {
                'commit_id':   c.get('id'),
                'commit_hash': c.get('commit_hash'),
                'risk_score':  c.get('risk_score'),
                'user':        (c.get('users') or {}).get('username', 'unknown'),
                'timestamp':   c.get('created_at'),
                'status':      c.get('status'),
                'dlt_tx_hash': c.get('dlt_tx_hash'),
            }
            for c in commits
        ]

        return jsonify({'logs': logs}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/commits/<commit_id>', methods=['GET'])
def get_commit(commit_id: str):
    """Get full commit details for the authenticated user."""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id if user_response.user else None

        if not user_id:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        commit_response = (
            supabase.table('commits')
            .select('id, user_id, commit_hash, risk_score, status, code_content, dlt_tx_hash, created_at')
            .eq('id', commit_id)
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        commit = commit_response.data[0] if commit_response.data else None
        if not commit:
            return jsonify({'error': 'Commit not found'}), 404

        code_content = commit.get('code_content')
        if not code_content and s3_service.is_enabled():
            code_from_s3 = s3_service.get_code_content(commit['commit_hash'], user_id)
            if code_from_s3 is not None:
                code_content = code_from_s3

        return jsonify({
            'commit_id':   commit['id'],
            'commit_hash': commit['commit_hash'],
            'risk_score':  commit['risk_score'],
            'status':      commit['status'],
            'code_content': code_content or '',
            'dlt_tx_hash': commit.get('dlt_tx_hash'),
            'timestamp':   commit.get('created_at'),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/commits/<commit_id>/download', methods=['GET'])
def download_commit(commit_id: str):
    """Download the code content for a specific commit as a text file."""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id if user_response.user else None

        if not user_id:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        commit_response = (
            supabase.table('commits')
            .select('id, user_id, commit_hash, code_content')
            .eq('id', commit_id)
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        commit = commit_response.data[0] if commit_response.data else None
        if not commit:
            return jsonify({'error': 'Commit not found'}), 404

        code_content = commit.get('code_content')
        if not code_content and s3_service.is_enabled():
            code_from_s3 = s3_service.get_code_content(commit['commit_hash'], user_id)
            if code_from_s3 is not None:
                code_content = code_from_s3

        if not code_content:
            return jsonify({'error': 'Code content not available for this commit'}), 404

        filename = f"commit_{commit['commit_hash']}.txt"
        response = make_response(code_content)
        response.headers.set('Content-Type', 'text/plain; charset=utf-8')
        response.headers.set('Content-Disposition', f'attachment; filename={filename}')
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Health & token budget endpoints ─────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    custom_model_info = {}
    try:
        from custom_model import CustomSecurityModel
        cm = CustomSecurityModel()
        custom_model_info = cm.get_stats()
    except Exception:
        custom_model_info = {'loaded': False}

    return jsonify({
        'status':  'healthy',
        'service': 'SCIP Guardian Backend',
        'services': {
            'ai_service':   'enabled' if ai_service.is_enabled() else 'mock',
            's3_service':   'enabled' if s3_service.is_enabled() else 'disabled',
            'blockchain':   dlt_bridge.get_mode(),
            'custom_model': custom_model_info,
        },
        'token_budget': {
            'used':              _openrouter_calls_this_session,
            'limit':             OPENROUTER_CALL_BUDGET,
            'remaining':         max(0, OPENROUTER_CALL_BUDGET - _openrouter_calls_this_session),
            'confidence_threshold': CUSTOM_MODEL_CONFIDENCE_THRESHOLD,
            'sampling_rate':     OPENROUTER_SAMPLING_RATE,
        },
    }), 200


@app.route('/api/token_budget', methods=['GET'])
def token_budget():
    """Return current OpenRouter token budget usage for this session."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth_header.split(' ')[1]
    user_response = supabase.auth.get_user(token)
    if not (user_response.user):
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'used':                  _openrouter_calls_this_session,
        'limit':                 OPENROUTER_CALL_BUDGET,
        'remaining':             max(0, OPENROUTER_CALL_BUDGET - _openrouter_calls_this_session),
        'confidence_threshold':  CUSTOM_MODEL_CONFIDENCE_THRESHOLD,
        'sampling_rate':         OPENROUTER_SAMPLING_RATE,
    }), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)