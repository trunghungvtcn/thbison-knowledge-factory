import assert from "node:assert/strict";
import { test } from "node:test";
import { validateDraftRequest, validateHeaderContract, noInvalidUnicode } from "./validate.ts";
import { ContractError } from "./errors.ts";
import { readFileSync } from "node:fs";

test("G08 naive datetime rejected", () => {
  const draft = JSON.parse(readFileSync(process.cwd() + "/vendor-kit/contracts/examples/DraftRequest.json", "utf8"));
  draft.budget.deadline_at = "2030-01-01T00:05:00";
  assert.throws(() => validateDraftRequest(draft), (e: unknown) => e instanceof ContractError);
});

test("G02 unsupported contract header", () => {
  assert.throws(() => validateHeaderContract("0.9.0"), (e: unknown) => e instanceof ContractError && e.code === "UNSUPPORTED_CONTRACT");
});

test("G07 unpaired surrogate rejected", () => {
  assert.throws(() => noInvalidUnicode("ok\uD800bad"), (e: unknown) => e instanceof ContractError && e.code === "INVALID_UNICODE");
});

test("C05 extra field on draft request", () => {
  const draft = JSON.parse(readFileSync(process.cwd() + "/vendor-kit/contracts/examples/DraftRequest.json", "utf8"));
  draft.extra = "nope";
  assert.throws(() => validateDraftRequest(draft));
});
