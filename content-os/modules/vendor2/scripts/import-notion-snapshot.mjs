import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import process from "node:process";
import pg from "pg";

const ALLOWLIST = new Map([
  ["87318868-8be2-4e27-8ab6-7a3d0b53bb32", "evidence"],
  ["a4812f47-e1a6-4aa1-a619-558a79a4c4ff", "products"],
  ["9d53865d-0cdd-41f3-a6c6-5d171b4e50f4", "knowledge"],
]);

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function requireText(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string`);
  return value.trim();
}

function validate(input) {
  if (!input || input.schema_version !== "1.0.0" || !Array.isArray(input.collections)) throw new Error("invalid snapshot envelope");
  requireText(input.captured_at, "captured_at");
  if (input.collections.length !== ALLOWLIST.size) throw new Error("snapshot must contain exactly three allowlisted collections");
  const seen = new Set();
  for (const collection of input.collections) {
    const id = requireText(collection.data_source_id, "data_source_id").replace(/^collection:\/\//, "");
    if (!ALLOWLIST.has(id) || seen.has(id)) throw new Error(`data source is missing, duplicated, or not allowlisted: ${id}`);
    seen.add(id);
    if (!Array.isArray(collection.rows)) throw new Error(`rows missing for ${id}`);
    const recordIds = new Set();
    for (const row of collection.rows) {
      const recordId = requireText(row.record_id, "record_id");
      if (recordIds.has(recordId)) throw new Error(`duplicate record_id in ${id}: ${recordId}`);
      recordIds.add(recordId);
      requireText(row.name, "name");
      if (!row.properties || typeof row.properties !== "object" || Array.isArray(row.properties)) throw new Error(`invalid properties for ${recordId}`);
    }
    collection.data_source_id = id;
  }
  return input;
}

const file = process.argv[2];
if (!file) throw new Error("usage: npm run notion:snapshot:import -- /absolute/path/snapshot.json");
const databaseUrl = process.env.DATABASE_URL?.trim();
if (!databaseUrl) throw new Error("DATABASE_URL is required; refusing embedded fallback");
const input = validate(JSON.parse(await readFile(file, "utf8")));
const snapshotSha256 = createHash("sha256").update(canonical(input)).digest("hex");
const client = new pg.Client({ connectionString: databaseUrl });
await client.connect();
try {
  await client.query("begin");
  const counts = Object.fromEntries(input.collections.map((c) => [ALLOWLIST.get(c.data_source_id), c.rows.length]));
  await client.query(
    `insert into cos_notion_snapshots (snapshot_sha256, project_id, captured_at, collection_counts_json)
     values ($1, $2, $3, $4) on conflict (snapshot_sha256) do nothing`,
    [snapshotSha256, "test-thbison", input.captured_at, JSON.stringify(counts)],
  );
  for (const collection of input.collections) {
    for (const row of collection.rows) {
      await client.query(
        `insert into cos_notion_snapshot_rows
          (snapshot_sha256, data_source_id, record_id, record_name, status, decision, source_url, body_json)
         values ($1,$2,$3,$4,$5,$6,$7,$8)
         on conflict (snapshot_sha256, data_source_id, record_id) do nothing`,
        [snapshotSha256, collection.data_source_id, row.record_id, row.name,
          row.properties.Status ?? null, row.properties.Decision ?? null,
          row.properties["Source URL"] ?? null, JSON.stringify(row.properties)],
      );
    }
  }
  await client.query("commit");
  process.stdout.write(`${JSON.stringify({ status: "IMPORTED", snapshot_sha256: snapshotSha256, counts })}\n`);
} catch (error) {
  await client.query("rollback");
  throw error;
} finally {
  await client.end();
}
