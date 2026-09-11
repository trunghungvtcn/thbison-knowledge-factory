import kit from "./kit-fixtures.json";
import type { ArticlePackage, ContentBrief, EvidenceBundle, PlanningOutput } from "./types";

export const kitBrief = kit.brief as ContentBrief;
export const kitEvidence = kit.evidence as EvidenceBundle;
export const kitArticle = kit.article as ArticlePackage;
export const kitPlanning = kit.planning as PlanningOutput;
export const holdEvidence = kit.hold as EvidenceBundle;
export const injectEvidence = kit.inject as EvidenceBundle;
export const stagingEvidence = kit.staging_evidence as EvidenceBundle;
export const stagingBrief = kit.staging_brief as ContentBrief;
export const manualBrief = kit.manual_brief as ContentBrief;
