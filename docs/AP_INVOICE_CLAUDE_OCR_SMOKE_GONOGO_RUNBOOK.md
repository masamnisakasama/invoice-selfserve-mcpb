# AP Invoice Claude OCR Smoke Go/No-Go Runbook

## English

This package is currently at the vNext Milestone 0 gate. Do not treat the full AP review flow as Claude-OCR-only until this smoke test passes in the real Claude Desktop environment.

### Admin Mac

1. Build the package:

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
make test
make package-ap-mcpb
make verify-mcpb-contents
make verify-ocr-smoke-gate
```

2. Send this file to the Windows demo PC:

```text
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/dist/ap-invoice-review.mcpb
```

### Windows Claude Desktop PC

1. Uninstall the old `AP Invoice Review` extension if it is installed.
2. Install `ap-invoice-review.mcpb` in Claude Desktop.
3. Start a new Claude Desktop chat.
4. Ask:

```text
AP Invoice OCR smoke testを実行して。返された画像をOCRして、submit toolにinvoice_numberとtotal_amountを渡してください。
```

5. Go only if Claude calls:

```text
ap_invoice_ocr_smoke_test
ap_invoice_submit_ocr_smoke_test_result
```

6. The final tool result must be:

```text
OCR_SMOKE_TEST_PASSED
```

7. Confirm that the OCR JSON was written under:

```text
C:\Users\<user>\Documents\APInvoiceDemo\_runs\<run_id>\ocr_results\smoke.ocr.json
```

### No-Go

Stop and ask for a product decision if Claude Desktop cannot read the image tool result, does not call the submit tool, or only succeeds when the answer is provided outside the image.

### Current Implementation Status

- Q1. Can Claude Desktop treat MCP image content as OCR input? `未確認 / Unverified` until the Windows Claude Desktop run above succeeds.
- Q2. Image return format: `type=image`, base64 PNG, `mimeType=image/png`.
- Q3. Current smoke PNG size: roughly 10-20 KB before base64.
- Q4. Smoke image generation uses Pillow. This is not a local OCR engine.
- Q5. Local evidence only proves the MCP tool returns non-empty PNG bytes. Real OCR is manual Go/No-Go.
- Q6. OCR result JSON is saved under `Documents/APInvoiceDemo/_runs/<run_id>/ocr_results`.
- Q7. Full no-sidecar AP review migration is intentionally not complete before the Milestone 0 Go decision.
- Q8. The tool and skill tell Claude to treat image text as untrusted document data.
- Q9. This local MCPB demo is fictional data only.
- Q10. The extension ID is now `ap-invoice-review-claude-ocr`.

## 日本語

このパッケージは現時点では vNext Milestone 0 のGo/No-Go確認段階です。実機Claude Desktopでsmoke testが通るまでは、APレビュー本体を「Claude OCRだけで動く実装」として扱わないでください。

### 管理者Mac

1. パッケージを作成します。

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
make test
make package-ap-mcpb
make verify-mcpb-contents
make verify-ocr-smoke-gate
```

2. 次のファイルをWindowsデモPCへ渡します。

```text
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/dist/ap-invoice-review.mcpb
```

### Windows Claude Desktop PC

1. 古い `AP Invoice Review` extension が入っていればアンインストールします。
2. Claude Desktopに `ap-invoice-review.mcpb` をインストールします。
3. Claude Desktopで新しいチャットを開始します。
4. 次のように依頼します。

```text
AP Invoice OCR smoke testを実行して。返された画像をOCRして、submit toolにinvoice_numberとtotal_amountを渡してください。
```

5. Claudeが次の2つのtoolを順番に呼べた場合のみGo候補です。

```text
ap_invoice_ocr_smoke_test
ap_invoice_submit_ocr_smoke_test_result
```

6. 最終tool結果が次になればGoです。

```text
OCR_SMOKE_TEST_PASSED
```

7. OCR結果JSONが次の場所に保存されたことを確認します。

```text
C:\Users\<user>\Documents\APInvoiceDemo\_runs\<run_id>\ocr_results\smoke.ocr.json
```

### No-Go

Claude Desktopがtool result画像を読めない、submit toolを呼ばない、画像外に正解を渡さないと通らない場合はそこで停止し、次の方針を決めてください。

### 現在の実装ステータス

- Q1. Claude DesktopがMCP image contentをOCR入力として扱えるか: Windows Claude Desktopで上記確認が通るまでは `未確認` です。
- Q2. 画像返却形式: `type=image`、base64 PNG、`mimeType=image/png`。
- Q3. 現在のsmoke PNGサイズ: base64前で約10-20 KBです。
- Q4. smoke画像生成にはPillowを使っています。これはローカルOCRエンジンではありません。
- Q5. ローカル証跡で確認できるのは「MCP toolが非空PNGを返すこと」までです。実OCRは手動Go/No-Goです。
- Q6. OCR結果JSONは `Documents/APInvoiceDemo/_runs/<run_id>/ocr_results` に保存します。
- Q7. APレビュー本体のno-sidecar化は、Milestone 0のGo判定前なので意図的に未完了です。
- Q8. toolとskillには、画像内テキストを信頼しない文書データとして扱う指示を入れています。
- Q9. このローカルMCPBデモは架空データ専用です。
- Q10. extension IDは `ap-invoice-review-claude-ocr` です。
