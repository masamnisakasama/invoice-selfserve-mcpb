# AP Invoice Exception Review Self-Serve MCPB Product Spec

作成日: 2026-06-21

対象: Enterprise bundle / Cowork on 3P / Bedrock Claude / Remote MCP / MCPB を流用し、Underwriting 以外の IDP 業務として「AP Invoice Exception Review（請求書・発注書・納品書/検収書の照合レビュー）」を Self-serve MCPB として提供する。

---

## 1. 結論

最初の Self-serve MCPB は **AP Invoice Exception Review** にする。

これは単なる請求書OCRではない。業務価値は以下にある。

```text
請求書 + 発注書 + 納品書/検収書 + 取引先マスタ + 過去請求DB + 支払ルール
    ↓
canonical facts
    ↓
3-way match / vendor master match / duplicate check / tax check / tolerance rule
    ↓
支払候補、要確認、重複疑い、取引先確認、税務確認、差戻し候補
    ↓
根拠・監査証跡・ERP/SaaS draft payload
```

MCPBとしての価値は、Claudeに「請求書を読ませる」ことではなく、Claude単体では保持できない **決定論的な照合実行環境、マスタ参照、重複検知、監査証跡、draft payload生成** を道具として提供することにある。

---

## 2. 製品名

推奨名:

```text
AP Invoice Exception Review MCPB
```

将来の横展開名:

```text
Document Decision Builder MCPB
```

初回デモでは、広げすぎずに `AP Invoice Exception Review` と言い切る。

---

## 3. なぜ AP Invoice なのか

### 3.1 業務価値が明確

経理・BPO・購買・支払業務で共通に発生する。

- 請求書の項目抽出
- 発注書との金額・品目・数量・取引先照合
- 納品書/検収書との納品数量・検収状態照合
- 取引先マスタとの支払先・口座・税区分確認
- 過去請求との重複検知
- 支払前の例外レビュー
- ERP/会計SaaS登録前のdraft payload作成

### 3.2 Claude単体では完結しない

Claude単体でも請求書の要約はできる。しかし、以下は難しい。

- 過去請求DBとの重複検知
- PO/GRN/取引先マスタとの照合
- tolerance ruleの決定論的評価
- 同一ルールでの再実行可能性
- 監査証跡の永続化
- ERP/SaaS登録用のdraft payload生成
- tenant別・部門別・金額別ルールの切り替え
- 回帰テストによる保守

したがって、MCPBは「会話に便利なアドオン」ではなく、**業務判断パケットを生成するミニ業務システム** として扱う。

---

## 4. 初回MVPスコープ

### 4.1 対象書類

必須:

```text
invoice.pdf
```

推奨:

```text
purchase_order.pdf
goods_receipt.pdf または inspection_report.pdf
```

デモでは3帳票を使う。

```text
invoice.pdf          請求書。支払請求の正本。
purchase_order.pdf   発注書。注文内容・単価・数量・税区分。
goods_receipt.pdf    納品書/検収書。納品数量・検収日・受領状態。
```

### 4.2 参照データ

最初はCSV同梱でよい。

```text
vendor_master.csv
po_master.csv
goods_receipt_master.csv
invoice_history.csv
tax_code_master.csv
cost_center_master.csv
```

本番化時はDynamoDB/RDS/既存SaaS APIに差し替える。

### 4.3 初期判定カテゴリ

```text
PAY_READY_CANDIDATE       人間承認後、支払登録してよい候補
REFER_PO_MISMATCH         発注書との差異あり
REFER_GRN_MISMATCH        納品/検収との差異あり
REFER_VENDOR_REVIEW       取引先確認が必要
REFER_DUPLICATE_REVIEW    重複請求の疑い
REFER_TAX_REVIEW          税額・税区分確認が必要
REFER_INFO_REQUEST        必須情報不足
BLOCKED_CANDIDATE         明示的ブロック候補
```

`PAY_READY_CANDIDATE` でも、自動支払はしない。人間承認前提。

---

## 5. ユーザーと体験

### 5.1 AP担当者

