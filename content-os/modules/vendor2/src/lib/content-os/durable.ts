import { mkdir, writeFile, readFile } from "node:fs/promises";
import path from "node:path";
import { getSql } from "@/lib/db";

const TABLES = [
  "cos_idempotency",
  "cos_jobs",
  "cos_briefs",
  "cos_evidence",
  "cos_articles",
  "cos_approvals",
  "cos_publications",
  "cos_cms_records",
  "cos_artifacts",
  "cos_outbox",
  "cos_provider_calls",
  "cos_audit",
  "cos_budget",
  "cos_clock",
  "cos_brief_cache",
] as const;

function coerce(v: unknown): unknown {
  if (v instanceof Date) return v.toISOString();
  if (typeof v === "bigint") return Number(v);
  return v;
}

export function durableDir(): string {
  return process.env.CONTENT_OS_DURABLE_DIR || "/tmp/thbison-ledger";
}

export type LedgerSnapshot = {
  saved_at: string;
  tables: Record<string, unknown[]>;
};

export async function exportSnapshot(): Promise<LedgerSnapshot> {
  const sql = await getSql();
  const tables: Record<string, unknown[]> = {};
  for (const t of TABLES) {
    tables[t] = await sql.query(`select * from ${t}`);
  }
  const snap: LedgerSnapshot = { saved_at: new Date().toISOString(), tables };
  await mkdir(durableDir(), { recursive: true });
  await writeFile(path.join(durableDir(), "snapshot.json"), JSON.stringify(snap), "utf8");
  return snap;
}

export async function importSnapshot(snap?: LedgerSnapshot): Promise<void> {
  const data =
    snap ??
    (JSON.parse(await readFile(path.join(durableDir(), "snapshot.json"), "utf8")) as LedgerSnapshot);
  const sql = await getSql();
  for (const t of [...TABLES].reverse()) {
    await sql.query(`delete from ${t}`);
  }
  for (const t of TABLES) {
    const rows = data.tables[t] ?? [];
    for (const row of rows) {
      const rec = row as Record<string, unknown>;
      const cols = Object.keys(rec);
      if (!cols.length) continue;
      const placeholders = cols.map((_, i) => `$${i + 1}`).join(", ");
      const values = cols.map((c) => coerce(rec[c]));
      await sql.query(
        `insert into ${t} (${cols.join(", ")}) values (${placeholders})`,
        values,
      );
    }
  }
}

/** Simulated process restart: persist → wipe in-memory tables → reload from disk. No THBISON DB. */
export async function simulateRestart(): Promise<{ jobs: number; approvals: number; publications: number }> {
  await exportSnapshot();
  await importSnapshot();
  const sql = await getSql();
  const jobs = await sql.query<{ n: number }>("select count(*)::int as n from cos_jobs");
  const appr = await sql.query<{ n: number }>("select count(*)::int as n from cos_approvals");
  const pubs = await sql.query<{ n: number }>("select count(*)::int as n from cos_publications");
  return { jobs: jobs[0]?.n ?? 0, approvals: appr[0]?.n ?? 0, publications: pubs[0]?.n ?? 0 };
}

export async function persistLedger(): Promise<void> {
  try {
    await exportSnapshot();
  } catch (err) {
    console.error("durable.persist", err);
  }
}
