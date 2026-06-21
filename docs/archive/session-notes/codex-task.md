# Task: Add /ap-review slash command to AP Invoice Review MCPB

## Repository
`C:\Users\Owner\Documents\mcpb-push` (already cloned, up to date)

## What to do

### Step 1: Create `commands/ap-review.md`

Create the file `commands/ap-review.md` with this exact content:

```markdown
---
description: "AP請求書の3-wayマッチレビューを実行する。引数: case-a〜case-f（デモ）またはフォルダパス（実運用）"
---

# /ap-review — AP Invoice Review

引数に応じて以下を即実行する。確認・質問は一切しない。

## 引数がない場合

1. `ap_invoice_setup_demo_workspace()` を呼ぶ
2. `ap_invoice_list_demo_cases()` を呼ぶ
3. 結果を日本語で表示する

## 引数が case-a〜case-f の場合（デモモード）

case_id マッピング:
- case-a → case-a-pay-ready
- case-b → case-b-po-mismatch
- case-c → case-c-duplicate
- case-d → case-d-vendor-review
- case-e → case-e-grn-mismatch
- case-f → case-f-tax-review

実行順序（省略・変更・確認不可）:

1. `ap_invoice_setup_demo_workspace()` を呼ぶ
2. `ap_invoice_review_demo_case(case_id)` を呼ぶ → PDF画像が返る
3. 返ってきた画像を Claude OCR で全フィールド読み取る（請求書・発注書・納品書）
4. `ap_invoice_submit_ocr_result(run_id, ocr_results)` を呼ぶ
   - ocr_results は必ず以下の形式:
   ```json
   {
     "invoice": { "document_type": "invoice", "fields": { ... } },
     "purchase_order": { "document_type": "purchase_order", "fields": { ... } },
     "goods_receipt": { "document_type": "goods_receipt", "fields": { ... } }
   }
   ```
5. `ap_invoice_review_from_ocr_result(run_id)` を呼ぶ
6. 判定結果を日本語で報告する（判定コード・理由・次アクション）
7. `write_performed=false` を必ず明示する

## 引数がフォルダパスの場合（実運用モード）

実行順序（省略・変更・確認不可）:

1. `ap_invoice_prepare_ocr_run(folder_path)` を呼ぶ → PDF画像が返る
2. 返ってきた画像を Claude OCR で全フィールド読み取る
3. `ap_invoice_submit_ocr_result(run_id, ocr_results)` を呼ぶ（上記と同じ形式）
4. `ap_invoice_review_from_ocr_result(run_id)` を呼ぶ
5. 判定結果を日本語で報告する
6. `write_performed=false` を必ず明示する

## 禁止事項

- ユーザーへの確認質問
- ファイル検索（Glob, Grep, Read）による case-a の探索
- レガシーツール（list_ap_demo_cases, review_ap_demo_case 等）の使用
- フォールバックや代替フロー
- ERP/SaaS への書き込みが行われたと示唆すること
```

### Step 2: Edit `scripts/package_ap_mcpb.py`

Find this block:

```python
INCLUDE_DIRS = [
    "ap_invoice_core",
    "ap_invoice_mcp",
    "workflow-packs",
    "samples",
    "docs",
    "enterprise-bundle/plugin/ap-invoice-review",
]
```

Replace with:

```python
INCLUDE_DIRS = [
    "ap_invoice_core",
    "ap_invoice_mcp",
    "workflow-packs",
    "samples",
    "docs",
    "enterprise-bundle/plugin/ap-invoice-review",
    "commands",
]
```

### Step 3: Commit, push, rebuild

```bash
cd C:\Users\Owner\Documents\mcpb-push
git add commands/ap-review.md scripts/package_ap_mcpb.py
git commit -m "feat: add /ap-review slash command for deterministic demo trigger"
git push
python scripts/package_ap_mcpb.py
```

Output will be: `dist\ap-invoice-review.mcpb`

### Step 4: Reinstall

Install `dist\ap-invoice-review.mcpb` via Claude Settings → 拡張機能 → 詳細設定 (drag & drop).

## Expected result

User types `/ap-review case-a` → deterministic execution, no false positives, no questions asked.
