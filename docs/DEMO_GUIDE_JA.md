# AP Invoice Review MCPB デモ手順

この文書は、Claude Desktopで `ap-invoice-review.mcpb` を使ってデモを行う人向けの手順です。

## できること

- 請求書、発注書、納品書/検収書PDFをClaude OCRで読み取る
- MCPB側で3-way match、取引先確認、重複確認、税額確認を行う
- 支払候補、差戻し、確認依頼などの判断を日本語で返す
- 購買担当、取引先、承認者向けの次アクション文面を作る
- 外部SaaS/ERP/銀行への本書き込みは行わない

## 使うファイル

```text
dist/ap-invoice-review.mcpb
```

このファイルをClaude Desktopにインストールします。

## Claude Desktopにインストールする

1. Claude Desktopを開きます。
2. Settings / Extensions から `ap-invoice-review.mcpb` をインストールします。
3. 必要に応じてextensionを有効化します。
4. 新しいチャットを開きます。

Claude Desktopのバージョンによって、MCPBのインストール方法はdrag-and-drop、double-click、Settingsからのinstallなどで変わる場合があります。

## まず実行するプロンプト

新しいチャットで次を入力します。

```text
AP Invoice Review MCPBを使って、デモワークスペースを作成し、case-a-pay-readyをレビューしてください。PDFをOCRして、判定・根拠・次アクション・write_performed=falseを日本語で返してください。
```

期待される結果:

```text
PAY_READY_CANDIDATE
write_performed=false
```

`Documents/APInvoiceDemo` にデモPDFが展開されます。請求書、発注書、納品書/検収書はそれぞれ見た目が異なる帳票です。

## 他のデモケース

| 入力 | 期待される判定 | 見せたいポイント |
|---|---|---|
| `case-a-pay-ready` | `PAY_READY_CANDIDATE` | 3点照合が通り、支払候補になる |
| `case-b-po-mismatch` | `REFER_PO_MISMATCH` | PO金額と請求金額の差異 |
| `case-c-duplicate` | `REFER_DUPLICATE_REVIEW` | 過去請求との重複疑い |
| `case-d-vendor-review` | `REFER_VENDOR_REVIEW` | 取引先マスタ不一致 |
| `case-e-grn-mismatch` | `REFER_GRN_MISMATCH` | 検収数量不足 |
| `case-f-tax-review` | `REFER_TAX_REVIEW` | 税額計算不一致 |

例:

```text
AP Invoice Review MCPBを使って、case-b-po-mismatchをレビューしてください。PDFをOCRして、日本語で結果を返してください。
```

## slash commandについて

環境によっては次のslash commandが使えます。

```text
/ap-review case-a
```

ただし、Claude Desktop/Coworkのバージョンによってslash commandの表示や登録が異なることがあります。表示されない場合は、slash commandにこだわらず自然文で依頼してください。MCPツールの本線は自然文からでも動きます。

## 結果で必ず見ること

- 判定コードが出ている
- 根拠、適用ルール、次アクションが出ている
- `write_performed=false` が明示されている
- ClaudeがPDF画像をOCRしてから `ap_invoice_submit_ocr_result` を呼んでいる
- Airtable、Google Drive、外部connector registryに逃げていない
- JSON sidecarやPDFテキスト抽出に逃げていない

## うまく動かないとき

### MCPツールが見えない

- MCPBが有効化されているか確認します。
- Claude Desktopを再起動します。
- 新しいチャットを開き直します。

### `/ap-review` が見えない

自然文で依頼してください。

```text
AP Invoice Review MCPBを使って、case-a-pay-readyをレビューしてください。
```

### OCRがsubmitされない

以下のsmoke promptで確認します。

```text
AP Invoice OCR smoke testを実行して。返された画像をOCRして、submit toolにinvoice_numberとtotal_amountを渡してください。
```

Claude Desktopが画像を読めない、submit toolを呼ばない、画像外の答えがないと通らない場合は、MCPB側ではなくClaude Desktop実機側のGo/No-Go確認が必要です。

## デモで言ってよいこと

- 架空データのAP請求書レビューMCPBです。
- ClaudeがPDFをOCRし、MCPBが決定論的な業務ルールで判定します。
- 結果はdraft-onlyです。
- 外部システムへの本書き込みや支払実行は行いません。

## デモで言ってはいけないこと

- 実データで検証済み
- freee/kintone/ERPに登録済み
- 支払が実行された
- OCRなしで判定している
- JSON sidecarを読んで答えを出している
