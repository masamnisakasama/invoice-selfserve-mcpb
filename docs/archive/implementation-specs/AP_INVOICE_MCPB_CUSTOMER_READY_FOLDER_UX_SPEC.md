# AP Invoice MCPB vNext 実装指示書
## Customer-Ready Folder UX / デモ使用者起点の再設計

## 0. 結論

現状のMCPBは、ConnectorがONになり、MCP toolsが登録されるところまでは進んでいる。しかし、顧客デモとしてはまだ弱い。

失敗している体験は以下。

```text
- ユーザーが「AP Invoiceのデモケース一覧を表示して」と言ってもAirtableへ逃げる
- ConnectorはONだが、どの帳票を読んでいるか分からない
- MCPB内部samplesを勝手に読むだけでは、ユーザーに実体が見えない
- 「このフォルダ内をレビューして」で動かない
- 低レベルtoolの存在は見えるが、業務フローとして使えない
```

vNextでは、**「このフォルダ内をレビューして」で、見えるPDFを使ったAP請求書レビューが完了する**ことを最重要要件にする。

目指す体験:

```text
.mcpbを入れる
→ AP Invoiceデモを開始して
→ Documents\APInvoiceDemo にサンプルPDFが展開される
→ ユーザーがExplorerでPDFを開ける
→ case-aをレビューして / このフォルダ内をレビューして
→ 請求書・発注書・検収書を自動分類
→ 3-way match / vendor / duplicate / tax check
→ 判定・根拠・次アクション・draft payloadを表示
→ write_performed=false を明示
```

これは単なるサンプル実行ではなく、**顧客が「自分のPC上の帳票フォルダをレビューできる」と理解できる体験**である。

---

## 1. 最重要UX原則

### 1.1 ConnectorがONは成功ではない

成功条件は以下。

```text
- ユーザーが見ることのできるローカルPDFがある
- ClaudeがどのPDFを使うかレビュー前に表示する
- フォルダを渡すだけでレビューが走る
- 結果が業務語彙で返る
- 外部書き込みしていないことが明示される
```

### 1.2 内部samplesだけで勝手に処理しない

MCPB内部にsamplesがあるだけでは、顧客には実体が見えない。

NG:

```text
MCPB内部のsamples/case-aを処理しました。
```

OK:

```text
サンプル帳票を以下に展開しました。
C:\Users\Owner\Documents\APInvoiceDemo\case-a-pay-ready

使用帳票:
- invoice.pdf
- purchase_order.pdf
- goods_receipt.pdf

この3帳票でレビューします。
```

### 1.3 GitHub cloneや手動パス指定を要求しない

`.mcpb`インストール後に、以下をユーザーへ要求してはいけない。

```text
GitHubからsamplesをcloneしてください
zipを展開してください
Downloads配下のsamplesを指定してください
```

MCPB自身がサンプルを `Documents\APInvoiceDemo` に展開する。

### 1.4 他connectorへ逃げない

実機でAirtableに逃げた。これはUX regressionとして扱う。

禁止:

```text
Airtable
Google Drive
mcp-registry
外部connector検索
```

AP Invoice関連の依頼では、必ずAP Invoice MCPB toolを最優先する。

---

## 2. 顧客に見せる業務価値

このMCPBはOCRデモではない。価値は以下。

```text
請求書 + 発注書 + 納品書/検収書 + 取引先マスタ + 過去請求 + 税コード + 支払ルール
    ↓
canonical facts
    ↓
vendor master match / PO match / GRN match / duplicate check / tax check
    ↓
支払候補・PO差異・重複疑い・取引先確認・税務確認
    ↓
根拠・監査証跡・draft-only ERP/SaaS payload
```

既存製品との差分:

```text
OCR製品:
  読むだけ。判断・照合・監査証跡は別。

iPaaS:
  接続はできるが、設定が重い。

会計SaaS:
  登録先としては強いが、複数帳票横断の例外レビューは設定が必要。

AP Invoice MCPB:
  フォルダを渡すだけで、支払前レビューpacketとdraft payloadができる。
```

デモで言うべき一言:

```text
このフォルダをレビューして、と言うだけで、
請求書・発注書・検収書を見分け、
支払候補か、PO差異か、重複疑いか、取引先確認かを根拠付きで返します。
外部システムには書き込みません。
```

---

## 3. 主役UX: Folder-first Review

vNextの主役toolはこれ。

```text
ap_invoice_review_folder
```

ユーザー入力例:

```text
C:\Users\Owner\Documents\APInvoiceDemo\case-b-po-mismatch
このフォルダ内をレビューして
```

または:

```text
/HOGEHOGE このフォルダ内をレビューして
```

tool入力:

