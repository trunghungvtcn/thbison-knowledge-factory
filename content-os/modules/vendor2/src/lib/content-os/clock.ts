let frozen: Date | null = null;

export function freezeClock(iso: string | null): void {
  frozen = iso ? instant(iso) : null;
}

export function now(): Date {
  return frozen ? new Date(frozen.getTime()) : new Date();
}

export function nowIso(): string {
  return now().toISOString().replace(/\.\d{3}Z$/, "Z");
}

export function instant(value: string): Date {
  if (!/[zZ]|[+-]\d{2}:\d{2}$/.test(value)) {
    const err = new Error("TIMEZONE_REQUIRED");
    (err as Error & { code: string }).code = "TIMEZONE_REQUIRED";
    throw err;
  }
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) {
    throw new Error("TIMEZONE_REQUIRED");
  }
  return d;
}

export function formatBangkok(iso: string): string {
  const d = instant(iso);
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Bangkok",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(d);
}
