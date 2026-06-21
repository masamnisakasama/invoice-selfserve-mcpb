# AP Invoice Review — 引き継ぎ文書 Session 3
作成日時: 2026-06-22

---

## 現在の状態（Session 3 終了時点）

### 動いているもの ✅
- Claude Desktop インストール済み（3回目のクリーンインストール後）
- `dist/ap-invoice-review.mcpb` がインストール済み
- MCP ツール群は正常ロード・動作確認済み（Cowork の deferred tools に出現）
  - `mcp__AP_Invoice_Review___Claude_OCR__ap_invoice_review_demo_case`
  - `mcp__AP_Invoice_Review___Claude_OCR__ap_invoice_submit_ocr_result`
  - `mcp__AP_Invoice_Review___Claude_OCR__ap_invoice_review_from_ocr_result`
  - その他多数

### 動いていないもの ❌
- `/ap-review` スラッシュコマンド → 「不明なスキル: ap-review」エラー
- Claude Desktop の拡張機能 UI からのアンインストール（できない）

---

## 失敗の歴史と確認済み事実（150回超の試行から）

### `.mcpb` ファイル自体は正常
```
dist/ap-invoice-review.mcpb 内を確認済み:
- skills/ap-review/SKILL.md ✅ 存在
- BOM なし ✅
- フォーマット正常（name: ap-review, description あり）✅
- ソース: workflow-packs/ap-invoice-v1/SKILL.md がビルド時にコピーされる
```

### ビルドスクリプトの挙動
`scripts/package_ap_mcpb.py` の重要な動作:
```python
def add_claude_plugin_aliases(zf):
    zf.write(PROJECT_ROOT / ".claude-plugin" / "plugin.json", ".claude-plugin/plugin.json")
    zf.write(
        PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "SKILL.md",
        "skills/ap-review/SKILL.md",  # ← これが zip 内のスキル
    )
```
- `skills/ap-review/` ディレクトリ自体は `INCLUDE_DIRS` に含まれない
- スキルのソースは必ず `workflow-packs/ap-invoice-v1/SKILL.md`
- `ensure_samples()` がサンドボックス内で PermissionError → サンプル再生成不要なら回避可能

### Cowork のスキルロードパス（重要）
Cowork が読むスキルディレクトリ:
```
C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\
  skills-plugin\
    afff51a2-02f1-4d86-9b98-80ea8c6239c4\
      3e207fec-46d2-45b8-8521-d965b9b4fbb9\
        skills\
          docx\SKILL.md
          pdf\SKILL.md
          pptx\SKILL.md
          （ここに ap-review\ が存在しない）
```

プラグイン由来のスキルは別パス:
```
C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\
  3e207fec-46d2-45b8-8521-d965b9b4fbb9\
    afff51a2-02f1-4d86-9b98-80ea8c6239c4\
      rpm\
        plugin_0155zZVATbJU3jHUmPP9NvMC\  ← cowork-plugin-management がここにある
          skills\
            cowork-plugin-customizer\
            create-cowork-plugin\
```

**結論: `.mcpb` をインストールしても ap-review スキルが上記どちらのパスにも展開されていないと推測される。MCP ツールは別経路で動く。**

### BOM 問題（過去に何十回も詰まった原因）
- `extensions-installations.json` を PowerShell の `Set-Content` で書くと UTF-8 BOM が付く
- BOM が付くと Claude Desktop が JSON parse に失敗して起動不能になる
- **必ず `WriteAllBytes` + ASCII 固定で書くこと**
- 正しいコマンド（核オプション）は下記参照

### アンインストール問題
- Claude Desktop の Settings → 拡張機能 UI から `.mcpb` を削除できない（ボタンが効かない or メニューなし）
- 核オプション（PowerShell）でリセットする必要がある
- 核オプション実行後に Claude Desktop が壊れる問題が発生している

---

## 核オプション（慎重に使うこと）

```powershell
Get-Process | Where-Object {$_.Name -like "*claude*"} | Stop-Process -Force
Start-Sleep 2
Get-ChildItem "C:\Users\Owner\AppData" -Recurse -Directory -EA 0 | Where-Object {$_.Name -like "*ap-invoice*" -or $_.Name -like "*masamnisakasama*"} | ForEach-Object {cmd /c rmdir /s /q """$($_.FullName)"""}
$bytes = [System.Text.Encoding]::ASCII.GetBytes('{"local.mcpb.masamnisakasama":{}}')
[System.IO.File]::WriteAllBytes("C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\extensions-installations.json", $bytes)
```

**注意**:
- `Set-Content` は絶対に使わない（BOM が付く）
- `WriteAllBytes` + ASCII のみ
- 実行後に Claude Desktop が壊れた場合は完全アンインストール → 再インストール

---

## OCR フォーマット（Session 3 で確認）

`ap_invoice_submit_ocr_result` に渡す形式（**フラット形式は NG、必ず fields キーで包む**）:

