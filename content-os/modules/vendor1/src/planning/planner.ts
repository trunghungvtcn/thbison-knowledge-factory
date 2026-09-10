import { CONTRACT_VERSION, nowIso } from "./config.ts";
import { idFrom } from "./hash.ts";
import type { ExistingPage, ResearchRequest, Scope } from "./validate.ts";
import { checkKeywordMetrics } from "./validate.ts";
import { asciiFold, type ProviderResult, type RawKeyword } from "./provider.ts";

export type KeywordOut = {
  keyword: string;
  volume: number | null;
  difficulty: number | null;
  measurement_status: "MEASURED" | "MISSING" | "STALE" | "SYNTHETIC";
  provider: string;
  captured_at: string;
  source_ref: string;
};

export type ResearchResult = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: "TEST_ONLY" | "STAGING" | "PRODUCTION";
  research_id: string;
  request_id: string;
  scope: Scope;
  keywords: KeywordOut[];
  provider_snapshot: { artifact_id: string; sha256: string; bytes: number; media_type: string };
  warnings: string[];
};

export type ContentBrief = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: "TEST_ONLY" | "STAGING" | "PRODUCTION";
  brief_id: string;
  brief_revision: number;
  research_id: string;
  scope: Scope;
  title: string;
  audience: string;
  intent: string;
  primary_keyword: string;
  secondary_keywords: string[];
  questions: string[];
  outline: string[];
  evidence_requirements: string[];
  product_refs: string[];
  proposed_publish_at: string | null;
  editorial_constraints: string[];
  origin: "RESEARCH" | "MANUAL";
};

export type Cluster = {
  intent: string;
  rationale: string;
  keywords: string[];
  product_scope: "pilot" | "off-pilot";
  recommendation: "CREATE" | "UPDATE" | "CANNIBALIZATION" | "SKIP_OFF_PILOT";
  existing_page_id: string | null;
};

export type PlanningExtras = {
  clusters: Cluster[];
  ranking_note: string;
  calendar_is_not_publication: true;
};

export function toResearchResult(req: ResearchRequest, provider: ProviderResult): ResearchResult {
  if (req.data_class !== "TEST_ONLY" && provider.synthetic) {
    throw new Error("SYNTHETIC_IN_REAL_DATA");
  }
  const keywords: KeywordOut[] = provider.keywords.map((k) => {
    checkKeywordMetrics(k);
    return {
      keyword: k.display,
      volume: k.volume,
      difficulty: k.difficulty,
      measurement_status: k.measurement_status,
      provider: k.provider,
      captured_at: k.captured_at,
      source_ref: k.source_ref,
    };
  });
  const research_id = idFrom("rsr", [
    req.project_id,
    req.scope.country_code,
    req.scope.language,
    req.seeds.map((s) => asciiFold(s)).sort().join(","),
    provider.snapshot.sha256,
  ]);
  const warnings = [...provider.warnings];
  if (provider.keywords.some((k) => k.product_scope === "off-pilot")) {
    warnings.push("Off-pilot product terms flagged (electric/lever hoist); not merged into manual-chain-hoist cluster.");
  }
  return {
    contract_version: CONTRACT_VERSION,
    project_id: req.project_id,
    data_class: req.data_class,
    research_id,
    request_id: req.request_id,
    scope: req.scope,
    keywords,
    provider_snapshot: provider.snapshot,
    warnings,
  };
}

function matchExisting(keyword: string, pages: ExistingPage[]): ExistingPage | undefined {
  const k = asciiFold(keyword);
  return pages.find((p) => asciiFold(p.title).includes(k) || k.includes(asciiFold(p.title)) || asciiFold(p.intent).includes(k));
}