```text
/ ap-review:review-invoice-packet
請求書、発注書、納品書を選ぶ
結果を見る
例外理由を確認する
必要なら差戻しコメントを生成する
```

### 5.2 承認者

```text
決定パケットを見る
根拠ページを見る
差異金額とルールIDを見る
承認 / 差戻し / 保留を判断する
```

### 5.3 管理者

```text
workflow-packを作る
ルールをYAMLで管理する
参照CSVを差し替える
サンプルケースと期待結果を置く
make package-mcpb を実行する
生成された .mcpb を配布する
```

### 5.4 開発者

```text
core engineを変更する
schema migrationを追加する
regression testを更新する
GitHub Actionsでlint/test/packageを通す
release tagを切る
```

---

## 6. Self-serve MCPB の配布像

### 6.1 小規模デモ: .mcpb

```text
ap-invoice-review.mcpb
```

利用者はダウンロードして、Claude Desktop等にドロップして使う。

MCPBは以下を含む。

```text
ap-invoice-review.mcpb
├── manifest.json
├── server/
│   ├── index.js または main.py
│   ├── mcp_server/
│   └── workflow_pack_loader/
├── workflow-packs/
│   └── ap-invoice-v1/
├── samples/
│   ├── case-a-pay-ready/
│   ├── case-b-po-mismatch/
│   ├── case-c-duplicate/
│   └── case-d-vendor-review/
├── icon.png
└── README.md
```

### 6.2 Enterprise / Cowork on 3P

Cowork on 3Pでは、以下の二層にする。

```text
managedMcpServers
  └── Remote MCP URL / 認証 / toolPolicy

organization Plugin
  └── Skill / 操作導線 / デモ手順
```

Remote MCP URL例:

```text
https://ap-review-mcp.example.com/mcp
```

配布物:

```text
enterprise-bundle/
├── deploy/cowork/generated/cowork-3p-ap-review.reg
├── deploy/cowork/generated/cowork-3p-ap-review.mobileconfig
├── plugin/ap-invoice-review/
│   ├── .claude-plugin/plugin.json
│   ├── version.json
│   └── skills/ap-review/SKILL.md
├── samples/
└── install scripts
```

### 6.3 両対応の原則

同じ core engine を2つの形で包む。

```text
core engine
├── local MCPB stdio adapter
└── remote MCP Streamable HTTP adapter
```

MCPBはPoC/デモ/個人配布。
Enterprise bundleは管理者配布/閉域Bedrock/toolPolicy固定。

---

## 7. 業務ワークフロー

### 7.1 基本フロー

```text
1. create_invoice_review_case
2. upload_documents
3. start_invoice_review
4. extract_documents
5. normalize_to_canonical_facts
6. validate_required_fields
7. match_vendor_master
8. match_purchase_order
9. match_goods_receipt
10. check_duplicate_invoice
11. evaluate_rules
12. generate_draft_payloads
13. assemble_decision_packet
14. explain_exceptions
15. persist_audit_artifacts
```

### 7.2 重要な設計方針

- LLMは抽出・正規化・説明に使う
- 最終 recommendation は決定論ルールエンジンが決める
- LLMの説明文は recommendation を変更できない
- draft payload は作るが、SaaS/ERPへ本書き込みしない
- すべての判断に evidence を付ける
- ルール、参照データ、抽出結果、実行トレースを分離保存する

---

## 8. Canonical Data Model

### 8.1 Invoice Packet

```json
{
  "case_id": "AP-CASE-0001",
  "tenant_id": "demo-tenant",
  "workflow_pack": "ap-invoice-v1",
  "ruleset_version": "ap-demo-2026-01",
  "documents": [],
  "canonical_facts": {},
  "match_results": {},
  "rule_results": [],
  "draft_payloads": {},
  "decision": {},
  "audit": {}
}
```

### 8.2 Canonical Facts

