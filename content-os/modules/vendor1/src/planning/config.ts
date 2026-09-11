import { createHash } from "node:crypto";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

export const CONTRACT_VERSION = "1.0.0" as const;
export const CONTRACT_SHA256 =
  "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8";
export const MAX_JSON_BYTES = 2_097_152;
export const SERVICE_NAME = "seo-planning" as const;

export const UPSTREAM = {
  project: "every-app/open-seo",
  commit: "3632f408528cd588fec98c3a174af8ea0ad205e8",
  commitDate: "2026-09-03T15:54:34Z",
  license: "MIT",
  copyright: "Copyright (c) 2026 Ben Senescu",
  mcpUrl: "https://app.openseo.so/mcp",
  hostedDocs: "https://openseo.so/docs/mcp",
  notice:
    "OpenSEO is MIT-licensed. This module is an adapter around MCP tools, not a fork of the OpenSEO application or its keyword/SERP engine.",
  /** Discovered 2026-09-10 from openseo.so/features/mcp and docs/mcp — not remembered tool names. */
  discoveredTools: [
    "research_keywords",
    "get_serp_results",
    "save_keywords",
    "get_rank_tracker_data",
    "get_domain_overview",
    "get_domain_keywords",
    "get_backlinks_overview",
    "get_gsc_performance",
    "inspect_urls",
    "get_project_context",
    "list_projects",
    "update_project_context",
    "create_project",
  ] as const,
  usedTools: ["research_keywords", "get_serp_results"] as const,
  costNotes:
    "Self-hosted OpenSEO uses DataForSEO pay-as-you-go. Hosted OpenSEO is $10/month plus provider usage. This adapter never issues paid calls unless OPENSEO_API_KEY is set and THBISON_MODE is STAGING or LIVE.",
};

function workspaceRoot(): string {
  return process.env.THBISON_ROOT ?? process.cwd();
}

export function dataDir(): string {
  return process.env.THBISON_DATA_DIR ?? resolve(workspaceRoot(), "data");
}

export function ledgerPath(): string {
  return resolve(dataDir(), "ledger.json");
}

export type ServiceIdentity = {
  project_id: string;
  roles: string[];
  token_id: string;
};

export type AppMode = "MOCK" | "STAGING" | "LIVE";

export function appMode(): AppMode {
  const m = (process.env.THBISON_MODE ?? "MOCK").toUpperCase();
  if (m === "STAGING" || m === "LIVE") return m;
  return "MOCK";
}

export function liveProviderEnabled(): boolean {
  return Boolean(process.env.OPENSEO_API_KEY) && appMode() !== "MOCK";
}

export function loadServiceTokens(): Map<string, ServiceIdentity> {
  const map = new Map<string, ServiceIdentity>();
  const raw = process.env.THBISON_SERVICE_TOKENS;
  if (raw) {
    const parsed = JSON.parse(raw) as Record<
      string,
      { project_id: string; roles?: string[] }
    >;
    for (const [token, v] of Object.entries(parsed)) {
      map.set(token, {
        project_id: v.project_id,
        roles: v.roles ?? ["planning"],
        token_id: token.slice(0, 12),
      });
    }
  }
  if (!map.size) {
    const idPath = resolve(workspaceRoot(), "simulate/identities.json");
    if (existsSync(idPath)) {
      const file = JSON.parse(readFileSync(idPath, "utf8")) as {
        tokens: Record<string, { project_id: string; roles?: string[] }>;
      };
      for (const [token, v] of Object.entries(file.tokens)) {
        map.set(token, {
          project_id: v.project_id,
          roles: v.roles ?? ["planning"],
          token_id: token.slice(0, 12),
        });
      }
    }
  }
  return map;
}

let cachedCommit: string | null = null;
export function codeCommit(): string {
  if (cachedCommit) return cachedCommit;
  const env = process.env.THBISON_CODE_COMMIT ?? "";
  if (/^[a-f0-9]{40,64}$/.test(env)) {
    cachedCommit = env;
    return cachedCommit;
  }
  const rev = resolve(workspaceRoot(), "delivery/SOURCE_REVISION");
  if (existsSync(rev)) {
    cachedCommit = readFileSync(rev, "utf8").trim().split(/\s+/)[0] ?? "";
    if (/^[a-f0-9]{40,64}$/.test(cachedCommit)) return cachedCommit;
  }
  const files = [
    "src/planning/config.ts",
    "src/planning/http.ts",
    "src/planning/planner.ts",
    "src/planning/provider.ts",
    "src/planning/ledger.ts",
    "src/planning/validate.ts",
    "src/planning/jobs.ts",
  ];
  const h = createHash("sha256");
  for (const f of files) {
    const p = resolve(workspaceRoot(), f);
    if (existsSync(p)) h.update(readFileSync(p));
  }
  cachedCommit = h.digest("hex");
  return cachedCommit;
}

export function nowIso(): string {
  if (process.env.THBISON_CLOCK_NOW) return process.env.THBISON_CLOCK_NOW;
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

export function freshnessMs(): number {
  const n = Number(process.env.THBISON_FRESHNESS_MS ?? 30 * 24 * 3600 * 1000);
  return Number.isFinite(n) ? n : 30 * 24 * 3600 * 1000;
}

export function providerRevision(): string {
  return process.env.THBISON_PROVIDER_REVISION ?? `openseo-${UPSTREAM.commit.slice(0, 12)}`;
}