```json
{
  "invoice": {
    "document_type": "invoice",
    "fields": {
      "invoice_number": "INV-2026-0008",
      "invoice_date": "2026-07-15",
      "due_date": "2026-08-14",
      "vendor_name": "Tokyo Office Supply Co",
      "vendor_id": "V-1001",
      "bank_account": "0001-1234567",
      "po_number": "PO-2026-0001",
      "currency": "JPY",
      "tax_code": "JP10",
      "cost_center": "CC-ADMIN",
      "subtotal_amount": 100000,
      "tax_amount": 10000,
      "total_amount": 110000,
      "line_items": [
        {"description": "Office supplies bundle", "quantity": 100, "unit_price": 1000, "amount": 100000}
      ]
    }
  },
  "purchase_order": {
    "document_type": "purchase_order",
    "fields": {
      "po_number": "PO-2026-0001",
      "vendor_id": "V-1001",
      "currency": "JPY",
      "approved": true,
      "remaining_balance": 110000,
      "total_amount": 110000,
      "line_items": [
        {"description": "Office supplies bundle", "quantity": 100, "unit_price": 1000, "amount": 100000}
      ]
    }
  },
  "goods_receipt": {
    "document_type": "goods_receipt",
    "fields": {
      "receipt_number": "GRN-2026-0001",
      "po_number": "PO-2026-0001",
      "received": true,
      "received_quantity": 100,
      "receipt_date": "2026-06-18"
    }
  }
}
```

---

## デモ実行フロー（スラッシュコマンドなしで動く）

`/ap-review` が動かなくても、Cowork から以下の順で MCP ツールを直接呼べば同じ結果が得られる。

```
1. ap_invoice_setup_demo_workspace()  ← 必要に応じて
2. ap_invoice_review_demo_case(case_id="case-a-pay-ready")
   → invoice.pdf / purchase_order.pdf / goods_receipt.pdf の画像が返る
3. Claude が画像を OCR で読み取る
4. ap_invoice_submit_ocr_result(run_id, ocr_results)  ← 上記フォーマットで
5. ap_invoice_review_from_ocr_result(run_id)
   → 判定結果（PAY_READY_CANDIDATE 等）
```

case_id マッピング:
| ユーザー入力 | case_id |
|---|---|
| case-a | case-a-pay-ready |
| case-b | case-b-po-mismatch |
| case-c | case-c-duplicate |
| case-d | case-d-vendor-review |
| case-e | case-e-grn-mismatch |
| case-f | case-f-tax-review |

---

## Codex への調査依頼

### 本質的な問題
`.mcpb` をインストールしても `skills/ap-review/SKILL.md` が Cowork のスキルシステムに認識されない。MCP ツールは動くのにスキルが動かない。

### 調査してほしいこと

1. **`.mcpb` インストール時に Claude Desktop はスキルをどこに展開するか？**
   - 展開先パスを特定する
   - `C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\` 以下を調べる

2. **Cowork はどのパスからスキルを読むか？**
   - 上記「Cowork のスキルロードパス」を参照
   - `skills-plugin\` と `rpm\plugin_XXXX\` の 2 パターンがある

3. **`.mcpb` のスキルが上記パスに展開されていない場合の原因**
   - `manifest.json` の設定に問題があるか
   - `.mcpb` の zip 構造に問題があるか（`skills/ap-review/SKILL.md` は存在している）
   - Claude Desktop のバージョン依存の問題か

4. **修正方法の候補**
   - `manifest.json` に skills の明示的な宣言が必要か
   - zip 内のディレクトリ構造を変える必要があるか
   - 別の形式（`.plugin`）にする必要があるか（ただし `.plugin` はローカル stdio サーバー不可の問題あり）

### 参考ファイル
```
C:\Users\Owner\Documents\mcpb-push\
  manifest.json                              ← プラグイン定義
  .claude-plugin\plugin.json                 ← Claude Plugin 定義
  workflow-packs\ap-invoice-v1\SKILL.md      ← スキルのソース
  dist\ap-invoice-review.mcpb               ← インストール済みバイナリ
  scripts\package_ap_mcpb.py                ← ビルドスクリプト
```

---

## リポジトリ

- ローカル: `C:\Users\Owner\Documents\mcpb-push`
- GitHub: https://github.com/masamnisakasama/invoice-selfserve-mcpb
- ブランチ: main
- 最終コミット: `feat: add /ap-review slash command for deterministic demo trigger`

---

## Session 3 でやったこと（無駄だったもの含む）

1. `ap_invoice_review_demo_case` を直接呼んだ → 動いた（PDF 3 枚の画像が返った）✅
2. `ap_invoice_submit_ocr_result` にフラット形式で送った → バリデーション失敗 ❌
3. `skills/ap-review/SKILL.md` を新規作成した → ビルドに使われないので無意味 ❌
4. `dist/ap-invoice-review-fixed.mcpb` をビルドした → 元と同じ内容なので意味なし ❌
5. 元の `.mcpb` の中身を確認 → SKILL.md は最初から正常に入っていた ✅
6. BOM チェック → 問題なし ✅

---

## 次のセッションへのお願い

1. **まず Codex に上記「Codex への調査依頼」を渡す**（スキルが展開されない根本原因を突き止める）
2. スラッシュコマンドなしでデモを動かしたい場合は、Cowork セッションで「case-a のデモを実行して」と言えば私（Claude）が MCP ツールを直接呼んで動かせる
3. Claude Desktop の再インストールは**根本解決にならない**のでしない
4. 核オプションは最終手段。使う場合は必ず `WriteAllBytes` + ASCII で `extensions-installations.json` を書くこと
