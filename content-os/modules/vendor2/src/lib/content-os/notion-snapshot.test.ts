import assert from "node:assert/strict";
import test from "node:test";
import { notionRecordEligible, NOTION_DATA_SOURCES } from "./notion-policy";

test("only ACTIVE evidence is eligible", () => {
  assert.equal(notionRecordEligible(NOTION_DATA_SOURCES.evidence, "ACTIVE", null), true);
  assert.equal(notionRecordEligible(NOTION_DATA_SOURCES.evidence, "BLOCKED", null), false);
});

test("product and knowledge require both APPROVED status and decision", () => {
  assert.equal(notionRecordEligible(NOTION_DATA_SOURCES.products, "APPROVED", "APPROVED"), true);
  assert.equal(notionRecordEligible(NOTION_DATA_SOURCES.knowledge, "REVIEW_REQUIRED", "PENDING"), false);
  assert.equal(notionRecordEligible(NOTION_DATA_SOURCES.knowledge, "APPROVED", "HOLD"), false);
});