```json
{
  "invoice": {
    "invoice_number": {
      "value": "INV-2026-0007",
      "confidence": 0.98,
      "evidence": [{ "document": "invoice.pdf", "page": 1, "field": "Invoice No" }]
    },
    "invoice_date": { "value": "2026-06-20" },
    "vendor_name": { "value": "Tokyo Office Supplies Co., Ltd." },
    "vendor_id": { "value": "V-1001" },
    "po_number": { "value": "PO-2026-0142" },
    "currency": { "value": "JPY" },
    "subtotal_amount": { "value": 100000 },
    "tax_amount": { "value": 10000 },
    "total_amount": { "value": 110000 },
    "bank_account": { "value": "0001-1234567" },
    "line_items": [
      {
        "description": "A4 copy paper",
        "quantity": 100,
        "unit_price": 1000,
        "amount": 100000,
        "tax_code": "JP10"
      }
    ]
  },
  "purchase_order": {
    "po_number": { "value": "PO-2026-0142" },
    "vendor_id": { "value": "V-1001" },
    "total_amount": { "value": 110000 },
    "approved": { "value": true }
  },
  "goods_receipt": {
    "receipt_number": { "value": "GR-2026-0129" },
    "po_number": { "value": "PO-2026-0142" },
    "received": { "value": true },
    "received_quantity": { "value": 100 }
  }
}
```

### 8.3 Evidence

すべての抽出値とルール結果に evidence を付ける。

```json
{
  "document_type": "invoice",
  "document_name": "invoice.pdf",
  "page": 1,
  "field_label": "合計金額",
  "raw_text": "¥110,000",
  "normalized_value": 110000,
  "bbox": [100, 200, 300, 240]
}
```

---

## 9. 照合ロジック

### 9.1 Vendor Master Match

確認項目:

```text
vendor_id exists
vendor_name similarity
bank_account match
invoice registration number match
payment terms match
tax category match
blocked vendor flag
```

結果例:

```json
{
  "match_type": "vendor_master",
  "status": "matched",
  "vendor_id": "V-1001",
  "rule_hits": []
}
```

### 9.2 PO Match

確認項目:

```text
po_number exists
po approved
vendor_id match
currency match
line item quantity match
unit price match
total amount within tolerance
remaining PO balance sufficient
```

### 9.3 Goods Receipt / Inspection Match

確認項目:

```text
goods received
inspection accepted
received quantity >= invoiced quantity
receipt date <= invoice date or within policy
```

### 9.4 Duplicate Check

最初は決定論的な重複候補でよい。

キー候補:

```text
vendor_id + invoice_number
vendor_id + invoice_date + total_amount
vendor_id + normalized_line_item_hash + total_amount
bank_account + invoice_number + total_amount
```

重複スコア:

```text
100: vendor_id + invoice_number 完全一致
90: vendor_id + total_amount + invoice_date ± 7日
80: bank_account + total_amount + line_item_hash
60: vendor_name類似 + amount一致
```

80点以上で `REFER_DUPLICATE_REVIEW`。

### 9.5 Tax Check

確認項目:

```text
tax_code exists
tax_rate expected
tax_amount = subtotal * tax_rate within rounding tolerance
reverse charge / exempt / reduced tax category if needed
```

---

## 10. Ruleset YAML

### 10.1 例

```yaml
ruleset_id: ap-demo-2026-01
workflow_pack: ap-invoice-v1
currency: JPY

tolerances:
  amount_absolute_jpy: 100
  amount_percent: 0.005
  tax_rounding_jpy: 1

rules:
  - id: AP-REQ-001
    severity: high
    category: required_fields
    description: Invoice number is required.
    when:
      missing: invoice.invoice_number
    then:
      recommendation: REFER_INFO_REQUEST
      missing_information:
        - invoice.invoice_number

  - id: AP-VENDOR-001
    severity: critical
    category: vendor_master
    description: Vendor must exist in vendor master.
    when:
      not_found: vendor_master.vendor_id
    then:
      recommendation: REFER_VENDOR_REVIEW

  - id: AP-VENDOR-002
    severity: critical
    category: vendor_master
    description: Bank account must match vendor master.
    when:
      mismatch:
        left: invoice.bank_account
        right: vendor_master.bank_account
    then:
      recommendation: REFER_VENDOR_REVIEW

  - id: AP-PO-001
    severity: high
    category: po_match
    description: Invoice total must match PO total within tolerance.
    when:
      amount_diff_exceeds_tolerance:
        left: invoice.total_amount
        right: purchase_order.total_amount
        tolerance: amount_absolute_jpy
    then:
      recommendation: REFER_PO_MISMATCH

  - id: AP-GRN-001
    severity: high
    category: grn_match
    description: Received quantity must cover invoiced quantity.
    when:
      less_than:
        left: goods_receipt.received_quantity
        right: invoice.total_quantity
    then:
      recommendation: REFER_GRN_MISMATCH

  - id: AP-DUP-001
    severity: critical
    category: duplicate_check
    description: Duplicate invoice candidate found.
    when:
      duplicate_score_at_least: 80
    then:
      recommendation: REFER_DUPLICATE_REVIEW

  - id: AP-BLOCK-001
    severity: critical
    category: blocked_vendor
    description: Vendor is blocked for payment.
    when:
      equals:
        left: vendor_master.blocked
        right: true
    then:
      recommendation: BLOCKED_CANDIDATE
```

