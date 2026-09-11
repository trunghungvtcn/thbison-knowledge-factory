# Field mapping ArticlePackage → simulator draft

| ArticlePackage | Simulator draft | Notes |
|---|---|---|
| title + blocks[].text | body | sanitized; citations preserved |
| slug | unused in sim | UNKNOWN native field |
| seo.title/description | unused in sim | SCHEMA_DRIFT if native requires missing field |
| content_sha256 | content_sha256 | bound to approval |
| article_id + revision | external_key prefix | |
| project_id | project_id | cross-project denied |
