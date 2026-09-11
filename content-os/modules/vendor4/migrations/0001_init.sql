-- Synthetic ledger only. TEST_ONLY.
CREATE TABLE IF NOT EXISTS knowledge_claims (
  claim_id TEXT NOT NULL,
  claim_version TEXT NOT NULL,
  project_id TEXT NOT NULL,
  status TEXT NOT NULL,
  quote TEXT NOT NULL,
  quote_sha256 TEXT NOT NULL,
  locator TEXT,
  source_sha256 TEXT NOT NULL,
  data_class TEXT NOT NULL DEFAULT 'TEST_ONLY'
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  state TEXT NOT NULL,
  data_class TEXT NOT NULL DEFAULT 'TEST_ONLY'
);

CREATE TABLE IF NOT EXISTS mutations (
  receipt_id TEXT PRIMARY KEY,
  test_run_id TEXT NOT NULL,
  payload TEXT NOT NULL
);
