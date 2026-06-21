# Claude Desktop Multi-PC Demo Runbook

## English

This runbook explains how to test the AP Invoice Review MCPB from two machines.

- Admin/build PC: this Mac, where the package is built.
- Demo PC: another PC, usually Windows, where Claude Desktop installs and runs the MCPB.

Repository:

```text
https://github.com/masamnisakasama/invoice-selfserve-mcpb
```

Demo package:

```text
dist/ap-invoice-review.mcpb
```

### Current Scope

This MCPB is a local, fictional-data demo for AP invoice review.

It does:

- Export visible sample PDFs to `Documents/APInvoiceDemo`.
- Render invoice, purchase order, and goods receipt PDFs to images.
- Require Claude Desktop vision/OCR before AP rule evaluation.
- Save OCR result JSON only under `Documents/APInvoiceDemo/_runs/<run_id>/ocr_results`.
- Run vendor, PO, GRN, duplicate, and tax checks from OCR-derived canonical facts.
- Return the final AP decision, evidence, next actions, draft payload summary, and `write_performed=false`.

It does not:

- Use input-folder JSON sidecars.
- Use local OCR, PDF text extraction, Bedrock, Textract, or an external OCR API.
- Use Airtable, Google Drive, or external connector registry.
- Write to freee, kintone, ERP, banking, or payment systems.
- Process production customer data.

### What To Do On This Mac

1. Go to the project.

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
```

2. Run verification.

```bash
make lint
make typecheck
make test
make package-ap-mcpb
make verify-no-answer-sidecars
make verify-mcpb-contents
make verify-ap-data-boundary
make verify-ocr-smoke-gate
make verify-e2e-ocr-flow
make smoke-ap-mcp
```

3. Confirm the package exists.

```bash
ls -lh dist/ap-invoice-review.mcpb
```

4. Send this file to the demo PC:

```text
dist/ap-invoice-review.mcpb
```

If MCPB install does not work on the demo PC, send the whole repository and use the manual fallback below.

### What To Do On The Claude Desktop PC

Prerequisites:

- Claude Desktop for Windows or macOS.
- A Claude account that can use local MCP / Desktop Extensions.
- The `.mcpb` file copied from this Mac, or access to the GitHub repository.

Recommended install:

1. Copy `ap-invoice-review.mcpb` to the demo PC.
2. Open Claude Desktop.
3. Open Settings, then Extensions.
4. Install the `.mcpb` file.
5. Enable the extension if Claude Desktop asks.
6. Start a new Claude Desktop chat.

Depending on Claude Desktop version, install may be double-click, drag-and-drop, or Settings -> Extensions -> Install Extension.

### Demo Prompts

Start with:

```text
Use the AP Invoice Review MCPB.
Start the AP Invoice demo.
Set up the visible local demo workspace, show me the PDF paths, then review case-a-pay-ready end-to-end.
Use Claude OCR. Do not use Airtable or Google Drive. Confirm write_performed=false.
```

Expected internal flow:

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_review_demo_case or ap_invoice_prepare_ocr_run
Claude reads the returned images with vision/OCR
ap_invoice_submit_ocr_result
ap_invoice_review_from_ocr_result
```

Expected result:

```text
case-a-pay-ready -> PAY_READY_CANDIDATE
write_performed -> false
```

Then test a folder-first review:

```text
Review this AP invoice folder end-to-end with Claude OCR:
C:\Users\<WindowsUser>\Documents\APInvoiceDemo\case-b-po-mismatch
Do not use sidecar JSON. Confirm write_performed=false.
```

Expected result:

```text
case-b-po-mismatch -> REFER_PO_MISMATCH
```

Other expected cases:

```text
case-c-duplicate     -> REFER_DUPLICATE_REVIEW
case-d-vendor-review -> REFER_VENDOR_REVIEW
case-e-grn-mismatch  -> REFER_GRN_MISMATCH
case-f-tax-review    -> REFER_TAX_REVIEW
```

### Expected Tools

