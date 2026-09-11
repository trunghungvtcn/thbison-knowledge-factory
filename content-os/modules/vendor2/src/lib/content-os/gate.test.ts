import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { checkArticle, checkBundle, gatePublish, defaultPolicy, sealArticle } from "./gate.ts";
import { DEMO_PRINCIPALS } from "./authz.ts";
import { generateSyntheticArticle } from "./writer.ts";
import type { ApprovalRecord, PublishRequest } from "./types.ts";

const examples = process.cwd() + "/vendor-kit/contracts/examples";
function load(name: string) {
  return JSON.parse(readFileSync(`${examples}/${name}.json`, "utf8"));
}

const principal = {
  principal_id: DEMO_PRINCIPALS.editor.principal_id,
  project_id: DEMO_PRINCIPALS.editor.project_id,
  subject_id: DEMO_PRINCIPALS.editor.subject_id,
  role: DEMO_PRINCIPALS.editor.role,
  can_publish: true,
};

test("C01 happy-path check_article + DRY_RUN gate", () => {
  const article = load("ArticlePackage");
  const bundle = load("EvidenceBundle");
  checkBundle(bundle);
  checkArticle(article, bundle);
  const approval: ApprovalRecord = load("ApprovalRecord");
  const request: PublishRequest = load("PublishRequest");
  const v = gatePublish(article, bundle, request, approval, principal, defaultPolicy(), "2030-01-01T00:01:00Z");
  assert.equal(v, "DRY_RUN");
});

test("C02 HOLD claim cannot be drafted", () => {
  const bundle = checkBundle(JSON.parse(readFileSync(process.cwd() + "/src/lib/content-os/kit-fixtures.json", "utf8")).hold);
  const brief = load("ContentBrief");
  const article = generateSyntheticArticle(brief, bundle, "art-hold", 1);
  assert.equal(article.status, "REVIEW_REQUIRED");
  assert.ok(article.unresolved_claim_ids.length + article.publication_blockers.length > 0);
});

test("C05 extra JSON field rejected by check_article via hash mismatch path", () => {
  const article = { ...load("ArticlePackage"), extra: true };
  const bundle = load("EvidenceBundle");
  assert.throws(() => checkArticle(article, bundle));
});

test("C07 LIVE TEST_ONLY is TEST_DATA_NOT_PUBLISHABLE", () => {
  const article = load("ArticlePackage");
  const bundle = load("EvidenceBundle");
  const approval: ApprovalRecord = { ...load("ApprovalRecord") };
  const request: PublishRequest = { ...load("PublishRequest"), mode: "LIVE" };
  assert.throws(
    () => gatePublish(article, bundle, request, approval, principal, { ...defaultPolicy(), allow_live: true }, "2030-01-01T00:01:00Z"),
    /TEST_DATA_NOT_PUBLISHABLE/,
  );
});

test("C09 stale content_sha256", () => {
  const article = load("ArticlePackage");
  const bundle = load("EvidenceBundle");
  const approval: ApprovalRecord = load("ApprovalRecord");
  const request: PublishRequest = { ...load("PublishRequest"), content_sha256: "0".repeat(64) };
  assert.throws(() => gatePublish(article, bundle, request, approval, principal, defaultPolicy(), "2030-01-01T00:01:00Z"));
});

test("C10 reader cannot publish", () => {
  const article = load("ArticlePackage");
  const bundle = load("EvidenceBundle");
  const approval: ApprovalRecord = load("ApprovalRecord");
  const request: PublishRequest = load("PublishRequest");
  const reader = {
    principal_id: "reader",
    project_id: "test-thbison",
    subject_id: "test-human-reader",
    role: "reader",
    can_publish: false,
  };
  assert.throws(
    () => gatePublish(article, bundle, request, approval, reader, defaultPolicy(), "2030-01-01T00:01:00Z"),
    /FORBIDDEN/,
  );
});

test("C19 FACTUAL without citation", () => {
  const article = sealArticle({
    ...load("ArticlePackage"),
    blocks: [{ block_id: "x", kind: "FACTUAL", text: "load 1 ton", claim_ids: [] }],
    unresolved_claim_ids: [],
    publication_blockers: [],
    content_sha256: "0".repeat(64),
  });
  const bundle = load("EvidenceBundle");
  assert.throws(() => checkArticle(article, bundle), /FACT_WITHOUT_CITATION/);
});