### 10.2 保守方針

- ルールIDは絶対に再利用しない
- `description` は人間が読める文にする
- `category` と `severity` を必須にする
- `then.recommendation` は列挙値のみ許可
- ルール変更時は必ず fixture の期待結果を更新する
- LLMがYAMLを書き換える機能は初期では入れない

---

## 11. MCP Tools

### 11.1 最小構成

最初は5 toolsでよい。

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

### 11.2 追加で便利な tools

```text
explain_ap_exception
compare_ap_what_if
list_ap_workflow_packs
validate_ap_workflow_pack
```

### 11.3 Tool 仕様

#### create_ap_review_case

入力:

```json
{
  "tenant_id": "demo-tenant",
  "workflow_pack": "ap-invoice-v1",
  "ruleset_version": "ap-demo-2026-01",
  "case_label": "June office supplies invoice"
}
```

出力:

```json
{
  "case_id": "AP-CASE-0001",
  "upload_slots": [
    { "document_type": "invoice", "required": true },
    { "document_type": "purchase_order", "required": true },
    { "document_type": "goods_receipt", "required": true }
  ]
}
```

#### upload_ap_document

MCPB local demoではローカルパスを読み、Remote MCPではpresigned uploadに変換する。

入力:

```json
{
  "case_id": "AP-CASE-0001",
  "document_type": "invoice",
  "file_path": "samples/case-a/invoice.pdf"
}
```

出力:

```json
{
  "document_id": "doc-invoice-001",
  "status": "uploaded",
  "sha256": "..."
}
```

#### start_ap_invoice_review

入力:

```json
{
  "case_id": "AP-CASE-0001"
}
```

出力:

```json
{
  "job_id": "job-0001",
  "status": "running"
}
```

#### get_ap_invoice_review_result

出力:

```json
{
  "case_id": "AP-CASE-0001",
  "recommendation": "PAY_READY_CANDIDATE",
  "confidence": 0.94,
  "summary": "請求書、発注書、納品書の主要項目は一致しています。",
  "exceptions": [],
  "match_results": {},
  "rule_results": [],
  "evidence": [],
  "draft_payloads": {
    "freee": {},
    "generic_ap": {}
  },
  "audit_artifacts": {
    "canonical_facts_uri": "...",
    "rule_result_uri": "...",
    "decision_result_uri": "...",
    "execution_trace_uri": "..."
  }
}
```

#### build_erp_draft_payload

本書き込みではなくdraftのみ。

入力:

```json
{
  "case_id": "AP-CASE-0001",
  "target_system": "freee",
  "mode": "draft_only"
}
```

出力:

```json
{
  "target_system": "freee",
  "mode": "draft_only",
  "payload": {
    "partner_code": "V-1001",
    "issue_date": "2026-06-20",
    "amount": 110000,
    "tax_code": "JP10",
    "memo": "Draft generated by AP Invoice Exception Review MCPB"
  },
  "write_performed": false
}
```

---

## 12. MCP Resources

