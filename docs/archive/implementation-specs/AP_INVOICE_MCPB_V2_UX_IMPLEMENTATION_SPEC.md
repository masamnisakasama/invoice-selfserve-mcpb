# AP Invoice MCPB v2 実装指示書 — 業務UX / Skill / 高レベルTool設計

## 0. このMDの目的

このドキュメントは、`invoice-selfserve-mcpb` の v2 実装を担当するAgentに渡すための実装指示書である。

v1では `.mcpb` のインストールとMCP toolsの登録までは成功している。しかし、ユーザーが期待していた「slashで業務フローを開始する」「入れたらすぐ使える」「長いプロンプトを書かずにAP請求書レビューを実行できる」というUXが未完成である。

v2では、既存のAP照合エンジンを活かしつつ、**業務ユーザーが `/ap-review` だけで請求書例外レビューを開始できるMCPB** に作り替える。

---

## 1. 現状診断

### 1.1 できていること

現在の実装には、以下の業務エンジンが存在する。

- 請求書、発注書、納品書/検収書の3-way match
- 取引先マスタ照合
- PO金額・承認・残高・通貨・取引先照合
- GRN / goods receipt 数量照合
- 過去請求との重複検知
- 税額・税区分確認
- draft-only ERP/SaaS payload生成
- audit artifact生成
- fixture / golden test
- MCPB package

現行MCP tools:

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

これらは低レベルAPIとしては妥当である。

### 1.2 できていないこと

現在の `.mcpb` は、ユーザーが直接使うには低レベルすぎる。

現状の問題:

```text
- /ap-review のような業務入口がない
- case-a / case-b / case-c / case-d を選ぶUXがない
- ユーザーが長い自然文プロンプトを書かないと始まらない
- Claudeが外部mcp-registry検索に逃げることがある
- toolsは入っているのに、Claudeが「AP Invoice MCPBが見つからない」と誤解する
- Skillは enterprise-bundle 側にはあるが、MCPB単体の体験に統合されていない
- サンプルケースの場所や期待結果をClaudeが自力で理解できない
- 低レベルtool順序をユーザーまたはClaudeの推論に任せすぎている
```

### 1.3 v2の結論

v2では、既存の5 toolsを残しつつ、**高レベル業務tools** と **Skill / Prompt導線** を追加する。

v2のユーザー体験:

```text
.mcpb をインストール
↓
/ap-demo または /ap-review
↓
case-a / case-b / case-c / case-d を選ぶ
↓
請求書・PO・GRNを自動upload
↓
AP exception review 実行
↓
結果・根拠・次アクション・draft payload・write_performed=false を表示
```

---

## 2. プロダクトとして提供すべき業務価値

### 2.1 このMCPBはOCRツールではない

このMCPBの価値は、請求書を読むことではない。

価値は以下にある。

```text
請求書 + 発注書 + 納品書/検収書 + 取引先マスタ + 過去請求 + 税コード + 支払ルール
    ↓
canonical facts
    ↓
vendor master match / PO match / GRN match / duplicate check / tax check
    ↓
支払候補・要確認・重複疑い・取引先確認・税務確認
    ↓
根拠・監査証跡・draft-only ERP/SaaS payload
```

ユーザーに見せるべき価値は、次の4つである。

1. **支払候補の自動整理**  
   正常な請求packetを `PAY_READY_CANDIDATE` として整理する。ただし自動支払ではなく、人間承認候補とする。

2. **例外検出**  
   PO金額差異、GRN数量不足、取引先口座不一致、重複請求、税額差異を検出する。

3. **次アクション提示**  
   「支払可」ではなく、「PO確認」「取引先確認」「重複確認」「税務確認」「差戻し候補」まで示す。

4. **draft-only payload**  
   ERP/SaaS登録用payloadを作るが、本書き込みはしない。`write_performed=false` を常に明示する。

---

## 3. v2で必要なSkill

v2で本当に必要なSkillは4つに絞る。

### 3.1 `/ap-review` — メイン業務入口

目的:

```text
請求書packetをレビューする
```

想定利用:

```text
/ap-review
```

または自然文:

