import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion, readIdempotency, readJsonLimited, requestIdOf } from "@/lib/content-os/http";
import { submitPublication } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/publications")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let rid = "publication";
        try {
          const body = await readJsonLimited(request);
          rid = requestIdOf(body, rid);
          const fault = request.headers.get("x-fault") === "timeout-after-accept" ? "timeout-after-accept" : "none";
          return json(
            await submitPublication(
              authPrincipal(request),
              body,
              readIdempotency(request),
              readContractVersion(request) ?? "",
              { fault },
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
