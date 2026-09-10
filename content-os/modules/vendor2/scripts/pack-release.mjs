#!/usr/bin/env node
/**
 * Two-layer release packer.
 *
 * payload.tar.gz  = gzip(git archive of HEAD)  → artifact_digest
 * envelope zip    = payload + filled receipt + manifest + sums + evidence
 * sidecar         = sha256 of the envelope zip (not stored inside it)
 *
 * Excludes caches via .gitignore / git (untracked files are not archived).
 */
import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync, cpSync } from "node:fs";
import { execSync } from "node:child_process";
import path from "node:path";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "releases");
const STAGE = path.join(OUT, "_stage");
const PAYLOAD_NAME = "payload.tar.gz";
const ZIP_NAME = "THBISON-VENDOR-2-CONTENT-WORKFLOW.zip";
const CONTRACT = "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8";

const FORBIDDEN_FRAGMENTS = [
  "/.grok/",
  "/.pytest_cache/",
  "/__pycache__/",
  "/.vercel/",
  "/node_modules/",
  "/dist/",
  "/.output/",
  "/.vite/",
  "/attachments/",
  "/releases/",
  ".pid",
];

function sha256File(p) {
  return createHash("sha256").update(readFileSync(p)).digest("hex");
}

function sha256Text(s) {
  return createHash("sha256").update(s, "utf8").digest("hex");
}

function git(args) {
  return execSync(`git ${args}`, { cwd: ROOT, encoding: "utf8" }).trim();
}

function mustCleanTree() {
  const dirty = execSync("git status --porcelain", { cwd: ROOT, encoding: "utf8" }).trim();
  if (dirty) {
    console.error("Working tree is not clean. Commit first.\n" + dirty);
    process.exit(1);
  }
}

function assertNoForbidden(files) {
  const bad = files.filter((f) => FORBIDDEN_FRAGMENTS.some((frag) => `/${f}`.includes(frag) || f.endsWith(frag)));
  if (bad.length) {
    console.error("Forbidden paths in git tree:", bad);
    process.exit(1);
  }
}

function treeListing(files) {
  const lines = files.map((f) => `${sha256File(path.join(ROOT, f))}  ${f}`);
  return lines.join("\n") + "\n";
}

function writeJson(p, obj) {
  writeFileSync(p, JSON.stringify(obj, null, 2) + "\n");
}

