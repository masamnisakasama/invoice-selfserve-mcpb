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

## 日本語

このパッケージは現時点では vNext Milestone 0 のGo/No-Go確認段階です。実機Claude Desktopでsmoke testが通るまでは、APレビュー本体を「Claude OCRだけで動く実装」として扱わないでください。

### 管理者Mac

1. パッケージを作成します。

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
make test
make package-ap-mcpb
make verify-mcpb-contents
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
