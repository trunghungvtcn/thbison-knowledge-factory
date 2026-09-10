import { createHash, timingSafeEqual } from "node:crypto";
import { ContractError } from "./errors";
import type { Principal } from "./types";

/** TEST_ONLY demo tokens. Never production credentials. */
export const DEMO_TOKENS = {
  editor: "svc_editor_test_thbison_ok12",
  reader: "svc_reader_test_thbison_ok12",
  other: "svc_editor_other_project_ok12",
} as const;

export const DEMO_PRINCIPALS: Record<string, Principal & { token: string }> = {
  editor: {
    principal_id: "editor",
    project_id: "test-thbison",
    subject_id: "test-human-editor",
    role: "editor",
    can_publish: true,
    token: DEMO_TOKENS.editor,
  },
  reader: {
    principal_id: "reader",
    project_id: "test-thbison",
    subject_id: "test-human-reader",
    role: "reader",
    can_publish: false,
    token: DEMO_TOKENS.reader,
  },
  other: {
    principal_id: "other",
    project_id: "other-thbison",
    subject_id: "other-editor",
    role: "editor",
    can_publish: true,
    token: DEMO_TOKENS.other,
  },
};

export function tokenSha256(token: string): string {
  return createHash("sha256").update(token, "utf8").digest("hex");
}

export function resolveBearer(header: string | null): Principal {
  if (!header || !header.toLowerCase().startsWith("bearer ")) {
    throw new ContractError("UNAUTHORIZED", "Missing bearer");
  }
  const token = header.slice(7).trim();
  if (!token) throw new ContractError("UNAUTHORIZED", "Missing bearer");
  for (const p of Object.values(DEMO_PRINCIPALS)) {
    const a = Buffer.from(tokenSha256(token), "hex");
    const b = Buffer.from(tokenSha256(p.token), "hex");
    if (a.length === b.length && timingSafeEqual(a, b)) {
      return {
        principal_id: p.principal_id,
        project_id: p.project_id,
        subject_id: p.subject_id,
        role: p.role,
        can_publish: p.can_publish,
      };
    }
  }
  throw new ContractError("UNAUTHORIZED", "Unknown or forged credential");
}

export function principalFromId(id: string | null | undefined): Principal {
  const key = id && id in DEMO_PRINCIPALS ? id : "editor";
  const p = DEMO_PRINCIPALS[key];
  return {
    principal_id: p.principal_id,
    project_id: p.project_id,
    subject_id: p.subject_id,
    role: p.role,
    can_publish: p.can_publish,
  };
}

export function assertProject(principal: Principal, projectId: string): void {
  if (principal.project_id !== projectId) {
    throw new ContractError("FORBIDDEN", "Cross-project access denied");
  }
}