```text
この請求書packetをレビューして
case-bをレビューして
このフォルダのinvoice/PO/GRNを確認して
```

動作:

1. ユーザーがcaseを指定していなければ `list_ap_demo_cases` を呼ぶ
2. case指定があれば `review_ap_demo_case` を呼ぶ
3. 3PDFパス指定があれば `review_ap_invoice_packet` を呼ぶ
4. 結果を日本語で業務レポート化する
5. draft payload summaryを表示する
6. `write_performed=false` を必ず表示する

出力構成:

```text
1. 判定
2. 業務上の意味
3. 例外理由
4. 適用ルール
5. 根拠
6. 不足情報
7. 次アクション
8. draft payload summary
9. write_performed=false
```

禁止事項:

```text
- 外部connector registryを探しに行かない
- ユーザーに低レベルtoolの順序を説明しない
- 「支払を実行した」と言わない
- PAY_READY_CANDIDATE を自動支払承認と表現しない
```

---

### 3.2 `/ap-demo` — self-serveデモ入口

目的:

```text
ユーザーが何も準備しなくてもMCPBの価値を理解できるようにする
```

想定利用:

```text
/ap-demo
```

動作:

1. `list_ap_demo_cases` を呼ぶ
2. 4つのケースを業務価値つきで表示
3. ユーザーに選ばせる
4. 選択されたcaseに対して `review_ap_demo_case` を実行
5. 結果を日本語で表示

表示例:

```text
デモケースを選んでください。

1. case-a-pay-ready
   期待結果: PAY_READY_CANDIDATE
   業務価値: 3-way match正常系。支払候補の自動整理。

2. case-b-po-mismatch
   期待結果: REFER_PO_MISMATCH
   業務価値: PO金額差異を検出し、支払前に止める。

3. case-c-duplicate
   期待結果: REFER_DUPLICATE_REVIEW
   業務価値: 過去請求との重複疑いを検出し、二重払いを防ぐ。

4. case-d-vendor-review
   期待結果: REFER_VENDOR_REVIEW
   業務価値: 支払先口座のマスタ不一致を検出する。
```

---

### 3.3 `/ap-explain` — 例外理由説明

目的:

```text
例外結果をAP担当者が理解できる説明に変換する
```

想定利用:

```text
/ap-explain
このREFER_PO_MISMATCHの理由を説明して
この請求が止まった理由を購買担当向けに説明して
```

動作:

1. 直近のjob/resultを参照
2. `explain_ap_exception` を呼ぶ
3. audienceに応じて説明を変える

audience候補:

```text
ap_operator
approver
purchasing_owner
vendor_contact
```

出力例:

```text
この請求はPO金額差異により要確認です。

根拠:
- invoice total: 121,000 JPY
- PO total: 110,000 JPY
- tolerance: max(100 JPY, 0.5%)
- 差額: 11,000 JPY
- rule_id: AP-PO-001

次アクション:
- 購買担当にPO変更有無を確認
- 変更POがある場合は承認済みPOを追加
- 変更がない場合は請求書差戻し候補
```

---

### 3.4 `/ap-approval-brief` — 承認者向け判断パケット

目的:

```text
承認者・上長が短時間で支払可否を判断できる資料を作る
```

想定利用:

```text
/ap-approval-brief
承認者向けに要点だけまとめて
```

動作:

1. `build_ap_approval_brief` を呼ぶ
2. 判定・支払判断・根拠・次アクションを短くまとめる

出力例:

```text
承認者向けサマリー

判定:
REFER_DUPLICATE_REVIEW

支払判断:
現時点では支払保留推奨

理由:
過去請求と vendor_id + invoice_number が一致しています。

確認事項:
1. 過去請求が支払済みか
2. 今回請求が再発行か
3. invoice numberに訂正履歴があるか

根拠:
- invoice.pdf: invoice_number INV-2026-0007
- invoice_history: duplicate score 100
- rule_id: AP-DUP-001
```

---

## 4. 後回しにするSkill

v2では入れなくてよい。

### 4.1 `/ap-admin`

workflow-packやruleset管理用。初回業務デモでは不要。

### 4.2 `/ap-policy-simulator`

