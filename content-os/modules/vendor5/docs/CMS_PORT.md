# CMSPort (internal, PROPOSED)

Frozen public schemas are unchanged. This port is an internal extension.

```
inspectCapabilities() -> Capabilities + provider matrix + native status
createDraft(project, destination, run_id, external_key, article, body_hash)
lookupByExternalKey(project, destination, external_key)
getDraft(provider_record_id)
updateDraft(provider_record_id, expectedRevision, body, content_hash)
reconcile(publication_id)
rollbackOwnTestMutation(test_run_id)
```

## Mapping to PublicationReceipt
| Port result | receipt.status | provider_record_id | actual_side_effects |
|---|---|---|---|
| DRY_RUN authorized | DRY_RUN | null | 0 |
| draft created | PUBLISHED (staging non-public) | sim id | 1 |
| lookup hit after timeout | UNKNOWN then reconciled | looked-up id | 0 or 1 |
| live denied | error LIVE_DISABLED | — | 0 |

LIVE in the shared enum is not an execution license.
