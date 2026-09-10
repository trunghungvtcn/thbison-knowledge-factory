import assert from "node:assert/strict";
import { test } from "node:test";
import { cmsCreateDraft, cmsFind, resetCms, setCmsFault, cmsCounters } from "./cms.ts";

test("C15 timeout-after-accept does not create a second draft", async () => {
  resetCms();
  setCmsFault("timeout-after-accept");
  const input = {
    projectId: "test-thbison",
    destinationId: "test-cms",
    articleId: "art-1",
    articleRevision: 1,
    contentSha256: "a".repeat(64),
    body: "draft",
  };
  await assert.rejects(
    () => cmsCreateDraft(input),
    (e) => e instanceof Error && "code" in e && e.code === "TIMEOUT",
  );
  assert.equal(cmsCounters().sideEffects, 1);
  setCmsFault("none");
  const second = await cmsCreateDraft(input);
  const found = cmsFind(input);
  assert.equal(found?.provider_record_id, second.provider_record_id);
  assert.equal(cmsCounters().sideEffects, 1);
});

test("C11 dry-run path never required CMS side effects — mock adapter starts empty", () => {
  resetCms();
  assert.equal(cmsCounters().sideEffects, 0);
});