許容差や税ルール変更のwhat-if。高度だがv2の最優先ではない。

### 4.3 `/ap-write-freee`

入れない。現在の設計では外部freee/kintone/ERP/banking/payment writesは非スコープであり、draft-onlyを守る。

### 4.4 `/ap-upload`

入れない。uploadは `/ap-review` の内部で実行する。ユーザーにupload toolを直接使わせない。

---

## 5. 追加すべき高レベルMCP tools

Slash / Skillがクライアントによって使えない可能性があるため、MCPB本体にも高レベルtoolsを追加する。

### 5.1 `list_ap_demo_cases`

目的:

```text
同梱デモケースと期待結果、業務価値を返す
```

入力:

```json
{}
```

出力:

```json
{
  "demo_cases": [
    {
      "case_id": "case-a-pay-ready",
      "label_ja": "支払候補",
      "expected_recommendation": "PAY_READY_CANDIDATE",
      "business_value_ja": "請求書・PO・GRN・税額・重複なしが一致する正常系です。"
    },
    {
      "case_id": "case-b-po-mismatch",
      "label_ja": "PO差異",
      "expected_recommendation": "REFER_PO_MISMATCH",
      "business_value_ja": "請求額がPO許容差を超過するケースです。"
    },
    {
      "case_id": "case-c-duplicate",
      "label_ja": "重複請求疑い",
      "expected_recommendation": "REFER_DUPLICATE_REVIEW",
      "business_value_ja": "過去請求との重複疑いを検出するケースです。"
    },
    {
      "case_id": "case-d-vendor-review",
      "label_ja": "取引先確認",
      "expected_recommendation": "REFER_VENDOR_REVIEW",
      "business_value_ja": "支払先口座が取引先マスタと一致しないケースです。"
    }
  ]
}
```

このtoolは必須。  
これがないとClaudeがサンプルケースを認識できず、外部registry検索に逃げる。

---

### 5.2 `review_ap_demo_case`

目的:

```text
同梱サンプルを使い、1回のtool callでAPレビューを完了する
```

入力:

```json
{
  "case_id": "case-a-pay-ready",
  "tenant_id": "demo-tenant",
  "target_system": "generic_ap"
}
```

内部処理:

```text
1. case_idを検証
2. samples/{case_id}/invoice.pdf を取得
3. samples/{case_id}/purchase_order.pdf を取得
4. samples/{case_id}/goods_receipt.pdf を取得
5. create_case
6. upload invoice
7. upload purchase_order
8. upload goods_receipt
9. start_review
10. get_review_result
11. build_draft_payload
12. decision packetを返す
```

出力:

```json
{
  "case_id": "AP-CASE-...",
  "job_id": "job-...",
  "demo_case_id": "case-a-pay-ready",
  "recommendation": "PAY_READY_CANDIDATE",
  "recommendation_label_ja": "支払候補",
  "summary_ja": "...",
  "exceptions": [],
  "rule_results": [],
  "match_results": {},
  "evidence": [],
  "draft_payload": {},
  "write_performed": false,
  "audit_artifacts": {}
}
```

これは「緊急回避」ではない。  
**self-serve MCPBの正規デモ入口**である。

---

### 5.3 `review_ap_invoice_packet`

目的:

```text
3つのローカルPDFパスを指定してAPレビューを完了する
```

入力:

```json
{
  "tenant_id": "demo-tenant",
  "invoice_path": "C:\\...\\invoice.pdf",
  "purchase_order_path": "C:\\...\\purchase_order.pdf",
  "goods_receipt_path": "C:\\...\\goods_receipt.pdf",
  "case_label": "July office supplies invoice",
  "target_system": "generic_ap"
}
```

注意:

現状の実装はPDF本体OCRではなく、同名 `.json` sidecarを読むデモ実装である。  
したがって、v2でも最初は以下のように明記する。

```text
This demo requires sidecar JSON files next to the sample PDFs.
Production OCR/Textract is out of scope for this MCPB demo.
```

出力は `review_ap_demo_case` と同じ構造にする。

---

### 5.4 `explain_ap_exception`

目的:

```text
例外結果の理由、根拠、次アクションを説明する
```

入力:

