import { createHash } from "node:crypto";
import { ContractError } from "./errors";
import { ALLOWED_DESTINATIONS } from "./constants";

export type CmsDraft = {
  provider_record_id: string;
  destination_id: string;
  article_id: string;
  article_revision: number;
  content_sha256: string;
  body: string;
};

const records = new Map<string, CmsDraft>();
let createCalls = 0;
let sideEffects = 0;

export type CmsFault = "none" | "timeout-after-accept" | "unavailable";

let fault: CmsFault = "none";

export function setCmsFault(next: CmsFault): void {
  fault = next;
}

export function cmsCounters() {
  return { createCalls, sideEffects, size: records.size };
}

export function resetCms(): void {
  records.clear();
  createCalls = 0;
  sideEffects = 0;
  fault = "none";
}

function logicalKey(
  projectId: string,
  destinationId: string,
  articleId: string,
  revision: number,
  hash: string,
): string {
  return `${projectId}|${destinationId}|${articleId}|${revision}|${hash}`;
}

function recordId(key: string): string {
  return "cms-" + createHash("sha256").update(key).digest("hex").slice(0, 20);
}

export async function cmsCreateDraft(input: {
  projectId: string;
  destinationId: string;
  articleId: string;
  articleRevision: number;
  contentSha256: string;
  body: string;
}): Promise<CmsDraft> {
  if (!ALLOWED_DESTINATIONS.has(input.destinationId)) {
    throw new ContractError("FORBIDDEN", "Destination not allowlisted");
  }
  createCalls += 1;
  const key = logicalKey(
    input.projectId,
    input.destinationId,
    input.articleId,
    input.articleRevision,
    input.contentSha256,
  );
  const existing = records.get(key);
  if (existing) return existing;
  if (fault === "unavailable") {
    throw new ContractError("PROVIDER_ERROR", "CMS unavailable", true);
  }
  const draft: CmsDraft = {
    provider_record_id: recordId(key),
    destination_id: input.destinationId,
    article_id: input.articleId,
    article_revision: input.articleRevision,
    content_sha256: input.contentSha256,
    body: input.body,
  };
  records.set(key, draft);
  sideEffects += 1;
  if (fault === "timeout-after-accept") {
    throw new ContractError("TIMEOUT", "CMS accepted then response lost", true);
  }
  return draft;
}

export function cmsRead(providerRecordId: string): CmsDraft | null {
  for (const d of records.values()) {
    if (d.provider_record_id === providerRecordId) return d;
  }
  return null;
}

export function cmsFind(input: {
  projectId: string;
  destinationId: string;
  articleId: string;
  articleRevision: number;
  contentSha256: string;
}): CmsDraft | null {
  return (
    records.get(
      logicalKey(
        input.projectId,
        input.destinationId,
        input.articleId,
        input.articleRevision,
        input.contentSha256,
      ),
    ) ?? null
  );
}
