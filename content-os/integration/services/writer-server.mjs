import http from "node:http";
import { createHash } from "node:crypto";
import { generateSyntheticArticle } from "../../modules/vendor2/src/lib/content-os/writer.ts";
import { checkArticle, checkBundle } from "../../modules/vendor2/src/lib/content-os/gate.ts";

const port = Number(process.env.PORT || 18082);
const state = new Map();
const json = (res, status, body) => {
  const raw = JSON.stringify(body);
  res.writeHead(status, { "content-type": "application/json", "content-length": Buffer.byteLength(raw) });
  res.end(raw);
};
const read = async (req) => {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
};

http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/healthz") return json(res, 200, { status: "ok", component: "vendor2-writer" });
    if (req.headers["authorization"] !== "Bearer lab-writer-token") return json(res, 401, { code: "UNAUTHORIZED" });
    if (req.headers["x-contract-version"] !== "1.0.0") return json(res, 400, { code: "UNSUPPORTED_CONTRACT" });
    const body = await read(req);
    if (req.method === "POST" && req.url === "/v1/draft") {
      checkBundle(body.bundle);
      const articleId = `article-${createHash("sha256").update(body.brief.brief_id).digest("hex").slice(0, 16)}`;
      const article = generateSyntheticArticle(body.brief, body.bundle, articleId, 1);
      checkArticle(article, body.bundle);
      state.set(article.article_id, { article, bundle: body.bundle });
      return json(res, 200, article);
    }
    if (req.method === "POST" && req.url === "/v1/approve") {
      const rec = state.get(body.article_id);
      if (!rec || rec.article.article_revision !== body.article_revision) return json(res, 404, { code: "ARTICLE_NOT_FOUND" });
      if (rec.article.status !== "PREVIEW_READY" || rec.article.publication_blockers.length || rec.bundle.gaps.length) {
        return json(res, 409, { code: "APPROVAL_BLOCKED" });
      }
      const approval = {
        contract_version: "1.0.0", project_id: rec.article.project_id, data_class: "TEST_ONLY",
        approval_id: `approval-${rec.article.article_id.slice(-16)}`, article_id: rec.article.article_id,
        article_revision: rec.article.article_revision, content_sha256: rec.article.content_sha256,
        evidence_snapshot_sha256: rec.article.evidence_snapshot_sha256, policy_version: rec.article.policy_version,
        destination_id: body.destination_id || "test-cms", decision: "APPROVED", approved_by: "lab-reviewer",
        approved_at: "2020-01-01T00:00:00Z", expires_at: "2099-01-01T00:00:00Z"
      };
      return json(res, 200, approval);
    }
    return json(res, 404, { code: "NOT_FOUND" });
  } catch (error) {
    return json(res, 400, { code: "VALIDATION_ERROR", message: String(error?.message || error) });
  }
}).listen(port, "127.0.0.1", () => console.log(`V2_WRITER_LISTENING:${port}`));
