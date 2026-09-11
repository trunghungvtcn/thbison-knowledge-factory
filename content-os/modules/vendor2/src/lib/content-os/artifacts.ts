import { createHash } from "node:crypto";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import path from "node:path";
import { ContractError } from "./errors";
import { sha256Utf8 } from "./hash";

const ROOT = "/tmp/thbison-artifacts";

function safeName(id: string): string {
  if (id.includes("..") || id.includes("/") || id.includes("\\")) {
    throw new ContractError("VALIDATION_ERROR", "path traversal");
  }
  return id;
}

export async function putArtifact(projectId: string, artifactId: string, bytes: Buffer, mediaType: string) {
  const id = safeName(artifactId);
  await mkdir(path.join(ROOT, projectId), { recursive: true });
  const storagePath = path.join(ROOT, projectId, `${id}.bin`);
  const sha = createHash("sha256").update(bytes).digest("hex");
  await writeFile(storagePath, bytes);
  const readBack = await readFile(storagePath);
  const back = createHash("sha256").update(readBack).digest("hex");
  if (back !== sha) throw new ContractError("VALIDATION_ERROR", "corrupt artifact");
  return { artifact_id: id, sha256: sha, bytes: bytes.length, media_type: mediaType, storage_path: storagePath, verified: true };
}

export async function getArtifact(projectId: string, artifactId: string, expectedSha: string) {
  const id = safeName(artifactId);
  const storagePath = path.join(ROOT, projectId, `${id}.bin`);
  const buf = await readFile(storagePath);
  const sha = createHash("sha256").update(buf).digest("hex");
  if (sha !== expectedSha) throw new ContractError("VALIDATION_ERROR", "hash mismatch");
  return buf;
}

export function quoteHash(text: string): string {
  return sha256Utf8(text);
}