```json
{
  "job_id": "job-...",
  "audience": "ap_operator"
}
```

出力:

```json
{
  "recommendation": "REFER_PO_MISMATCH",
  "exception_summary_ja": "...",
  "root_causes": [
    {
      "rule_id": "AP-PO-001",
      "reason_ja": "...",
      "evidence": []
    }
  ],
  "next_actions_ja": [],
  "draft_message_ja": "..."
}
```

audience別の出力:

```text
ap_operator:
  詳細な照合結果と次作業

approver:
  支払可否判断に必要な要点

purchasing_owner:
  PO変更・承認履歴の確認依頼

vendor_contact:
  差戻し・追加資料依頼文
```

---

### 5.5 `build_ap_approval_brief`

目的:

```text
承認者向けに短い判断パケットを作る
```

入力:

```json
{
  "job_id": "job-..."
}
```

出力:

```json
{
  "approval_recommendation": "approve_candidate | hold | return_to_requester",
  "brief_ja": "...",
  "risk_points_ja": [],
  "evidence": [],
  "write_performed": false
}
```

判断例:

```text
PAY_READY_CANDIDATE       -> approve_candidate
REFER_PO_MISMATCH         -> hold
REFER_GRN_MISMATCH        -> hold
REFER_VENDOR_REVIEW       -> hold
REFER_DUPLICATE_REVIEW    -> hold
REFER_TAX_REVIEW          -> hold
REFER_INFO_REQUEST        -> hold
BLOCKED_CANDIDATE         -> return_to_requester
```

---

## 6. 既存toolsの扱い

既存5 toolsは残す。ただし、UX上はAdvanced扱いにする。

| tool | v2での位置づけ |
|---|---|
| `create_ap_review_case` | Advanced/internal |
| `upload_ap_document` | Advanced/internal |
| `start_ap_invoice_review` | Advanced/internal |
| `get_ap_invoice_review_result` | Advanced/internal |
| `build_erp_draft_payload` | Advanced/internal。ただし結果では必ず表示 |

Claudeの通常利用では、高レベルtoolsを優先させる。

---

## 7. 実装対象ファイル

### 7.1 `ap_invoice_mcp/server.py`

現状は5 toolsのみ。  
以下を追加する。

```python
@mcp.tool()
def list_ap_demo_cases() -> dict[str, Any]:
    """List bundled AP invoice demo cases and expected outcomes."""
    return service.list_demo_cases()


@mcp.tool()
def review_ap_demo_case(
    case_id: str,
    tenant_id: str = "demo-tenant",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Run a bundled AP invoice demo case end-to-end."""
    return service.review_demo_case(
        case_id=case_id,
        tenant_id=tenant_id,
        target_system=target_system,
    )


@mcp.tool()
def review_ap_invoice_packet(
    tenant_id: str,
    invoice_path: str,
    purchase_order_path: str,
    goods_receipt_path: str,
    case_label: str = "",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Review an invoice, purchase order, and goods receipt packet end-to-end."""
    return service.review_invoice_packet_from_paths(
        tenant_id=tenant_id,
        invoice_path=invoice_path,
        purchase_order_path=purchase_order_path,
        goods_receipt_path=goods_receipt_path,
        case_label=case_label,
        target_system=target_system,
    )


@mcp.tool()
def explain_ap_exception(
    job_id: str,
    audience: str = "ap_operator",
) -> dict[str, Any]:
    """Explain AP review exceptions with evidence, rule IDs, and next actions."""
    return service.explain_exception(job_id=job_id, audience=audience)


@mcp.tool()
def build_ap_approval_brief(job_id: str) -> dict[str, Any]:
    """Build a concise AP approval or hold brief for an approver."""
    return service.build_approval_brief(job_id=job_id)
```

---

### 7.2 `ap_invoice_core/service.py`

追加メソッド:

```text
list_demo_cases
review_demo_case
review_invoice_packet_from_paths
explain_exception
build_approval_brief
```

#### `list_demo_cases`

固定値でよい。

```python
DEMO_CASES = {
    "case-a-pay-ready": {
        "expected_recommendation": "PAY_READY_CANDIDATE",
        "label_ja": "支払候補",
        "business_value_ja": "請求書、PO、GRN、税額、重複なしが一致する正常系です。",
    },
    ...
}
```

