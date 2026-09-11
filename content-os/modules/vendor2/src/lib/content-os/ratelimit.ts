import { ContractError } from "./errors";

const hits = new Map<string, { n: number; t: number }>();

export function rateLimit(principalId: string, limitOverride?: number): void {
  const limit = limitOverride ?? Number(process.env.CONTENT_OS_RATE_LIMIT ?? 200);
  const now = Date.now();
  const w = hits.get(principalId) ?? { n: 0, t: now };
  if (now - w.t > 60_000) {
    w.n = 0;
    w.t = now;
  }
  w.n += 1;
  hits.set(principalId, w);
  if (w.n > limit) {
    throw new ContractError("RATE_LIMITED", "Retry after 60 seconds", true);
  }
}

export function resetRateLimit(): void {
  hits.clear();
}
