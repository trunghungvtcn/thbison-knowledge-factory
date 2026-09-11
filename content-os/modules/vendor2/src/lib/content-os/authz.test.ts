import assert from "node:assert/strict";
import { test } from "node:test";
import { DEMO_TOKENS, resolveBearer, assertProject } from "./authz.ts";
import { ContractError } from "./errors.ts";

test("G03 missing bearer is UNAUTHORIZED", () => {
  assert.throws(() => resolveBearer(null), (e: unknown) => e instanceof ContractError && e.code === "UNAUTHORIZED");
});

test("G03 forged token is UNAUTHORIZED", () => {
  assert.throws(() => resolveBearer("Bearer totally-not-a-real-token-xx"), (e: unknown) => e instanceof ContractError && e.code === "UNAUTHORIZED");
});

test("G03 valid token binds project", () => {
  const p = resolveBearer(`Bearer ${DEMO_TOKENS.editor}`);
  assert.equal(p.project_id, "test-thbison");
  assert.equal(p.can_publish, true);
  assert.throws(() => assertProject(p, "other-thbison"), (e: unknown) => e instanceof ContractError && e.code === "FORBIDDEN");
});

test("G03 other project token cannot read test-thbison", () => {
  const p = resolveBearer(`Bearer ${DEMO_TOKENS.other}`);
  assert.equal(p.project_id, "other-thbison");
  assert.throws(() => assertProject(p, "test-thbison"), (e: unknown) => e instanceof ContractError && e.code === "FORBIDDEN");
});
