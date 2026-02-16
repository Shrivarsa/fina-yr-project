import hashlib
import time
import jwt
import datetime
import oracledb
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# Relative imports within the backend folder
from ai_model import load_model, predict_risk_score
from web3_bridge import DLTBridge 

app = Flask(__name__)
CORS(app)
dlt_bridge = DLTBridge()

# --- CONFIGURATION ---
SECRET_KEY = "scip_ultra_secure_secret_key_change_me"
# ORACLE CONNECTION (Update with your credentials)
ORACLE_USER = "admin"
ORACLE_PW = "password"
ORACLE_DSN = "localhost:1521/xe" 

def get_db_connection():
    """Returns a connection to the Oracle Database."""
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PW, dsn=ORACLE_DSN)

# ==========================================================
# AUTHENTICATION HELPERS
# ==========================================================

def create_token(user_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'message': 'Token is missing or invalid!'}), 401
        try:
            actual_token = token.split(" ")[1]
            jwt.decode(actual_token, SECRET_KEY, algorithms=['HS256'])
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# ==========================================================
# API ENDPOINTS
# ==========================================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    hashed_pw = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (:1, :2)", (username, hashed_pw))
        conn.commit()
        return jsonify({"message": "Registration successful"}), 201
    except oracledb.IntegrityError:
        return jsonify({"message": "User already exists"}), 409
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = :1", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        token = create_token(user[0])
        return jsonify({"token": token, "user": {"id": user[0], "username": username}})
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/analyze_commit', methods=['POST'])
@token_required
def analyze_commit():
    data = request.json
    user_id = data.get('user_id')
    code_content = data.get('code_content')
    commit_id = data.get('commit_id')
    
    # 1. Integrity Hash
    code_hash = hashlib.sha256(code_content.encode()).hexdigest()
    
    # 2. AI Assessment
    risk_score = predict_risk_score(code_content)
    
    # 3. DLT Logging
    tx_hash = dlt_bridge.log_commit_data(user_id, code_hash, risk_score, commit_id)
    
    # 4. Oracle Logging
    status = "ACCEPTED" if risk_score < 0.75 else "ROLLBACK"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO commits (user_id, commit_id, code_hash, risk_score, status, tx_hash)
        VALUES (:1, :2, :3, :4, :5, :6)
    """, (user_id, commit_id, code_hash, risk_score, status, tx_hash))
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": status,
        "risk_score": risk_score,
        "tx_hash": tx_hash
    })

@app.route('/api/logs', methods=['GET'])
@token_required
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Oracle requires specific SQL for returning JSON or mapped objects
    cursor.execute("""
        SELECT c.id, c.commit_id, c.code_hash, c.risk_score, c.status, c.timestamp, u.username 
        FROM commits c JOIN users u ON c.user_id = u.id 
        ORDER BY c.timestamp DESC
    """)
    logs = []
    for row in cursor.fetchall():
        logs.append({
            "id": row[0], "commit_id": row[1], "code_hash": row[2],
            "risk_score": row[3], "status": row[4], "timestamp": str(row[5]),
            "username": row[6]
        })
    conn.close()
    return jsonify(logs)

if __name__ == '__main__':
    load_model()
    app.run(port=5000, debug=True)