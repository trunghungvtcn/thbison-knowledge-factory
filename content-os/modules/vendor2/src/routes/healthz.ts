import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/healthz")({
  server: {
    handlers: {
      GET: async () =>
        new Response(JSON.stringify({ status: "ok" }), {
          headers: { "content-type": "application/json; charset=utf-8" },
        }),
    },
  },
});
