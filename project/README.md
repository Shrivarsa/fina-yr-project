# SCIP Guardian - AI-Powered Code Security Platform

A full-stack proof-of-concept demonstrating an AI-powered code security platform with blockchain integration.

## Architecture

The platform consists of three main components:

- **Guardian (Backend)**: Python Flask API for code analysis
- **Ledger (DLT)**: Hardhat/Solidity for blockchain verification
- **Client**: React web dashboard and Python CLI

## Directory Structure

```
scip-guardian/
├── scip_orchestrator.py       # Flask API server
├── ai_model.py                 # AI risk prediction (placeholder)
├── web3_bridge.py              # DLT blockchain bridge (mock)
├── requirements.txt            # Python dependencies
├── hardhat.config.js           # Hardhat configuration
├── cli/
│   ├── scip_cli.py            # CLI tool for file analysis
│   └── config.json            # CLI configuration
├── contracts/
│   └── CommitVerification.sol # Smart contract for commit logging
└── frontend/
    └── src/
        ├── SCIPDashboard.jsx  # Main dashboard UI
        ├── App.tsx            # React app entry
        └── main.tsx           # React DOM entry
```

## Setup Instructions

### 1. Backend Setup (Python)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the Flask API server:

```bash
python scip_orchestrator.py
```

The server will run on `http://localhost:5000` and initialize a SQLite database (`scip_database.db`).

### 2. Frontend Setup (React)

Install Node.js dependencies:

```bash
npm install
```

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

Analyze a code file:

```bash
python scip_cli.py path/to/your/file.py
```

### 4. Smart Contract (Optional)

Install Hardhat dependencies:

```bash
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
```

Compile the contract:

```bash
npx hardhat compile
```

Deploy to local network:

```bash
npx hardhat node
npx hardhat run scripts/deploy.js --network localhost
```

## Features

### Web Dashboard

- **Commit Simulator**: Paste code and analyze security risks in real-time
- **Real-time Audit Log**: View all analyzed commits with risk scores
- **Visual Indicators**:
  - Green: Accepted (risk score < 0.75)
  - Red: Rollback Enforced (risk score >= 0.75)
- **Auto-refresh**: Logs update every 3 seconds

### Backend API

**Endpoints:**

- `POST /analyze_commit`: Analyze code and return risk score
  ```json
  {
    "code_content": "your code here",
    "user": "username"
  }
  ```

- `GET /api/logs`: Retrieve commit history

### CLI Tool

Analyze local files and send them to the backend for security assessment:

```bash
python scip_cli.py example.py
```

## Current Implementation Status

### Implemented (Functional)
- Flask API with CORS support
- SQLite database for commit storage
- Web dashboard with real-time updates
- CLI tool for file analysis
- Mock AI risk prediction
- Mock DLT logging

### Placeholder (To Be Implemented)
- **AI Model**: Currently returns random risk scores
  - Future: TensorFlow/Keras-based risk prediction
- **Web3 Bridge**: Currently mocks blockchain calls
  - Future: Real Web3.py integration with Ethereum/Polygon
- **Smart Contract**: Solidity contract ready but not deployed
  - Future: Deploy to testnet/mainnet

## Configuration

### Backend Configuration
Edit database and API settings in `scip_orchestrator.py`:
- `DATABASE`: SQLite database path
- `RISK_THRESHOLD`: Risk score threshold (default: 0.75)

### CLI Configuration
Edit `cli/config.json`:
```json
{
  "api_url": "http://localhost:5000",
  "user": "cli-user",
  "network": "ethereum-testnet"
}
```

## Technology Stack

- **Backend**: Python 3.x, Flask, SQLite
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons
- **DLT**: Solidity 0.8.19, Hardhat
- **AI**: TensorFlow/Keras (placeholder)
- **Blockchain**: Web3.py (mock implementation)

## API Response Examples

### Analyze Commit Response
```json
{
  "commit_hash": "a1b2c3d4e5f6g7h8",
  "risk_score": 0.42,
  "status": "Accepted",
  "timestamp": "2024-01-18T10:30:00",
  "dlt_tx_hash": "9i8h7g6f5e4d3c2b"
}
```

### Logs Response
```json
{
  "logs": [
    {
      "commit_hash": "a1b2c3d4e5f6g7h8",
      "risk_score": 0.42,
      "user": "web-user",
      "timestamp": "2024-01-18T10:30:00",
      "status": "Accepted",
      "dlt_tx_hash": "9i8h7g6f5e4d3c2b"
    }
  ]
}
```

## Next Steps

1. Implement real AI model using TensorFlow/Keras
2. Integrate Web3.py for actual blockchain transactions
3. Deploy smart contract to testnet
4. Add authentication and user management
5. Implement code diff visualization
6. Add detailed risk analysis reports

## License

MIT License - This is a proof-of-concept demonstration.
