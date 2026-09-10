import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, requireContract } from "@/lib/content-os/http";
import { getApproval } from "@/lib/content-os/service";
import { ContractError } from "@/lib/content-os/errors";

export const Route = createFileRoute("/v1/approvals/$approval_id")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          requireContract(request);
          authPrincipal(request);
          const rec = await getApproval(params.approval_id);
          if (!rec) throw new ContractError("VALIDATION_ERROR", "unknown approval");
          return json(rec);
        } catch (err) {
          return errorBody(params.approval_id, err);
        }
      },
    },
  },
});
