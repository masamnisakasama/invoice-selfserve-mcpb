# MCPB Validation

この文書は、`dist/ap-invoice-review.mcpb` を配布・デモする前に実行する検証手順です。

## 一括validation

通常はこれだけ実行します。

```bash
make validate-mcpb-release
```

含まれる検証:

- `make lint`
- `make typecheck`
- `make test`
- `make package-ap-mcpb`
- `make verify-ap-data-boundary`
- `make verify-mcpb-contents`
- `make verify-no-answer-sidecars`
- `make verify-ocr-smoke-gate`
- `make verify-e2e-ocr-flow`
- `make smoke-ap-mcp`
- `make verify-mcpb-schema`

## 何を保証するか

`make validate-mcpb-release` は、ローカルで検証できるMCPB品質をまとめて確認します。

- MCPB manifestが公式schemaに通る
- MCPBに必要なtools/prompts/commands/skillsが入っている
- `commands/ap-review.md` と `.claude/commands/ap-review.md` が一致している
- `skills/ap-review/SKILL.md` と `.claude/skills/ap-review/SKILL.md` が一致している
- root samples と workflow-pack samples の両方に6ケース×3帳票のPDFがある
- PDFが画像レンダリングPDFで、テキストレイヤーに逃げていない
- 請求書、発注書、納品書/検収書が同じ見た目になっていない
- sample JSON sidecarが入っていない
- BOM入りテキストファイルが入っていない
- 作業メモやarchive文書がMCPBに混ざっていない
- 外部SaaS/ERP/支払の本書き込みを示すpayloadが入っていない
- E2E OCR flowのtool sequenceが通る
- MCP smokeが通る

## 手動Go/No-Go

ローカルvalidationでは、Claude Desktop実機がMCP tool resultの画像を本当にvision/OCR入力として扱うかまでは完全には保証できません。

Claude DesktopにMCPBを入れた後、次を実行してください。

```text
AP Invoice OCR smoke testを実行して。返された画像をOCRして、submit toolにinvoice_numberとtotal_amountを渡してください。
```

Go条件:

- `ap_invoice_ocr_smoke_test` が呼ばれる
- Claudeが返された画像をOCRする
- `ap_invoice_submit_ocr_smoke_test_result` が呼ばれる
- 結果が `OCR_SMOKE_TEST_PASSED` になる
- Airtable、Google Drive、外部connector registryを使わない

No-Go条件:

- Claude Desktopが画像を読めない
- submit toolを呼ばない
- 画像以外の場所に答えを書かないと通らない
- JSON sidecarやPDFテキスト抽出に逃げる

## 成果物

配布対象はMCPBのみです。

```text
dist/ap-invoice-review.mcpb
```

`.plugin` はデモ対象ではありません。
