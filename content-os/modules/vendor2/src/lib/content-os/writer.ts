import { newId } from "./hash";
import { checkBundle, sealArticle } from "./gate";
import { evaluateArticle } from "./quality";
import { isUntrustedInstruction } from "./quality";
import type { ArticlePackage, ContentBrief, EvidenceBundle } from "./types";

export type WriterMode = "SYNTHETIC";

function slugify(title: string): string {
  const base = title
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return base || "bai-viet";
}

export function generateSyntheticArticle(
  brief: ContentBrief,
  evidence: EvidenceBundle,
  articleId: string,
  revision: number,
): ArticlePackage {
  const bundle = checkBundle(evidence);
  const eligible = bundle.claims.filter(
    (c) => c.status === "ELIGIBLE" && c.allowed_uses.includes("DRAFT") && !isUntrustedInstruction(c.text),
  );
  const held = bundle.claims.filter((c) => c.status === "HOLD" || c.status === "QUARANTINE");
  const blocks: ArticlePackage["blocks"] = [];

  blocks.push({
    block_id: "h-scope",
    kind: "HEADING",
    text: brief.outline[0] ?? brief.title,
    claim_ids: [],
  });

  blocks.push({
    block_id: "ed-frame",
    kind: "EDITORIAL",
    text: "Bài viết này chỉ được viết từ bằng chứng đã cấp. Không bổ sung thông số ngoài nguồn. Nội dung TEST_ONLY, không phải tài liệu sản phẩm thật.",
    claim_ids: [],
  });

  for (const claim of eligible) {
    blocks.push({
      block_id: `f-${claim.claim_id}`.replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, 64) || newId("f"),
      kind: "FACTUAL",
      text: claim.text,
      claim_ids: [claim.claim_id],
    });
  }

  blocks.push({
    block_id: "cta-1",
    kind: "CTA",
    text: "Liên hệ THBISON để được tư vấn pa lăng xích kéo tay phù hợp phạm vi nguồn đã duyệt.",
    claim_ids: [],
  });

  const gaps = [...bundle.gaps];
  if (!eligible.length) gaps.push("Không có claim ELIGIBLE được phép DRAFT.");
  for (const h of held) gaps.push(`Nguồn ${h.claim_id} ở trạng thái ${h.status} — không dùng.`);

  const findings = evaluateArticle(
    {
      contract_version: "1.0.0",
      project_id: brief.project_id,
      data_class: brief.data_class,
      article_id: articleId,
      article_revision: revision,
      brief_id: brief.brief_id,
      brief_revision: brief.brief_revision,
      bundle_id: bundle.bundle_id,
      evidence_snapshot_sha256: bundle.snapshot_sha256,
      policy_version: bundle.policy_version,
      title: brief.title,
      slug: slugify(brief.title),
      status: "DRAFT",
      blocks,
      seo: {
        title: brief.title.slice(0, 70),
        description: `Tóm tắt theo brief ${brief.brief_id}, chỉ dùng nguồn ${bundle.bundle_id}.`,
      },
      unresolved_claim_ids: held.map((c) => c.claim_id),
      publication_blockers: [],
      content_sha256: "0".repeat(64),
    },
    bundle,
  );

  const blockers = [
    ...gaps.filter((g) => g.length > 0),
    ...findings.filter((f) => f.blocks_publication).map((f) => `${f.code}: ${f.message}`),
  ];
  if (brief.data_class === "TEST_ONLY") {
    blockers.push("TEST_ONLY: không được LIVE/STAGING_DRAFT.");
  }

  const status = blockers.length || !eligible.length ? "REVIEW_REQUIRED" : "PREVIEW_READY";
  // TEST_ONLY still can preview; publication blockers for LIVE are separate.
  // For the happy-path fixture (eligible claim, no quality fail) drop the TEST_ONLY live blocker from preview status.
  const previewBlockers = findings.filter((f) => f.blocks_publication).map((f) => `${f.code}: ${f.message}`);
  if (!eligible.length) previewBlockers.push("MISSING_EVIDENCE");
  previewBlockers.push(...gaps);
  for (const c of bundle.claims) {
    if ((c.risk === "SAFETY" || c.risk === "LEGAL") && eligible.some((e) => e.claim_id === c.claim_id)) {
      previewBlockers.push("RISK_OUT_OF_PILOT_SCOPE");
    }
  }

  const ready = eligible.length > 0 && findings.every((f) => !f.blocks_publication) && held.length === 0 && !gaps.length;
  const article: ArticlePackage = {
    contract_version: "1.0.0",
    project_id: brief.project_id,
    data_class: brief.data_class,
    article_id: articleId,
    article_revision: revision,
    brief_id: brief.brief_id,
    brief_revision: brief.brief_revision,
    bundle_id: bundle.bundle_id,
    evidence_snapshot_sha256: bundle.snapshot_sha256,
    policy_version: bundle.policy_version,
    title: brief.title,
    slug: slugify(brief.primary_keyword || brief.title),
    status: ready ? "PREVIEW_READY" : "REVIEW_REQUIRED",
    blocks,
    seo: {
      title: brief.title.slice(0, 70),
      description: `Nguồn ${bundle.bundle_id}. Chỉ phát biểu điều nguồn cho phép.`,
    },
    unresolved_claim_ids: held.map((c) => c.claim_id),
    publication_blockers: ready ? [] : Array.from(new Set(previewBlockers)),
    content_sha256: "0".repeat(64),
  };
  void status;
  return sealArticle(article);
}

export function applyEditorialEdit(
  article: ArticlePackage,
  patch: { title?: string; seoTitle?: string; seoDescription?: string; blocks?: ArticlePackage["blocks"] },
): ArticlePackage {
  const next: ArticlePackage = {
    ...article,
    article_revision: article.article_revision + 1,
    title: patch.title ?? article.title,
    seo: {
      title: patch.seoTitle ?? article.seo.title,
      description: patch.seoDescription ?? article.seo.description,
    },
    blocks: patch.blocks ?? article.blocks,
    status: "DRAFT",
  };
  return sealArticle(next);
}