```json
{
  "folder_path": "C:\\Users\\Owner\\Documents\\APInvoiceDemo\\case-b-po-mismatch",
  "tenant_id": "demo-tenant",
  "target_system": "generic_ap"
}
```

処理:

```text
1. フォルダ存在確認
2. PDF一覧取得
3. sidecar JSON一覧取得
4. invoice / purchase_order / goods_receipt へ分類
5. 必須帳票・sidecar確認
6. 処理前previewを返す
7. AP review実行
8. draft payload生成
9. 業務レポートpacket生成
```

正常出力イメージ:

```json
{
  "folder_path": "C:\\Users\\Owner\\Documents\\APInvoiceDemo\\case-b-po-mismatch",
  "detected_documents": [
    {"document_type": "invoice", "path": "...\\invoice.pdf"},
    {"document_type": "purchase_order", "path": "...\\purchase_order.pdf"},
    {"document_type": "goods_receipt", "path": "...\\goods_receipt.pdf"}
  ],
  "recommendation": "REFER_PO_MISMATCH",
  "recommendation_label_ja": "発注書差異確認",
  "business_meaning_ja": "PO金額・承認・残高・取引先などの確認が必要です。",
  "rule_ids": ["AP-PO-001"],
  "next_actions_ja": [
    "購買担当にPO変更有無を確認してください。",
    "変更POがある場合は承認済みPOを追加してください。",
    "変更がない場合は請求書差戻し候補として扱ってください。"
  ],
  "draft_payload_summary": {
    "payment_status": "draft",
    "write_performed": false
  },
  "write_performed": false
}
```

---

## 4. Demo Workspace

### 4.1 `ap_invoice_setup_demo_workspace`

目的:

```text
MCPB同梱samplesを、ユーザーが見えるDocuments配下へ展開する
```

入力:

```json
{
  "workspace_dir": null,
  "overwrite": false
}
```

`workspace_dir` がnullなら:

```text
Path.home() / "Documents" / "APInvoiceDemo"
```

出力:

```json
{
  "workspace_dir": "C:\\Users\\Owner\\Documents\\APInvoiceDemo",
  "cases": [
    {
      "case_id": "case-a-pay-ready",
      "case_dir": "C:\\Users\\Owner\\Documents\\APInvoiceDemo\\case-a-pay-ready",
      "documents": [
        {"document_type": "invoice", "path": "...\\invoice.pdf"},
        {"document_type": "purchase_order", "path": "...\\purchase_order.pdf"},
        {"document_type": "goods_receipt", "path": "...\\goods_receipt.pdf"}
      ]
    }
  ],
  "usage_ja": "PDFを開いて確認できます。レビューする場合は『case-aをレビューして』またはフォルダパスを指定してください。",
  "write_performed": false
}
```

必ずコピーするもの:

```text
samples/case-a-pay-ready/
  invoice.pdf
  invoice.json
  purchase_order.pdf
  purchase_order.json
  goods_receipt.pdf
  goods_receipt.json

samples/case-b-po-mismatch/
samples/case-c-duplicate/
samples/case-d-vendor-review/
```

### 4.2 `ap_invoice_list_demo_cases`

workspace展開状況も含めて返す。

```json
{
  "workspace_dir": "C:\\Users\\Owner\\Documents\\APInvoiceDemo",
  "workspace_initialized": true,
  "demo_cases": [
    {
      "case_id": "case-a-pay-ready",
      "short_aliases": ["case-a", "a"],
      "label_ja": "支払候補",
      "expected_recommendation": "PAY_READY_CANDIDATE",
      "business_value_ja": "請求書・PO・GRN・税額・重複なしが一致する正常系です。",
      "case_dir": "...\\case-a-pay-ready",
      "documents": ["invoice.pdf", "purchase_order.pdf", "goods_receipt.pdf"]
    }
  ],
  "write_performed": false
}
```

### 4.3 `ap_invoice_preview_folder`

レビュー前に、フォルダ内の帳票と主要項目を表示する。

入力:

```json
{
  "folder_path": "C:\\Users\\Owner\\Documents\\APInvoiceDemo\\case-b-po-mismatch"
}
```

出力:

```json
{
  "folder_path": "...",
  "detected_documents": [
    {
      "document_type": "invoice",
      "path": "...\\invoice.pdf",
      "key_fields": {
        "invoice_number": "INV-2026-0009",
        "vendor_id": "V-1001",
        "po_number": "PO-2026-0002",
        "total_amount": 121000
      }
    }
  ],
  "ready_for_review": true,
  "write_performed": false
}
```

---

## 5. フォルダ内ファイル分類

### 5.1 ファイル名分類

invoice候補:

```text
invoice.pdf
請求書.pdf
*_invoice.pdf
invoice_*.pdf
```

