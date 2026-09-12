import { getSql } from "@/lib/db";
import { notionRecordEligible, NOTION_DATA_SOURCES } from "./notion-policy";
export { NOTION_DATA_SOURCES } from "./notion-policy";

export type NotionSourceKind = keyof typeof NOTION_DATA_SOURCES;
export type NotionSnapshotRow = {
  dataSourceId: string;
  recordId: string;
  name: string;
  status: string | null;
  decision: string | null;
  sourceUrl: string | null;
  eligible: boolean;
  scope: string | null;
};
export type NotionSnapshotView = {
  available: boolean;
  snapshotSha256: string | null;
  capturedAt: string | null;
  importedAt: string | null;
  counts: Record<NotionSourceKind, number>;
  rows: NotionSnapshotRow[];
};

export async function latestNotionSnapshot(): Promise<NotionSnapshotView> {
  const sql = await getSql();
  const snapshots = await sql<{
    snapshot_sha256: string;
    captured_at: string;
    imported_at: string;
    collection_counts_json: string;
  }>`select snapshot_sha256, captured_at::text, imported_at::text, collection_counts_json
     from cos_notion_snapshots where project_id = ${"test-thbison"}
     order by captured_at desc, imported_at desc limit 1`;
  const snapshot = snapshots[0];
  if (!snapshot) return {
    available: false, snapshotSha256: null, capturedAt: null, importedAt: null,
    counts: { evidence: 0, products: 0, knowledge: 0 }, rows: [],
  };
  const records = await sql<{
    data_source_id: string; record_id: string; record_name: string;
    status: string | null; decision: string | null; source_url: string | null; body_json: string;
  }>`select data_source_id, record_id, record_name, status, decision, source_url, body_json
     from cos_notion_snapshot_rows where snapshot_sha256 = ${snapshot.snapshot_sha256}
     order by data_source_id, record_name, record_id`;
  const rows = records.map((row) => {
    const body = JSON.parse(row.body_json) as Record<string, unknown>;
    const scopeValue = body["Applicability Scope"] ?? body["Product Family"] ?? body["Model"];
    const view: NotionSnapshotRow = {
      dataSourceId: row.data_source_id, recordId: row.record_id, name: row.record_name,
      status: row.status, decision: row.decision, sourceUrl: row.source_url,
      eligible: false, scope: typeof scopeValue === "string" ? scopeValue : null,
    };
    view.eligible = notionRecordEligible(view.dataSourceId, view.status, view.decision);
    return view;
  });
  return {
    available: true, snapshotSha256: snapshot.snapshot_sha256,
    capturedAt: snapshot.captured_at, importedAt: snapshot.imported_at,
    counts: JSON.parse(snapshot.collection_counts_json) as Record<NotionSourceKind, number>, rows,
  };
}
