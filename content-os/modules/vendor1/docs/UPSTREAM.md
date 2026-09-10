# OpenSEO upstream pin (Vendor 1)

Inspected 2026-09-10. Adapter only — we do not rewrite the keyword/SERP engine.

| Field | Value |
|---|---|
| Repository | https://github.com/every-app/open-seo |
| Commit | `3632f408528cd588fec98c3a174af8ea0ad205e8` (2026-09-03, “Blog: What Broke the $99 Ceiling”) |
| License | MIT, Copyright (c) 2026 Ben Senescu — notice preserved in `NOTICE` |
| Hosted MCP | `https://app.openseo.so/mcp` |
| Docs | https://openseo.so/features/mcp · https://openseo.so/docs/mcp · https://openseo.so/docs/skills/keyword-research |
| Auth | Interactive OpenSEO login for MCP clients; headless/CI uses API key. This adapter never embeds a key in the browser. |
| Cost | Hosted OpenSEO $10/month; self-host uses DataForSEO pay-as-you-go. No paid call unless `OPENSEO_API_KEY` set and `THBISON_MODE` is STAGING or LIVE. |

## Tools discovered (not remembered from an old README)

From the live MCP feature page on 2026-09-10:

- Keywords: `research_keywords`, `get_serp_results`, `save_keywords`, `get_rank_tracker_data`
- Competitive: `get_domain_overview`, `get_domain_keywords`, `get_backlinks_overview`
- Search Console: `get_gsc_performance`, `inspect_urls`
- Project context: `get_project_context`, `list_projects`, `update_project_context`, `create_project`

This service **calls** only `research_keywords` (and optionally `get_serp_results` in live mode). `save_keywords` is not invoked (no write into the customer OpenSEO project from planning).

`/v1/planning/*` routes are THBISON wrappers (contract 1.0.0, hash in `CONTRACT_SHA256.txt`). They are not OpenSEO native URLs.