function main() {
  mustCleanTree();
  const sourceCommit = git("rev-parse HEAD");
  const files = git("ls-files -z").split("\0").filter(Boolean).sort();
  assertNoForbidden(files);

  mkdirSync(OUT, { recursive: true });
  rmSync(STAGE, { recursive: true, force: true });
  mkdirSync(STAGE, { recursive: true });

  const listing = treeListing(files);
  const sourceTreeSha256 = sha256Text(listing);
  writeFileSync(path.join(STAGE, "SOURCE_TREE_SHA256SUMS.txt"), listing);

  const payloadPath = path.join(STAGE, PAYLOAD_NAME);
  execSync(`git archive --format=tar --prefix=THBISON-VENDOR-2-CONTENT-OS/ HEAD | gzip -n -9 > "${payloadPath}"`, {
    cwd: ROOT,
    shell: "/bin/bash",
  });
  const artifactDigest = sha256File(payloadPath);

  const lockfileSha256 = sha256File(path.join(ROOT, "package-lock.json"));
  const kitManifestSha256 = sha256File(path.join(ROOT, "vendor-kit/KIT_MANIFEST.json"));
  const contractFileSha256 = readFileSync(path.join(ROOT, "vendor-kit/CONTRACT_SHA256.txt"), "utf8").trim();
  if (contractFileSha256 !== CONTRACT) {
    console.error("CONTRACT_SHA256.txt mismatch", contractFileSha256);
    process.exit(1);
  }

  const evidence = {
    "artifacts/unit-tests.log": existsSync(path.join(ROOT, "artifacts/unit-tests.log"))
      ? sha256File(path.join(ROOT, "artifacts/unit-tests.log"))
      : null,
    "artifacts/acceptance-junit.xml": existsSync(path.join(ROOT, "artifacts/acceptance-junit.xml"))
      ? sha256File(path.join(ROOT, "artifacts/acceptance-junit.xml"))
      : null,
    "artifacts/acceptance-cases.json": existsSync(path.join(ROOT, "artifacts/acceptance-cases.json"))
      ? sha256File(path.join(ROOT, "artifacts/acceptance-cases.json"))
      : null,
    "artifacts/kit-self-test.log": existsSync(path.join(ROOT, "artifacts/kit-self-test.log"))
      ? sha256File(path.join(ROOT, "artifacts/kit-self-test.log"))
      : null,
    "artifacts/kit-self-test.xml": existsSync(path.join(ROOT, "artifacts/kit-self-test.xml"))
      ? sha256File(path.join(ROOT, "artifacts/kit-self-test.xml"))
      : null,
    "docs/SCOPE_STATUS.json": sha256File(path.join(ROOT, "docs/SCOPE_STATUS.json")),
    "docs/KNOWN_LIMITATIONS.md": sha256File(path.join(ROOT, "docs/KNOWN_LIMITATIONS.md")),
    "docs/DOCKER_BUILD_RECEIPT.json": sha256File(path.join(ROOT, "docs/DOCKER_BUILD_RECEIPT.json")),
    "package-lock.json": lockfileSha256,
    "vendor-kit/KIT_MANIFEST.json": kitManifestSha256,
  };

  const receipt = JSON.parse(readFileSync(path.join(ROOT, "docs/DELIVERY_RECEIPT.json"), "utf8"));
  receipt.source_commit = sourceCommit;
  receipt.source_tree_sha256 = sourceTreeSha256;
  receipt.artifact_digest = artifactDigest;
  receipt.artifact_digest_subject = PAYLOAD_NAME;
  receipt.release_zip = ZIP_NAME;
  receipt.release_zip_sha256 = null;
  receipt.contract_sha256 = CONTRACT;
  receipt.lockfile_sha256 = lockfileSha256;
  receipt.test_fixture_sha256 = kitManifestSha256;
  receipt.junit_sha256 = evidence["artifacts/acceptance-junit.xml"];
  receipt.kit_junit_sha256 = evidence["artifacts/kit-self-test.xml"];
  receipt.packed_at = new Date().toISOString();
  receipt.hashing_scheme = {
    source_commit: "git rev-parse HEAD",
    source_tree_sha256: "sha256 of sorted 'sha256  path\\n' listing of git ls-files (SOURCE_TREE_SHA256SUMS.txt)",
    contract_sha256: "vendor-kit/CONTRACT_SHA256.txt (must match this field)",
    artifact_digest: "sha256 of payload.tar.gz (git archive of source_commit | gzip -n -9). Linked to the three hashes above. Never null.",
    release_zip_sha256: "sha256 of this envelope ZIP; canonical copy is the sidecar *.zip.sha256 because a ZIP cannot contain its own digest",
  };

  const manifest = {
    name: ZIP_NAME,
    module: "VENDOR_2",
    status: "CHANGES_ADDRESSED_MOCK",
    acceptance_claimed: false,
    kit_self_test: "PARTIAL",
    p05: "NOT_MET",
    labels: {
      KIT_SELF_TEST_PASS: false,
      ADAPTER_VERIFIED: false,
      INTEGRATED_CANARY_PASS: false,
    },
    source_commit: sourceCommit,
    source_tree_sha256: sourceTreeSha256,
    artifact_digest: artifactDigest,
    artifact_digest_subject: PAYLOAD_NAME,
    contract_sha256: CONTRACT,
    lockfile_sha256: lockfileSha256,
    test_fixture_sha256: kitManifestSha256,
    junit_sha256: receipt.junit_sha256,
    kit_junit_sha256: receipt.kit_junit_sha256,
    docker: { status: "NOT_BUILT", receipt: "docs/DOCKER_BUILD_RECEIPT.json" },
    hashing_scheme: receipt.hashing_scheme,
    excludes: [
      ".grok",
      ".pytest_cache",
      "__pycache__",
      ".vercel",
      "node_modules",
      "dist",
      ".output",
      ".vite",
      "attachments",
      "preview pid/log",
      "releases",
    ],
    contents: [
      PAYLOAD_NAME,
      "DELIVERY_RECEIPT.json",
      "RELEASE_MANIFEST.json",
      "SHA256SUMS.txt",
      "SOURCE_TREE_SHA256SUMS.txt",
      "README-RELEASE.md",
      "docs/",
      "artifacts/",
    ],
    evidence_sha256: evidence,
  };

  writeJson(path.join(STAGE, "DELIVERY_RECEIPT.json"), receipt);
  writeJson(path.join(STAGE, "RELEASE_MANIFEST.json"), manifest);

  const readme = `# THBISON Vendor 2 — release envelope

Status: **CHANGES_ADDRESSED_MOCK**. Kit self-test **PARTIAL**. P05 **NOT_MET**.
Not KIT_SELF_TEST_PASS. Not ADAPTER_VERIFIED. Not INTEGRATED_CANARY_PASS.

## Verify

\`\`\`bash
sha256sum -c THBISON-VENDOR-2-CONTENT-OS-release.zip.sha256   # sidecar, next to this zip
sha256sum -c SHA256SUMS.txt
\`\`\`

\`artifact_digest\` in DELIVERY_RECEIPT.json / RELEASE_MANIFEST.json MUST equal SHA-256 of \`${PAYLOAD_NAME}\`.

It is linked to:

- source_commit = ${sourceCommit}
- source_tree_sha256 = ${sourceTreeSha256}
- contract_sha256 = ${CONTRACT}

The envelope ZIP cannot contain its own digest. Use the sidecar \`.sha256\`.

## Unpack source

\`\`\`bash
tar -xzf payload.tar.gz
cd THBISON-VENDOR-2-CONTENT-OS
npm ci
CONTENT_OS_MODE=MOCK npm run dev
\`\`\`

See docs/OPERATOR_RUNBOOK.md and docs/KNOWN_LIMITATIONS.md.
`;
  writeFileSync(path.join(STAGE, "README-RELEASE.md"), readme);

  const copyInto = (rel) => {
    const src = path.join(ROOT, rel);
    const dst = path.join(STAGE, rel);
    mkdirSync(path.dirname(dst), { recursive: true });
    cpSync(src, dst, { recursive: true });
  };
  copyInto("docs/KNOWN_LIMITATIONS.md");
  copyInto("docs/DOCKER_BUILD_RECEIPT.json");
  copyInto("docs/SCOPE_STATUS.json");
  copyInto("docs/OPERATOR_RUNBOOK.md");
  copyInto("docs/REVIEW_RESPONSE.md");
  copyInto("artifacts/unit-tests.log");
  copyInto("artifacts/acceptance-junit.xml");
  copyInto("artifacts/acceptance-cases.json");
  copyInto("artifacts/kit-self-test.log");
  if (existsSync(path.join(ROOT, "artifacts/kit-self-test.xml"))) copyInto("artifacts/kit-self-test.xml");
  if (existsSync(path.join(ROOT, "artifacts/scope-status.json"))) copyInto("artifacts/scope-status.json");
  if (existsSync(path.join(ROOT, "artifacts/acceptance-http.log"))) copyInto("artifacts/acceptance-http.log");

  const sumsLines = [
    `${artifactDigest}  ${PAYLOAD_NAME}`,
    `${sha256File(path.join(STAGE, "DELIVERY_RECEIPT.json"))}  DELIVERY_RECEIPT.json`,
    `${sha256File(path.join(STAGE, "RELEASE_MANIFEST.json"))}  RELEASE_MANIFEST.json`,
    `${sha256File(path.join(STAGE, "SOURCE_TREE_SHA256SUMS.txt"))}  SOURCE_TREE_SHA256SUMS.txt`,
    `${sha256File(path.join(STAGE, "README-RELEASE.md"))}  README-RELEASE.md`,
  ];
  writeFileSync(path.join(STAGE, "SHA256SUMS.txt"), sumsLines.join("\n") + "\n");

  const zipPath = path.join(OUT, ZIP_NAME);
  rmSync(zipPath, { force: true });
  execSync(
    `python3 - <<'PY'
import os, zipfile
stage = ${JSON.stringify(STAGE)}
zip_path = ${JSON.stringify(zipPath)}
fixed = (2026, 9, 10, 0, 0, 0)
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, files in os.walk(stage):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, stage).replace(os.sep, "/")
            info = zipfile.ZipInfo(rel, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, "rb") as f:
                z.writestr(info, f.read())
print("wrote", zip_path)
PY`,
    { cwd: ROOT, shell: "/bin/bash" },
  );

  const envelopeSha = sha256File(zipPath);
  writeFileSync(path.join(OUT, ZIP_NAME + ".sha256"), `${envelopeSha}  ${ZIP_NAME}\n`);
  writeFileSync(
    path.join(OUT, "SHA256SUMS.txt"),
    [
      `${envelopeSha}  ${ZIP_NAME}`,
      `${artifactDigest}  ${PAYLOAD_NAME}`,
      `${sourceCommit}  SOURCE_COMMIT`,
      `${sourceTreeSha256}  SOURCE_TREE`,
      `${CONTRACT}  CONTRACT_SHA256`,
    ].join("\n") + "\n",
  );

  receipt.release_zip_sha256 = envelopeSha;
  receipt.release_zip = ZIP_NAME;

  const sidecarReceipt = { ...receipt };
  sidecarReceipt.artifact_digest = envelopeSha;
  sidecarReceipt.artifact_digest_subject = ZIP_NAME;
  sidecarReceipt.payload_sha256 = artifactDigest;
  sidecarReceipt.artifact_digest_note =
    "This sidecar copy sets artifact_digest to SHA-256 of the envelope ZIP. The in-archive DELIVERY_RECEIPT.json uses payload.tar.gz (a ZIP cannot contain its own digest). Both are linked to source_commit, source_tree_sha256, and contract_sha256.";
  writeJson(path.join(OUT, "DELIVERY_RECEIPT.sidecar.json"), sidecarReceipt);

  const pub = path.join(ROOT, "public");
  mkdirSync(pub, { recursive: true });
  cpSync(zipPath, path.join(pub, ZIP_NAME));
  cpSync(path.join(OUT, ZIP_NAME + ".sha256"), path.join(pub, ZIP_NAME + ".sha256"));
  cpSync(path.join(OUT, "SHA256SUMS.txt"), path.join(pub, "SHA256SUMS.txt"));
  cpSync(path.join(STAGE, "RELEASE_MANIFEST.json"), path.join(pub, "RELEASE_MANIFEST.json"));
  cpSync(path.join(OUT, "DELIVERY_RECEIPT.sidecar.json"), path.join(pub, "DELIVERY_RECEIPT.json"));

  const verifyPayload = sha256File(payloadPath);
  if (verifyPayload !== artifactDigest) {
    console.error("payload digest drifted");
    process.exit(1);
  }

  console.log(
    JSON.stringify(
      {
        source_commit: sourceCommit,
        source_tree_sha256: sourceTreeSha256,
        artifact_digest: artifactDigest,
        contract_sha256: CONTRACT,
        release_zip_sha256: envelopeSha,
        zip: zipPath,
        files_in_tree: files.length,
      },
      null,
      2,
    ),
  );
}

main();
