# AP Invoice MCPB 価値集中版 実装計画・テスト設計

対象リポジトリ: `masamnisakasama/invoice-selfserve-mcpb`  
対象クライアント: Claude Desktop / local MCPB  
目的: CI/CD・配布・Remote MCP本番運用ではなく、**MCPとしてデモで価値が見える業務機能**に限定して完成度を上げる。

---

## 0. 結論

現状のAP Invoice MCPBは、すでに以下の良い骨格を持っている。

- Claude DesktopからMCP toolとして呼べる。
- ローカルフォルダ内のPDFを対象に、Claude OCRを通してAPレビューへ進める。
- 請求書・発注書・検収書を使った3-way match、vendor、duplicate、tax checkの方向性がある。
- 外部ERP/SaaSへの書き込みを行わず、draft payloadと判断根拠を返す設計になっている。

ただし、このままだとデモの見え方はまだ「OCR + ルール判定」に近い。価値を強く見せるには、MCPの強みである **ローカル状態管理、過去判断の参照、再実行可能な比較、業務アクション生成** を前面に出すべきである。

最優先で作るべきものは次の3つ。

| 優先度 | 機能 | デモ価値 | 実装難易度 | 理由 |
|---|---|---:|---:|---|
| P0 | Resolution Pack生成 | 非常に高い | 低 | 例外を検出して終わりではなく、購買担当・ベンダー・承認者に何を送るかまで出せる。すぐ使える感が出る。 |
| P0 | Local Decision Memory / 類似過去例検索 | 非常に高い | 中 | Claude単体では難しい「前回このベンダーで何が起きたか」をMCPがローカル履歴から引ける。MCPらしい価値が出る。 |
| P1 | Run Compare / 修正版差分レビュー | 高い | 中 | PO修正・請求書差替え後に「何が変わって支払可能になったか」を示せる。デモの物語が作れる。 |
| P1 | Vendor Payment Risk Checklist | 高い | 中 | 取引先・支払先・税区分・口座変更などの支払前リスクをチェックできると、OCRとの差分が明確になる。 |

逆に、今回やらないもの。

- GitHub Actions / CI/CD整備
- Remote MCP化
- OAuth認証認可
- freee/kintone/ERPへの本書き込み
- 大規模UI実装
- ベクトルDBやRAG基盤
- 複雑なマルチテナント実装

このMCPBの短期価値は、**「このフォルダをレビューして」から、支払判断・根拠・類似過去例・差分・次アクションまで出ること**である。

---

## 1. デモで見せるべきユースケース

### 1.1 ユースケースA: PO差異を検出し、購買担当へ確認依頼を作る

ユーザー発話:

```text
case-bをレビューして。支払ってよいか、必要なら購買担当への確認文も作って。
```

期待される見え方:

1. Claude DesktopがAP Invoice MCPBを呼ぶ。
2. MCPBが請求書・発注書・検収書のOCR結果から照合する。
3. `REFER_PO_MISMATCH` を返す。
4. さらにResolution Packで、購買担当への確認文、必要資料、承認者向け要約を返す。

価値:

- 単に「差異があります」ではなく、**次に誰へ何を聞くべきか**まで返る。
- AP担当者の実務に直結する。
- 外部SaaSに書き込まないのでデモ安全性が高い。

---

### 1.2 ユースケースB: 重複疑いを、過去レビュー履歴と照合する

ユーザー発話:

```text
この請求書、前にも似たものを見ていないか確認して。
```

期待される見え方:

1. 現在のレビュー結果から `vendor_id`, `invoice_number`, `po_number`, `amount`, `rule_ids` を抽出。
2. `_runs/decision_index.jsonl` を検索。
3. 類似ケースをスコア順に返す。
4. 「前回も同一ベンダー・同一PO・近い金額でduplicate reviewになっている」と説明する。

価値:

- Claudeの会話メモリではなく、MCPBが監査可能なローカル履歴として持つ。
- 「MCPが業務システムの小さな記憶装置になる」ことが見える。
- ただのOCRデモではなく、支払前統制のデモになる。

---

### 1.3 ユースケースC: 修正版POを入れて再レビューし、差分を出す

ユーザー発話:

```text
修正版POを入れたので、前回のレビューと比べて何が変わったか見て。
```

期待される見え方:

