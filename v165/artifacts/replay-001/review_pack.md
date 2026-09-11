# V16.5 complete-record review pack

DRAFT — no real activation/adjudication.

## 0496c4f5-fe89-5d30-b948-34505fb64143

Proposal hash: `c93810a4a8b3b8ada1038872063012e6fd1c982b1d1df4d4e948942348a7d1f9`

Target version: null (DRAFT).

Issues: ri_231ee183bc333b130c9238c9a002aa282c2b8e1b224ee969d378e29712bfd3f8, ri_6d93315b540a7c320f94ddf548687d733c86e0859d72436a7d86ee92f3faaafc

```json
{
  "before": {
    "applicability": "MANUAL_CHAIN_HOIST_CAPACITY_GTE_1000_KG",
    "condition_ast": {
      "legacy_tags": [
        "COVERED",
        "FIXED_INSTALLATION"
      ],
      "op": "UNRESOLVED",
      "reason": "LEGACY_LIST_HAS_NO_BOOLEAN_CONNECTIVE"
    },
    "exception_ast": {
      "op": "FALSE"
    },
    "jurisdiction": "VN",
    "legal_status": "CURRENT_REFERENCED_BY_19_2025_TT_BNV",
    "object_value": {
      "type": "legacy_text",
      "value": "Với các palăng xích kéo tay lắp đặt cố định tại nơi có mái che: thời hạn kiểm định định kỳ 3 năm."
    },
    "predicate": "inspection_interval",
    "product_family": "manual hand chain hoist",
    "subject": "manual hand chain hoist"
  },
  "after": {
    "applicability": "MANUAL_CHAIN_HOIST_CAPACITY_GTE_1000_KG",
    "condition_ast": {
      "op": "UNRESOLVED",
      "legacy_tags": [
        "COVERED",
        "FIXED_INSTALLATION"
      ],
      "reason": "LEGACY_LIST_HAS_NO_BOOLEAN_CONNECTIVE"
    },
    "exception_ast": {
      "op": "FALSE"
    },
    "jurisdiction": "VN",
    "legal_status": "CURRENT_REFERENCED_BY_19_2025_TT_BNV",
    "object_value": {
      "type": "quantity",
      "amount": "3",
      "unit": "year",
      "operator": "EQ"
    },
    "predicate": "inspection_interval",
    "product_family": "manual hand chain hoist",
    "subject": "manual hand chain hoist"
  },
  "assessments": {
    "quantity": "SUPPORTED",
    "conditions": "UNKNOWN",
    "exceptions": "UNKNOWN",
    "applicability": "SUPPORTED",
    "jurisdiction": "SUPPORTED",
    "legal_status": "UNKNOWN",
    "overlap": "UNRESOLVED",
    "reviewed_scope": {
      "corpus_sha256": "bcadfadbc117bfb367a1577871f6d59e13ce0cca38a935523e816a3bb3dfcba4",
      "units": [
        "pdf:page:60",
        "pdf:page:61",
        "pdf:page:62",
        "pdf:page:63",
        "pdf:page:64",
        "pdf:page:65",
        "pdf:page:66",
        "pdf:page:67",
        "pdf:page:68",
        "pdf:page:69",
        "pdf:page:70",
        "pdf:page:71",
        "pdf:page:72"
      ],
      "sections": [
        "1",
        "2",
        "3",
        "10.1",
        "10.2",
        "10.3",
        "10.4"
      ],
      "limitations": "Source-text audit only; cross-reference current validity and semantic review outstanding."
    }
  },
  "blockers": [
    {
      "issue_id": "v165_ade2607b1ca706d7a123890769938c5fa7c401d3676c6b2dd0b1000f41f01e41",
      "entity_id": "0496c4f5-fe89-5d30-b948-34505fb64143",
      "issue_type": "LEGAL_STATUS_UNVERIFIED",
      "resolution_status": "NEEDS_REVIEW",
      "reason": "No pinned authoritative 19/2025 reference/current amendment corpus establishes inherited current-validity flag.",
      "source_ref": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2016/12/23923/17902-1-2017431-43254-2016-tt-bldtbxh.pdf",
      "discovered_from": [
        "ri_231ee183bc333b130c9238c9a002aa282c2b8e1b224ee969d378e29712bfd3f8",
        "ri_6d93315b540a7c320f94ddf548687d733c86e0859d72436a7d86ee92f3faaafc"
      ]
    },
    {
      "issue_id": "v165_4cdc0dd2e2da5adb96636e594f595d08a0f03d914dd0e3fd526090a25655874a",
      "entity_id": "0496c4f5-fe89-5d30-b948-34505fb64143",
      "issue_type": "RULE_OVERLAP_UNRESOLVED",
      "resolution_status": "NEEDS_REVIEW",
      "reason": "Fixed covered equipment older than 12 years is a review scenario potentially covered by both intervals; no approved precedence.",
      "source_ref": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2016/12/23923/17902-1-2017431-43254-2016-tt-bldtbxh.pdf",
      "discovered_from": [
        "ri_231ee183bc333b130c9238c9a002aa282c2b8e1b224ee969d378e29712bfd3f8",
        "ri_6d93315b540a7c320f94ddf548687d733c86e0859d72436a7d86ee92f3faaafc"
      ]
    },
    {
      "issue_id": "v165_8f8f43699f49ba43ed475472bb88816671a7e209131cf50893796283286fa15a",
      "entity_id": "0496c4f5-fe89-5d30-b948-34505fb64143",
      "issue_type": "EXCEPTION_COVERAGE_UNKNOWN",
      "resolution_status": "NEEDS_REVIEW",
      "reason": "Sections 10.2-10.4 contain shorter-interval and QCVN provisions; inherited FALSE is unproven.",
      "source_ref": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2016/12/23923/17902-1-2017431-43254-2016-tt-bldtbxh.pdf",
      "discovered_from": [
        "ri_231ee183bc333b130c9238c9a002aa282c2b8e1b224ee969d378e29712bfd3f8",
        "ri_6d93315b540a7c320f94ddf548687d733c86e0859d72436a7d86ee92f3faaafc"
      ]
    }
  ]
}
```

