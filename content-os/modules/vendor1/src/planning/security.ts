import { loadServiceTokens, type ServiceIdentity } from "./config.ts";
import { ApiError } from "./errors.ts";
import { isId } from "./hash.ts";

const tokens = () => loadServiceTokens();

export function requestIdFrom(req: Request, body?: { request_id?: string }): string {
  const h = req.headers.get("x-request-id");
  if (h && isId(h)) return h;
  if (body?.request_id && isId(body.request_id)) return body.request_id;
  return "req-missing-00000001";
}

export function authorize(req: Request, requestId: string): ServiceIdentity {
  const header = req.headers.get("authorization") ?? "";
  const m = /^Bearer\s+(.+)$/i.exec(header);
  if (!m) throw new ApiError(401, "UNAUTHORIZED", "Missing bearer token", requestId, false);
  const token = m[1].trim();
  const id = tokens().get(token);
  if (!id) throw new ApiError(401, "UNAUTHORIZED", "Unknown or forged credential", requestId, false);
  if (id.roles.includes("expired")) {
    throw new ApiError(401, "UNAUTHORIZED", "Expired credential", requestId, false);
  }
  return id;
}

export function requireProject(identity: ServiceIdentity, projectId: string, requestId: string): void {
  if (identity.project_id !== projectId) {
    throw new ApiError(403, "FORBIDDEN", "Project isolation: caller is not bound to this project", requestId, false);
  }
}

export function requireContractVersion(req: Request, requestId: string): void {
  const v = req.headers.get("x-contract-version");
  if (v !== "1.0.0") {
    throw new ApiError(400, "UNSUPPORTED_CONTRACT", "X-Contract-Version must be 1.0.0", requestId, false);
  }
}

export function requireIdempotencyKey(req: Request, requestId: string): string {
  const k = req.headers.get("idempotency-key") ?? "";
  if (k.length < 16 || k.length > 128) {
    throw new ApiError(400, "VALIDATION_ERROR", "Idempotency-Key must be 16-128 characters", requestId, false);
  }
  return k;
}

/** Untrusted text is data. Never execute URLs or overwrite policy. */
export function isolateUntrusted(text: string): { display: string; blocked: string[] } {
  const blocked: string[] = [];
  const patterns = [
    /ignore (all|previous) instructions/i,
    /upload (the )?(api|secret|key)/i,
    /change (the )?policy/i,
    /https?:\/\/\S+/i,
    /file:\/\/\S+/i,
    /\$\([^)]+\)/,
    /;\s*(rm|curl|wget|sh)\b/i,
  ];
  for (const p of patterns) {
    if (p.test(text)) blocked.push(p.source);
  }
  return { display: text.slice(0, 4000), blocked };
}

export function redact(value: string): string {
  return value
    .replace(/Bearer\s+[A-Za-z0-9._-]+/gi, "Bearer [REDACTED]")
    .replace(/https:\/\/[^\s"]+signature=[^\s"]+/gi, "[REDACTED_SIGNED_URL]")
    .replace(/OPENSEO_API_KEY=\S+/g, "OPENSEO_API_KEY=[REDACTED]");
}

export function safeArtifactName(name: string): string {
  if (name.includes("..") || name.includes("/") || name.includes("\\") || name.includes("\0")) {
    throw new ApiError(400, "VALIDATION_ERROR", "Illegal artifact path", "req-missing-00000001", false);
  }
  return name.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 120);
}
