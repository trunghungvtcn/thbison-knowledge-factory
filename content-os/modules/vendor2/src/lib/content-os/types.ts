export type DataClass = "TEST_ONLY" | "STAGING" | "PRODUCTION";
export type JobStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | "BLOCKED_INPUT"
  | "NO_CHANGE"
  | "BUDGET_EXHAUSTED"
  | "TIMED_OUT";
export type ArticleStatus = "DRAFT" | "PREVIEW_READY" | "REVIEW_REQUIRED";
export type BlockKind = "HEADING" | "FACTUAL" | "EDITORIAL" | "CTA";
export type ClaimStatus = "ELIGIBLE" | "HOLD" | "QUARANTINE";
export type ClaimRisk = "DESCRIPTIVE" | "PRODUCT_SPEC" | "SAFETY" | "LEGAL";
export type PublishMode = "DRY_RUN" | "STAGING_DRAFT" | "LIVE";
export type PublicationStatus =
  | "DRY_RUN"
  | "SCHEDULED"
  | "PUBLISHING"
  | "PUBLISHED"
  | "UNKNOWN"
  | "FAILED"
  | "CANCELLED";
export type ApprovalDecision = "APPROVED" | "REJECTED" | "REVOKED";

export type Scope = {
  country_code: string;
  language: string;
  timezone: "Asia/Bangkok";
  domain: string;
};

export type Budget = {
  max_provider_requests: number;
  max_tokens: number;
  max_cost_usd: string;
  deadline_at: string;
  max_transport_attempts: number;
};

export type ContentBrief = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
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

export type Claim = {
  claim_id: string;
  text: string;
  status: ClaimStatus;
  risk: ClaimRisk;
  allowed_uses: Array<"DRAFT" | "PUBLISH">;
  source_ref: string;
  source_version: string;
  source_sha256: string;
  locator: string;
  quote: string;
  quote_sha256: string;
  applicability: string;
  jurisdiction: string;
};

export type EvidenceBundle = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  bundle_id: string;
  snapshot_sha256: string;
  policy_version: string;
  as_of: string;
  claims: Claim[];
  gaps: string[];
};

export type ArticleBlock = {
  block_id: string;
  kind: BlockKind;
  text: string;
  claim_ids: string[];
};

export type ArticlePackage = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  article_id: string;
  article_revision: number;
  brief_id: string;
  brief_revision: number;
  bundle_id: string;
  evidence_snapshot_sha256: string;
  policy_version: string;
  title: string;
  slug: string;
  status: ArticleStatus;
  blocks: ArticleBlock[];
  seo: { title: string; description: string };
  unresolved_claim_ids: string[];
  publication_blockers: string[];
  content_sha256: string;
};

export type DraftRequest = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  request_id: string;
  brief: ContentBrief;
  evidence: EvidenceBundle;
  budget: Budget;
};

export type ApprovalRecord = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  approval_id: string;
  article_id: string;
  article_revision: number;
  content_sha256: string;
  evidence_snapshot_sha256: string;
  policy_version: string;
  destination_id: string;
  decision: ApprovalDecision;
  approved_by: string;
  approved_at: string;
  expires_at: string;
};

export type PublishRequest = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  request_id: string;
  article_id: string;
  article_revision: number;
  content_sha256: string;
  evidence_snapshot_sha256: string;
  approval_id: string;
  destination_id: string;
  mode: PublishMode;
  scheduled_at: string | null;
};

export type PublicationReceipt = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  publication_id: string;
  request_id: string;
  article_id: string;
  article_revision: number;
  destination_id: string;
  content_sha256: string;
  status: PublicationStatus;
  provider_record_id: string | null;
  provider_url: string | null;
  created_at: string;
  actual_side_effects: number;
};

export type JobReceipt = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  job_id: string;
  request_id: string;
  status: JobStatus;
  code_commit: string;
  contract_sha256: string;
  result_artifact: {
    artifact_id: string;
    sha256: string;
    bytes: number;
    media_type: string;
  } | null;
  error_code: string | null;
};

export type ContractErrorBody = {
  contract_version: "1.0.0";
  request_id: string;
  code: string;
  message: string;
  retryable: boolean;
};

export type Principal = {
  principal_id: string;
  project_id: string;
  subject_id: string;
  role: string;
  can_publish: boolean;
};

export type KeywordMetric = {
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
  data_class: DataClass;
  research_id: string;
  request_id: string;
  scope: Scope;
  keywords: KeywordMetric[];
  provider_snapshot: {
    artifact_id: string;
    sha256: string;
    bytes: number;
    media_type: string;
  };
  warnings: string[];
};

export type PlanningOutput = {
  research: ResearchResult;
  brief: ContentBrief;
};

export type ResearchRequest = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: DataClass;
  request_id: string;
  scope: Scope;
  seeds: string[];
  existing_pages: string[];
  budget: Budget;
};
