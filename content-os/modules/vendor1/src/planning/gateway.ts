import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { dataDir } from "./config.ts";
import { sha256Hex } from "./hash.ts";
import { ApiError } from "./errors.ts";
import { safeArtifactName } from "./security.ts";
import { withLedger } from "./ledger.ts";

const ROOT = () => resolve(dataDir(), "artifacts");

export async function putArtifact(
  name: string,
  bytes: Buffer,
  mediaType: string,
  expectedHash?: string,
): Promise<{ artifact_id: string; sha256: string; bytes: number; media_type: string }> {
  const safe = safeArtifactName(name);
  const hash = sha256Hex(bytes);
  if (expectedHash && expectedHash !== hash) {
    throw new ApiError(400, "VALIDATION_ERROR", "Artifact hash mismatch", "req-missing-00000001", false);
  }
  mkdirSync(ROOT(), { recursive: true });
  const path = resolve(ROOT(), safe);
  if (!path.startsWith(ROOT())) {
    throw new ApiError(400, "VALIDATION_ERROR", "Path escape", "req-missing-00000001", false);
  }
  if (existsSync(path)) {
    const prev = sha256Hex(readFileSync(path));
    if (prev !== hash) {
      throw new ApiError(409, "VALIDATION_ERROR", "Filename collision with different bytes", "req-missing-00000001", false);
    }
  } else {
    writeFileSync(path, bytes);
  }
  const rec = { artifact_id: safe, sha256: hash, bytes: bytes.length, media_type: mediaType, pathSafe: safe };
  await withLedger((s) => {
    s.artifacts[safe] = rec;
  });
  return { artifact_id: rec.artifact_id, sha256: rec.sha256, bytes: rec.bytes, media_type: rec.media_type };
}

export async function refreshUrl(artifactId: string, expiredUrl: string): Promise<string> {
  const safe = safeArtifactName(artifactId);
  const path = resolve(ROOT(), safe);
  if (!existsSync(path)) throw new ApiError(400, "VALIDATION_ERROR", "Unknown artifact", "req-missing-00000001", false);
  void expiredUrl;
  return `artifact://${safe}?n=${Date.now()}`;
}