export function clusterKeywords(raw: RawKeyword[], pages: ExistingPage[]): Cluster[] {
  const groups = new Map<string, RawKeyword[]>();
  for (const k of raw) {
    const key = `${k.product_scope}|${k.intent_hint}`;
    const arr = groups.get(key) ?? [];
    arr.push(k);
    groups.set(key, arr);
  }
  const clusters: Cluster[] = [];
  for (const [, items] of [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const primary = items[0];
    const page = matchExisting(primary.display, pages);
    let recommendation: Cluster["recommendation"] = "CREATE";
    if (primary.product_scope === "off-pilot") recommendation = "SKIP_OFF_PILOT";
    else if (page) recommendation = page.intent === primary.intent_hint ? "UPDATE" : "CANNIBALIZATION";
    clusters.push({
      intent: primary.intent_hint,
      rationale:
        primary.intent_hint === "transactional"
          ? "Buying/pricing language is kept separate from informational anatomy queries."
          : primary.product_scope === "off-pilot"
            ? "Term is outside the manual chain hoist pilot and must not be silently merged."
            : "Informational intent: structure, usage, and source-supported description.",
      keywords: items.map((i) => i.display),
      product_scope: primary.product_scope,
      recommendation,
      existing_page_id: page?.page_id ?? null,
    });
  }
  return clusters;
}

export function buildBrief(
  req: ResearchRequest,
  research: ResearchResult,
  clusters: Cluster[],
  previousRevision: number | null,
  proposedPublishAt: string | null,
): ContentBrief | null {
  const create = clusters.find((c) => c.recommendation === "CREATE" && c.product_scope === "pilot");
  const update = clusters.find((c) => c.recommendation === "UPDATE" || c.recommendation === "CANNIBALIZATION");
  const chosen = create ?? (update && update.recommendation !== "CANNIBALIZATION" ? update : create);
  if (!chosen) {
    // Collision-only: still emit a brief that recommends update, not a duplicate page.
    if (update) {
      return briefFromCluster(req, research, update, previousRevision, proposedPublishAt, true);
    }
    return null;
  }
  return briefFromCluster(req, research, chosen, previousRevision, proposedPublishAt, false);
}

function briefFromCluster(
  req: ResearchRequest,
  research: ResearchResult,
  cluster: Cluster,
  previousRevision: number | null,
  proposedPublishAt: string | null,
  collision: boolean,
): ContentBrief {
  const primary = cluster.keywords[0];
  const secondary = cluster.keywords.slice(1);
  const brief_id = idFrom("brf", [req.project_id, req.scope.domain, asciiFold(primary)]);
  const title = collision ? `Cập nhật: ${primary}` : `Cấu tạo ${primary}`;
  const origin: "RESEARCH" | "MANUAL" = "RESEARCH";
  return {
    contract_version: CONTRACT_VERSION,
    project_id: req.project_id,
    data_class: req.data_class,
    brief_id,
    brief_revision: (previousRevision ?? 0) + 1,
    research_id: research.research_id,
    scope: req.scope,
    title: title.slice(0, 12000),
    audience:
      "Kỹ thuật viên nhà máy, nhân viên mua hàng thiết bị nâng hạ tại Việt Nam (pilot THBISON, không dùng làm bằng chứng sản phẩm).",
    intent: cluster.intent,
    primary_keyword: primary,
    secondary_keywords: secondary,
    questions: [
      `Những gì có thể nêu về ${primary} chỉ từ nguồn được phép?`,
      "Phạm vi sản phẩm pa lăng xích kéo tay khác pa lăng điện/đòn bẩy như thế nào?",
    ],
    outline: [
      "Phạm vi và giới hạn (không an toàn/pháp lý)",
      "Mô tả được nguồn hỗ trợ",
      collision ? "Khuyến nghị cập nhật trang hiện có, không tạo URL trùng" : "Câu hỏi thường gặp",
    ],
    evidence_requirements: [
      "Every factual block maps to allowed claim IDs.",
      "Competitor SERP snippets are not technical evidence.",
      "Missing volume stays null; ranking is not safety confidence.",
    ],
    product_refs: cluster.product_scope === "pilot" ? ["manual-chain-hoist"] : [],
    proposed_publish_at: proposedPublishAt,
    editorial_constraints: [
      req.data_class === "TEST_ONLY"
        ? "TEST ONLY: do not publish or treat synthetic facts as product evidence."
        : "Do not publish until Vendor 2 approval; planning dates are not publication authority.",
      "Vietnamese diacritics must be preserved.",
      cluster.recommendation === "CANNIBALIZATION"
        ? `Cannibalization vs existing page ${cluster.existing_page_id}: do not force a duplicate brief URL.`
        : "Keep intent clusters editable; do not silently rewrite live pages.",
    ],
    origin,
  };
}

export function planningOutput(
  research: ResearchResult,
  brief: ContentBrief,
): { research: ResearchResult; brief: ContentBrief } {
  return { research, brief };
}

export function rankingNote(): string {
  return "Opportunity ranking uses volume/difficulty when MEASURED; it is independent of factual confidence and never substitutes evidence.";
}

export { nowIso };
