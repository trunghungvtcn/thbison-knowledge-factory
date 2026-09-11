import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, requireContract } from "@/lib/content-os/http";
import { revokeEvidence } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/evidence/$bundle_id/revoke")({
  server: {
    handlers: {
      POST: async ({ request, params }) => {
        try {
          requireContract(request);
          const rec = await revokeEvidence(authPrincipal(request), params.bundle_id);
          return json(rec);
        } catch (err) {
          return errorBody(params.bundle_id, err);
        }
      },
    },
  },
});
