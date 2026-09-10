import { createHash } from "node:crypto";

export function sha256Hex(data: string | Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

/** Compact sorted JSON, ensure_ascii-equivalent via JSON.stringify (ASCII keys). */
export function canonicalBytes(value: unknown): Buffer {
  return Buffer.from(JSON.stringify(sortValue(value)), "utf8");
}

export function digest(value: unknown): string {
  return sha256Hex(stableStringify(value));
}

export function stableStringify(value: unknown): string {
  return JSON.stringify(sortValue(value));
}

function sortValue(value: unknown): unknown {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(sortValue);
  const obj = value as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const k of Object.keys(obj).sort()) out[k] = sortValue(obj[k]);
  return out;
}

export function digestWithout(obj: Record<string, unknown>, field: string): string {
  const copy = { ...obj };
  delete copy[field];
  return digest(copy);
}

export function payloadHash(value: unknown): string {
  return digest(value);
}

export function hasSurrogates(value: unknown): boolean {
  if (typeof value === "string") {
    for (const c of value) {
      const code = c.codePointAt(0) ?? 0;
      if (code >= 0xd800 && code <= 0xdfff) return true;
    }
    return false;
  }
  if (Array.isArray(value)) return value.some(hasSurrogates);
  if (value && typeof value === "object") {
    return Object.entries(value as object).some(([k, v]) => hasSurrogates(k) || hasSurrogates(v));
  }
  return false;
}

const ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
export function isId(s: string): boolean {
  return ID_RE.test(s);
}

export function idFrom(prefix: string, parts: string[]): string {
  const hex = sha256Hex(parts.join("|")).slice(0, 20);
  const id = `${prefix}-${hex}`;
  if (!isId(id)) throw new Error("bad id");
  return id;
}
