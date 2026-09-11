import { appMode, codeCommit, CONTRACT_SHA256, CONTRACT_VERSION, liveProviderEnabled, MAX_JSON_BYTES, SERVICE_NAME, UPSTREAM } from "./config.ts";
import { ApiError, jsonResponse } from "./errors.ts";
import {
  admitPlanningJob,
  cancelJob,
  getBrief,
  getJob,
  getOutput,
  listJobsForProject,
  reviseBriefPublishAt,
} from "./jobs.ts";
import { loadLedger } from "./ledger.ts";
import { authorize, redact, requestIdFrom, requireContractVersion, requireIdempotencyKey, requireProject } from "./security.ts";
import { assertAwareInstant, assertAwareInstantOrNull, validateResearchRequest } from "./validate.ts";

function vendor2Forbidden(rid: string): never {
  throw new ApiError(
    403,
    "FORBIDDEN",
    "This service is seo-planning (Vendor 1). Content, approval and publication routes belong to Vendor 2.",
    rid,
    false,
  );
}

async function readJson(req: Request, rid: string): Promise<unknown> {
  const cl = Number(req.headers.get("content-length") ?? "0");
  if (cl > MAX_JSON_BYTES) throw new ApiError(400, "VALIDATION_ERROR", "JSON too large", rid, false);
  const text = await req.text();
  if (Buffer.byteLength(text) > MAX_JSON_BYTES) {
    throw new ApiError(400, "VALIDATION_ERROR", "JSON too large", rid, false);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new ApiError(400, "VALIDATION_ERROR", "Malformed JSON", rid, false);
  }
}

export async function handlePlanningHttp(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  let rid = requestIdFrom(req);
  try {
    if (req.method === "GET" && (path === "/healthz" || path === "/healthz/")) {
      return jsonResponse(200, { status: "ok" });
    }

    if (req.method === "GET" && path === "/v1/capabilities") {
      const id = authorize(req, rid);
      void id;
      return jsonResponse(200, {
        contract_version: CONTRACT_VERSION,
        service: SERVICE_NAME,
        code_commit: codeCommit(),
        contract_sha256: CONTRACT_SHA256,
        mode: appMode() === "LIVE" && liveProviderEnabled() ? "LIVE" : appMode() === "STAGING" && liveProviderEnabled() ? "STAGING" : "MOCK",
        enabled_operations: ["planning.create", "brief.read"],
        max_json_bytes: MAX_JSON_BYTES,
      });
    }

    if (path.startsWith("/v1/content") || path.startsWith("/v1/articles") || path.startsWith("/v1/publications")) {
      rid = requestIdFrom(req);
      authorize(req, rid);
      requireContractVersion(req, rid);
      vendor2Forbidden(rid);
    }

    if (req.method === "POST" && path === "/v1/planning/jobs") {
      requireContractVersion(req, rid);
      const body = await readJson(req, rid);
      const parsed = validateResearchRequest(body, rid);
      rid = parsed.request_id;
      const identity = authorize(req, rid);
      requireProject(identity, parsed.project_id, rid);
      const idem = requireIdempotencyKey(req, rid);
      const proposed = req.headers.get("x-thbison-proposed-publish-at");
      if (proposed) assertAwareInstant(proposed, rid, "proposed_publish_at");
      const { receipt } = await admitPlanningJob(parsed, idem, proposed);
      return jsonResponse(202, receipt);
    }

    const jobM = /^\/v1\/planning\/jobs\/([^/]+)$/.exec(path);
    if (req.method === "GET" && jobM) {
      requireContractVersion(req, rid);
      const identity = authorize(req, rid);
      rid = requestIdFrom(req);
      return jsonResponse(200, await getJob(identity.project_id, jobM[1], rid));
    }

    const cancelM = /^\/v1\/planning\/jobs\/([^/]+)\/cancel$/.exec(path);
    if (req.method === "POST" && cancelM) {
      requireContractVersion(req, rid);
      const identity = authorize(req, rid);
      const idem = requireIdempotencyKey(req, rid);
      return jsonResponse(200, await cancelJob(identity.project_id, cancelM[1], rid, idem));
    }

    const outM = /^\/v1\/planning\/jobs\/([^/]+)\/output$/.exec(path);
    if (req.method === "GET" && outM) {
      requireContractVersion(req, rid);
      const identity = authorize(req, rid);
      const out = await getOutput(identity.project_id, outM[1], rid);
      return jsonResponse(200, out);
    }

    const briefM = /^\/v1\/briefs\/([^/]+)$/.exec(path);
    if (req.method === "GET" && briefM) {
      requireContractVersion(req, rid);
      const identity = authorize(req, rid);
      const expected = url.searchParams.get("expected_revision");
      const brief = await getBrief(identity.project_id, briefM[1], rid);
      if (expected && String(brief.brief_revision) !== expected) {
        throw new ApiError(409, "STALE_REVISION", "Cached brief revision is stale", rid, false);
      }
      return jsonResponse(200, brief);
    }

    if (req.method === "POST" && briefM) {
      requireContractVersion(req, rid);
      const identity = authorize(req, rid);
      const idem = requireIdempotencyKey(req, rid);
      void idem;
      const body = (await readJson(req, rid)) as { brief_revision?: number; proposed_publish_at?: string | null };
      if (!body || typeof body.brief_revision !== "number") {
        throw new ApiError(400, "VALIDATION_ERROR", "brief_revision required for optimistic edit", rid, false);
      }
      const proposedAt = assertAwareInstantOrNull(body.proposed_publish_at ?? null, rid, "proposed_publish_at");
      const next = await reviseBriefPublishAt(
        identity.project_id,
        briefM[1],
        body.brief_revision,
        proposedAt,
        rid,
      );
      return jsonResponse(200, next);
    }

    if (req.method === "GET" && path === "/v1/planning/jobs") {
      requireContractVersion(req, rid);
      const identity = authorize(req, rid);
      return jsonResponse(200, { jobs: await listJobsForProject(identity.project_id) });
    }

    if (path === "/v1/meta/upstream") {
      authorize(req, rid);
      return jsonResponse(200, { ...UPSTREAM, live_enabled: liveProviderEnabled() });
    }

    if (path === "/v1/meta/counters") {
      const identity = authorize(req, rid);
      void identity;
      const s = loadLedger();
      return jsonResponse(200, { counters: s.counters });
    }

    return jsonResponse(400, {
      contract_version: CONTRACT_VERSION,
      request_id: rid,
      code: "VALIDATION_ERROR",
      message: `Unknown route ${req.method} ${path}`,
      retryable: false,
    });
  } catch (e) {
    if (e instanceof ApiError) {
      return jsonResponse(e.http, e.body());
    }
    const msg = redact(e instanceof Error ? e.message : "internal");
    return jsonResponse(503, {
      contract_version: CONTRACT_VERSION,
      request_id: rid,
      code: "PROVIDER_ERROR",
      message: msg,
      retryable: true,
    });
  }
}
