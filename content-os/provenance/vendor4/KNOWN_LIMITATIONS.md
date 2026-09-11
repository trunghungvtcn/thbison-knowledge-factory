# Known limitations

- Staging Notion calls are BLOCKED_ACCESS without an out-of-band token; this package never ships credentials.
- Relation remap on staging Knowledge/Canonical rows is an owner concern; preflight does not rewrite relations.
- Ranking is deterministic rule baseline, not a trained model.
- Signed URLs are `sim://` tokens.
- Capabilities `service` uses frozen enum value `content-workflow` (shared schema does not list a vendor-4-specific service name). Contract file is not modified.
- Docker image build is NOT_RUN in this remediation environment unless an operator runs it.
- Durable pending blobs live under V4_DATA_DIR (default `./var/uploads`) with atomic write; operators must point the directory at persistent disk.