purchase_order候補:

```text
purchase_order.pdf
po.pdf
発注書.pdf
*_po.pdf
```

goods_receipt候補:

```text
goods_receipt.pdf
grn.pdf
receipt.pdf
納品書.pdf
検収書.pdf
inspection_report.pdf
```

### 5.2 sidecar優先

`*.json` sidecarに `document_type` がある場合は、それを優先する。  
PDF名とsidecarが矛盾する場合はfail fast。

### 5.3 分類できない場合

勝手に推測して進めない。明確に返す。

```json
{
  "error_code": "DOCUMENT_CLASSIFICATION_REQUIRED",
  "message_ja": "フォルダ内に分類できないPDFがあります。どの帳票種別か確認してください。",
  "unclassified_files": ["2026-07-tokyo-office-supply.pdf"],
  "detected_documents": {
    "invoice": null,
    "purchase_order": "purchase_order.pdf",
    "goods_receipt": "goods_receipt.pdf"
  },
  "allowed_document_types": ["invoice", "purchase_order", "goods_receipt"]
}
```

---

## 6. 必須tools

### 6.1 ユーザー向けtools

manifest先頭に置く。

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_preview_folder
ap_invoice_review_folder
ap_invoice_review_demo_case
ap_invoice_explain_exception
ap_invoice_build_approval_brief
```

### 6.2 既存advanced tools

残すが通常UXでは使わせない。

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

---

## 7. Skill / Prompt設計

### 7.1 `/ap-demo`

実行順:

```text
1. ap_invoice_setup_demo_workspace
2. ap_invoice_list_demo_cases
3. ユーザーにケース一覧を表示
4. 選択されたケースに対して ap_invoice_preview_folder
5. ap_invoice_review_folder
```

必ず表示する文:

```text
サンプル帳票をローカルに展開しました。
PDFを開いて確認できます。
外部ERP/SaaSへの書き込みは行いません。
```

### 7.2 `/ap-review`

判断:

```text
フォルダパスあり:
  ap_invoice_review_folder

case-a / case-bなど:
  ap_invoice_review_demo_case

何も指定なし:
  ap_invoice_list_demo_cases
