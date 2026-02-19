/*
  # Create Users and Commits Tables for Multi-User Security Platform

  1. New Tables
    - `users` - Stores user profile information linked to Supabase auth
      - `id` (uuid, primary key, references auth.users)
      - `username` (text, unique)
      - `email` (text, unique)
      - `created_at` (timestamp)
      - `updated_at` (timestamp)
    
    - `commits` - Stores analyzed code commits with risk assessment
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to users)
      - `commit_hash` (text, unique)
      - `risk_score` (numeric, 0-100)
      - `status` (text, Accepted or Rollback Enforced)
      - `code_content` (text, stored for audit)
      - `dlt_tx_hash` (text, blockchain transaction reference)
      - `created_at` (timestamp)

  2. Security
    - Enable RLS on both tables
    - Users can only view their own data
    - Users can only insert/update/delete their own commits
    - Service role can read all data for admin operations

  3. Indexes
    - Index on user_id for fast commit queries
    - Index on created_at for audit log sorting
*/

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username text UNIQUE NOT NULL,
  email text UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  commit_hash text UNIQUE NOT NULL,
  risk_score numeric NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
  status text NOT NULL CHECK (status IN ('Accepted', 'Rollback Enforced')),
  code_content text NOT NULL,
  dlt_tx_hash text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE commits ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS commits_user_id_idx ON commits(user_id);
CREATE INDEX IF NOT EXISTS commits_created_at_idx ON commits(created_at DESC);
CREATE INDEX IF NOT EXISTS commits_user_created_idx ON commits(user_id, created_at DESC);

CREATE POLICY "Users can read own profile"
  ON users FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Service role can read all profiles"
  ON users FOR SELECT
  TO service_role
  USING (true);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can view own commits"
  ON commits FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Service role can read all commits"
  ON commits FOR SELECT
  TO service_role
  USING (true);

CREATE POLICY "Users can insert own commits"
  ON commits FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own commits"
  ON commits FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own commits"
  ON commits FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