#### `review_demo_case`

実装方針:

```python
def review_demo_case(self, *, case_id: str, tenant_id: str, target_system: str) -> dict[str, Any]:
    if case_id not in DEMO_CASES:
        raise ValueError(...)
    case_dir = self.project_root / "samples" / case_id
    invoice = case_dir / "invoice.pdf"
    po = case_dir / "purchase_order.pdf"
    grn = case_dir / "goods_receipt.pdf"
    return self.review_invoice_packet_from_paths(
        tenant_id=tenant_id,
        invoice_path=str(invoice),
        purchase_order_path=str(po),
        goods_receipt_path=str(grn),
        case_label=case_id,
        target_system=target_system,
    )
```

#### `review_invoice_packet_from_paths`

既存メソッドを内部利用する。

```text
create_case
upload_document invoice
upload_document purchase_order
upload_document goods_receipt
start_review
get_review_result
build_draft_payload
```

注意:

- completed reviewのidempotencyは既存挙動に合わせる
- `write_performed=false` を必ず返す
- low-level tool outputをそのまま返さず、業務向けpacketに整形する

#### `explain_exception`

LLMは不要。まずは決定論的説明でよい。

入力:

```text
job_id
audience
```

出力に含めるもの:

```text
recommendation
recommendation_label_ja
root_causes
rule_ids
evidence
next_actions_ja
draft_message_ja
```

#### `build_approval_brief`

LLMは不要。まずはテンプレートでよい。

recommendation別のapproval action:

```text
PAY_READY_CANDIDATE       -> approve_candidate
REFER_PO_MISMATCH         -> hold
REFER_GRN_MISMATCH        -> hold
REFER_VENDOR_REVIEW       -> hold
REFER_DUPLICATE_REVIEW    -> hold
REFER_TAX_REVIEW          -> hold
REFER_INFO_REQUEST        -> hold
BLOCKED_CANDIDATE         -> return_to_requester
```

---

### 7.3 `manifest.json`

新しい高レベルtoolsを追加し、順番を上にする。

```json
{
  "tools": [
    {
      "name": "list_ap_demo_cases",
      "description": "List bundled AP invoice demo cases and explain their business value."
    },
    {
      "name": "review_ap_demo_case",
      "description": "Run a bundled AP invoice demo case end-to-end and return a business decision packet."
    },
    {
      "name": "review_ap_invoice_packet",
      "description": "Review an invoice, purchase order, and goods receipt packet end-to-end."
    },
    {
      "name": "explain_ap_exception",
      "description": "Explain AP invoice review exceptions with evidence, rule IDs, and next actions."
    },
    {
      "name": "build_ap_approval_brief",
      "description": "Build a concise approval or hold brief for an AP approver."
    },
    {
      "name": "create_ap_review_case",
      "description": "Advanced: create an AP invoice review case and return required upload slots."
    },
    {
      "name": "upload_ap_document",
      "description": "Advanced: attach a bundled demo invoice, purchase order, or goods receipt PDF to a case."
    },
    {
      "name": "start_ap_invoice_review",
      "description": "Advanced: run deterministic AP 3-way match, duplicate, vendor, and tax checks."
    },
    {
      "name": "get_ap_invoice_review_result",
      "description": "Advanced: return a completed AP review decision packet with evidence and artifacts."
    },
    {
      "name": "build_erp_draft_payload",
      "description": "Advanced: build a draft-only ERP/SaaS payload. External writes are never performed."
    }
  ]
}
```

---

### 7.4 Skill / Prompt導線

既存:

```text
enterprise-bundle/plugin/ap-invoice-review/skills/ap-review/SKILL.md
```

これを拡張する。最低限、以下を入れる。

