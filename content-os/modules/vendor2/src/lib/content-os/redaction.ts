const SECRET = /(bearer\s+[a-z0-9._\-]+|sk-[a-z0-9]+|token=[^\s&]+|X-Amz-Signature=[^&\s]+|https?:\/\/[^\s]+[?&](X-Amz-|signature=)[^\s]+)/gi;

export function redact(text: string): string {
  return text.replace(SECRET, "[REDACTED]");
}

export function redactValue(value: unknown): unknown {
  if (typeof value === "string") return redact(value);
  if (Array.isArray(value)) return value.map(redactValue);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      if (/token|secret|password|authorization|signed/i.test(k)) out[k] = "[REDACTED]";
      else out[k] = redactValue(v);
    }
    return out;
  }
  return value;
}

export function safeLog(event: string, detail: unknown): void {
  const payload = JSON.stringify(redactValue(detail));
  if (/bearer\s|sk-|X-Amz-Signature/i.test(payload)) {
    console.info(event, "[blocked-secret]");
    return;
  }
  console.info(event, payload.slice(0, 2000));
}
