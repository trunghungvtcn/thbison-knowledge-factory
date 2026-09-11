import { mkdirSync, readFileSync, writeFileSync, existsSync, renameSync } from "node:fs";
import { dirname } from "node:path";
import { digest, payloadHash } from "./hash.ts";
import { ledgerPath } from "./config.ts";

export type JobStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | "BLOCKED_INPUT"
  | "NO_CHANGE"
  | "BUDGET_EXHAUSTED"
  | "TIMED_OUT";

export type ArtifactRef = {
  artifact_id: string;
  sha256: string;
  bytes: number;
  media_type: string;
};

export type JobRecord = {
  job_id: string;
  project_id: string;
  data_class: "TEST_ONLY" | "STAGING" | "PRODUCTION";
  request_id: string;
  operation: string;
  status: JobStatus;
  error_code: string | null;
  payload: unknown;
  idempotency_key: string;
  payload_hash: string;
  result_artifact: ArtifactRef | null;
  output?: unknown;
  brief_id?: string;
  created_at: string;
  updated_at: string;
  cancel_requested: boolean;
  provider_calls: number;
  reserved_requests: number;
  reserved_tokens: number;
  reserved_cost_usd: string;
  first_request_id: string;
};

export type BriefRecord = {
  brief: Record<string, unknown>;
  project_id: string;
};

export type LedgerState = {
  jobs: Record<string, JobRecord>;
  idempotency: Record<string, string>;
  briefs: Record<string, BriefRecord>;
  artifacts: Record<string, { bytes: number; sha256: string; media_type: string; pathSafe: string }>;
  counters: {
    provider_calls: number;
    publish_calls: number;
    admissions: number;
    cache_hits: number;
    cache_misses: number;
    policy_overwrites: number;
    secret_leaks: number;
    executed_untrusted_urls: number;
  };
  cache: Record<
    string,
    {
      captured_at: string;
      provider_calls: number;
      keywords: unknown;
      serp: unknown;
      snapshot: ArtifactRef;
    }
  >;
  reservations: Record<string, { requests: number; tokens: number; cost: number; charged_unknown: number }>;
};

const empty = (): LedgerState => ({
  jobs: {},
  idempotency: {},
  briefs: {},
  artifacts: {},
  counters: {
    provider_calls: 0,
    publish_calls: 0,
    admissions: 0,
    cache_hits: 0,
    cache_misses: 0,
    policy_overwrites: 0,
    secret_leaks: 0,
    executed_untrusted_urls: 0,
  },
  cache: {},
  reservations: {},
});

let mem: LedgerState | null = null;
let chain: Promise<void> = Promise.resolve();

function persistPath(): string {
  return ledgerPath();
}

export function loadLedger(): LedgerState {
  if (mem) return mem;
  const p = persistPath();
  try {
    if (existsSync(p)) {
      mem = JSON.parse(readFileSync(p, "utf8")) as LedgerState;
      mem.counters ??= empty().counters;
      mem.cache ??= {};
      mem.reservations ??= {};
      mem.artifacts ??= {};
      return mem;
    }
  } catch {
    /* corrupt -> empty, truthful */
  }
  mem = empty();
  return mem;
}

function flush(state: LedgerState): void {
  const p = persistPath();
  mkdirSync(dirname(p), { recursive: true });
  const tmp = p + ".tmp";
  writeFileSync(tmp, JSON.stringify(state));
  renameSync(tmp, p);
}

export function withLedger<T>(fn: (s: LedgerState) => T): Promise<T> {
  const run = chain.then(() => {
    const s = loadLedger();
    const result = fn(s);
    flush(s);
    return result;
  });
  chain = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

export function idemKey(project: string, op: string, key: string): string {
  return `${project}|${op}|${key}`;
}

export function hashPayload(payload: unknown): string {
  return payloadHash(payload);
}

export function bump(s: LedgerState, k: keyof LedgerState["counters"], n = 1): void {
  s.counters[k] += n;
}

export function resetMemoryForTests(): void {
  mem = empty();
  flush(mem);
}

export function digestState(s: LedgerState): string {
  return digest({ jobs: Object.keys(s.jobs).length, counters: s.counters });
}
