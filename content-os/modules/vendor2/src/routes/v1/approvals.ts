import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readJsonLimited, requireContract } from "@/lib/content-os/http";
import { issueApproval } from "@/lib/content-os/service";
import { asObject, requireId } from "@/lib/content-os/validate";

export const Route = createFileRoute("/v1/approvals")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          requireContract(request);
          const p = authPrincipal(request);
          const body = asObject(await readJsonLimited(request));
          const rec = await issueApproval(
            p,
            requireId(body.article_id, "article_id"),
            typeof body.destination_id === "string" ? body.destination_id : "test-cms",
            body.decision === "REJECTED" ? "REJECTED" : "APPROVED",
          );
          return json(rec, 201);
        } catch (err) {
          return errorBody("approval", err);
        }
      },
    },
  },
});