```

### 7.3 `/ap-explain`

直近jobに対して:

```text
ap_invoice_explain_exception
```

### 7.4 `/ap-approval-brief`

直近jobに対して:

```text
ap_invoice_build_approval_brief
```

---

## 8. SKILL.md 必須文言

必ず入れる。

```text
Use AP Invoice MCPB tools before any other connector.
Do not search Airtable.
Do not use Google Drive unless the user explicitly asks for Google Drive.
Do not search external connector registry.
Do not ask the user to clone GitHub samples.
Do not ask the user to type long file paths for bundled demo cases.
If the user gives a folder path, call ap_invoice_review_folder.
If the user asks for a demo, call ap_invoice_setup_demo_workspace first.
Show visible local PDF paths before review.
Never claim external ERP/SaaS writes.
Always show write_performed=false.
```

---

## 9. Manifest改善

### 9.1 version

```json
"version": "0.4.0"
```

### 9.2 display_name

```json
"display_name": "AP Invoice Review — Folder Demo"
```

### 9.3 long_description

必ず以下を含める。

```text
Review AP invoice folders by detecting invoice, purchase order, and goods receipt PDFs from a visible local folder. Includes bundled demo PDFs exported to Documents/APInvoiceDemo. Never uses Airtable, Google Drive, or external ERP/SaaS writes.
```

### 9.4 tools順

```text
1. ap_invoice_setup_demo_workspace
2. ap_invoice_list_demo_cases
3. ap_invoice_preview_folder
4. ap_invoice_review_folder
5. ap_invoice_review_demo_case
6. ap_invoice_explain_exception
7. ap_invoice_build_approval_brief
8. Advanced tools...
```

---

## 10. Packaging要件

### 10.1 sourceだけpushしない

必ずdistを更新する。

```bash
make generate-ap-samples
make test
make package-ap-mcpb
make verify-ap-data-boundary
make smoke-ap-mcp
```

### 10.2 MCPB内容検証

追加:

```text
scripts/verify_mcpb_contents.py
```

検証内容:

```text
- manifest.json exists
- version >= 0.4.0
- ap_invoice_review_folder exists in manifest
- ap_invoice_setup_demo_workspace exists in manifest
- samples/case-a-pay-ready/invoice.pdf exists
- samples/case-a-pay-ready/invoice.json exists
- all 4 cases have 3 PDFs and 3 sidecars
- workflow-packs/ap-invoice-v1/ruleset.yaml exists
```

---

## 11. テスト計画

### 11.1 Unit tests

```text
test_setup_demo_workspace_exports_visible_files
test_review_folder_detects_invoice_po_grn
test_review_folder_case_a_pay_ready
test_review_folder_case_b_po_mismatch
test_review_folder_case_c_duplicate
test_review_folder_case_d_vendor_review
test_review_folder_missing_po_fails_clearly
test_review_folder_missing_sidecar_fails_clearly
test_preview_folder_returns_key_fields
```

### 11.2 UX regression tests

```text
test_skill_mentions_ap_invoice_review_folder
test_skill_forbids_airtable
test_skill_forbids_external_registry
test_skill_requires_visible_pdf_paths_before_review
test_manifest_high_level_folder_tools_first
test_tool_descriptions_contain_folder_and_local
```

### 11.3 Manual QA

```text
1. 古いextensionをアンインストール
2. 最新mcpbをインストール
3. Connector ON
4. 「AP Invoiceデモを開始して」
5. Documents/APInvoiceDemo が作成される
6. PDFをExplorerで開ける
7. 「case-aをレビューして」
8. PAY_READY_CANDIDATE
9. 「case-bをレビューして」
10. REFER_PO_MISMATCH
11. Airtable許可ダイアログが出ない
12. 「C:\Users\...\Documents\APInvoiceDemo\case-c-duplicate このフォルダ内をレビューして」
13. REFER_DUPLICATE_REVIEW
```

---

## 12. 受入条件

### Customer UX

```text
- .mcpbインストール後、「AP Invoiceデモを開始して」で始まる
- Documents/APInvoiceDemo にPDFが展開される
- ユーザーがPDFを開ける
- 「このフォルダ内をレビューして」で動く
- 「case-aをレビューして」で動く
- Airtable/Google Drive/registryに逃げない
```

### Business

```text
- case-a -> PAY_READY_CANDIDATE
- case-b -> REFER_PO_MISMATCH
- case-c -> REFER_DUPLICATE_REVIEW
- case-d -> REFER_VENDOR_REVIEW
- 結果に判定、業務上の意味、根拠、次アクションが出る
- draft payload summaryが出る
- write_performed=falseが出る
```

### Packaging

```text
- version >= 0.4.0
- dist/ap-invoice-review.mcpb が更新済み
- mcpb内にsamplesがある
- verify_mcpb_contents.py が通る
```

### Safety

```text
- 外部SaaS/ERP/banking/payment writeなし
- arbitrary local file accessなし
- allowed roots制限あり
- sidecar検証あり
```

---

## 13. 実装Agentへの短い依頼文

```text
AP Invoice MCPBを顧客デモ可能なUXに作り直してください。現在はConnectorがONでもAirtableへ逃げたり、MCPB内部samplesを勝手に読むだけで、ユーザーから見える帳票レビュー体験になっていません。

vNextの本命UXは「このフォルダ内をレビューして」で動くことです。ap_invoice_review_folder を主役toolとして追加し、指定フォルダ内のPDFを検出して invoice / purchase_order / goods_receipt に分類し、sidecar JSONを検証し、APレビューを実行してください。case-aなどのデモも、まず ap_invoice_setup_demo_workspace で Documents/APInvoiceDemo にPDF/JSONを展開し、ユーザーがExplorerで開ける状態にしてください。

SKILL.mdではAirtable、Google Drive、外部connector registryを使わないこと、AP Invoice toolsを最優先すること、フォルダパスがあれば ap_invoice_review_folder を呼ぶこと、レビュー前に可視PDFパスを表示することを明記してください。

manifestは version 0.4.0 以上に上げ、display_nameを AP Invoice Review — Folder Demo にし、ap_invoice_setup_demo_workspace、ap_invoice_list_demo_cases、ap_invoice_preview_folder、ap_invoice_review_folder、ap_invoice_review_demo_case、ap_invoice_explain_exception、ap_invoice_build_approval_brief を先頭に並べてください。dist/ap-invoice-review.mcpbを必ず再生成してpushしてください。

受入条件は、通常Claude DesktopでMCPBをインストールし、「AP Invoiceデモを開始して」で Documents/APInvoiceDemo が作成され、PDFが見え、「case-aをレビューして」でPAY_READY_CANDIDATE、「このフォルダ内をレビューして」で対象フォルダが処理され、Airtable許可ダイアログが一度も出ないことです。
```

---

## 14. まとめ

これ以上、低レベルtoolの追加だけでUXを良くしようとしてはいけない。

顧客に使ってもらえるMCPBとは、以下である。

```text
帳票フォルダを渡す
→ 何が入っているか確認される
→ 自動分類される
→ 支払前レビューが走る
→ 例外理由と次アクションが出る
→ 外部書き込みなし
```

この体験をデモ時点で見せつけること。