```text
ap-review://workflow-packs
ap-review://workflow-packs/ap-invoice-v1
ap-review://rulesets/ap-demo-2026-01
ap-review://cases/{case_id}/decision
ap-review://cases/{case_id}/evidence
ap-review://cases/{case_id}/audit
ap-review://schemas/ap-invoice-v1/canonical-facts
ap-review://schemas/ap-invoice-v1/decision-result
```

---

## 13. Skill / Prompt 設計

### 13.1 Skill名

```text
ap-review:review-invoice-packet
```

### 13.2 SKILL.md の役割

SkillはMCP toolsの呼び出し順を固定する。

```text
1. ユーザーに invoice / purchase_order / goods_receipt を選ばせる
2. create_ap_review_case を呼ぶ
3. 各帳票を upload_ap_document で登録する
4. start_ap_invoice_review を呼ぶ
5. get_ap_invoice_review_result をポーリングする
6. recommendation, exceptions, rule_results, evidence, draft payload を表示する
7. BLOCKED / REFER の場合は差戻しコメント案を作る
```

### 13.3 出力フォーマット

```markdown
# AP Invoice Review Result

## 判定
PAY_READY_CANDIDATE / REFER_* / BLOCKED_CANDIDATE

## 理由
- ...

## 差異
| 種別 | 請求書 | 参照先 | 差分 | ルール |

## 不足情報
- ...

## 根拠
- invoice.pdf p.1 合計金額: 110,000円
- purchase_order.pdf p.1 合計金額: 110,000円

## Draft Payload
```json
{}
```

## 人間が確認すべき事項
- ...
```

---

## 14. Workflow Pack 構造

```text
workflow-packs/ap-invoice-v1/
├── pack.yaml
├── document_types.yaml
├── extraction_schema.json
├── canonical_schema.json
├── decision_schema.json
├── ruleset.yaml
├── reference_tables/
│   ├── vendor_master.csv
│   ├── po_master.csv
│   ├── goods_receipt_master.csv
│   ├── invoice_history.csv
│   └── tax_code_master.csv
├── prompts/
│   ├── normalize_invoice.md
│   ├── normalize_purchase_order.md
│   ├── normalize_goods_receipt.md
│   └── explain_exceptions.md
├── mapping/
│   ├── generic_ap_payload.json
│   └── freee_draft_payload.json
├── samples/
│   ├── case-a-pay-ready/
│   ├── case-b-po-mismatch/
│   ├── case-c-duplicate/
│   └── case-d-vendor-review/
└── tests/
    ├── expected-case-a.json
    ├── expected-case-b.json
    ├── expected-case-c.json
    └── expected-case-d.json
```

### 14.1 pack.yaml

```yaml
pack_id: ap-invoice-v1
name: AP Invoice Exception Review
version: 0.1.0
business_domain: accounts_payable
supported_languages:
  - ja
  - en
document_types:
  - invoice
  - purchase_order
  - goods_receipt
recommendations:
  - PAY_READY_CANDIDATE
  - REFER_PO_MISMATCH
  - REFER_GRN_MISMATCH
  - REFER_VENDOR_REVIEW
  - REFER_DUPLICATE_REVIEW
  - REFER_TAX_REVIEW
  - REFER_INFO_REQUEST
  - BLOCKED_CANDIDATE
write_policy:
  external_write_allowed: false
  draft_payload_allowed: true
```

---

## 15. 回帰テスト設計

### 15.1 なぜ必須か

IDPは「抽出できた」だけでは保守不能になる。

保守不能になる典型例:

- ルール追加で既存ケースの判定が変わる
- LLMの出力揺れで同じ入力の結果が変わる
- PO/GRN照合の差異理由が説明できない
- draft payloadの項目名が壊れる
- 取引先マスタの差し替えで全件REFERになる
- 例外判定の優先順位が曖昧になる

したがって、workflow packごとに fixture と expected result を必須にする。

### 15.2 テスト階層