1. 修正版フォルダを再レビューする。
2. 新旧run_idを比較する。
3. `recommendation`, `rule_ids`, `amount_diff`, `missing_fields`, `draft_payload` の差分を返す。
4. 「PO差異が解消され、支払候補に変わった」と示す。

価値:

- AP業務は一回の判定で終わらず、差戻し・修正・再確認が多い。
- 修正後の改善点を説明できると、実務の流れに近くなる。
- デモでストーリーが作りやすい。

---

### 1.4 ユースケースD: 支払先リスクをチェックする

ユーザー発話:

```text
この請求書、支払先や税区分にリスクがないか見て。
```

期待される見え方:

1. OCR結果から `vendor_name`, `vendor_id`, `bank_account`, `tax_registration`, `payment_terms` などを拾う。
2. vendor master / tax code master と照合する。
3. 口座不一致、新規口座、inactive vendor、税コード不整合などを返す。
4. 支払保留または追加確認の次アクションを返す。

価値:

- 経理BPO・支払統制で非常に刺さる。
- 「読む」ではなく「払ってよいかを見る」デモになる。
- ただしデータ追加が必要な場合があるためP1扱い。

---

## 2. 全体アーキテクチャ方針

### 2.1 現状の主経路を維持する

既存の主経路は維持する。

```text
ap_invoice_prepare_ocr_run
  -> Claude OCR
  -> ap_invoice_submit_ocr_result
  -> ap_invoice_review_from_ocr_result
  -> ap_invoice_explain_exception / ap_invoice_build_approval_brief
```

今回追加する価値機能は、この後段に付ける。

```text
review completed
  -> decision index append
  -> similar case search
  -> resolution pack generation
  -> run comparison
```

### 2.2 新規モジュール

追加するPythonモジュール候補。

```text
ap_invoice_core/
  resolution.py   # Resolution Pack生成
  history.py      # ローカル判断履歴 index / 類似検索
  compare.py      # run間差分比較
  risk.py         # vendor/payment risk checklist（P1）
```

### 2.3 新規MCP tools

manifestとserverに追加する高価値tool。

```text
ap_invoice_build_resolution_pack
ap_invoice_find_similar_reviews
ap_invoice_compare_review_runs
ap_invoice_check_vendor_payment_risk  # P1、可能なら追加
```

既存の `ap_invoice_build_approval_brief` は残す。新規 `resolution_pack` は承認者向けbriefよりも広く、AP担当者・購買担当・ベンダー向け文面まで含める。

---

## 3. P0: Resolution Pack生成

### 3.1 目的

APレビューの結果から、実務担当者がそのまま使える次アクション一式を生成する。

現在のレビュー結果が `REFER_PO_MISMATCH`, `REFER_DUPLICATE_REVIEW`, `REFER_VENDOR_REVIEW`, `PAY_READY_CANDIDATE` などを返すなら、それぞれに応じて以下を生成する。

- AP担当者向け要約
- 購買担当への確認依頼文
- ベンダーへの差戻し/確認依頼文
- 承認者向けbrief
- 必要添付・確認すべき証跡
- 支払可否の暫定結論
- 外部書き込みなしの明示

### 3.2 新規tool

```python
def ap_invoice_build_resolution_pack(
    run_id: str,
    audience: str = "ap_operator",
    language: str = "ja",
) -> dict:
    """Build a practical resolution pack for a completed AP invoice review."""
```

### 3.3 入力

| field | type | required | description |
|---|---|---:|---|
| `run_id` | string | yes | completed OCR review run id |
| `audience` | string | no | `ap_operator`, `approver`, `procurement`, `vendor` |
| `language` | string | no | initially `ja` only |

### 3.4 出力スキーマ