```markdown
# AP Invoice Review Skill

Use this skill when the user asks to:
- review an AP invoice
- review a demo case such as case-a, case-b, case-c, or case-d
- determine whether an invoice is pay-ready
- explain an AP invoice exception
- build a draft ERP/SaaS payload
- create an approver brief

## UX Rules

- Prefer high-level tools.
- If the user did not specify a case or file paths, call `list_ap_demo_cases` first.
- If the user specified a demo case, call `review_ap_demo_case`.
- If the user specified three PDFs, call `review_ap_invoice_packet`.
- Do not ask the user to manually call low-level tools.
- Do not search external connector registry.
- Use the installed AP Invoice MCP tools.
- Never claim that an external ERP/SaaS write occurred.
- Always show `write_performed=false`.

## Response Format

1. 判定
2. 業務上の意味
3. 例外理由
4. 適用ルール
5. 根拠
6. 不足情報
7. 次アクション
8. draft payload summary
9. write_performed=false
```

可能なら `.mcpb` package内にもこのSkill/Promptを含める。  
もしMCPB仕様上Skill同梱が難しい場合、MCP promptsとして同等の導線を実装する。

---

## 8. MCP Promptsを実装する場合

FastMCPがpromptをサポートするなら、以下を追加する。

```python
@mcp.prompt()
def ap_demo() -> str:
    return "AP Invoice demoを開始します。まず list_ap_demo_cases を呼び、ユーザーにケースを選ばせてください。"


@mcp.prompt()
def ap_review(case_id: str = "") -> str:
    return "AP Invoice reviewを実行します。case_idがあれば review_ap_demo_case を呼んでください。"


@mcp.prompt()
def ap_explain(job_id: str = "") -> str:
    return "AP例外理由を説明します。explain_ap_exceptionを呼び、根拠と次アクションを日本語で示してください。"


@mcp.prompt()
def ap_approval_brief(job_id: str = "") -> str:
    return "承認者向け判断パケットを作ります。build_ap_approval_briefを呼んでください。"
```

ただし、Claude Desktopのslash表示仕様に依存するため、**promptsだけに依存しないこと**。  
高レベルtoolsを必ず実装する。

---

## 9. UX上の重要要件

### 9.1 初回導線

ユーザーが以下だけで動くこと。

```text
case-aをレビューして
```

期待動作:

```text
review_ap_demo_case(case_id="case-a-pay-ready")
```

ユーザーが以下だけで動くこと。

```text
請求書レビューのデモを見せて
```

期待動作:

```text
list_ap_demo_cases()
```

### 9.2 外部registry検索禁止

今回の実機テストで、Claudeが `mcp-registry連携` を使って外部connectorを探しに行った。これはUX破綻である。

Skillに必ず以下を入れる。

```text
Do not search external connector registry.
Use the installed AP Invoice Exception Review MCP tools.
```

高レベルtoolのdescriptionにも、`bundled demo cases` と明記する。

### 9.3 ファイルパスをユーザーに打たせない

サンプルケースでは、ユーザーにパスを打たせない。

NG:

```text
C:\Users\Owner\Downloads\invoice-selfserve-mcpb-main\samples\case-a-pay-ready を指定してください
```

OK:

```text
case-a-pay-ready を選択してください。
```

内部で `samples/case-a-pay-ready` を解決する。

### 9.4 低レベルtoolsを見せない

UI上のtool一覧には表示されてもよいが、Claudeの通常応答では低レベルtoolsを説明しない。

NG:

```text
まず create_ap_review_case を呼び、次に upload_ap_document を...
```

OK:

```text
請求書packetを作成し、3帳票を取り込み、照合レビューを開始します。
```

### 9.5 結果は業務語彙で出す

NG:

```text
tool returned result object
```

OK:

```text
判定: REFER_PO_MISMATCH
支払判断: 保留
理由: 請求額がPO許容差を超過
次アクション: 購買担当にPO変更有無を確認
```

---

## 10. Demo Case UX

### 10.1 case-a-pay-ready

期待:

```text
PAY_READY_CANDIDATE
```

業務価値:

```text
正常な3-way match。支払候補を自動整理する。
```

表示:

```text
請求書、PO、GRN、税額、取引先、重複チェックが一致しました。
人間承認後の支払候補です。
外部書き込みは行っていません。
```

---

### 10.2 case-b-po-mismatch

期待:

```text
REFER_PO_MISMATCH
```

業務価値:

```text
PO金額差異を検出し、支払前に止める。
```