High-level and OCR tools:

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_preview_folder
ap_invoice_prepare_ocr_run
ap_invoice_submit_ocr_result
ap_invoice_review_from_ocr_result
ap_invoice_review_folder
ap_invoice_review_demo_case
ap_invoice_explain_exception
ap_invoice_build_approval_brief
```

Diagnostic tools:

```text
ap_invoice_ocr_smoke_test
ap_invoice_submit_ocr_smoke_test_result
```

Legacy compatibility tools may still appear, but they are intentionally blocked. Do not use them for the demo.

### Manual Fallback: Windows Claude Desktop Config

Use this only if `.mcpb` installation does not work.

1. Install Git, Python 3.11+, and `uv` on the Windows PC.

2. Clone the repository.

```powershell
cd $env:USERPROFILE\Documents
git clone https://github.com/masamnisakasama/invoice-selfserve-mcpb.git
cd invoice-selfserve-mcpb
uv sync
uv run python -m pytest -q tests/fixtures
```

3. Open Claude Desktop config.

Common path:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

4. Add or merge this MCP server config.

Replace `YOUR_WINDOWS_USER` if needed.

```json
{
  "mcpServers": {
    "ap-invoice-review": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\YOUR_WINDOWS_USER\\Documents\\invoice-selfserve-mcpb",
        "python",
        "-m",
        "ap_invoice_mcp"
      ]
    }
  }
}
```

5. Restart Claude Desktop, or reload MCP configuration if available.

6. In a new chat, ask:

```text
List the available AP Invoice MCP tools.
```

### Troubleshooting

If tools do not appear:

- Confirm the extension is enabled.
- Restart Claude Desktop.
- Check whether the installed Claude Desktop version supports MCPB / Extensions.
- Use the manual fallback config.
- Confirm `uv` is on PATH by running `uv --version`.

If Claude stops after OCR preparation:

- Ask it to continue with the returned images, submit structured OCR results, then call `ap_invoice_review_from_ocr_result`.
- The correct sequence is prepare -> Claude OCR -> submit -> review.

If JSON sidecar errors appear:

- Remove `*.json` from the input folder.
- This version intentionally requires PDF-only input folders.
- OCR result JSON belongs under `_runs/<run_id>/ocr_results`, not next to the PDFs.

If a result differs from expected:

- On Mac, rebuild with `make package-ap-mcpb`.
- Reinstall the rebuilt `.mcpb`.
- Confirm the demo prompt says to use Claude OCR and not Airtable or Google Drive.

### References

- https://www.anthropic.com/engineering/desktop-extensions
- https://github.com/modelcontextprotocol/mcpb
- https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md

## Japanese

このrunbookは、AP Invoice Review MCPBを2台構成で試すための手順です。

- 管理/ビルドPC: このMac。packageを作成します。
- デモPC: Claude Desktopを使う別PC。通常はWindows想定です。

Repository:

```text
https://github.com/masamnisakasama/invoice-selfserve-mcpb
```

Demo package:

```text
dist/ap-invoice-review.mcpb
```

### 現在の範囲

これはローカル・架空データ専用のAP請求書レビューMCPBデモです。

できること:

- 見えるサンプルPDFを `Documents/APInvoiceDemo` に展開する
- 請求書、発注書、検収書PDFを画像としてレンダリングする
- APルール判定前にClaude Desktopのvision/OCRを必須にする
- OCR結果JSONを `Documents/APInvoiceDemo/_runs/<run_id>/ocr_results` にだけ保存する
- OCR由来のcanonical factsから vendor、PO、GRN、duplicate、tax check を実行する
- 最終判定、根拠、次アクション、draft payload summary、`write_performed=false` を返す

やらないこと:

- 入力フォルダのJSON sidecar利用
- local OCR、PDF text extraction、Bedrock、Textract、外部OCR API利用
- Airtable、Google Drive、外部connector registry利用
- freee、kintone、ERP、銀行、支払システムへの本書き込み
- 顧客本番データ処理

### このMacでやること

1. プロジェクトへ移動します。

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
```

2. 検証を実行します。

```bash
make lint
make typecheck
make test
make package-ap-mcpb
make verify-no-answer-sidecars
make verify-mcpb-contents
make verify-ap-data-boundary
make verify-ocr-smoke-gate
make verify-e2e-ocr-flow
make smoke-ap-mcp
```

3. packageがあることを確認します。

```bash
ls -lh dist/ap-invoice-review.mcpb
```

4. デモPCへこのファイルを渡します。

```text
dist/ap-invoice-review.mcpb
```

MCPB installがうまくいかない場合に備えるなら、repo一式も渡して手動fallbackを使います。

### Claude Desktopを使う別PCでやること

前提:

- Claude Desktop for Windows または macOS
- local MCP / Desktop Extensions が使えるClaude account
- このMacからコピーした `.mcpb` file、またはGitHub repositoryへのアクセス

推奨install:

