# AP Invoice Self-Serve MCPB Handoff

## English

This project implements the AP Invoice Exception Review MCPB described in `AP_INVOICE_SELF_SERVE_MCPB_PRODUCT_SPEC.md`.

Implemented scope:

- Deterministic workflow pack: `workflow-packs/ap-invoice-v1`
- Reference CSVs: vendor, PO, GRN, invoice history, tax code, and cost center
- Core checks: vendor master, PO amount, GRN quantity, duplicate invoice, and tax amount
- MCP tools: create case, upload document, start review, get result, and build draft payload
- V2 UX tools: list demo cases, review demo case end-to-end, review packet end-to-end, explain exception, and build approval brief
- MCP prompts: `/ap-demo`, `/ap-review`, `/ap-explain`, and `/ap-approval-brief` equivalents
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

V2 UX entrypoints:

- `list_ap_demo_cases`
- `review_ap_demo_case`
- `review_ap_invoice_packet`
- `explain_ap_exception`
- `build_ap_approval_brief`

Security review fixes applied for the demo scope:

- Upload paths are restricted to bundled demo sample directories.
- Only `.pdf` demo documents can be uploaded.
- Sidecar JSON must match the expected document type.
- Basic value validation rejects empty IDs, negative amounts, and invalid dates.
- Completed cases cannot be modified by later document uploads.
- Re-running a completed review is idempotent and returns the original job.
- Case and job IDs are randomized instead of sequential.
- PO not found, unapproved/mismatched PO, exhausted balance, GRN not received, and GRN PO mismatch now produce referral rules instead of falling through to pay-ready.
- PO tolerance now applies the larger of absolute JPY tolerance and percent tolerance.
- Public API responses use logical `artifact://...` URIs instead of local absolute filesystem paths.

Remaining non-scope security items for production Remote MCP:

- Authentication and tenant identity must come from the hosting platform or verified token.
- Authorization and tenant ownership checks must be enforced before multi-tenant deployment.
- Centralized, append-only audit logging should be added for production financial processing.

## Japanese

このプロジェクトは `AP_INVOICE_SELF_SERVE_MCPB_PRODUCT_SPEC.md` に基づく AP Invoice Exception Review MCPB の実装です。

実装済み範囲:

- 決定論的 workflow pack: `workflow-packs/ap-invoice-v1`
- 参照CSV: 取引先、PO、GRN、過去請求、税コード、コストセンター
- Core checks: 取引先マスタ照合、PO金額照合、GRN数量照合、重複請求、税額確認
- MCP tools: case作成、document upload、review開始、結果取得、draft payload生成
- V2 UX tools: demo case一覧、demo case end-to-end review、packet end-to-end review、例外説明、承認者brief
- MCP prompts: `/ap-demo`、`/ap-review`、`/ap-explain`、`/ap-approval-brief` 相当
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

V2 UX entrypoints:

- `list_ap_demo_cases`
- `review_ap_demo_case`
- `review_ap_invoice_packet`
- `explain_ap_exception`
- `build_ap_approval_brief`

デモスコープで適用済みのSecurity review対応:

- upload path は同梱デモサンプル配下に制限
- upload可能なファイルは `.pdf` デモ帳票のみ
- sidecar JSON の `document_type` が期待値と一致することを検証
- 空ID、負の金額、不正日付などの基本値検証を追加
- review完了後のdocument差し替えを禁止
- 完了済みreviewの再実行は同じjobを返すidempotent動作に変更
- case/job ID を連番からランダムIDへ変更
- PO未存在、未承認/不一致PO、残高不足、GRN未受領、GRN PO番号不一致を支払候補に落とさず referral rule に変更
- PO tolerance は絶対JPY許容値とpercent許容値の大きい方を適用
- API応答ではローカル絶対パスではなく `artifact://...` URI を返すように変更

本番Remote MCP化で残る非スコープのSecurity項目:

- 認証とtenant identityはhosting platformまたは検証済みtokenから取得する必要があります
- multi-tenant deployment前にauthorizationとtenant ownership checkが必要です
- 金融処理の本番運用では集中管理されたappend-only audit loggingが必要です
