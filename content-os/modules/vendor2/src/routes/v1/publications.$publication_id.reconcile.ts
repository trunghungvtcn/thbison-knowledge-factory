import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, requireContract } from "@/lib/content-os/http";
import { reconcilePublication } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/publications/$publication_id/reconcile")({
  server: {
    handlers: {
      POST: async ({ request, params }) => {
        try {
          requireContract(request);
          return json(await reconcilePublication(authPrincipal(request), params.publication_id));
        } catch (err) {
          return errorBody(params.publication_id, err);
        }
      },
    },
  },
});
