# AP Invoice Review — 開発知見まとめ

**日付:** 2026-06-22  
**セッション概要:** Claude Desktop Cowork で `/ap-review` スキルを動かすまでの試行記録

---

## うまくいったこと

### スキルのインストール方法

`.skill` ファイル（zip）を Cowork の「Save skill」ボタンで保存する方式が正常動作。

- `ap-review/SKILL.md` を zip 圧縮し、拡張子を `.skill` に変更
- Cowork チャットで `present_files` ツールでファイルを表示 → ユーザーが「Save skill」をクリック
- クリック後、`/ap` と入力すると `ap-review` がオートコンプリートに出るようになった

### SKILL.md の要件

```yaml
---
name: ap-review
description: "..."  # 200文字以内（超えるとトリガーされない）
---
```

- `name` と `description` のフロントマター必須
- 説明文に日本語トリガーワード（`レビュー`、`請求書`）と英語コマンド（`case-a` 〜 `case-f`、`/ap-review`）を両方含めると認識精度が上がる

### OCR 提出フォーマット

`ap_invoice_submit_ocr_result` に渡す `ocr_results` の正しい形式:

```json
{
  "invoice": {
    "document_type": "invoice",
    "fields": { ... }
  },
  "purchase_order": {
    "document_type": "purchase_order",
    "fields": { ... }
  },
  "goods_receipt": {
    "document_type": "goods_receipt",
    "fields": { ... }
  }
}
```

`fields` キーが必須（省略するとバリデーション失敗）。

### line_items の許可フィールド

`line_items` 配列の各要素に使えるフィールドは以下のみ:

- `description`
- `quantity`
- `unit_price`
- `amount`

`item_code` や `tax_rate` を入れると `Extra inputs are not permitted`（pydantic エラー）になる。

### HTML → PDF 変換

weasyprint（Python）で日本語 HTML を PDF に変換できる:

```bash
pip install weasyprint --break-system-packages
weasyprint input.html output.pdf
```

`box-shadow` は警告が出るが無視でよい。Noto CJK フォントがあれば日本語も正常に出力される。

---

## 失敗したこと

### `.mcpb` ドラッグ&ドロップではスキルがインストールされない

- `.mcpb` はコネクタ（MCP サーバー）のみインストールする
- `.mcpb` 内に `skills/ap-review/SKILL.md` が入っていても、スキルとしては登録されない
- スキルは別途 `.skill` ファイルで配布する必要がある
- 解決策: `.plugin` 形式（コネクタ + スキルのバンドル）に移行する

### PowerShell の `Set-Content` で BOM が付く

`Set-Content` はデフォルトで UTF-8 BOM を付与するため、JSON ファイルが壊れる。

正しい書き方（PowerShell 6+）:

```powershell
Set-Content -Path $path -Value $content -Encoding utf8NoBOM
```

または:

```powershell
[System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)
```

### bash サンドボックスからの Windows パスへのアクセス

- `Read/Write/Edit` ツールは Windows パス（`C:\...`）を使う
- bash は `/sessions/.../mnt/...` のマウントパスを使う
- マウントされていないフォルダ（`APInvoiceDemo` 等）は bash から読み書き不可
- `outputs` フォルダは bash で `/sessions/.../mnt/outputs/` でアクセスできる

### `ap_invoice_prepare_ocr_run` のフォルダ制限

以下のパス以外はエラーになる:

```
C:\Users\<username>\Documents\APInvoiceDemo\
C:\Users\<username>\Documents\mcpb-push\samples\
C:\Users\<username>\Documents\mcpb-push\workflow-packs\
```

`Downloads` や任意フォルダには非対応（セキュリティ制限）。

### ファイル名でのドキュメント分類

`purchase_order_sample.pdf` や `delivery_note_sample.pdf` は MCP に認識されない。  
`invoice` / `purchase_order` / `goods_receipt` という文字列をファイル名に含める必要がある。

### `git init` を誤ったディレクトリで実行

`C:\Users\Owner\Documents` 直下で誤って `git init` してしまった。  
以下で削除:

```powershell
Remove-Item -Recurse -Force "C:\Users\Owner\Documents\.git"
```

実際のリポジトリは `C:\Users\Owner\Documents\mcpb-push` にあり、すでに `origin` が設定済みだった。

---

## アーキテクチャ理解

### `.mcpb` vs `.skill` vs `.plugin`

| 形式 | 内容 | インストール方法 | インストールされるもの |
|------|------|--------------|------------------|
| `.mcpb` | MCP サーバー + manifest.json | ドラッグ&ドロップ | コネクタのみ |
| `.skill` | スキルディレクトリの zip | Save skill ボタン | スキル（スラッシュコマンド）のみ |
| `.plugin` | コネクタ + スキルのバンドル | プラグインマーケット / ドラッグ&ドロップ | 両方 |

スキルとコネクタを一緒に配布するには `.plugin` 形式が必要。  
現在 `dist/ap-invoice-review.plugin` が存在するが、インストール方法は未検証。

### OCR フロー（Pattern A: デモケース）

```
ap_invoice_setup_demo_workspace(overwrite=true)
→ ap_invoice_review_demo_case(case_id)         # 3枚の画像が返る
→ [Claude が画像を OCR してフィールドを抽出]
→ ap_invoice_submit_ocr_result(run_id, ocr_results)
→ ap_invoice_review_from_ocr_result(run_id)    # 判定結果
```

### OCR フロー（Pattern B: 実フォルダ）

```
ap_invoice_prepare_ocr_run(folder_path)         # 3枚の画像が返る
→ [Claude が画像を OCR してフィールドを抽出]
→ ap_invoice_submit_ocr_result(run_id, ocr_results)
→ ap_invoice_review_from_ocr_result(run_id)    # 判定結果
```

---

## デモ実行結果（2026-06-22）

| ケース | 請求書番号 | 判定 |
|--------|-----------|------|
| case-a | INV-2026-0001 | PAY_READY_CANDIDATE |
| case-b | INV-2026-0003 | REFER_PO_MISMATCH（差額¥11,000） |
| case-c | INV-2026-0007 | REFER_DUPLICATE_REVIEW（重複スコア100） |
| case-d | INV-2026-0009 | REFER_VENDOR_REVIEW（口座不一致） |
| case-e | INV-2026-0010 | REFER_GRN_MISMATCH（検収数60/100） |
| case-f | INV-2026-0012 | REFER_TAX_REVIEW（税額¥8,000 vs 期待¥10,000） |

全6ケース完走、判定すべて期待通り。
