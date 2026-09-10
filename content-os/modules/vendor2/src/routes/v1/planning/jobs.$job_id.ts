import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion } from "@/lib/content-os/http";
import { getJob } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/planning/jobs/$job_id")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          return json(await getJob(authPrincipal(request), params.job_id, readContractVersion(request) ?? ""));
        } catch (err) {
          return errorBody(params.job_id, err);
        }
      },
    },
  },
});