1. `ap-invoice-review.mcpb` をデモPCへコピーします。
2. Claude Desktopを開きます。
3. Settings、Extensionsを開きます。
4. `.mcpb` fileをinstallします。
5. Claude Desktopが聞いてきたらextensionをenableします。
6. 新しいClaude Desktop chatを開きます。

Claude Desktopのversionによって、double-click、drag-and-drop、Settings -> Extensions -> Install Extension など操作が変わる可能性があります。

### デモ用プロンプト

まず以下を使います。

```text
Use the AP Invoice Review MCPB.
Start the AP Invoice demo.
Set up the visible local demo workspace, show me the PDF paths, then review case-a-pay-ready end-to-end.
Use Claude OCR. Do not use Airtable or Google Drive. Confirm write_performed=false.
```

期待される内部flow:

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_review_demo_case または ap_invoice_prepare_ocr_run
Claudeが返された画像をvision/OCRで読む
ap_invoice_submit_ocr_result
ap_invoice_review_from_ocr_result
```

期待結果:

```text
case-a-pay-ready -> PAY_READY_CANDIDATE
write_performed -> false
```

次にfolder-first reviewを試します。

```text
Review this AP invoice folder end-to-end with Claude OCR:
C:\Users\<WindowsUser>\Documents\APInvoiceDemo\case-b-po-mismatch
Do not use sidecar JSON. Confirm write_performed=false.
```

期待結果:

```text
case-b-po-mismatch -> REFER_PO_MISMATCH
```

他の期待ケース:

```text
case-c-duplicate     -> REFER_DUPLICATE_REVIEW
case-d-vendor-review -> REFER_VENDOR_REVIEW
case-e-grn-mismatch  -> REFER_GRN_MISMATCH
case-f-tax-review    -> REFER_TAX_REVIEW
```

### 期待されるtools

High-level / OCR tools:

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_preview_folder
ap_invoice_prepare_ocr_run
ap_invoice_submit_ocr_result
ap_invoice_review_from_ocr_result
ap_invoice_review_folder
ap_invoice_review_demo_case
ap_invoice_explain_exception
ap_invoice_build_approval_brief
```

Diagnostic tools:

```text
ap_invoice_ocr_smoke_test
ap_invoice_submit_ocr_smoke_test_result
```

legacy compatibility toolsが見える場合がありますが、意図的にblockedです。デモでは使いません。

### 手動fallback: Windows Claude Desktop Config

`.mcpb` installがうまくいかない場合だけ使います。

1. Windows PCに Git、Python 3.11+、`uv` を入れます。

2. repositoryをcloneします。

```powershell
cd $env:USERPROFILE\Documents
git clone https://github.com/masamnisakasama/invoice-selfserve-mcpb.git
cd invoice-selfserve-mcpb
uv sync
uv run python -m pytest -q tests/fixtures
```

3. Claude Desktop configを開きます。

一般的なpath:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

4. 以下のMCP server configを追加またはmergeします。

`YOUR_WINDOWS_USER` は必要に応じて置き換えます。

```json
{
  "mcpServers": {
    "ap-invoice-review": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\YOUR_WINDOWS_USER\\Documents\\invoice-selfserve-mcpb",
        "python",
        "-m",
        "ap_invoice_mcp"
      ]
    }
  }
}
```

5. Claude Desktopをrestartします。reload MCP configurationがあればそれでも構いません。

6. 新しいchatで聞きます。

```text
List the available AP Invoice MCP tools.
```

### Troubleshooting

toolsが出ない場合:

- extensionがenabledか確認
- Claude Desktopをrestart
- Claude Desktop versionがMCPB / Extensions対応か確認
- manual fallback configを使う
- `uv --version` で `uv` がPATHにいるか確認

ClaudeがOCR準備で止まる場合:

- 返された画像を読んで、structured OCR resultをsubmitし、`ap_invoice_review_from_ocr_result` を呼ぶよう依頼します。
- 正しい順番は prepare -> Claude OCR -> submit -> review です。

JSON sidecar errorが出る場合:

- 入力フォルダから `*.json` を削除します。
- このversionはPDF-only input folderを意図的に要求します。
- OCR結果JSONはPDF横ではなく `_runs/<run_id>/ocr_results` 配下に保存されます。

結果が期待と違う場合:

- Macで `make package-ap-mcpb` を実行して再buildします。
- 再生成した `.mcpb` をinstallし直します。
- promptで Claude OCRを使うこと、Airtable/Google Driveを使わないことを明示します。

### References

- https://www.anthropic.com/engineering/desktop-extensions
- https://github.com/modelcontextprotocol/mcpb
- https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
