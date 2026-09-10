# Bàn giao nhà thầu Vendor 1 — 1.0.0-r3

Một artifact: `THBISON-VENDOR-1-seo-planning-source.zip`.

Giải nén rồi chạy `sha256sum -c CHECKSUMS.txt` tại cùng thư mục (các file khai báo nằm cùng cấp).

| File cùng cấp CHECKSUMS | Vai trò |
|---|---|
| `source.zip` | Source + MOCK + evidence |
| `SOURCE_REVISION` | Merkle SHA-256 của source tree |
| `package-lock.json` | Lockfile đã pin |
| `RECEIPT.json` | Biên lai |
| `RELEASE_MANIFEST.json` | Version, tests, file list |

`code_commit` và `source_commit` = `null` (không có Git). Định danh tree: `source_revision_sha256`.

Kit đóng băng: 50 PASS, 1 FAIL `test_naive_date_rejected` (upstream). `NOTION_PAGES.json` không nằm trong phát hành.
