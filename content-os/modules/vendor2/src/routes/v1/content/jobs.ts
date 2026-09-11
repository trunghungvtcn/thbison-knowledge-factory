import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion, readIdempotency, readJsonLimited, requestIdOf } from "@/lib/content-os/http";
import { submitContentJob } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/content/jobs")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let rid = "content-job";
        try {
          const body = await readJsonLimited(request);
          rid = requestIdOf(body, rid);
          const rec = await submitContentJob(
            authPrincipal(request),
            body,
            readIdempotency(request),
            readContractVersion(request) ?? "",
          );
          return json(rec, 202);
        } catch (err) {
          return errorBody(rid, err);
        }
      },
    },
  },
});
