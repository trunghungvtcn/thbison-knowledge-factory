export const NOTION_DATA_SOURCES = {
  evidence: "87318868-8be2-4e27-8ab6-7a3d0b53bb32",
  products: "a4812f47-e1a6-4aa1-a619-558a79a4c4ff",
  knowledge: "9d53865d-0cdd-41f3-a6c6-5d171b4e50f4",
} as const;

export function notionRecordEligible(dataSourceId: string, status: string | null, decision: string | null): boolean {
  if (dataSourceId === NOTION_DATA_SOURCES.evidence) return status === "ACTIVE";
  if (dataSourceId === NOTION_DATA_SOURCES.products || dataSourceId === NOTION_DATA_SOURCES.knowledge) {
    return status === "APPROVED" && decision === "APPROVED";
  }
  return false;
}
