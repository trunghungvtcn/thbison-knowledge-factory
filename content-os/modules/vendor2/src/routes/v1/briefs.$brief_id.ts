import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion } from "@/lib/content-os/http";
import { getBrief } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/briefs/$brief_id")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          return json(await getBrief(authPrincipal(request), params.brief_id, readContractVersion(request) ?? ""));
        } catch (err) {
          return errorBody(params.brief_id, err);
        }
      },
    },
  },
});
