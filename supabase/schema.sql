-- IFC-GPT v2 Supabase Database Schema
-- Run in Supabase SQL editor

-- Projects table
CREATE TABLE projects (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL DEFAULT 'Untitled',
  description TEXT,
  ifc_path    TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Job history
CREATE TABLE jobs (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id),
  project_id  UUID REFERENCES projects(id),
  status      TEXT NOT NULL DEFAULT 'queued',
  message     TEXT,
  ifc_url     TEXT,
  error       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Row-level security
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs     ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own projects"
  ON projects USING (auth.uid() = user_id);

CREATE POLICY "Users can view own jobs"
  ON jobs USING (auth.uid() = user_id);
