import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { canonicalJson, digest, hashWithout, sha256Utf8 } from "./hash.ts";

const examples = process.cwd() + "/vendor-kit/contracts/examples";

function load(name: string) {
  return JSON.parse(readFileSync(`${examples}/${name}.json`, "utf8"));
}

test("G01 hash matches kit ArticlePackage content_sha256", () => {
  const article = load("ArticlePackage");
  assert.equal(hashWithout(article, "content_sha256"), article.content_sha256);
});

test("G01 hash matches kit EvidenceBundle snapshot_sha256", () => {
  const bundle = load("EvidenceBundle");
  assert.equal(hashWithout(bundle, "snapshot_sha256"), bundle.snapshot_sha256);
});

test("G01 quote_sha256 is SHA-256 of UTF-8 quote", () => {
  const bundle = load("EvidenceBundle");
  assert.equal(sha256Utf8(bundle.claims[0].quote), bundle.claims[0].quote_sha256);
});

test("G01 canonical JSON is sorted, compact, ascii-escaped", () => {
  const json = canonicalJson({ b: "ă", a: 1 });
  assert.equal(json, '{"a":1,"b":"\\u0103"}');
  assert.match(digest({ z: 1, a: 2 }), /^[a-f0-9]{64}$/);
});

test("G01 extra field changes digest", () => {
  const a = load("ArticlePackage");
  const b = { ...a, extra: "nope" };
  assert.notEqual(digest(a), digest(b));
});