```json
{
  "status": "RESOLUTION_PACK_BUILT",
  "run_id": "ocr-run-20260621-...",
  "recommendation": "REFER_PO_MISMATCH",
  "recommendation_label_ja": "発注書差異確認",
  "business_summary_ja": "請求金額が発注書の許容差を超えています。支払前に購買担当へ変更POの有無を確認してください。",
  "risk_level": "medium",
  "decision": {
    "payment_action": "hold",
    "can_pay_now": false,
    "external_write_performed": false
  },
  "next_actions": [
    {
      "owner": "procurement",
      "action_ja": "PO変更有無と承認済み変更POの存在を確認する",
      "due_hint_ja": "支払予定日前まで",
      "required_evidence": ["approved revised PO", "buyer confirmation"]
    }
  ],
  "messages": {
    "to_procurement_ja": "購買担当者様\n請求書 INV-... について、PO金額との差異が検出されています。変更POまたは承認済み差額の有無をご確認ください。",
    "to_vendor_ja": "お取引先様\n請求書 INV-... について、発注書との差異確認中です。必要に応じて修正版請求書のご提出をお願いする可能性があります。",
    "to_approver_ja": "本件はPO差異のため現時点では支払保留候補です。購買担当確認後に再レビューしてください。"
  },
  "evidence_refs": [
    {
      "source": "invoice",
      "field": "total_amount",
      "value": 121000,
      "page": 1
    }
  ],
  "draft_payload_summary": {
    "payment_status": "draft_hold",
    "write_performed": false
  },
  "write_performed": false
}
```

### 3.5 実装設計

#### 3.5.1 `resolution.py`

新規ファイル。

```python
class ResolutionPackBuilder:
    def build(self, completed_review: dict, audience: str = "ap_operator") -> dict:
        ...
```

責務。

- `recommendation` に応じたテンプレート選択
- `rule_ids` と `match_results` から next action を生成
- `evidence` を人間が読める形に要約
- copy-paste可能な文面を作成
- `write_performed=false` を必ず出す

#### 3.5.2 recommendation別テンプレート

| recommendation | payment_action | owner | next action |
|---|---|---|---|
| `PAY_READY_CANDIDATE` | `ready_to_pay` | AP | 支払候補として承認フローへ回す |
| `REFER_PO_MISMATCH` | `hold` | Procurement | 変更PO・承認済み差額の確認 |
| `REFER_DUPLICATE_REVIEW` | `hold` | AP | 過去請求・支払履歴の確認 |
| `REFER_VENDOR_REVIEW` | `hold` | Vendor Master Owner | 取引先マスタ・支払先情報確認 |
| `REFER_TAX_REVIEW` | `hold` | Tax/AP | 税コード・消費税額確認 |
| unknown | `manual_review` | AP | 手動確認 |

#### 3.5.3 `ReviewService`への追加

```python
def build_resolution_pack(self, run_id: str, audience: str = "ap_operator", language: str = "ja") -> dict:
    completed = self._load_completed_review(run_id)
    return ResolutionPackBuilder().build(completed, audience=audience)
```

#### 3.5.4 `server.py`への追加

```python
@mcp.tool()
def ap_invoice_build_resolution_pack(
    run_id: str,
    audience: str = "ap_operator",
    language: str = "ja",
) -> dict[str, Any]:
    return service.build_resolution_pack(run_id=run_id, audience=audience, language=language)
```

#### 3.5.5 manifest更新

既存の `ap_invoice_build_approval_brief` の直後に追加。

```json
{
  "name": "ap_invoice_build_resolution_pack",
  "description": "Build practical next-action messages and evidence packet for a completed AP invoice review."
}
```

### 3.6 受入条件

- `case-b` のPO差異で、購買担当への確認文が出る。
- `case-c` の重複疑いで、過去請求確認のnext actionが出る。
- `case-d` の取引先確認で、vendor master確認のnext actionが出る。
- `case-a` の正常系で、支払候補として承認へ進めるbriefが出る。
- すべての出力に `write_performed=false` が含まれる。
- 外部SaaS/ERPへの書き込みを示唆しない。

### 3.7 テスト設計

#### Unit tests

```text
test_resolution_pack_pay_ready_candidate
test_resolution_pack_po_mismatch_has_procurement_message
test_resolution_pack_duplicate_has_history_review_action
test_resolution_pack_vendor_review_has_vendor_master_action
test_resolution_pack_unknown_recommendation_falls_back_to_manual_review
test_resolution_pack_always_write_performed_false
test_resolution_pack_messages_do_not_claim_external_write
```

#### Integration tests

```text
test_case_a_review_then_resolution_pack
test_case_b_review_then_resolution_pack
test_case_c_review_then_resolution_pack
test_case_d_review_then_resolution_pack
```

#### E2E manual QA

