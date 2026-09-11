import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion, readIdempotency, readJsonLimited, requestIdOf } from "@/lib/content-os/http";
import { submitPlanningJob } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/planning/jobs")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let rid = "planning-job";
        try {
          const body = await readJsonLimited(request);
          rid = requestIdOf(body, rid);
          return json(
            await submitPlanningJob(
              authPrincipal(request),
              body,
              readIdempotency(request),
              readContractVersion(request) ?? "",
            ),
            202,
          );
        } catch (err) {
          return errorBody(rid, err);
        }
      },
    },
  },
});
