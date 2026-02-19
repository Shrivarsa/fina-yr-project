# Quick Start - Running Backend & Frontend

## Prerequisites

1. **Python 3.8+** installed
2. **Node.js 18+** installed
3. **Supabase account** and credentials

---

## Step 1: Backend Setup

### 1.1 Navigate to backend directory
```bash
cd backend
```

### 1.2 Install Python dependencies
```bash
pip install -r requirements.txt
```

### 1.3 Create `.env` file
Copy the example file:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

### 1.4 Edit `.env` file
Open `.env` and add your Supabase credentials:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

### 1.5 Run the backend server
```bash
python scip_orchestrator.py
```

You should see:
```
[S3Service] S3_BUCKET_NAME not set. Running without S3 storage.
[AIService] OPENROUTER_API_KEY not set. Running in mock mode.
[DLT Bridge] Connected to Hardhat node at http://localhost:8545...
 * Running on http://127.0.0.1:5000
```

**Backend is now running on http://localhost:5000** ✅

---

## Step 2: Frontend Setup

### 2.1 Open a NEW terminal window
Keep the backend running in the first terminal.

### 2.2 Navigate to frontend directory
```bash
cd frontend
```

### 2.3 Install Node.js dependencies
```bash
npm install
```

### 2.4 Create `.env` file
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

### 2.5 Edit `.env` file
Open `.env` and add your Supabase credentials:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
VITE_API_URL=http://localhost:5000
```

### 2.6 Run the frontend development server
```bash
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Frontend is now running on http://localhost:5173** ✅

---

## Step 3: Access the Application

1. Open your browser
2. Go to: **http://localhost:5173**
3. You should see the login page
4. Create an account or login

---

## Troubleshooting

### Backend Issues

**Error: "Module not found"**
```bash
# Make sure you're in the backend directory
cd backend
pip install -r requirements.txt
```

**Error: "Supabase connection failed"**
- Check your `.env` file has correct Supabase credentials
- Make sure you copied `.env.example` to `.env` (not just renamed it)

**Error: "Port 5000 already in use"**
- Change the port in `scip_orchestrator.py`:
  ```python
  app.run(debug=True, port=5001)  # Change to 5001 or another port
  ```
- Update `frontend/.env`:
  ```env
  VITE_API_URL=http://localhost:5001
  ```

### Frontend Issues

**Error: "Cannot find module"**
```bash
cd frontend
rm -rf node_modules package-lock.json  # Linux/Mac
# OR
Remove-Item -Recurse -Force node_modules, package-lock.json  # Windows PowerShell
npm install
```

**Error: "VITE_SUPABASE_URL is not defined"**
- Make sure `.env` file exists in `frontend/` directory
- Restart the dev server after creating/editing `.env`
- Check that variable names start with `VITE_`

**Blank page or errors in browser console**
- Check browser console (F12) for errors
- Make sure backend is running on the correct port
- Verify Supabase credentials are correct

---

## Running Both Together

### Option 1: Two Terminal Windows (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
python scip_orchestrator.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Option 2: Background Process (Linux/Mac)

**Backend in background:**
```bash
cd backend
python scip_orchestrator.py &
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Option 3: Windows PowerShell (Background)

**Backend in background:**
```powershell
cd backend
Start-Process python -ArgumentList "scip_orchestrator.py" -WindowStyle Hidden
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## Stopping the Servers

### Backend
- Press `Ctrl+C` in the backend terminal

### Frontend
- Press `Ctrl+C` in the frontend terminal

---

## Verify Everything Works

1. ✅ Backend shows "Running on http://127.0.0.1:5000"
2. ✅ Frontend shows "Local: http://localhost:5173/"
3. ✅ Browser opens login page at http://localhost:5173
4. ✅ Can create account and login
5. ✅ Can analyze code and see results

---

## Next Steps

Once both are running:
1. Create a user account via the frontend
2. Try analyzing some code
3. Check the backend logs for analysis results
4. (Optional) Add S3, OpenRouter, or Hardhat for enhanced features