```text
1. Claude DesktopでAP Invoice MCPBを有効化
2. 「AP Invoiceデモを開始して」
3. 「case-bをレビューして」
4. review完了後、「購買担当に送る確認文を作って」
5. ap_invoice_build_resolution_pack が呼ばれること
6. PO差異・購買担当確認・write_performed=falseが出ること
```

---

## 4. P0: Local Decision Memory / 類似過去例検索

### 4.1 目的

レビュー完了ごとに、判断結果の軽量indexをローカルに保存し、次回以降に類似ケースを検索できるようにする。

これはMCPとして非常に価値が高い。Claude単体では「過去にこのローカルMCPBで処理したAPレビュー履歴」を安定して持てない。MCPが小さな業務履歴を持つことで、会話が業務システム化する。

### 4.2 保存場所

```text
Documents/APInvoiceDemo/_runs/decision_index.jsonl
```

または現在の `_runs` ルート配下。

1行1レビュー。

```json
{
  "run_id": "ocr-run-20260621-001",
  "completed_at": "2026-06-21T13:00:00+09:00",
  "case_id": "case-b-po-mismatch",
  "folder_path_hash": "sha256:...",
  "vendor_id": "V-1001",
  "vendor_name": "Tokyo Office Supply",
  "invoice_number": "INV-2026-0009",
  "po_number": "PO-2026-0002",
  "invoice_total": 121000,
  "currency": "JPY",
  "recommendation": "REFER_PO_MISMATCH",
  "rule_ids": ["AP-PO-001"],
  "risk_level": "medium",
  "artifact_uri": "artifact://ap-invoice-runs/ocr-run-20260621-001/review.json",
  "write_performed": false
}
```

注意: `folder_path` の絶対パスをそのまま保存しない。必要ならhash化する。出力には `artifact_uri` を使う。

### 4.3 新規tool

```python
def ap_invoice_find_similar_reviews(
    run_id: str | None = None,
    vendor_id: str | None = None,
    po_number: str | None = None,
    invoice_number: str | None = None,
    recommendation: str | None = None,
    rule_id: str | None = None,
    limit: int = 5,
) -> dict:
    """Find similar completed AP reviews from local decision history."""
```

### 4.4 類似度スコア

まずはembedding不要。決定論的スコアで十分。

| 条件 | score |
|---|---:|
| vendor_id exact match | +40 |
| po_number exact match | +30 |
| invoice_number exact match | +50 |
| recommendation same | +20 |
| rule_ids overlap | +20 |
| amount within 1% | +15 |
| amount within 5% | +8 |
| same case family | +5 |

重複判定の場合は `invoice_number exact match` を強くする。PO差異やvendor reviewの場合は vendor/PO/rule overlap を強くする。

### 4.5 `review_from_ocr_result` への統合

レビュー完了時にindexへappendする。

```python
completed = self.review_from_ocr_result(...)
DecisionHistoryStore(...).append(completed)
completed["similar_cases"] = DecisionHistoryStore(...).find_similar(completed, limit=3)
return completed
```

ただし、自分自身のrun_idは類似結果から除外する。

### 4.6 出力例

```json
{
  "status": "SIMILAR_REVIEWS_FOUND",
  "query": {
    "run_id": "ocr-run-20260621-002",
    "vendor_id": "V-1001",
    "po_number": "PO-2026-0002"
  },
  "similar_reviews": [
    {
      "run_id": "ocr-run-20260620-004",
      "score": 90,
      "matched_on": ["vendor_id", "po_number", "rule_ids"],
      "recommendation": "REFER_PO_MISMATCH",
      "summary_ja": "同一取引先・同一POで、前回もPO差異確認になっています。",
      "artifact_uri": "artifact://ap-invoice-runs/ocr-run-20260620-004/review.json"
    }
  ],
  "write_performed": false
}
```

### 4.7 実装設計

#### 4.7.1 `history.py`

```python
class DecisionHistoryStore:
    def __init__(self, runs_dir: Path):
        self.index_path = runs_dir / "decision_index.jsonl"

    def append(self, completed_review: dict) -> None:
        ...

    def find_similar(self, query: dict, limit: int = 5) -> list[dict]:
        ...

    def score(self, query: dict, candidate: dict) -> tuple[int, list[str]]:
        ...
```

#### 4.7.2 正規化

index化する前に、以下を正規化する。

```text
vendor_id: uppercase trim
po_number: uppercase trim
invoice_number: uppercase trim
currency: uppercase
amount: Decimal -> int/float safe
rule_ids: sorted unique
recommendation: uppercase trim
```

