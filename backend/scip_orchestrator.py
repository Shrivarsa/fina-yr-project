from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Import services
from ai_service import AIService
from s3_service import S3Service

# Import blockchain bridge (from parent blockchain folder)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'blockchain'))
from web3_bridge import DLTBridge

load_dotenv()

app = Flask(__name__)
CORS(app)

# Supabase configuration
SUPABASE_URL = os.getenv('VITE_SUPABASE_URL') or os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('VITE_SUPABASE_ANON_KEY') or os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

RISK_THRESHOLD = 0.75

# Initialize Supabase client
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and key must be set via environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_KEY)

# Initialize services
ai_service = AIService()
s3_service = S3Service()
dlt_bridge = DLTBridge()

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user via Supabase Auth."""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        username = data.get('username', '').strip()

        if not email or not password or not username:
            return jsonify({'error': 'Email, password, and username are required'}), 400

        auth_response = supabase.auth.sign_up({
            'email': email,
            'password': password,
        })

        user_id = auth_response.user.id if auth_response.user else None

        if not user_id:
            return jsonify({'error': 'Failed to create user'}), 500

        try:
            supabase.table('users').insert({
                'id': user_id,
                'email': email,
                'username': username,
            }).execute()
        except Exception as e:
            return jsonify({'error': f'Failed to create user profile: {str(e)}'}), 500

        return jsonify({
            'user_id': user_id,
            'email': email,
            'username': username,
            'message': 'Registration successful'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user via Supabase Auth."""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        auth_response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password,
        })

        user = auth_response.user
        session = auth_response.session

        user_profile = supabase.table('users').select('*').eq('id', user.id).maybeSingle().execute()

        return jsonify({
            'user_id': user.id,
            'email': user.email,
            'username': user_profile.data['username'] if user_profile.data else email,
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'message': 'Login successful'
        }), 200

    except Exception as e:
        return jsonify({'error': 'Invalid credentials or user not found'}), 401

@app.route('/api/analyze_commit', methods=['POST'])
def analyze_commit():
    """Analyze code commit for security risks."""
    try:
        # Authenticate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]

        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id if user_response.user else None

        if not user_id:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        # Get code content
        data = request.json
        code_content = data.get('code_content', '')

        if not code_content.strip():
            return jsonify({'error': 'Code content is required'}), 400

        # Generate commit hash
        commit_hash = hashlib.sha256(code_content.encode()).hexdigest()[:16]

        # Analyze code using AI service
        analysis = ai_service.analyze_code_security(code_content)
        risk_score = analysis['risk_score']
        risk_percentage = risk_score * 100

        status = 'Accepted' if risk_score < RISK_THRESHOLD else 'Rollback Enforced'

        # Log to blockchain
        dlt_tx_hash = dlt_bridge.log_commit_data(commit_hash, risk_percentage, status)

        # Upload code content to S3 (if enabled)
        s3_code_key = None
        if s3_service.is_enabled():
            s3_code_key = s3_service.upload_code_content(commit_hash, code_content, user_id)
            
            # Upload analysis result to S3
            analysis_data = {
                'commit_hash': commit_hash,
                'risk_score': risk_percentage,
                'status': status,
                'reasoning': analysis.get('reasoning', ''),
                'vulnerabilities': analysis.get('vulnerabilities', []),
                'dlt_tx_hash': dlt_tx_hash,
                'timestamp': datetime.now().isoformat()
            }
            s3_service.upload_analysis_result(commit_hash, analysis_data, user_id)

        # Save to Supabase
        try:
            commit_response = supabase.table('commits').insert({
                'user_id': user_id,
                'commit_hash': commit_hash,
                'risk_score': risk_percentage,
                'status': status,
                'code_content': code_content,
                'dlt_tx_hash': dlt_tx_hash,
            }).execute()

            commit_data = commit_response.data[0] if commit_response.data else {}

        except Exception as db_error:
            return jsonify({'error': f'Failed to save commit: {str(db_error)}'}), 500

        # Prepare response
        response_data = {
            'commit_id': commit_data.get('id'),
            'commit_hash': commit_hash,
            'risk_score': risk_percentage,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'dlt_tx_hash': dlt_tx_hash,
            'reasoning': analysis.get('reasoning', ''),
            'vulnerabilities': analysis.get('vulnerabilities', [])
        }
        
        if s3_code_key:
            response_data['s3_code_key'] = s3_code_key

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get commit logs for authenticated user."""
    try:
        # Authenticate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]

        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id if user_response.user else None

        if not user_id:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        # Fetch commits from Supabase
        commits_response = supabase.table('commits').select(
            '*, users(username, email)'
        ).eq('user_id', user_id).order('created_at', desc=True).limit(50).execute()

        commits = commits_response.data if commits_response.data else []

        logs = []
        for commit in commits:
            logs.append({
                'commit_id': commit.get('id'),
                'commit_hash': commit.get('commit_hash'),
                'risk_score': commit.get('risk_score'),
                'user': commit.get('users', {}).get('username') if commit.get('users') else 'unknown',
                'timestamp': commit.get('created_at'),
                'status': commit.get('status'),
                'dlt_tx_hash': commit.get('dlt_tx_hash')
            })

        return jsonify({'logs': logs}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    services_status = {
        'ai_service': 'enabled' if ai_service.is_enabled() else 'mock',
        's3_service': 'enabled' if s3_service.is_enabled() else 'disabled',
        'blockchain': dlt_bridge.get_mode()
    }
    
    return jsonify({
        'status': 'healthy',
        'service': 'SCIP Guardian Backend',
        'services': services_status
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