```text
unit tests
  - ruleset parser
  - tolerance calculation
  - duplicate scorer
  - vendor matcher
  - payload mapper

schema tests
  - canonical_schema.json
  - decision_schema.json
  - draft payload schema

fixture tests
  - case-a PAY_READY_CANDIDATE
  - case-b REFER_PO_MISMATCH
  - case-c REFER_DUPLICATE_REVIEW
  - case-d REFER_VENDOR_REVIEW

golden tests
  - decision_result.json snapshot
  - rule_result.json snapshot
  - audit_artifacts manifest snapshot

live smoke tests
  - deployed MCP tools/list
  - create/upload/start/get result
  - case-a happy path
```

### 15.3 期待ケース

#### Case A: 支払候補

```text
invoice total = 110,000
PO total = 110,000
GRN received quantity = invoice quantity
vendor bank account matches
no duplicate

Expected: PAY_READY_CANDIDATE
```

#### Case B: PO金額差異

```text
invoice total = 121,000
PO total = 110,000
vendor matches
GRN matches

Expected: REFER_PO_MISMATCH
Rule: AP-PO-001
```

#### Case C: 重複請求疑い

```text
invoice number = INV-2026-0007
invoice_history contains same vendor_id + invoice_number

Expected: REFER_DUPLICATE_REVIEW
Rule: AP-DUP-001
```

#### Case D: 取引先口座不一致

```text
invoice bank account != vendor_master bank_account

Expected: REFER_VENDOR_REVIEW
Rule: AP-VENDOR-002
```

#### Case E: 検収不足

```text
invoice quantity = 100
goods_receipt received_quantity = 80

Expected: REFER_GRN_MISMATCH
Rule: AP-GRN-001
```

### 15.4 Make targets

```makefile
make generate-ap-samples
make test-ap-rules
make test-ap-fixtures
make test-ap-golden
make package-ap-mcpb
make verify-ap-data-boundary
make smoke-ap-mcp
```

### 15.5 CI必須条件

GitHub Actionsで以下を必須にする。

```text
npm run build
make lint
make typecheck
make test-ap-rules
make test-ap-fixtures
make test-ap-golden
make package-ap-mcpb
make verify-ap-data-boundary
```

PRはこれが通らない限りmergeしない。

---

## 16. 監査証跡

各実行で以下を保存する。

```text
source_documents/
  invoice.pdf
  purchase_order.pdf
  goods_receipt.pdf

artifacts/
  extracted_text.json
  canonical_facts.json
  vendor_match_result.json
  po_match_result.json
  grn_match_result.json
  duplicate_check_result.json
  rule_result.json
  agent_assessment.json
  decision_result.json
  draft_payloads.json
  execution_trace.json
```

### 16.1 execution_trace.json

```json
{
  "case_id": "AP-CASE-0001",
  "workflow_pack": "ap-invoice-v1",
  "ruleset_version": "ap-demo-2026-01",
  "started_at": "2026-06-21T00:00:00Z",
  "completed_at": "2026-06-21T00:00:10Z",
  "model_id": "bedrock-claude-model-id",
  "rule_engine_version": "0.1.0",
  "reference_data_versions": {
    "vendor_master": "2026-06-01",
    "po_master": "2026-06-01",
    "invoice_history": "2026-06-20"
  },
  "tool_calls": [],
  "warnings": []
}
```

---

## 17. Draft Payload 設計

初期では外部書き込み禁止。

生成するのは以下のみ。

```text
generic_ap_draft.json
freee_draft.json
kintone_review_record_draft.json
```

### 17.1 generic_ap_draft.json

```json
{
  "vendor_id": "V-1001",
  "invoice_number": "INV-2026-0007",
  "invoice_date": "2026-06-20",
  "due_date": "2026-07-20",
  "currency": "JPY",
  "subtotal_amount": 100000,
  "tax_amount": 10000,
  "total_amount": 110000,
  "po_number": "PO-2026-0142",
  "cost_center": "CC-001",
  "payment_status": "draft",
  "source_case_id": "AP-CASE-0001",
  "write_performed": false
}
```

### 17.2 kintone_review_record_draft.json

