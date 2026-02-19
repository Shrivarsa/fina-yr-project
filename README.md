# SCIP Guardian - Multi-User Cloud Platform

A full-stack multi-user cloud platform for AI-powered code security analysis with blockchain integration.

## Architecture

The platform consists of four main components:

- **Backend**: Python Flask API with Supabase, S3, and OpenRouter AI integration
- **Frontend**: React web dashboard with Supabase Auth
- **Blockchain**: Hardhat/Solidity for blockchain verification
- **CLI**: Python CLI tool for file analysis

## Directory Structure

```
scip-guardian/
├── backend/
│   ├── scip_orchestrator.py    # Flask API server
│   ├── ai_service.py            # OpenRouter AI service
│   ├── s3_service.py             # AWS S3 service
│   ├── ai_model.py              # AI model wrapper (backward compatibility)
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # React app entry
│   │   ├── AuthContext.tsx      # Supabase Auth context
│   │   ├── AuthPage.tsx         # Login/signup page
│   │   ├── SCIPDashboard.jsx    # Main dashboard UI
│   │   ├── lib/
│   │   │   └── supabase.ts      # Supabase client
│   │   └── main.tsx             # React DOM entry
│   └── package.json             # Node.js dependencies
├── blockchain/
│   └── web3_bridge.py           # Hardhat blockchain bridge
├── cli/
│   ├── scip_cli.py             # CLI tool for file analysis
│   └── config.json             # CLI configuration
└── contracts/
    └── CommitVerification.sol  # Smart contract for commit logging
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 18+
- Supabase account and project
- (Optional) AWS account for S3 storage
- (Optional) OpenRouter API key for AI analysis
- (Optional) Hardhat for local blockchain development

### 1. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
- `VITE_SUPABASE_URL`: Your Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Your Supabase anon key
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key
- (Optional) AWS credentials for S3
- (Optional) `OPENROUTER_API_KEY` for AI analysis
- (Optional) Blockchain configuration

Start the Flask API server:

```bash
python scip_orchestrator.py
```

The server will run on `http://localhost:5000`.

### 2. Frontend Setup

Navigate to the frontend directory:

```bash
cd frontend
```

Install Node.js dependencies:

```bash
npm install
```

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:
- `VITE_SUPABASE_URL`: Your Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Your Supabase anon key
- `VITE_API_URL`: Backend API URL (default: http://localhost:5000)

Start the development server:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

### 3. CLI Usage

Navigate to the CLI directory:

```bash
cd cli
```

Login to the platform:

```bash
python scip_cli.py login
```

Analyze a code file:

```bash
python scip_cli.py analyze path/to/your/file.py
# Or simply:
python scip_cli.py path/to/your/file.py
```

Logout:

```bash
python scip_cli.py logout
```

### 4. Blockchain Setup (Optional)

Install Hardhat dependencies:

```bash
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
```

Start local Hardhat node:

```bash
npx hardhat node
```

The node will run on `http://localhost:8545` (default).

Compile and deploy the contract:

```bash
npx hardhat compile
npx hardhat run scripts/deploy.js --network localhost
```

Update `.env` in the backend with the contract address and a private key from Hardhat.

## Features

### Web Dashboard

- **Supabase Authentication**: Direct Supabase Auth integration for login/signup
- **Commit Simulator**: Paste code and analyze security risks in real-time
- **Real-time Audit Log**: View all analyzed commits with risk scores
- **Visual Indicators**:
  - Green: Accepted (risk score < 75%)
  - Yellow: Medium risk (50-75%)
  - Red: Rollback Enforced (risk score >= 75%)
- **Auto-refresh**: Logs update every 3 seconds

### Backend API

**Endpoints:**

- `POST /api/register`: Register new user (legacy, frontend uses Supabase directly)
- `POST /api/login`: Login user (legacy, frontend uses Supabase directly)
- `POST /api/analyze_commit`: Analyze code and return risk score
  ```json
  {
    "code_content": "your code here"
  }
  ```
  Headers: `Authorization: Bearer <supabase_access_token>`

- `GET /api/logs`: Retrieve commit history
  Headers: `Authorization: Bearer <supabase_access_token>`

- `GET /health`: Health check with service status

### CLI Tool

- **Login Command**: `scip_cli.py login` - Authenticate and persist session
- **Logout Command**: `scip_cli.py logout` - Clear saved session
- **Analyze Command**: `scip_cli.py analyze <file>` - Analyze code file
- **Session Persistence**: Saves Supabase session token locally

### Services

#### S3Service (Optional)

Stores code content and analysis results in AWS S3. Falls back gracefully if not configured.

#### AIService (Optional)

Uses OpenRouter API for AI-powered code analysis. Falls back to mock analysis if not configured.

#### DLTBridge

Connects to local Hardhat node by default (`http://localhost:8545`). Falls back to mock mode if node is offline.

## Configuration

### Environment Variables

#### Backend (.env)

- `VITE_SUPABASE_URL`: Supabase project URL (required)
- `VITE_SUPABASE_ANON_KEY`: Supabase anon key (required)
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (required)
- `AWS_ACCESS_KEY_ID`: AWS access key (optional)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional)
- `AWS_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET_NAME`: S3 bucket name (optional)
- `OPENROUTER_API_KEY`: OpenRouter API key (optional)
- `OPENROUTER_MODEL`: Model to use (default: openai/gpt-4o-mini)
- `WEB3_PROVIDER_URL`: Blockchain RPC URL (default: http://localhost:8545)
- `WEB3_CONTRACT_ADDRESS`: Smart contract address (optional)
- `WEB3_PRIVATE_KEY`: Private key for transactions (optional)

#### Frontend (.env)

- `VITE_SUPABASE_URL`: Supabase project URL (required)
- `VITE_SUPABASE_ANON_KEY`: Supabase anon key (required)
- `VITE_API_URL`: Backend API URL (default: http://localhost:5000)

## Technology Stack

- **Backend**: Python 3.x, Flask, Supabase, Boto3 (S3), OpenRouter AI
- **Frontend**: React 18, Vite, Tailwind CSS, Supabase Auth, Lucide Icons
- **Blockchain**: Solidity 0.8.19, Hardhat, Web3.py
- **Database**: Supabase (PostgreSQL)
- **Storage**: AWS S3 (optional)
- **AI**: OpenRouter API (optional)

## Migration Notes

This refactored version replaces:
- SQLite → Supabase (PostgreSQL)
- Backend Auth API → Direct Supabase Auth in frontend
- Mock AI → OpenRouter AI Service (with fallback)
- Local storage → S3 Service (optional)
- Generic Web3 → Hardhat-specific Web3 bridge

All services gracefully degrade to mock/fallback modes if not configured.

## License

MIT License - This is a proof-of-concept demonstration.
