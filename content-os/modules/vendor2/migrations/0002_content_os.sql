-- THBISON Content OS durable ledger (unowned rows; tenant is project_id).
create table if not exists cos_principals (
  principal_id text primary key,
  token_sha256 text not null unique,
  project_id text not null,
  subject_id text not null,
  role text not null,
  can_publish boolean not null default false
);

create table if not exists cos_idempotency (
  project_id text not null,
  operation text not null,
  key text not null,
  payload_sha256 text not null,
  object_id text not null,
  created_at timestamptz not null default now(),
  primary key (project_id, operation, key)
);
create index if not exists cos_idempotency_object_idx on cos_idempotency (object_id);

create table if not exists cos_jobs (
  job_id text primary key,
  project_id text not null,
  data_class text not null,
  request_id text not null,
  kind text not null,
  status text not null,
  payload_json text not null,
  result_json text,
  error_code text,
  provider_requests integer not null default 0,
  tokens_used integer not null default 0,
  cost_usd text not null default '0.000000',
  cancelled boolean not null default false,
  deadline_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists cos_jobs_project_idx on cos_jobs (project_id, created_at);

create table if not exists cos_briefs (
  brief_id text not null,
  brief_revision integer not null,
  project_id text not null,
  data_class text not null,
  body_json text not null,
  created_at timestamptz not null default now(),
  primary key (brief_id, brief_revision)
);
create index if not exists cos_briefs_project_idx on cos_briefs (project_id);

create table if not exists cos_evidence (
  bundle_id text primary key,
  project_id text not null,
  snapshot_sha256 text not null,
  revoked boolean not null default false,
  body_json text not null,
  created_at timestamptz not null default now()
);

create table if not exists cos_articles (
  article_id text not null,
  article_revision integer not null,
  project_id text not null,
  data_class text not null,
  brief_id text not null,
  brief_revision integer not null,
  bundle_id text not null,
  content_sha256 text not null,
  status text not null,
  expected_revision integer not null,
  body_json text not null,
  created_at timestamptz not null default now(),
  primary key (article_id, article_revision)
);
create index if not exists cos_articles_project_idx on cos_articles (project_id, article_id);

create table if not exists cos_approvals (
  approval_id text primary key,
  project_id text not null,
  article_id text not null,
  article_revision integer not null,
  content_sha256 text not null,
  evidence_snapshot_sha256 text not null,
  destination_id text not null,
  decision text not null,
  body_json text not null,
  created_at timestamptz not null default now()
);
create index if not exists cos_approvals_article_idx on cos_approvals (article_id, article_revision);

create table if not exists cos_publications (
  publication_id text primary key,
  project_id text not null,
  request_id text not null,
  article_id text not null,
  article_revision integer not null,
  destination_id text not null,
  content_sha256 text not null,
  status text not null,
  provider_record_id text,
  provider_url text,
  actual_side_effects integer not null default 0,
  body_json text not null,
  created_at timestamptz not null default now()
);
create unique index if not exists cos_pub_logical_idx
  on cos_publications (project_id, article_id, article_revision, destination_id, content_sha256);

create table if not exists cos_cms_records (
  provider_record_id text primary key,
  project_id text not null,
  destination_id text not null,
  article_id text not null,
  article_revision integer not null,
  content_sha256 text not null,
  body_json text not null,
  created_at timestamptz not null default now()
);

create table if not exists cos_artifacts (
  artifact_id text primary key,
  project_id text not null,
  sha256 text not null,
  bytes integer not null,
  media_type text not null,
  storage_path text not null,
  verified boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists cos_outbox (
  outbox_id text primary key,
  project_id text not null,
  kind text not null,
  body_json text not null,
  attempts integer not null default 0,
  status text not null,
  created_at timestamptz not null default now()
);

create table if not exists cos_provider_calls (
  call_id text primary key,
  project_id text not null,
  job_id text,
  provider text not null,
  retryable boolean not null,
  status_code integer,
  created_at timestamptz not null default now()
);

create table if not exists cos_audit (
  audit_id text primary key,
  project_id text not null,
  action text not null,
  detail_json text not null,
  created_at timestamptz not null default now()
);

create table if not exists cos_budget (
  project_id text not null,
  window_id text not null,
  reserved_requests integer not null default 0,
  reserved_tokens integer not null default 0,
  reserved_cost_usd text not null default '0.000000',
  charged_unknown integer not null default 0,
  primary key (project_id, window_id)
);

create table if not exists cos_clock (
  k text primary key,
  v text not null
);

create table if not exists cos_brief_cache (
  cache_key text primary key,
  project_id text not null,
  body_json text not null,
  created_at timestamptz not null default now()
);
