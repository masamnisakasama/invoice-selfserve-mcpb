# AP Invoice Review — デモ手順書

**バージョン:** 1.0  
**更新日:** 2026-06-22

---

## インストール方法

ダウンロードしたユーザーは以下の2ステップが必要です:

**ステップ1: コネクタ（MCP）のインストール**
- `dist/ap-invoice-review.mcpb` を Claude Desktop にドラッグ&ドロップ

**ステップ2: スキル（スラッシュコマンド）のインストール**
- Cowork のチャットに `.skill` ファイルを添付 → 「Save skill」ボタンをクリック

インストール確認: Cowork で `/ap` と入力したとき `ap-review` がオートコンプリートに出れば成功。

> **TODO**: `.plugin` 形式に変換すれば1ステップになる（`dist/ap-invoice-review.plugin` が候補）

---

## 概要

Claude Desktop の Cowork モードで `/ap-review` スキルを使い、請求書・発注書・納品書の 3-way マッチングを自動実行するデモです。

処理フロー:

```
PDF取得 → Claude OCR（3帳票読み取り）→ 決定論的ルールエンジン → 判定・出力
```

---

## 前提条件

- Claude Desktop に AP Invoice Review MCP（Claude OCR版）がインストール・起動済み
- Cowork モードが起動していること
- `/ap` と入力したとき `ap-review` がオートコンプリートに表示されること

---

## パターンA: デモケース（最速確認）

新しい Cowork チャットで以下を入力するだけで動作します。

```
/ap-review case-a
```

自然言語でも起動できます:

```
case-b のレビューをお願いします
請求書 case-c を確認してください
```

### 全ケース一覧

| コマンド | 期待判定 | シナリオ |
|---------|---------|---------|
| `/ap-review case-a` | PAY_READY_CANDIDATE | 全チェック通過。¥110,000 |
| `/ap-review case-b` | REFER_PO_MISMATCH | 請求¥121,000 vs PO¥110,000（差額¥11,000超過） |
| `/ap-review case-c` | REFER_DUPLICATE_REVIEW | 同一請求書番号が過去履歴と一致（重複スコア100） |
| `/ap-review case-d` | REFER_VENDOR_REVIEW | 振込口座 9999-9999999 がマスタ 0001-1234567 と不一致 |
| `/ap-review case-e` | REFER_GRN_MISMATCH | 発注数100に対し検収数60（未納40個） |
| `/ap-review case-f` | REFER_TAX_REVIEW | JP10（10%）で小計¥100,000なら税¥10,000 → 請求は¥8,000 |

### 判定後の追加コマンド

| 入力例 | 動作 |
|--------|------|
| `Resolution Pack を出して` | 購買担当・取引先・承認者向けのアクションメッセージを生成 |
| `承認ブリーフを作って` | 承認者向けブリーフ（判定理由・リスク・ネクストアクション） |

---

## パターンB: 実フォルダのPDF照合

### ファイル命名規則（重要）

| 帳票種別 | 必要なファイル名 |
|---------|---------------|
| 請求書 | `invoice.pdf` |
| 発注書 | `purchase_order.pdf` |
| 納品書・検収記録 | `goods_receipt.pdf` |

### フォルダパス制限

セキュリティ制限により、以下のパス配下のみ読み取り可能です:

```
C:\Users\<username>\Documents\APInvoiceDemo\
```

### 手順

1. `APInvoiceDemo` 配下にサブフォルダを作成
2. 3つの PDF を上記の名前で配置
3. Cowork で依頼:

```
このフォルダのAPレビューをしてください:
C:\Users\<username>\Documents\APInvoiceDemo\<フォルダ名>
```

---

## ローカル出力ファイル

レビュー実行後、自動保存されます:

```
C:\Users\<username>\Documents\APInvoiceDemo\_runs\<run_id>\
  ocr_results\      -- Claude OCR 読み取り結果 (JSON)
  artifacts\
    canonical_facts.json   -- 正規化データ
    decision_result.json   -- 判定結果
    draft_payloads.json    -- freee / kintone / generic_ap ドラフト
```

ERP への実送信は行いません（`write_performed: false`）。

---

## 現バージョンの制限事項

| 制限 | 詳細 |
|------|------|
| インストール | 2ステップ（.mcpb + .skill）。.plugin 化で1ステップ可能（未対応） |
| フォルダパス | `APInvoiceDemo` 配下のみ |
| ファイル形式 | PDF のみ |
| 3帳票必須 | 請求書・発注書・納品書がすべて揃っていること |
| ERP書き込み | ドラフト生成のみ |
| ファイル名 | `invoice` / `purchase_order` / `goods_receipt` を含む名前が必要 |

---

## やるべきこと（TODO）

### 最優先

- [ ] `.plugin` 形式で配布して1ステップインストールを実現（`dist/ap-invoice-review.plugin` を検証）
- [ ] `ap_invoice_prepare_ocr_run` のフォルダパス制限を撤廃または拡張
- [ ] ファイル名によらずコンテンツベースでドキュメント種別を自動分類

### 機能面

- [ ] freee / kintone への実書き込み対応（現在はドラフトのみ）
- [ ] 複数セットの一括バッチ処理
- [ ] HTML → PDF 変換を MCP 内に組み込む

### デモ改善

- [ ] ビデオウォークスルーの録画
- [ ] 想定問答（FAQ）の拡充

---

## よくある質問

**Q: `/ap-review` と入力しても表示されない**  
A: .skill ファイルが未インストールです。スキルファイルを Cowork に添付して「Save skill」をクリックし、再起動してください。

**Q: フォルダが読めないエラーが出る**  
A: `Documents\APInvoiceDemo\` 配下にフォルダを移動してください。

**Q: DOCUMENT_CLASSIFICATION_REQUIRED エラーが出る**  
A: ファイル名を `invoice.pdf` / `purchase_order.pdf` / `goods_receipt.pdf` に変更してください。
