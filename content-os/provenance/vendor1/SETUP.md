# Môi trường mô phỏng (nhà thầu) và cấu hình nội bộ (sau tiếp nhận)

## Nhà thầu / offline (không cần tài nguyên THBISON)

```sh
export THBISON_MODE=MOCK
# không set OPENSEO_API_KEY
npm ci
npm run dev
sh simulate/run-offline-acceptance.sh
```

Identity giả lập: `simulate/identities.json`.  
Fixture giao thức: `fixtures/openseo/`.  
Compose sandbox: `docker-compose.sandbox.yml`.

Rollback MOCK: dừng process, khôi phục `$THBISON_DATA_DIR/ledger.json`. Vendor 1 không publish nên không có unpublish.

## Phụ lục — đội nội bộ (ngoài phạm vi nhà thầu)

Khi sẵn sàng tích hợp, nội bộ tự gắn:

- `THBISON_SERVICE_TOKENS` (credential thật, không dùng token TEST_ONLY)
- tuỳ chọn `OPENSEO_API_KEY` + `THBISON_MODE=STAGING` cho cổng S02
- TLS, project binding, ArtifactGateway, VPS B

Nhà thầu không cấp, không giữ, không gọi các tài nguyên đó.