```json
{
  "app": "AP_EXCEPTION_REVIEW",
  "record": {
    "case_id": { "value": "AP-CASE-0001" },
    "recommendation": { "value": "REFER_PO_MISMATCH" },
    "vendor_id": { "value": "V-1001" },
    "invoice_number": { "value": "INV-2026-0007" },
    "total_amount": { "value": 121000 },
    "exception_summary": { "value": "PO金額との差異が許容範囲を超えています。" }
  },
  "write_performed": false
}
```

---

## 18. セキュリティ / データ境界

### 18.1 Cowork on 3P

Bedrock/Vertex等を使う場合、会話・ファイル・ツール出力は設定した推論エンドポイントとローカル端末に保持する前提で設計する。

### 18.2 MCPB local

- ローカルファイル読み取りは、ユーザーが選んだファイルに限定
- 環境変数に秘密情報を直書きしない
- bundle内に本番tokenを含めない
- ログに原本PDFや全文を出さない
- write toolは含めない

### 18.3 Remote MCP

- `AUTH_MODE=jwt` を使う
- upload token は短期single-use
- Origin検証
- Content-Type/MIME/PDF signature/サイズ/ページ数検証
- S3 SSE-KMS
- DynamoDB TTL
- WAF optional
- toolPolicyでwrite系をblockedにする

---

## 19. 実装方針

### 19.1 流用できる既存Underwriting資産

- MCP tools/resources の構造
- Streamable HTTP `/mcp`
- JWT auth
- short-lived upload token
- PDF validation
- Skill-only organization Plugin
- managedMcpServers 配布テンプレート
- Windows/macOS installer
- S3/DynamoDB/Step Functions adapters
- Bedrock structured output repair
- deterministic recommendation pattern
- What-if diff pattern
- regression plan pattern

### 19.2 新規実装が必要な部分

```text
workflow-packs/ap-invoice-v1
ap canonical schema
vendor matcher
PO matcher
GRN matcher
duplicate scorer
tax checker
draft payload mapper
AP-specific SKILL.md
AP sample PDFs
AP fixture expected results
AP-specific regression suite
MCPB manifest and package target
```

---

## 20. GitHubにpushするタイミング

pushする。ただし、**設計だけではなく、テンプレートとして使える状態**でpushする。

### 20.1 推奨ブランチ

```text
feature/ap-invoice-self-serve-mcpb
```

### 20.2 推奨ディレクトリ

既存repoに入れるなら:

```text
examples/ap-invoice-review-mcpb/
```

独立repoにするなら:

```text
idp-ap-invoice-review-mcpb/
```

### 20.3 push前の必須条件

```text
1. サンプルケースA-Dがある
2. expected結果がある
3. make test-ap-fixtures が通る
4. make package-ap-mcpb が通る
5. .mcpbに秘密情報が入っていない
6. READMEにデモ手順がある
7. write_performed=false を保証している
8. GitHub Actionsが最低限のCIを通す
```

### 20.4 GitHubに入れないもの

```text
.env
JWT秘密鍵
Cognito secret
AWS account IDを含む本番設定
顧客データ
実請求書
本番vendor master
本番invoice history
本番freee/kintone token
```

### 20.5 コマンド例

```bash
git checkout -b feature/ap-invoice-self-serve-mcpb
mkdir -p examples/ap-invoice-review-mcpb
# filesを配置
make test-ap-fixtures
make package-ap-mcpb
git status
git add examples/ap-invoice-review-mcpb docs/AP_INVOICE_SELF_SERVE_MCPB_PRODUCT_SPEC.md
git commit -m "feat: add AP invoice self-serve MCPB design"
git push -u origin feature/ap-invoice-self-serve-mcpb
```

---

## 21. 実装マイルストーン

### Phase 1: Design-only usable handoff

成果物:

```text
docs/AP_INVOICE_SELF_SERVE_MCPB_PRODUCT_SPEC.md
workflow-packs/ap-invoice-v1/pack.yaml
workflow-packs/ap-invoice-v1/ruleset.yaml
workflow-packs/ap-invoice-v1/canonical_schema.json
workflow-packs/ap-invoice-v1/decision_schema.json
```

### Phase 2: Local deterministic engine

成果物:

```text
vendor matcher
PO matcher
GRN matcher
duplicate scorer
ruleset evaluator
fixture tests
```

