import { createHash } from "node:crypto";

/** Python json.dumps(ensure_ascii=True, sort_keys=True, separators=(',',':'), allow_nan=False). */
export function canonicalJson(value: unknown): string {
  return asciiEscape(JSON.stringify(sortKeys(value)));
}

function sortKeys(value: unknown): unknown {
  if (value === null || typeof value !== "object") {
    if (typeof value === "number" && !Number.isFinite(value)) {
      throw new Error("allow_nan=False");
    }
    return value;
  }
  if (Array.isArray(value)) return value.map(sortKeys);
  const obj = value as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(obj).sort()) {
    out[key] = sortKeys(obj[key]);
  }
  return out;
}

function asciiEscape(json: string): string {
  return json.replace(/[\u007f-\uffff]/g, (ch) => {
    const code = ch.charCodeAt(0);
    return "\\u" + code.toString(16).padStart(4, "0");
  });
}

export function canonicalBytes(value: unknown): Buffer {
  return Buffer.from(canonicalJson(value), "utf8");
}

export function digest(value: unknown): string {
  return createHash("sha256").update(canonicalBytes(value)).digest("hex");
}

export function hashWithout(value: Record<string, unknown>, field: string): string {
  const copy: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    if (k !== field) copy[k] = v;
  }
  return digest(copy);
}

export function sha256Utf8(text: string): string {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

export function sha1Utf8(text: string): string {
  return createHash("sha1").update(text, "utf8").digest("hex");
}

export function newId(prefix: string): string {
  const n = createHash("sha256")
    .update(`${prefix}:${Date.now()}:${Math.random()}:${process.hrtime.bigint()}`)
    .digest("hex")
    .slice(0, 16);
  return `${prefix}${n}`;
}
