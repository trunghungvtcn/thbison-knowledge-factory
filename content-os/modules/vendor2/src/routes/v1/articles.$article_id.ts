import { createFileRoute } from "@tanstack/react-router";
import { authPrincipal, errorBody, json, readContractVersion } from "@/lib/content-os/http";
import { getArticle } from "@/lib/content-os/service";

export const Route = createFileRoute("/v1/articles/$article_id")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          return json(await getArticle(authPrincipal(request), params.article_id, readContractVersion(request) ?? ""));
        } catch (err) {
          return errorBody(params.article_id, err);
        }
      },
    },
  },
});
