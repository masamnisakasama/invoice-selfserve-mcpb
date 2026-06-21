# AP Invoice Review MCPB

Claude Desktopで使う、買掛請求書レビューのMCPBデモです。請求書、発注書、納品書/検収書のPDFをClaude OCRで読み取り、MCPB側の決定論的ルールで3-way match、取引先確認、重複確認、税額確認を行います。

This is a Claude Desktop MCPB demo for accounts payable invoice review. Claude reads the PDF forms with vision/OCR, then the MCPB applies deterministic AP rules and returns the payment decision, evidence, next actions, and draft-only payload summaries.

## デモを使う人へ

最初に読む文書:

- [日本語デモ手順](docs/DEMO_GUIDE_JA.md)
- [Validation / 検証手順](docs/VALIDATION.md)

配布・インストールするファイル:

```text
dist/ap-invoice-review.mcpb
```

このデモは架空データ専用です。freee、kintone、ERP、銀行、支払システムへの本書き込みは行いません。結果には必ず `write_performed=false` を含めます。

## クイック確認

開発PCでMCPBを再生成し、リリース前検証をまとめて実行します。

```bash
make install
make validate-mcpb-release
```

`make validate-mcpb-release` には、lint、typecheck、全pytest、MCPB再生成、bundle内容検証、sidecar禁止、OCR smoke、E2E OCR flow、MCP smoke、公式MCPB manifest validationが含まれます。

## Claude Desktopでの基本プロンプト

MCPBをClaude Desktopにインストールした後、新しいチャットで次のように依頼します。

```text
AP Invoice Review MCPBを使って、デモワークスペースを作成し、case-a-pay-readyをレビューしてください。PDFをOCRして、判定・根拠・次アクション・write_performed=falseを日本語で返してください。
```

他のケース:

```text
case-b-po-mismatchをレビューしてください
case-c-duplicateをレビューしてください
case-d-vendor-reviewをレビューしてください
case-e-grn-mismatchをレビューしてください
case-f-tax-reviewをレビューしてください
```

`/ap-review case-a` が使える環境では、それを使っても構いません。Claude Desktop/Coworkのバージョンによってslash command表示が異なる場合は、上の自然文プロンプトを使ってください。

## デモケース

| Case | Expected result | Meaning |
|---|---|---|
| `case-a-pay-ready` | `PAY_READY_CANDIDATE` | 支払候補 |
| `case-b-po-mismatch` | `REFER_PO_MISMATCH` | PO金額差異 |
| `case-c-duplicate` | `REFER_DUPLICATE_REVIEW` | 重複請求疑い |
| `case-d-vendor-review` | `REFER_VENDOR_REVIEW` | 取引先マスタ確認 |
| `case-e-grn-mismatch` | `REFER_GRN_MISMATCH` | 検収数量不足 |
| `case-f-tax-review` | `REFER_TAX_REVIEW` | 税額確認 |

## 主要MCPツール

通常のデモでは、Claudeが以下の流れでツールを呼びます。

```text
ap_invoice_setup_demo_workspace
ap_invoice_review_demo_case
Claude OCR
ap_invoice_submit_ocr_result
ap_invoice_review_from_ocr_result
ap_invoice_build_resolution_pack
```

フォルダを指定する場合は `ap_invoice_prepare_ocr_run` から始まります。

## 文書構成

利用者向け文書は `docs/` 直下に置いています。長い実装仕様、過去のhandoff、作業メモは `docs/archive/` に退避しています。MCPB成果物にはarchive文書を含めません。
