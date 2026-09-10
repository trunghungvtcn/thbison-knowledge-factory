import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, requireContract } from "@/lib/content-os/http";
import { simulateRestart } from "@/lib/content-os/durable";
import { markSeeded } from "@/lib/content-os/service";

/** MOCK durable-store simulator. Not a THBISON database. */
export const Route = createFileRoute("/v1/mock/ledger/restart")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          requireContract(request);
          authPrincipal(request);
          const counts = await simulateRestart();
          markSeeded();
          return json({ simulated: true, store: "file-snapshot", ...counts });
        } catch (err) {
          return errorBody("ledger-restart", err);
        }
      },
    },
  },
});
