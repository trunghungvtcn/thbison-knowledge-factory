create extension if not exists pgcrypto;

create table if not exists claim_entities_v16 (
  claim_entity_id uuid primary key,
  product_family text not null,
  current_claim_version_id text,
  created_from_legacy_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists claim_versions_v16 (
  claim_version_id text primary key,
  claim_entity_id uuid not null references claim_entities_v16(claim_entity_id),
  canonical_text text not null,
  semantic_payload jsonb not null,
  condition_ast jsonb not null,
  exception_ast jsonb not null,
  condition_unresolved boolean not null default false,
  valid_from timestamptz not null default now(),
  valid_to timestamptz,
  superseded_by text references claim_versions_v16(claim_version_id),
  migration_run_id text not null,
  created_at timestamptz not null default now()
);

alter table claim_entities_v16
  drop constraint if exists claim_entities_v16_current_version_fk;

alter table claim_entities_v16
  add constraint claim_entities_v16_current_version_fk
  foreign key (current_claim_version_id)
  references claim_versions_v16(claim_version_id)
  deferrable initially deferred;

create table if not exists claim_aliases_v16 (
  alias_key text primary key,
  alias_type text not null,
  alias_value text not null,
  claim_entity_id uuid not null references claim_entities_v16(claim_entity_id),
  first_seen_run_id text not null,
  created_at timestamptz not null default now(),
  unique(alias_type, alias_value)
);

create table if not exists review_decisions_v16 (
  decision_id uuid primary key default gen_random_uuid(),
  claim_entity_id uuid not null references claim_entities_v16(claim_entity_id),
  reviewed_claim_version_id text references claim_versions_v16(claim_version_id),
  decision text not null check (decision in ('PENDING','APPROVED','HOLD','REJECTED')),
  reviewer text,
  notes text,
  decided_at timestamptz,
  source_system text not null default 'NOTION',
  created_at timestamptz not null default now()
);

create table if not exists publication_mappings_v16 (
  target_system text not null,
  claim_entity_id uuid not null references claim_entities_v16(claim_entity_id),
  remote_page_id text not null,
  last_published_version_id text references claim_versions_v16(claim_version_id),
  updated_at timestamptz not null default now(),
  primary key(target_system, claim_entity_id),
  unique(target_system, remote_page_id)
);

create table if not exists migration_issues_v16 (
  issue_id uuid primary key default gen_random_uuid(),
  migration_run_id text not null,
  claim_entity_id uuid,
  legacy_canonical_id text,
  issue_code text not null,
  blocking boolean not null default true,
  details jsonb not null default '{}'::jsonb,
  resolved_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists claim_versions_v16_entity_idx
  on claim_versions_v16(claim_entity_id, valid_from desc);

create index if not exists review_decisions_v16_entity_idx
  on review_decisions_v16(claim_entity_id, decided_at desc);
