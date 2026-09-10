import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion } from "@/lib/content-os/http";
import { getJobOutput } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/content/jobs/$job_id/output")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          return json(await getJobOutput(authPrincipal(request), params.job_id, readContractVersion(request) ?? ""));
        } catch (err) {
          return errorBody(params.job_id, err);
        }
      },
    },
  },
});