#### 4.7.3 プライバシー

- 絶対パスは保存しない。
- 必要なら `folder_path_hash` のみにする。
- OCR全文はindexに保存しない。
- 必要最小限の業務メタデータのみ保存する。

### 4.8 受入条件

- review完了後、`decision_index.jsonl` に1行追加される。
- 同一run_idの重複appendは起きない。再実行時はupsertまたはskip。
- `ap_invoice_find_similar_reviews(run_id=...)` が類似ケースを返す。
- exact matchなしの場合でも、vendor/rule/amountに基づく近似類似が返る。
- index内に絶対ローカルパスが保存されない。
- 出力に `write_performed=false` が含まれる。

### 4.9 テスト設計

#### Unit tests

```text
test_decision_history_append_creates_jsonl
test_decision_history_append_is_idempotent_by_run_id
test_decision_history_does_not_store_absolute_paths
test_similarity_score_invoice_number_exact_highest
test_similarity_score_vendor_po_rule_overlap
test_similarity_score_amount_tolerance
test_find_similar_excludes_same_run_id
test_find_similar_limit_is_respected
test_find_similar_empty_index_returns_empty_list
```

#### Integration tests

```text
test_case_b_review_appends_history_index
test_case_c_duplicate_finds_previous_same_invoice
test_case_d_vendor_review_finds_same_vendor_history
test_review_result_includes_top_similar_cases_when_available
```

#### E2E manual QA

```text
1. case-cをレビューする
2. 同じcase-cまたは類似caseをもう一度レビューする
3. 「似た過去レビューを探して」と言う
4. 同一vendor / invoice / rule_idに基づく類似ケースが出る
5. Claudeが「前回も重複疑い」と説明できる
```

---

## 5. P1: Run Compare / 修正版差分レビュー

### 5.1 目的

同じフォルダまたは同じcaseを再レビューしたときに、前回runと今回runの差分を返す。

AP実務では、例外発生後に以下が起きる。

- 修正版POが追加される。
- 請求書が差し替えられる。
- 検収書が追加される。
- 取引先マスタが修正される。
- 税コードが修正される。

その後に「何が変わって支払可能になったのか」を説明できると強い。

### 5.2 新規tool

```python
def ap_invoice_compare_review_runs(
    base_run_id: str,
    candidate_run_id: str,
) -> dict:
    """Compare two completed AP invoice review runs and explain what changed."""
```

### 5.3 出力例

```json
{
  "status": "RUNS_COMPARED",
  "base_run_id": "ocr-run-001",
  "candidate_run_id": "ocr-run-002",
  "recommendation_change": {
    "from": "REFER_PO_MISMATCH",
    "to": "PAY_READY_CANDIDATE",
    "meaning_ja": "PO差異が解消され、支払候補に変わりました。"
  },
  "rule_changes": {
    "resolved": ["AP-PO-001"],
    "new": [],
    "unchanged": []
  },
  "field_changes": [
    {
      "field": "po_total_amount",
      "from": 110000,
      "to": 121000,
      "meaning_ja": "発注書金額が請求金額に一致しました。"
    }
  ],
  "payment_readiness_change": {
    "from": false,
    "to": true
  },
  "next_action_ja": "承認者向けbriefを作成し、支払候補として確認してください。",
  "write_performed": false
}
```

### 5.4 実装設計

#### 5.4.1 `compare.py`

```python
class ReviewRunComparator:
    def compare(self, base_review: dict, candidate_review: dict) -> dict:
        ...
```

比較対象。

```text
recommendation
recommendation_label_ja
rule_ids
match_results.vendor
match_results.po
match_results.grn
match_results.duplicate
match_results.tax
draft_payload_summary.payment_status
canonical_facts.invoice.total_amount
canonical_facts.purchase_order.total_amount
canonical_facts.goods_receipt.received_quantity
```

#### 5.4.2 差分分類

| 差分 | meaning |
|---|---|
| rule_idが消えた | 問題が解消した可能性 |
| rule_idが増えた | 新しい問題が出た |
| recommendationがholdからpay_ready | 支払候補へ改善 |
| recommendationがpay_readyからhold | リスク悪化 |
| amount差分が縮小 | PO/請求差異の改善 |
| evidence pageが変わった | OCR対象/帳票差替えの可能性 |