### Phase 3: MCP tools

成果物:

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

### Phase 4: MCPB package

成果物:

```text
manifest.json
local stdio server
make package-ap-mcpb
ap-invoice-review.mcpb
```

### Phase 5: Enterprise bundle

成果物:

```text
managedMcpServers template
Skill-only organization Plugin
Windows/macOS installer
sample PDFs
handoff docs
```

### Phase 6: AWS runtime optional

成果物:

```text
Remote MCP /mcp
S3/DynamoDB/Step Functions
Bedrock normalization
Textract or OCR adapter
live smoke test
```

---

## 22. 受入条件

### 22.1 Business acceptance

- AP担当者が請求書・発注書・納品書を渡して、5分以内にレビュー結果を確認できる
- `PAY_READY_CANDIDATE` と `REFER_*` の理由が人間に説明できる
- 金額差異、重複疑い、取引先口座不一致が検出できる
- draft payload が生成されるが、外部書き込みは行われない
- 監査証跡として evidence と rule_result が残る

### 22.2 Technical acceptance

- MCP tools/list が安定して返る
- すべてのtoolsにinput/output schemaがある
- fixture testが通る
- golden snapshotが通る
- packageした `.mcpb` をインストールできる
- Enterprise bundleでSkillが表示される
- 秘密情報がbundleに混入しない
- 同じ入力で同じrecommendationが返る

---

## 23. Claude Code 実装依頼プロンプト

```text
このリポジトリに AP Invoice Exception Review MCPB を追加してください。

目的:
- Underwriting MCPの設計資産を流用し、請求書・発注書・納品書の照合レビューを行うSelf-serve MCPBを作る。
- Claude単体ではできない、マスター照合、重複検知、決定論ルール、監査証跡、draft payload生成を実装する。
- 外部SaaSへの本書き込みは禁止。draft payloadのみ生成する。

実装範囲:
1. workflow-packs/ap-invoice-v1 を追加
2. canonical_schema.json / decision_schema.json を追加
3. ruleset.yaml を追加
4. vendor matcher, PO matcher, GRN matcher, duplicate scorer, tax checker を追加
5. MCP tools を追加:
   - create_ap_review_case
   - upload_ap_document
   - start_ap_invoice_review
   - get_ap_invoice_review_result
   - build_erp_draft_payload
6. samples case-a〜case-d と expected JSON を追加
7. regression tests を追加
8. MCPB manifest.json と package target を追加
9. Enterprise bundle用Skillを追加
10. READMEとhandoff docsを追加

非スコープ:
- freee/kintone/ERPへの本書き込み
- 本番顧客データ
- LLMによる最終recommendation変更
- ルールの自動書き換え

受入条件:
- make test-ap-fixtures が通る
- make package-ap-mcpb が通る
- case-a は PAY_READY_CANDIDATE
- case-b は REFER_PO_MISMATCH
- case-c は REFER_DUPLICATE_REVIEW
- case-d は REFER_VENDOR_REVIEW
- draft payloadのwrite_performedは常にfalse
- .mcpbに秘密情報が含まれない
```

---

## 24. 最初に作るデモストーリー

### Story 1: 問題ない請求書

```text
ユーザー:
請求書、発注書、納品書をレビューしてください。

Claude:
AP Invoice Review MCPBを使って3-way matchを実行します。

結果:
PAY_READY_CANDIDATE
請求書、発注書、納品書の金額・数量・取引先情報が一致しています。
```

### Story 2: PO金額差異

```text
結果:
REFER_PO_MISMATCH
請求金額 121,000円 が発注金額 110,000円 を超過しています。
差異 11,000円 は許容差額100円を超えています。
```

### Story 3: 重複請求疑い

```text
結果:
REFER_DUPLICATE_REVIEW
同一 vendor_id + invoice_number の過去請求が存在します。
```

### Story 4: 取引先口座不一致

```text
結果:
REFER_VENDOR_REVIEW
請求書記載の口座番号が取引先マスタと一致しません。
```

この4ケースだけで、OCRではなく業務判断エンジンであることを示せる。

