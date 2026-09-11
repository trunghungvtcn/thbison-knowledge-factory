import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, requireContract } from "@/lib/content-os/http";
import { capabilities, ensureSeed } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/capabilities")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        try {
          requireContract(request);
          authPrincipal(request);
          await ensureSeed();
          return json(capabilities());
        } catch (err) {
          return errorBody("capabilities", err);
        }
      },
    },
  },
});