### 5.5 受入条件

- 2つのcompleted runを比較できる。
- `recommendation` の変化が日本語で説明される。
- 解消したrule、新規rule、継続ruleを分けて返す。
- 支払可否の変化が明示される。
- 絶対パスを返さない。
- `write_performed=false` を返す。

### 5.6 テスト設計

#### Unit tests

```text
test_compare_recommendation_hold_to_pay_ready
test_compare_recommendation_pay_ready_to_hold
test_compare_resolved_rule_ids
test_compare_new_rule_ids
test_compare_field_amount_changes
test_compare_handles_missing_optional_fields
test_compare_always_write_performed_false
```

#### Integration tests

```text
test_compare_case_b_original_vs_fixed_po_fixture
test_compare_case_missing_grn_vs_with_grn_fixture
test_compare_duplicate_review_unchanged
```

#### Test fixtures

追加fixture候補。

```text
case-b-po-mismatch-fixed/
  invoice.pdf
  purchase_order.pdf   # amount corrected
  goods_receipt.pdf
```

またはOCR結果JSONだけをfixtureとして持つ。

---

## 6. P1: Vendor Payment Risk Checklist

### 6.1 目的

支払前統制として、取引先・支払先・税区分・支払条件のリスクを明示する。

### 6.2 最小スコープ

最初は以下のみでよい。

| check | 入力 | 参照先 | recommendation |
|---|---|---|---|
| vendor_id exists | OCR invoice vendor_id | vendor_master | not foundならvendor review |
| vendor active | vendor_master.status | vendor_master | inactiveならhold |
| vendor name fuzzy match | OCR vendor name | vendor_master | 低スコアならreview |
| tax code valid | OCR tax code | tax_code_master | invalidならtax review |
| bank account match | OCR bank_account | vendor_master | mismatchならpayment risk |

bank accountがOCR/CSVに存在しない場合は、P1ではwarning扱いにする。

### 6.3 新規tool

```python
def ap_invoice_check_vendor_payment_risk(
    run_id: str,
) -> dict:
    """Check vendor and payment risk signals for a completed AP invoice review."""
```

### 6.4 出力例

```json
{
  "status": "VENDOR_PAYMENT_RISK_CHECKED",
  "run_id": "ocr-run-...",
  "risk_level": "high",
  "risk_signals": [
    {
      "code": "BANK_ACCOUNT_MISMATCH",
      "severity": "high",
      "message_ja": "請求書の振込先口座が取引先マスタと一致しません。支払前に取引先マスタ管理者へ確認してください。"
    }
  ],
  "next_actions_ja": [
    "支払を保留し、取引先マスタ管理者へ口座変更の承認証跡を確認してください。"
  ],
  "write_performed": false
}
```

### 6.5 実装注意

- OCRでbank accountが取れない場合に誤検知しない。
- `missing_bank_account` は `high risk` ではなく `needs_manual_check` にする。
- デモデータにbank accountを入れられるなら価値が上がるが、時間がなければvendor active / tax codeだけでもよい。

### 6.6 テスト設計

```text
test_vendor_risk_active_vendor_no_signal
test_vendor_risk_inactive_vendor_high_signal
test_vendor_risk_unknown_vendor_review_signal
test_vendor_risk_tax_code_invalid
test_vendor_risk_missing_bank_account_is_warning_not_high
test_vendor_risk_bank_account_mismatch_high_if_data_available
test_vendor_risk_write_performed_false
```

---

## 7. MCP tool順序と会話設計

### 7.1 推奨tool順

