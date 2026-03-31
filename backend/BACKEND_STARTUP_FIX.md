# Backend Startup Fix - Supabase .env Variables

**Issue**: `ValueError("Supabase URL and key must be set via environment variables")`

**Cause**: Wrong .env variable names.

**Code expects** (scip_orchestrator.py):
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
