# Quick Setup Guide

## ✅ REQUIRED: Supabase Configuration

**You MUST configure Supabase** - the platform won't work without it.

### Steps:
1. Create a Supabase account at https://supabase.com
2. Create a new project
3. Get your credentials from Project Settings → API:
   - Project URL
   - Anon/public key
   - Service role key (keep this secret!)

### Backend Configuration (`backend/.env`):
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Frontend Configuration (`frontend/.env`):
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VITE_API_URL=http://localhost:5000
```

### Database Setup:
Run the Supabase migration in `project/supabase/migrations/20260118060149_create_users_and_commits_tables.sql`:
- Go to Supabase Dashboard → SQL Editor
- Run the migration SQL to create `users` and `commits` tables

---

## 🔵 OPTIONAL: S3 Storage

**Without S3**: Code content is stored only in Supabase database (works fine for small projects)

**With S3**: Code content is also backed up to AWS S3 (better for production)

### Steps:
1. Create AWS account
2. Create S3 bucket
3. Create IAM user with S3 permissions
4. Get access key and secret

### Configuration (`backend/.env`):
```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

---

## 🟢 OPTIONAL: OpenRouter AI

**Without OpenRouter**: System uses mock/random risk scores (0-100%)

**With OpenRouter**: Real AI-powered security analysis

### Steps:
1. Sign up at https://openrouter.ai
2. Get your API key from dashboard
3. Add credits to your account

### Configuration (`backend/.env`):
```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o-mini  # or any model you prefer
```

---

## 🟡 OPTIONAL: Blockchain (Hardhat)

**Without Hardhat**: Blockchain transactions are mocked (works fine for testing)

**With Hardhat**: Real blockchain transactions on local network

### Steps:
1. Install Hardhat: `npm install --save-dev hardhat`
2. Start local node: `npx hardhat node`
3. Deploy contract and get address
4. Use a private key from Hardhat accounts

### Configuration (`backend/.env`):
```env
WEB3_PROVIDER_URL=http://localhost:8545
WEB3_CONTRACT_ADDRESS=0x...
WEB3_PRIVATE_KEY=0x...
```

---

## 🚀 Minimum Setup (Just Supabase)

To get started quickly, you only need:

1. **Supabase credentials** (required)
2. Create `.env` files in `backend/` and `frontend/` with Supabase keys
3. Run database migration in Supabase
4. Start backend: `cd backend && python scip_orchestrator.py`
5. Start frontend: `cd frontend && npm run dev`

The platform will work with:
- ✅ Supabase Auth (login/signup)
- ✅ Database storage (Supabase)
- ⚠️ Mock AI analysis (random scores)
- ⚠️ Mock blockchain (fake transaction hashes)
- ⚠️ No S3 backup (stored only in Supabase)

---

## 📝 Quick Start Checklist

- [ ] Create Supabase project
- [ ] Add Supabase keys to `backend/.env`
- [ ] Add Supabase keys to `frontend/.env`
- [ ] Run database migration in Supabase SQL Editor
- [ ] (Optional) Add S3 credentials for cloud storage
- [ ] (Optional) Add OpenRouter key for real AI analysis
- [ ] (Optional) Start Hardhat node for blockchain

Then run:
```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
python scip_orchestrator.py

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```