manifestでは、ユーザー価値が高い順に並べる。

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_preview_folder
ap_invoice_review_folder
ap_invoice_review_demo_case
ap_invoice_submit_ocr_result
ap_invoice_review_from_ocr_result
ap_invoice_explain_exception
ap_invoice_build_approval_brief
ap_invoice_build_resolution_pack
ap_invoice_find_similar_reviews
ap_invoice_compare_review_runs
ap_invoice_check_vendor_payment_risk
```

### 7.2 Claudeに誘導してほしい自然言語

以下の発話で自然にtoolが呼ばれること。

```text
AP Invoiceデモを開始して
case-bをレビューして
このフォルダ内をレビューして
この例外の理由を説明して
購買担当に確認する文面を作って
似た過去レビューを探して
前回のレビューと何が変わったか比較して
支払先リスクを確認して
```

### 7.3 やってはいけない誘導

```text
Airtableを探す
Google Driveを探す
外部connector registryを探す
ERPへ登録したと主張する
支払実行したと主張する
ローカル絶対パスを監査成果物として露出する
```

---

## 8. 実装タスク分解

### 8.1 Day 1: Resolution Pack

```text
1. ap_invoice_core/resolution.py を追加
2. recommendation別テンプレートを実装
3. ReviewService.build_resolution_pack を追加
4. server.pyに ap_invoice_build_resolution_pack を追加
5. manifest.jsonにtool追加
6. unit tests追加
7. case-a〜dのintegration test追加
```

完了条件。

```text
case-b review後に購買担当向け確認文が出る。
case-c review後に重複確認アクションが出る。
case-d review後に取引先マスタ確認アクションが出る。
```

### 8.2 Day 2: Local Decision Memory

```text
1. ap_invoice_core/history.py を追加
2. DecisionHistoryStore.append/find_similar/score を実装
3. review_from_ocr_result完了時にindex append
4. ap_invoice_find_similar_reviews toolを追加
5. manifest.jsonにtool追加
6. 類似スコアunit tests追加
7. 同一run除外・絶対パス非保存テスト追加
```

完了条件。

```text
case-cを2回処理すると、2回目に類似過去レビューを返せる。
indexに絶対パスが残らない。
```

### 8.3 Day 3: Run Compare

```text
1. ap_invoice_core/compare.py を追加
2. ReviewRunComparator.compare を実装
3. ReviewService.compare_review_runs を追加
4. ap_invoice_compare_review_runs toolを追加
5. fixed PO fixtureまたはsynthetic completed review fixtureを追加
6. unit/integration tests追加
```

完了条件。

```text
PO差異runと修正版runを比較し、recommendation改善・解消ruleを説明できる。
```

### 8.4 Day 4以降: Vendor Payment Risk Checklist

```text
1. vendor_masterにstatus/bank_account/tax_registration等があるか確認
2. 足りない場合はデモデータに最小追加
3. ap_invoice_core/risk.py を追加
4. vendor/tax/payment risk rulesを実装
5. ap_invoice_check_vendor_payment_risk toolを追加
6. tests追加
```

完了条件。

```text
unknown vendor / inactive vendor / tax code invalid / bank mismatchを説明できる。
```

---

## 9. テスト全体設計

### 9.1 Unit Test Matrix

| area | test target | must verify |
|---|---|---|
| Resolution Pack | recommendation mapping | payment action / owner / next action |
| Resolution Pack | message generation | AP/procurement/vendor/approver文面 |
| Resolution Pack | safety | write_performed=false、外部write主張なし |
| History | append | jsonl作成、idempotent、schema |
| History | privacy | 絶対パス非保存、OCR全文非保存 |
| History | similarity | vendor/PO/invoice/rule/amount scoring |
| Compare | recommendation diff | hold->pay, pay->hold |
| Compare | rule diff | resolved/new/unchanged |
| Compare | field diff | amount/vendor/tax/status差分 |
| Risk | vendor checks | unknown/inactive/name mismatch |
| Risk | tax checks | invalid tax code |
| Risk | payment checks | bank mismatch/missing handling |

### 9.2 Integration Test Matrix

| scenario | flow | expected |
|---|---|---|
| case-a pay ready | review -> resolution | 支払候補brief |
| case-b PO mismatch | review -> resolution | 購買担当確認文 |
| case-c duplicate | review -> history -> similar | 類似重複候補 |
| case-d vendor review | review -> risk/resolution | 取引先確認action |
| fixed PO | review old -> review fixed -> compare | 差異解消 |
| missing docs | preview/review | fail fast with remediation |
| blocked legacy | old tool call | blocked and migration guidance |

### 9.3 Golden Tests

既存のgolden testに次を追加する。

```text
golden_resolution_case_a.json
golden_resolution_case_b.json
golden_resolution_case_c.json
golden_resolution_case_d.json
golden_similarity_case_c.json
golden_compare_case_b_fixed.json
```

Goldenで固定すべきもの。

```text
status
recommendation
risk_level
payment_action
next_actions owner/action
message keys existence
write_performed=false
rule_ids
```

Goldenで固定しすぎないもの。

```text
自然文の完全一致
日時
run_id
artifact_uriの細部
scoreの小数部
```

### 9.4 Manual QA Script

```text
1. Claude DesktopでMCPBを有効化する
2. 「AP Invoiceデモを開始して」
3. 「case-bをレビューして」
4. OCR結果submit後、REFER_PO_MISMATCHになること
5. 「購買担当に送る確認文を作って」
6. ap_invoice_build_resolution_pack が呼ばれ、確認文が出ること
7. 「似た過去レビューを探して」
8. ap_invoice_find_similar_reviews が呼ばれること
9. 修正版caseをレビューする
10. 「前回と今回を比較して」
11. ap_invoice_compare_review_runs が呼ばれ、解消ruleが表示されること
12. すべての回答で外部書き込みなしが明示されること
```

---

## 10. 受入条件

### 10.1 Business Value

```text
- 例外検出だけでなく、次アクション文面まで出る
- 類似過去レビューをローカル履歴から引ける
- 修正版との差分を説明できる
- 支払可否・保留理由・証跡・担当者が明確
```

### 10.2 MCP Value

```text
- Claude単体ではなくMCPが履歴・照合・差分・成果物生成を担う
- 低レベルtool名を知らなくても自然文で動く
- ローカルフォルダとローカル履歴を安全に扱える
- 外部SaaSに逃げない
```

### 10.3 Safety

```text
- external ERP/SaaS writeなし
- write_performed=falseを常に返す
- 絶対パスやOCR全文をdecision_indexに保存しない
- legacy sidecar flowは引き続きblocked
- 類似履歴検索はローカル_runs配下のみ
```

### 10.4 Test

```text
- 新規unit testsがすべて通る
- case-a〜dのintegration testsが通る
- golden testsが通る
- Claude Desktop manual QAで主要発話が通る
```

---

## 11. 実装Agentへの依頼文

```text
AP Invoice MCPBの価値機能を、CI/CDやRemote MCPではなく、Claude Desktop上のMCPとしての業務価値に絞って実装してください。

