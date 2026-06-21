# Claude Desktop Multi-PC Demo Runbook

## English

This runbook explains how to test the AP Invoice Exception Review MCPB from two machines.

- Admin/build PC: this Mac, where the project is developed and packaged.
- Demo PC: another PC, likely Windows, where Claude Desktop is used.

Repository:

```text
https://github.com/masamnisakasama/invoice-selfserve-mcpb
```

Demo package:

```text
dist/ap-invoice-review.mcpb
```

### Current Demo Scope

This is a local self-serve MCPB demo. It performs deterministic checks using bundled sample data only.

It does:

- Create AP review cases
- Upload bundled demo documents
- Run vendor, PO, GRN, duplicate, and tax checks
- Return rule results and evidence
- Build draft-only ERP/SaaS payloads

It does not:

- Write to freee, kintone, ERP, banking, or payment systems
- Use production customer data
- Authenticate users or enforce tenant authorization
- Process arbitrary local files outside bundled demo samples

### What To Do On This Mac

1. Go to the project.

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
```

2. Pull the latest repo state if needed.

```bash
git pull
```

3. Run full verification.

```bash
make test
make lint
make typecheck
make package-ap-mcpb
make verify-ap-data-boundary
make smoke-ap-mcp
```

4. Confirm the package exists.

```bash
ls -lh dist/ap-invoice-review.mcpb
```

5. Share the package with the demo PC.

Recommended options:

- Download from GitHub after cloning/pulling the repo on the demo PC.
- Send only `dist/ap-invoice-review.mcpb` if the demo PC only needs Claude Desktop install.
- If MCPB install has issues, send the whole repo and use the manual fallback config below.

6. Optional sanity check on this Mac.

```bash
uv run --directory . python -m ap_invoice_mcp
```

The command starts an MCP stdio server and will wait for MCP protocol input. Stop it with `Ctrl+C`.

### What To Do On The Claude Desktop PC

Prerequisites:

- Claude Desktop for Windows or macOS
- A Claude account that can use local MCP / Extensions
- Network access to GitHub, or the `.mcpb` file copied from this Mac

Recommended install path:

1. Download or copy:

```text
ap-invoice-review.mcpb
```

2. Open Claude Desktop.

3. Open Settings.

4. Open Extensions.

5. Install the `.mcpb` file.

Depending on Claude Desktop version, this may be:

- Double-click the `.mcpb` file.
- Drag the `.mcpb` file into the Extensions page.
- Use Settings -> Extensions -> Install Extension.

6. Enable the extension if Claude Desktop asks.

7. Start a new Claude Desktop chat.

8. Ask Claude to list or use the AP Invoice tools.

Example prompt:

```text
Use the AP Invoice Exception Review MCPB.
Create a demo AP review case for tenant demo-tenant.
Upload the bundled case-a-pay-ready invoice, purchase_order, and goods_receipt documents.
Start the review, get the result, and build a generic_ap draft payload.
Confirm that write_performed is false.
```

Expected result:

```text
case-a-pay-ready -> PAY_READY_CANDIDATE
write_performed -> false
```

Other expected demo cases:

```text
case-b-po-mismatch   -> REFER_PO_MISMATCH
case-c-duplicate     -> REFER_DUPLICATE_REVIEW
case-d-vendor-review -> REFER_VENDOR_REVIEW
```

### Manual Fallback: Windows Claude Desktop Config

Use this only if `.mcpb` installation does not work on the demo PC.

1. Install Git, Python 3.11+, and uv on the Windows PC.

2. Clone the repo.

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

You can also open it from Claude Desktop Settings -> Developer -> Edit Config.

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

5. Save the config.

6. Restart Claude Desktop, or reload MCP configuration if the app provides that button.

7. In a new chat, ask:

```text
List the available AP Invoice MCP tools.
```

Expected tools:

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

### File Paths For Manual Tool Calls

If Claude asks for exact local file paths in manual fallback mode, use paths under the cloned repo.

Windows examples:

```text
C:\Users\YOUR_WINDOWS_USER\Documents\invoice-selfserve-mcpb\samples\case-a-pay-ready\invoice.pdf
C:\Users\YOUR_WINDOWS_USER\Documents\invoice-selfserve-mcpb\samples\case-a-pay-ready\purchase_order.pdf
C:\Users\YOUR_WINDOWS_USER\Documents\invoice-selfserve-mcpb\samples\case-a-pay-ready\goods_receipt.pdf
```

macOS examples:

```text
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/samples/case-a-pay-ready/invoice.pdf
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/samples/case-a-pay-ready/purchase_order.pdf
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/samples/case-a-pay-ready/goods_receipt.pdf
```

### Troubleshooting

If Claude Desktop does not show the tools:

- Confirm the extension is enabled.
- Restart Claude Desktop.
- Check whether the installed Claude Desktop version supports MCPB/Extensions.
- Use the manual fallback config.
- Run `uv run python -m pytest -q tests/fixtures` in the cloned repo.
- Confirm `uv` is on PATH. In PowerShell, run `uv --version`.

If upload fails with a path error:

- This is expected for arbitrary files.
- The demo intentionally allows only bundled sample PDFs under `samples/` or `workflow-packs/ap-invoice-v1/samples/`.

If result is not as expected:

- Run `make generate-ap-samples` on Mac, or `uv run python scripts/generate_ap_samples.py` on Windows.
- Rebuild the package on Mac with `make package-ap-mcpb`.
- Reinstall the rebuilt `.mcpb`.

### Sources Checked

- Anthropic describes Desktop Extensions as one-click MCP server installation for Claude Desktop.
- The MCPB spec states that `.mcpb` files are zip archives containing a local MCP server and `manifest.json`.
- The MCPB manifest spec defines required fields such as `manifest_version`, `name`, `version`, `description`, `author`, and `server`.

Reference URLs:

- https://www.anthropic.com/engineering/desktop-extensions
- https://github.com/modelcontextprotocol/mcpb
- https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md

## Japanese

このrunbookは、AP Invoice Exception Review MCPB を2台構成で試すための手順です。

- 管理/ビルドPC: このMac。開発、検証、package作成を行います。
- デモPC: Claude Desktop を使う別PC。Windows想定です。

Repository:

```text
https://github.com/masamnisakasama/invoice-selfserve-mcpb
```

Demo package:

```text
dist/ap-invoice-review.mcpb
```

### 現在のデモ範囲

これはローカル self-serve MCPB デモです。同梱サンプルデータだけを使い、決定論的に照合します。

できること:

- AP review case作成
- 同梱デモ帳票のupload
- vendor、PO、GRN、duplicate、tax check
- rule result と evidence の返却
- draft-only ERP/SaaS payload生成

やらないこと:

- freee、kintone、ERP、銀行、支払システムへの本書き込み
- 顧客本番データ利用
- user認証やtenant authorization
- 同梱サンプル外の任意ローカルファイル処理

### このMacでやること

1. プロジェクトへ移動します。

```bash
cd /Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP
```

2. 必要なら最新化します。

```bash
git pull
```

3. 全検証を実行します。

```bash
make test
make lint
make typecheck
make package-ap-mcpb
make verify-ap-data-boundary
make smoke-ap-mcp
```

4. packageがあることを確認します。

```bash
ls -lh dist/ap-invoice-review.mcpb
```

5. デモPCへpackageを渡します。

おすすめ:

- デモPCでGitHubからclone/pullする
- Claude Desktopへ入れるだけなら `dist/ap-invoice-review.mcpb` だけ渡す
- MCPB installで詰まる場合に備えて、repo一式も渡せるようにしておく

6. 任意の起動確認です。

```bash
uv run --directory . python -m ap_invoice_mcp
```

これはMCP stdio serverを起動し、MCP protocol input待ちになります。止めるときは `Ctrl+C` です。

### Claude Desktopを使う別PCでやること

前提:

- Claude Desktop for Windows または macOS
- local MCP / Extensions が使えるClaude account
- GitHubへアクセスできる、または `.mcpb` fileをこのMacからコピー済み

推奨install:

1. 以下をdownloadまたはcopyします。

```text
ap-invoice-review.mcpb
```

2. Claude Desktopを開きます。

3. Settingsを開きます。

4. Extensionsを開きます。

5. `.mcpb` fileをinstallします。

Claude Desktopのversionによって操作は少し違う可能性があります。

- `.mcpb` fileをdouble-click
- Extensions画面へdrag
- Settings -> Extensions -> Install Extension から選択

6. Claude Desktopが聞いてきたらextensionをenableします。

7. 新しいchatを開きます。

8. AP Invoice toolsを使うようClaudeに依頼します。

Example prompt:

```text
Use the AP Invoice Exception Review MCPB.
Create a demo AP review case for tenant demo-tenant.
Upload the bundled case-a-pay-ready invoice, purchase_order, and goods_receipt documents.
Start the review, get the result, and build a generic_ap draft payload.
Confirm that write_performed is false.
```

期待結果:

```text
case-a-pay-ready -> PAY_READY_CANDIDATE
write_performed -> false
```

他のデモケース期待値:

```text
case-b-po-mismatch   -> REFER_PO_MISMATCH
case-c-duplicate     -> REFER_DUPLICATE_REVIEW
case-d-vendor-review -> REFER_VENDOR_REVIEW
```

### 手動fallback: Windows Claude Desktop Config

`.mcpb` installがうまくいかない場合だけ使います。

1. Windows PCに Git、Python 3.11+、uv を入れます。

2. repoをcloneします。

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

Claude Desktop Settings -> Developer -> Edit Config から開ける場合もあります。

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

5. configを保存します。

6. Claude Desktopをrestartします。Reload MCP Configurationボタンがあればそれでも構いません。

7. 新しいchatで聞きます。

```text
List the available AP Invoice MCP tools.
```

期待されるtools:

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

### 手動tool call用のファイルpath

Claudeが正確なpathを求める場合は、cloneしたrepo配下のsampleを指定します。

Windows例:

```text
C:\Users\YOUR_WINDOWS_USER\Documents\invoice-selfserve-mcpb\samples\case-a-pay-ready\invoice.pdf
C:\Users\YOUR_WINDOWS_USER\Documents\invoice-selfserve-mcpb\samples\case-a-pay-ready\purchase_order.pdf
C:\Users\YOUR_WINDOWS_USER\Documents\invoice-selfserve-mcpb\samples\case-a-pay-ready\goods_receipt.pdf
```

macOS例:

```text
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/samples/case-a-pay-ready/invoice.pdf
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/samples/case-a-pay-ready/purchase_order.pdf
/Users/ikedamasahiro/Agentmemory_MVP/invoice-selfserveMCP/samples/case-a-pay-ready/goods_receipt.pdf
```

### Troubleshooting

Claude Desktopにtoolsが出ない場合:

- extensionがenabledか確認
- Claude Desktopをrestart
- Claude DesktopのversionがMCPB/Extensions対応か確認
- manual fallback configを使う
- cloneしたrepoで `uv run python -m pytest -q tests/fixtures` を実行
- `uv` がPATHにいるか確認。PowerShellで `uv --version`

uploadがpath errorになる場合:

- これは想定動作です。
- デモでは安全のため、`samples/` または `workflow-packs/ap-invoice-v1/samples/` 配下の同梱PDFだけ許可しています。

結果が期待と違う場合:

- Macでは `make generate-ap-samples` を実行
- Windowsでは `uv run python scripts/generate_ap_samples.py` を実行
- Macで `make package-ap-mcpb` を再実行
- 再生成した `.mcpb` を入れ直す

### 確認した外部仕様

- AnthropicはDesktop ExtensionsをClaude Desktop向けのone-click MCP server installationとして説明しています。
- MCPB specでは、`.mcpb` はlocal MCP serverと `manifest.json` を含むzip archiveです。
- MCPB manifest specでは、`manifest_version`、`name`、`version`、`description`、`author`、`server` などがrequiredです。

Reference URLs:

- https://www.anthropic.com/engineering/desktop-extensions
- https://github.com/modelcontextprotocol/mcpb
- https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