表示:

```text
請求額がPO金額と一致していません。
許容差を超えているため、購買担当によるPO変更有無の確認が必要です。
```

---

### 10.3 case-c-duplicate

期待:

```text
REFER_DUPLICATE_REVIEW
```

業務価値:

```text
二重払いを防ぐ。
```

表示:

```text
過去請求と重複する可能性があります。
支払済み履歴、再発行請求、訂正請求の有無を確認してください。
```

---

### 10.4 case-d-vendor-review

期待:

```text
REFER_VENDOR_REVIEW
```

業務価値:

```text
支払先口座不一致を検出し、誤送金・不正支払を防ぐ。
```

表示:

```text
請求書上の銀行口座が取引先マスタと一致しません。
支払先確認が完了するまで支払保留を推奨します。
```

---

## 11. Test Plan

### 11.1 Unit Tests

追加する。

```text
test_list_demo_cases_returns_four_cases
test_review_demo_case_a_pay_ready
test_review_demo_case_b_po_mismatch
test_review_demo_case_c_duplicate
test_review_demo_case_d_vendor_review
test_review_demo_case_unknown_case_fails
test_review_invoice_packet_requires_three_pdfs
test_explain_exception_po_mismatch
test_build_approval_brief_pay_ready
test_build_approval_brief_duplicate_hold
```

### 11.2 Contract Tests

MCP tools schemaの回帰防止。

対象:

```text
list_ap_demo_cases
review_ap_demo_case
review_ap_invoice_packet
explain_ap_exception
build_ap_approval_brief
```

検証:

```text
- required fields
- enum values
- error response
- write_performed=false
- recommendation enum
- evidence structure
```

### 11.3 Golden Tests

4ケースの期待結果を固定する。

```text
tests/golden/case-a-pay-ready/expected_decision.json
tests/golden/case-b-po-mismatch/expected_decision.json
tests/golden/case-c-duplicate/expected_decision.json
tests/golden/case-d-vendor-review/expected_decision.json
```

比較対象:

```text
recommendation
rule_results.rule_id
match_results.status
write_performed
draft_payloads.generic_ap.write_performed
audit_artifacts presence
```

比較対象にしないもの:

```text
case_id
job_id
timestamp
自然文の完全一致
```

### 11.4 UX Regression Tests

Skill/Promptの回帰防止。

確認項目:

```text
- SKILL.md contains "Do not search external connector registry"
- SKILL.md instructs to prefer high-level tools
- SKILL.md mentions /ap-review /ap-demo /ap-explain /ap-approval-brief
- manifest lists high-level tools before low-level tools
- high-level tool descriptions include "bundled demo cases" or "end-to-end"
```

### 11.5 Smoke Test

以下を追加または更新する。

```bash
make smoke-ap-mcp
```

期待:

```text
- list_ap_demo_cases works
- review_ap_demo_case case-a works
- build draft payload returns write_performed=false
```

---

## 12. Acceptance Criteria

v2完了条件:

```text
Functional:
- .mcpb install後、AP Invoice toolsが表示される
- list_ap_demo_cases が4ケースを返す
- review_ap_demo_case("case-a-pay-ready") が PAY_READY_CANDIDATE を返す
- review_ap_demo_case("case-b-po-mismatch") が REFER_PO_MISMATCH を返す
- review_ap_demo_case("case-c-duplicate") が REFER_DUPLICATE_REVIEW を返す
- review_ap_demo_case("case-d-vendor-review") が REFER_VENDOR_REVIEW を返す
- すべてのdraft payloadで write_performed=false
- explain_ap_exception が根拠・ルールID・次アクションを返す
- build_ap_approval_brief が承認者向け判断パケットを返す

UX:
- ユーザーが低レベルtool順序を知らなくても使える
- "case-aをレビューして" で動く
- "/ap-demo" または同等導線でデモケース一覧が出る
- 外部connector registry検索に逃げない
- ファイルパスを要求しないデモ入口がある
- 日本語で業務レポートが出る

Security/Data boundary:
- 外部SaaS/ERP/banking/payment writeはしない
- write_performed=falseを保持
- 任意ローカルファイルは不用意に処理しない
- sidecar document_type検証を維持
- sample path制約を維持

Maintainability:
- 既存5 low-level toolsは破壊しない
- 高レベルtoolsはReviewServiceに集約する
- MCP handlerに業務ロジックを散らさない
- tests/goldenを更新
- make test / make package-ap-mcpb / make verify-ap-data-boundary / make smoke-ap-mcp が通る
```