## 59957ace-b4fb-519e-b92d-773bc74ad268

Proposal hash: `4056fee5983e3cadca0d1054171135d34e0d40b2933c43ee6b975f5bd97f3796`

Target version: null (DRAFT).

Issues: ri_65dc0aae82336138e784f05ae96015be21ee620418c5c719cca3c19f42116fbf, ri_935aceff9ee04c8f76118eaea10053842556726e272fdc01eabb73636f445d68

```json
{
  "before": {
    "applicability": "MANUAL_CHAIN_HOIST_CAPACITY_GTE_1000_KG",
    "condition_ast": {
      "legacy_tags": [
        "AGE_OVER_12_YEARS",
        "FIXED_INSTALLATION",
        "MOBILE_USE",
        "OUTDOOR"
      ],
      "op": "UNRESOLVED",
      "reason": "LEGACY_LIST_HAS_NO_BOOLEAN_CONNECTIVE"
    },
    "exception_ast": {
      "op": "FALSE"
    },
    "jurisdiction": "VN",
    "legal_status": "CURRENT_REFERENCED_BY_19_2025_TT_BNV",
    "object_value": {
      "type": "legacy_text",
      "value": "Thời hạn kiểm định định kỳ 1 năm đối với các palăng xích kéo tay sau: lắp đặt cố định ngoài trời; thiết bị được sử dụng lưu động; thiết bị sử dụng trên 12 năm."
    },
    "predicate": "inspection_interval",
    "product_family": "manual hand chain hoist",
    "subject": "manual hand chain hoist"
  },
  "after": {
    "applicability": "MANUAL_CHAIN_HOIST_CAPACITY_GTE_1000_KG",
    "condition_ast": {
      "op": "UNRESOLVED",
      "legacy_tags": [
        "AGE_OVER_12_YEARS",
        "FIXED_INSTALLATION",
        "MOBILE_USE",
        "OUTDOOR"
      ],
      "reason": "LEGACY_LIST_HAS_NO_BOOLEAN_CONNECTIVE"
    },
    "exception_ast": {
      "op": "FALSE"
    },
    "jurisdiction": "VN",
    "legal_status": "CURRENT_REFERENCED_BY_19_2025_TT_BNV",
    "object_value": {
      "type": "quantity",
      "amount": "1",
      "unit": "year",
      "operator": "EQ"
    },
    "predicate": "inspection_interval",
    "product_family": "manual hand chain hoist",
    "subject": "manual hand chain hoist"
  },
  "assessments": {
    "quantity": "SUPPORTED",
    "conditions": "UNKNOWN",
    "exceptions": "UNKNOWN",
    "applicability": "SUPPORTED",
    "jurisdiction": "SUPPORTED",
    "legal_status": "UNKNOWN",
    "overlap": "UNRESOLVED",
    "reviewed_scope": {
      "corpus_sha256": "bcadfadbc117bfb367a1577871f6d59e13ce0cca38a935523e816a3bb3dfcba4",
      "units": [
        "pdf:page:60",
        "pdf:page:61",
        "pdf:page:62",
        "pdf:page:63",
        "pdf:page:64",
        "pdf:page:65",
        "pdf:page:66",
        "pdf:page:67",
        "pdf:page:68",
        "pdf:page:69",
        "pdf:page:70",
        "pdf:page:71",
        "pdf:page:72"
      ],
      "sections": [
        "1",
        "2",
        "3",
        "10.1",
        "10.2",
        "10.3",
        "10.4"
      ],
      "limitations": "Source-text audit only; cross-reference current validity and semantic review outstanding."
    }
  },
  "blockers": [
    {
      "issue_id": "v165_669af21f6f5b0e1f4256d91c6b073f78daae982634554b69873cfd5b65400e2b",
      "entity_id": "59957ace-b4fb-519e-b92d-773bc74ad268",
      "issue_type": "EXCEPTION_COVERAGE_UNKNOWN",
      "resolution_status": "NEEDS_REVIEW",
      "reason": "Sections 10.2-10.4 contain shorter-interval and QCVN provisions; inherited FALSE is unproven.",
      "source_ref": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2016/12/23923/17902-1-2017431-43254-2016-tt-bldtbxh.pdf",
      "discovered_from": [
        "ri_65dc0aae82336138e784f05ae96015be21ee620418c5c719cca3c19f42116fbf",
        "ri_935aceff9ee04c8f76118eaea10053842556726e272fdc01eabb73636f445d68"
      ]
    },
    {
      "issue_id": "v165_0fedd62d84bde653564b0f7907cc3c780c50ae2cb8d41917c44d1418ee73bb91",
      "entity_id": "59957ace-b4fb-519e-b92d-773bc74ad268",
      "issue_type": "LEGAL_STATUS_UNVERIFIED",
      "resolution_status": "NEEDS_REVIEW",
      "reason": "No pinned authoritative 19/2025 reference/current amendment corpus establishes inherited current-validity flag.",
      "source_ref": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2016/12/23923/17902-1-2017431-43254-2016-tt-bldtbxh.pdf",
      "discovered_from": [
        "ri_65dc0aae82336138e784f05ae96015be21ee620418c5c719cca3c19f42116fbf",
        "ri_935aceff9ee04c8f76118eaea10053842556726e272fdc01eabb73636f445d68"
      ]
    },
    {
      "issue_id": "v165_32e30ff94d401cabd78d88222d2009f13a8daeccb0e4ba334366978732596954",
      "entity_id": "59957ace-b4fb-519e-b92d-773bc74ad268",
      "issue_type": "RULE_OVERLAP_UNRESOLVED",
      "resolution_status": "NEEDS_REVIEW",
      "reason": "Fixed covered equipment older than 12 years is a review scenario potentially covered by both intervals; no approved precedence.",
      "source_ref": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2016/12/23923/17902-1-2017431-43254-2016-tt-bldtbxh.pdf",
      "discovered_from": [
        "ri_65dc0aae82336138e784f05ae96015be21ee620418c5c719cca3c19f42116fbf",
        "ri_935aceff9ee04c8f76118eaea10053842556726e272fdc01eabb73636f445d68"
      ]
    }
  ]
}
```

