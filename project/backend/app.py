from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from functools import wraps
import uuid
import datetime
import hashlib

# 🔗 Blockchain bridge
from web3_bridge import anchor_to_blockchain

# ---------------- APP SETUP ----------------
app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

app.config["SECRET_KEY"] = "scip-secret-key"
API_PREFIX = "/api"

# ---------------- IN-MEMORY STORAGE ----------------
USERS = {}
TOKENS = {}
COMMITS = []

# ---------------- TOKEN GENERATION ----------------
def generate_token(user_id):
    token = str(uuid.uuid4())
    TOKENS[token] = {
        "user_id": user_id,
        "created_at": datetime.datetime.utcnow()
    }
    return token

# ---------------- AUTH DECORATOR ----------------
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authorization token missing"}), 401

        token = auth_header.split(" ")[1]

        if token not in TOKENS:
            return jsonify({"error": "Invalid or expired token"}), 401

        request.user_id = TOKENS[token]["user_id"]
        return f(*args, **kwargs)

    return decorated

# ---------------- ROUTES ----------------

# Health Check
@app.route(API_PREFIX + "/health", methods=["GET"])
def health():
    return jsonify({
        "status": "SCIP backend running",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

# ---------------- REGISTER ----------------
@app.route(API_PREFIX + "/register", methods=["POST"])
def register():
    data = request.json or {}

    email = data.get("email")
    password = data.get("password")
    username = data.get("username")

    if not email or not password or not username:
        return jsonify({"error": "All fields required"}), 400

    if email in USERS:
        return jsonify({"error": "User already exists"}), 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user_id = str(uuid.uuid4())

    USERS[email] = {
        "user_id": user_id,
        "email": email,
        "username": username,
        "password_hash": password_hash
    }

    return jsonify({"message": "User registered successfully"}), 201

# ---------------- LOGIN ----------------
@app.route(API_PREFIX + "/login", methods=["POST"])
def login():
    data = request.json or {}

    email = data.get("email")
    password = data.get("password")

    user = USERS.get(email)

    if not user or not bcrypt.check_password_hash(
        user["password_hash"], password
    ):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user["user_id"])

    return jsonify({
        "access_token": token,
        "user_id": user["user_id"],
        "email": user["email"],
        "username": user["username"]
    })

# ---------------- ANALYZE COMMIT ----------------
@app.route(API_PREFIX + "/analyze_commit", methods=["POST"])
@auth_required
def analyze_commit():
    data = request.json or {}
    code = data.get("code_content", "")

    if not code.strip():
        return jsonify({"error": "Empty code"}), 400

    # Generate hash
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    # Anchor to blockchain
    try:
        tx_hash = anchor_to_blockchain(code_hash)
    except Exception as e:
        tx_hash = "Blockchain anchor failed"
        print("Blockchain Error:", str(e))

    # Dummy AI risk logic
    risk_score = min(100, (len(code) % 100) + 10)
    status = "Accepted" if risk_score < 75 else "Rejected"

    commit = {
        "commit_id": str(uuid.uuid4()),
        "commit_hash": code_hash[:12],
        "risk_score": risk_score,
        "status": status,
        "user_id": request.user_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "dlt_tx_hash": tx_hash
    }

    COMMITS.insert(0, commit)

    return jsonify({
        "message": "Commit analyzed successfully",
        "commit": commit
    })

# ---------------- LOGS ----------------
@app.route(API_PREFIX + "/logs", methods=["GET"])
@auth_required
def logs():
    user_commits = [
        commit for commit in COMMITS
        if commit["user_id"] == request.user_id
    ]

    return jsonify({"logs": user_commits})

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    print("SCIP Backend running on http://localhost:5000")
    app.run(debug=True, port=5000)
