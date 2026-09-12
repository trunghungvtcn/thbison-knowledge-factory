create table if not exists cos_notion_snapshots (
  snapshot_sha256 text primary key,
  project_id text not null,
  captured_at timestamptz not null,
  imported_at timestamptz not null default now(),
  collection_counts_json text not null
);

create table if not exists cos_notion_snapshot_rows (
  snapshot_sha256 text not null references cos_notion_snapshots(snapshot_sha256),
  data_source_id text not null,
  record_id text not null,
  record_name text not null,
  status text,
  decision text,
  source_url text,
  body_json text not null,
  primary key (snapshot_sha256, data_source_id, record_id)
);

create index if not exists cos_notion_snapshot_rows_source_idx
  on cos_notion_snapshot_rows (data_source_id, snapshot_sha256);
