import { ERROR_STATUS } from "./constants";
import { ContractError, isRetryableCode, publicErrorCode } from "./errors";
import { resolveBearer } from "./authz";
import type { Principal } from "./types";
import { freezeClock } from "./clock";
import { rateLimit } from "./ratelimit";
import { redact } from "./redaction";
import { validateHeaderContract } from "./validate";

export function json(data: unknown, status = 200, extra?: HeadersInit): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...extra,
    },
  });
}

export function errorBody(requestId: string, err: unknown): Response {
  const c = err instanceof ContractError ? err : new ContractError("VALIDATION_ERROR", String(err));
  const code = publicErrorCode(c.code);
  const status = ERROR_STATUS[code] ?? 400;
  const extra = status === 429 ? { "retry-after": "60" } : undefined;
  return json(
    {
      contract_version: "1.0.0",
      request_id: requestId,
      code,
      message: redact(c.message).slice(0, 4000),
      retryable: c.retryable || isRetryableCode(code),
    },
    status,
    extra,
  );
}

export function readContractVersion(request: Request): string | null {
  return request.headers.get("x-contract-version") ?? request.headers.get("X-Contract-Version");
}

export function readIdempotency(request: Request): string {
  const key = request.headers.get("idempotency-key") ?? request.headers.get("Idempotency-Key") ?? "";
  if (key.length < 16 || key.length > 128) throw new ContractError("VALIDATION_ERROR", "Idempotency-Key");
  return key;
}

export function authPrincipal(request: Request): Principal {
  const p = resolveBearer(request.headers.get("authorization"));
  const forced = request.headers.get("x-test-rate-limit");
  const testNow = request.headers.get("x-test-now");
  if (testNow) freezeClock(testNow);
  rateLimit(p.principal_id, forced ? Number(forced) : undefined);
  return p;
}

export function requireContract(request: Request): void {
  validateHeaderContract(readContractVersion(request));
}

export async function readJsonLimited(request: Request, max = 2_097_152): Promise<unknown> {
  const text = await request.text();
  if (Buffer.byteLength(text, "utf8") > max) throw new ContractError("VALIDATION_ERROR", "payload too large");
  if (!text) throw new ContractError("VALIDATION_ERROR", "empty body");
  try {
    return JSON.parse(text);
  } catch {
    throw new ContractError("VALIDATION_ERROR", "invalid json");
  }
}

export function requestIdOf(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "request_id" in body && typeof (body as { request_id: unknown }).request_id === "string") {
    return (body as { request_id: string }).request_id;
  }
  return fallback;
}