---

## 13. 実装順序

### P0: UX破綻の修正

1. `list_ap_demo_cases` を実装
2. `review_ap_demo_case` を実装
3. `manifest.json` に高レベルtoolsを追加
4. `SKILL.md` を拡張し、外部registry検索禁止・高レベルtool優先を明記
5. `make package-ap-mcpb` で再パッケージ

### P1: 業務説明力の強化

6. `explain_ap_exception` を実装
7. `build_ap_approval_brief` を実装
8. 日本語レポートテンプレートを整備

### P2: 任意packet入口

9. `review_ap_invoice_packet` を実装
10. sidecar付きPDF packetのエラーを分かりやすくする

### P3: 回帰防止

11. unit tests追加
12. contract tests追加
13. golden tests追加
14. UX regression tests追加
15. runbook更新

---

## 14. 実装Agentへの短い依頼文

以下をそのまま実装Agentに渡してよい。

```text
AP Invoice MCPB v2を実装してください。v1はMCPBインストールと5つの低レベルtools登録には成功していますが、/ap-reviewのような業務入口がなく、ユーザーが長いプロンプトやtool順序を理解しないと使えません。これはself-serve業務MCPBとしてUXが弱いです。

v2では、既存のcreate/upload/start/get/build toolsを残しつつ、list_ap_demo_cases、review_ap_demo_case、review_ap_invoice_packet、explain_ap_exception、build_ap_approval_briefを追加してください。特にreview_ap_demo_caseはcase-a〜case-dの同梱サンプルを内部解決し、case作成、3PDF upload、review開始、result取得、draft payload生成まで一回で完了する高レベルtoolにしてください。

Skill/Prompt導線として /ap-review、/ap-demo、/ap-explain、/ap-approval-brief 相当を設計してください。SKILL.mdには、Do not search external connector registry、Use installed AP Invoice MCP tools、Prefer high-level tools、Never claim external ERP/SaaS writes、Always show write_performed=false を明記してください。

業務価値は、請求書OCRではなく、vendor master match、PO match、GRN match、duplicate check、tax check、audit artifacts、draft-only ERP/SaaS payload生成です。case-aはPAY_READY_CANDIDATE、case-bはREFER_PO_MISMATCH、case-cはREFER_DUPLICATE_REVIEW、case-dはREFER_VENDOR_REVIEWを返すこと。結果は日本語で、判定、業務上の意味、例外理由、ルールID、根拠、次アクション、draft payload summary、write_performed=falseを出してください。

任意ファイルの処理範囲やsidecar検証、write_performed=false、外部SaaS/ERPへの本書き込み禁止は維持してください。unit tests、contract tests、golden tests、UX regression tests、smoke-ap-mcpを追加・更新し、make test / make package-ap-mcpb / make verify-ap-data-boundary / make smoke-ap-mcp が通る状態にしてください。
```

---

## 15. 重要な設計判断

### 15.1 高レベルtoolは「フォールバック」ではない

`review_ap_demo_case` は緊急回避ではなく、self-serve demoの正規入口である。

### 15.2 low-level toolsは残す

既存5 toolsは後方互換とdebugのために残す。ただし、通常ユーザーに直接使わせない。

### 15.3 Skillだけに依存しない

slashやSkill表示はClaude DesktopのバージョンやMCPB仕様に依存する。  
そのため、高レベルtoolsを必ず追加する。

### 15.4 UXは業務価値そのもの

ユーザーが以下のように感じたら失敗。

```text
何のtoolをどう呼べばいいのか分からない
case-aがどこにあるか分からない
AP Invoice MCPBが見つからないと言われる
結局長いプロンプトを打たないといけない
```

v2では、ユーザーが以下だけで成功すること。

```text
case-aをレビューして
```

または

```text
/ap-demo
```
