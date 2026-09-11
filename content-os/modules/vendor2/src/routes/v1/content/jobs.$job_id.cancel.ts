import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion, readIdempotency } from "@/lib/content-os/http";
import { cancelJob } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/content/jobs/$job_id/cancel")({
  server: {
    handlers: {
      POST: async ({ request, params }) => {
        try {
          return json(
            await cancelJob(
              authPrincipal(request),
              params.job_id,
              readIdempotency(request),
              readContractVersion(request) ?? "",
            ),
          );
        } catch (err) {
          return errorBody(params.job_id, err);
        }
      },
    },
  },
});
