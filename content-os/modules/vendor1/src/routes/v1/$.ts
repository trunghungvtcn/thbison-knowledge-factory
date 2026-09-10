import { createFileRoute } from "@tanstack/react-router";
import { handlePlanningHttp } from "@/planning/http";

export const Route = createFileRoute("/v1/$")({
  server: {
    handlers: {
      GET: async ({ request }) => handlePlanningHttp(request),
      POST: async ({ request }) => handlePlanningHttp(request),
    },
  },
});
