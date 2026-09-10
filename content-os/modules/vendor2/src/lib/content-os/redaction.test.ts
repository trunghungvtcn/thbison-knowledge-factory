import assert from "node:assert/strict";
import { test } from "node:test";
import { redact, redactValue } from "./redaction.ts";

test("G10 secrets stripped from logs", () => {
  const text = redact("Authorization Bearer abcdef0123456789 and sk-ABCDEFG123456 and https://s3.example/x?X-Amz-Signature=deadbeef");
  assert.equal(text.includes("abcdef0123456789"), false);
  assert.equal(text.includes("sk-ABCDEFG"), false);
  assert.equal(text.includes("deadbeef"), false);
  assert.match(text, /REDACTED/);
  const obj = redactValue({ token: "secret-value", note: "ok" });
  assert.deepEqual(obj, { token: "[REDACTED]", note: "ok" });
});
