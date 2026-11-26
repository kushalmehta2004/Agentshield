create table sessions (
  id text primary key,
  created_at timestamptz default now(),
  scenario text,
  mode text check (mode in ('off','regex','shield')) default 'shield',
  status text default 'running'  -- running | allowed | blocked | warn
);

create table llm_calls (
  id uuid primary key default gen_random_uuid(),
  session_id text references sessions(id) on delete cascade,
  created_at timestamptz default now(),
  request_messages jsonb not null,
  response jsonb not null,
  latency_ms int
);

create table tool_calls (
  id uuid primary key default gen_random_uuid(),
  session_id text references sessions(id) on delete cascade,
  llm_call_id uuid references llm_calls(id) on delete cascade,
  created_at timestamptz default now(),
  tool_name text not null,
  args jsonb not null,
  is_sensitive boolean default false
);

create table verdicts (
  id uuid primary key default gen_random_uuid(),
  session_id text references sessions(id) on delete cascade,
  tool_call_id uuid references tool_calls(id) on delete cascade,
  created_at timestamptz default now(),
  mode text not null,
  decision text check (decision in ('ALLOW','BLOCK','WARN')) not null,
  attack_detected boolean,
  unstable boolean default false,
  causes jsonb default '[]',   -- [{source_label, chunk_index, chunk_text, effect}]
  reruns jsonb default '[]',   -- [{variant, tool_calls}]
  latency_ms int
);

create table outbox (            -- fake side effects from the demo agent
  id uuid primary key default gen_random_uuid(),
  session_id text,
  created_at timestamptz default now(),
  kind text,                     -- email | http_post
  payload jsonb
);

create table eval_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  mode text not null,
  total_attacks int, successful_attacks int,
  total_benign int, benign_passed int,
  avg_latency_ms int,
  details jsonb
);

-- Enable realtime
alter publication supabase_realtime add table sessions, verdicts, tool_calls;

-- RLS: enable on all tables; anon role gets SELECT only; service role writes.
alter table sessions enable row level security;
alter table llm_calls enable row level security;
alter table tool_calls enable row level security;
alter table verdicts enable row level security;
alter table outbox enable row level security;
alter table eval_runs enable row level security;

create policy "anon select sessions" on sessions for select to anon using (true);
create policy "anon select llm_calls" on llm_calls for select to anon using (true);
create policy "anon select tool_calls" on tool_calls for select to anon using (true);
create policy "anon select verdicts" on verdicts for select to anon using (true);
create policy "anon select outbox" on outbox for select to anon using (true);
create policy "anon select eval_runs" on eval_runs for select to anon using (true);
