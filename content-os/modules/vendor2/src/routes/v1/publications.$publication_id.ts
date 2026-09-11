import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion } from "@/lib/content-os/http";
import { getPublication } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/publications/$publication_id")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          return json(
            await getPublication(authPrincipal(request), params.publication_id, readContractVersion(request) ?? ""),
          );
        } catch (err) {
          return errorBody(params.publication_id, err);
        }
      },
    },
  },
});
