-- Durable CMS adapter ledger. Applied by app.ledger.Ledger on open.
CREATE TABLE IF NOT EXISTS idempotency (
  ledger_key TEXT PRIMARY KEY,
  payload_hash TEXT NOT NULL,
  receipt_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
