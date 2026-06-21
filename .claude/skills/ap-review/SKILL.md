---
name: ap-review
description: "Use this skill whenever the user wants to review an AP invoice, purchase order, or goods receipt for payment approval, or asks what to send next after an AP review. Triggers: 'review invoice', 'AP review', 'invoice check', 'payment review', 'レビュー', '請求書', '支払審査', '帳票', 'case-a', 'case-b', 'case-c', 'case-d', 'case-e', 'case-f', '/ap-review', '/ap-demo', '/ap-explain', '/ap-approval-brief', '確認文', '次アクション', 'resolution pack', any mention of reviewing PDF documents in a folder for 3-way matching or AP processing."
---

# AP Invoice Review — Auto-Flow Skill

## 概要

このスキルは、Coworkセッションで「case-a をレビューして」などのコマンドを受けると、ユーザーの操作なしに以下の流れを自動実行します。

1. デモワークスペース準備 / フォルダ確認
2. PDFをMCP経由で画像レンダリング（Claude OCR用）
3. Claude OCRで帳票3点（請求書・発注書・納品書）を読み取り
4. 決定論的3-wayマッチ → 判定結果を返す
5. 必要に応じて購買担当・取引先・承認者向けのResolution Packを返す

---

## Auto-Flow Rule

**Pattern A — デモケース（case-a 〜 case-f）**

```
ap_invoice_setup_demo_workspace()
→ ap_invoice_review_demo_case(case_id)   # 画像が返ってくる
→ [Claude OCR: 3帳票を全フィールド読み取り]
→ ap_invoice_submit_ocr_result(run_id, ocr_results)
→ ap_invoice_review_from_ocr_result(run_id)
→ 判定結果を日本語で報告
```

**Pattern B — 実フォルダ（絶対パス指定）**

```
ap_invoice_prepare_ocr_run(folder_path)   # 画像が返ってくる
→ [Claude OCR: 3帳票を全フィールド読み取り]
→ ap_invoice_submit_ocr_result(run_id, ocr_results)
→ ap_invoice_review_from_ocr_result(run_id)
→ 判定結果を日本語で報告
```

ユーザーが「確認文も作って」「次に何を送るか」「購買担当向けにまとめて」「resolution pack」などを求めた場合は、レビュー完了後に続けて実行する。

```
ap_invoice_build_resolution_pack(run_id, audience="ap_operator", language="ja")
→ 次アクション、必要証跡、購買/取引先/承認者向け文面、write_performed=false を報告
```

---

## case_id マッピング

| ユーザー入力 | case_id |
|---|---|
| case-a | case-a-pay-ready |
| case-b | case-b-po-mismatch |
| case-c | case-c-duplicate |
| case-d | case-d-vendor-review |
| case-e | case-e-grn-mismatch |
| case-f | case-f-tax-review |

---

## OCR フォーマット

`ap_invoice_submit_ocr_result` に渡す `ocr_results` は必ず以下の形式：

```json
{
  "invoice": {
    "document_type": "invoice",
    "fields": { "invoice_number": "...", "total_amount": 110000, ... }
  },
  "purchase_order": {
    "document_type": "purchase_order",
    "fields": { "po_number": "...", "approved": true, ... }
  },
  "goods_receipt": {
    "document_type": "goods_receipt",
    "fields": { "receipt_number": "...", "received_quantity": 100, ... }
  }
}
```

`fields` キーが欠けている場合はバリデーション失敗になる。flat形式（fieldsなし）は送らないこと。

---

## 判定一覧

| 判定コード | 意味 |
|---|---|
| PAY_READY_CANDIDATE | 全チェック通過、支払可 |
| REFER_PO_MISMATCH | PO金額差異あり |
| REFER_DUPLICATE_REVIEW | 重複請求の疑い |
| REFER_VENDOR_REVIEW | 取引先マスタ不一致 |
| REFER_GRN_MISMATCH | 検収数量不足 |
| REFER_TAX_REVIEW | 税額計算不一致 |

---

## 部分帳票の扱い

| 状況 | 対応 |
|---|---|
| 請求書のみ | このデモMCPBではレビューを開始しない。請求書・発注書・検収書PDFを含むフォルダを依頼する |
| PO/GRN不足 | このデモMCPBではレビューを開始しない。不足PDFを追加してから再実行する |
| フィールド欠損 | `missing_information` に列挙される |
| 画像が不鮮明 | OCR結果を最善努力で読み取り、不明フィールドはnullで送る |

付け焼き刃のfallbackは使わない。帳票種別が不明な場合はClaudeが内容から推定する。

## Resolution Pack

レビュー完了後、ユーザーが次アクション、確認文、購買担当・取引先・承認者への文面を求めたら、会話内で作文だけをせず、必ず `ap_invoice_build_resolution_pack` を呼ぶ。

返答には以下を含める。

1. 支払アクション（支払候補 / 保留 / 手動確認）
2. 担当者別の次アクション
3. 必要証跡
4. 購買担当・取引先・承認者向け文面
5. `write_performed=false`

外部ERP/SaaSへの登録、支払実行、外部送信を行ったとは絶対に書かない。
