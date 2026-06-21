# AP Invoice Self-Serve MCPB Handoff

## English

This project implements the AP Invoice Exception Review MCPB described in `AP_INVOICE_SELF_SERVE_MCPB_PRODUCT_SPEC.md`.

Implemented scope:

- Deterministic workflow pack: `workflow-packs/ap-invoice-v1`
- Reference CSVs: vendor, PO, GRN, invoice history, tax code, and cost center
- Core checks: vendor master, PO amount, GRN quantity, duplicate invoice, and tax amount
- MCP tools: create case, upload document, start review, get result, and build draft payload
- Demo fixtures: case-a through case-d
- Regression tests: unit, fixture, and golden artifact tests
- MCPB packaging: `make package-ap-mcpb`
- Data boundary scan: `make verify-ap-data-boundary`
- Enterprise bundle Skill: `enterprise-bundle/plugin/ap-invoice-review`

Not implemented by design:

- Actual freee, kintone, ERP, banking, or payment writes
- Production OCR/Textract integration
- Customer production data
- LLM-based final recommendation override
- Automatic ruleset rewriting

Primary commands:

```bash
make install
make generate-ap-samples
make test-ap-fixtures
make test-ap-golden
make package-ap-mcpb
make verify-ap-data-boundary
make smoke-ap-mcp
```

Expected fixture outcomes:

- `case-a-pay-ready`: `PAY_READY_CANDIDATE`
- `case-b-po-mismatch`: `REFER_PO_MISMATCH`
- `case-c-duplicate`: `REFER_DUPLICATE_REVIEW`
- `case-d-vendor-review`: `REFER_VENDOR_REVIEW`

All draft payloads must keep `write_performed` set to `false`.

## Japanese

このプロジェクトは `AP_INVOICE_SELF_SERVE_MCPB_PRODUCT_SPEC.md` に基づく AP Invoice Exception Review MCPB の実装です。

実装済み範囲:

- 決定論的 workflow pack: `workflow-packs/ap-invoice-v1`
- 参照CSV: 取引先、PO、GRN、過去請求、税コード、コストセンター
- Core checks: 取引先マスタ照合、PO金額照合、GRN数量照合、重複請求、税額確認
- MCP tools: case作成、document upload、review開始、結果取得、draft payload生成
- Demo fixtures: case-a から case-d
- 回帰テスト: unit、fixture、golden artifact tests
- MCPB package: `make package-ap-mcpb`
- 秘密情報混入チェック: `make verify-ap-data-boundary`
- Enterprise bundle Skill: `enterprise-bundle/plugin/ap-invoice-review`

意図的に非スコープとしているもの:

- freee、kintone、ERP、銀行、支払への本書き込み
- 本番OCR/Textract連携
- 顧客本番データ
- LLMによる最終recommendation上書き
- rulesetの自動書き換え

主要コマンド:

```bash
make install
make generate-ap-samples
make test-ap-fixtures
make test-ap-golden
make package-ap-mcpb
make verify-ap-data-boundary
make smoke-ap-mcp
```

期待fixture結果:

- `case-a-pay-ready`: `PAY_READY_CANDIDATE`
- `case-b-po-mismatch`: `REFER_PO_MISMATCH`
- `case-c-duplicate`: `REFER_DUPLICATE_REVIEW`
- `case-d-vendor-review`: `REFER_VENDOR_REVIEW`

すべての draft payload は `write_performed: false` を維持します。
