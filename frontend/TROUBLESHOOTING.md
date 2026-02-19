# Troubleshooting White Screen Issue

## Common Causes & Solutions

### 1. Missing `.env` File (Most Common)

**Symptom:** White screen, no errors visible

**Solution:**
1. Create `.env` file in the `frontend/` directory
2. Copy from `.env.example`:
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   
   # Linux/Mac
   cp .env.example .env
   ```
3. Add your Supabase credentials:
   ```env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your_anon_key_here
   VITE_API_URL=http://localhost:5000
   ```
4. **Restart the dev server** (stop with Ctrl+C, then `npm run dev` again)

---

### 2. Check Browser Console

**How to check:**
1. Open browser DevTools (F12)
2. Go to "Console" tab
3. Look for red error messages

**Common errors:**
- `Missing Supabase environment variables` → Create `.env` file
- `Failed to fetch` → Backend not running or wrong API URL
- `Module not found` → Run `npm install`

---

### 3. Environment Variables Not Loading

**Issue:** Vite requires restart after creating/editing `.env`

**Solution:**
1. Stop dev server (Ctrl+C)
2. Delete `.env` if it exists
3. Create new `.env` file
4. Add variables (must start with `VITE_`)
5. Start dev server: `npm run dev`

**Note:** Variables MUST start with `VITE_` to be accessible in the frontend!

---

### 4. Missing Dependencies

**Symptom:** Import errors in console

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

### 5. Port Already in Use

**Symptom:** `Port 5173 is already in use`

**Solution:**
```bash
# Kill process on port 5173
# Windows PowerShell
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Or change port in vite.config.ts
```

---

### 6. Backend Not Running

**Symptom:** API calls fail, white screen after login attempt

**Solution:**
1. Make sure backend is running: `cd backend && python scip_orchestrator.py`
2. Check backend is on http://localhost:5000
3. Verify `VITE_API_URL=http://localhost:5000` in `.env`

---

## Quick Diagnostic Steps

1. **Check `.env` exists:**
   ```bash
   cd frontend
   ls .env  # Linux/Mac
   dir .env  # Windows
   ```

2. **Check browser console:**
   - Press F12
   - Look for errors

3. **Check terminal output:**
   - Look for compilation errors
   - Check if server started successfully

4. **Verify file structure:**
   ```
   frontend/
   ├── .env          ← Must exist!
   ├── src/
   │   ├── lib/
   │   │   └── supabase.ts  ← Must exist!
   │   ├── App.tsx
   │   └── main.tsx
   └── package.json
   ```

---

## Still Not Working?

1. **Clear browser cache:**
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - Or clear browser cache completely

2. **Check Supabase credentials:**
   - Verify URL is correct
   - Verify anon key is correct
   - Check Supabase project is active

3. **Check network tab:**
   - Open DevTools → Network tab
   - Look for failed requests
   - Check if requests are being made

4. **Try incognito/private window:**
   - Rules out browser extension issues

---

## Expected Behavior

When working correctly, you should see:
1. ✅ Dev server starts: `Local: http://localhost:5173/`
2. ✅ Browser shows login page (not white screen)
3. ✅ No errors in browser console
4. ✅ Can create account and login