最優先は3つです。

1. ap_invoice_build_resolution_pack を追加してください。
completed reviewのrun_idから、AP担当者・購買担当・ベンダー・承認者向けの次アクション、確認文、支払可否、根拠、write_performed=falseを返してください。PO差異、重複疑い、取引先確認、正常支払候補の4パターンを最低限カバーしてください。

2. ap_invoice_find_similar_reviews を追加してください。
review完了時に _runs/decision_index.jsonl へ軽量indexをappendし、vendor_id、po_number、invoice_number、amount、recommendation、rule_idsで類似過去レビューを決定論的に検索できるようにしてください。絶対パスやOCR全文は保存しないでください。

3. ap_invoice_compare_review_runs を追加してください。
2つのcompleted runを比較し、recommendationの変化、解消したrule、新規rule、金額や主要fieldの差分、支払可能性の変化を日本語で返してください。

可能ならP1として ap_invoice_check_vendor_payment_risk も追加してください。取引先マスタ、税コード、支払先情報の不一致を支払前リスクとして返す機能です。データが足りない場合はbank accountはwarning扱いにし、unknown vendor / inactive vendor / invalid tax codeを先に実装してください。

既存のClaude OCR folder flowは維持してください。外部ERP/SaaSへの書き込みは絶対に行わず、すべての新規tool出力に write_performed=false を含めてください。

テストは、unit / integration / golden / Claude Desktop manual QAを追加してください。特にcase-b PO mismatchで購買担当向け確認文が出ること、case-c duplicateで類似過去レビューが返ること、修正版PO fixtureでrun比較によりPO差異解消が説明されることを受入条件にしてください。
```

---

## 12. 最終判断

「MCPとして本当に価値があるか」という観点では、OCR精度を少し上げるよりも、次の3点の方がデモ効果が大きい。

```text
1. 例外を見つけて終わらず、次に送る文面と必要証跡まで作る
2. 過去のローカル判断履歴を使って、似た支払リスクを探す
3. 修正前後の差分を説明し、支払可能になった理由を示す
```

これにより、AP Invoice MCPBは「帳票を読むMCP」ではなく、**支払前判断を会話内で完結させるローカル業務ワークベンチ**として見える。
