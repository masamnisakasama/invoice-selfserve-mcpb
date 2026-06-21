from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_SAMPLES = PROJECT_ROOT / "samples"
PACK_SAMPLES = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "samples"
PACK_TESTS = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "tests"
PDF_METADATA_DATE = "D:20260101000000Z"
PAGE_SIZE = (1240, 1754)
INK = "#1F2933"
MUTED = "#52616B"
RULE = "#B7C4CF"
RULE_DARK = "#6B7C8F"
PAPER = "#FBFAF6"
PALE_BLUE = "#EAF3FA"
PALE_GRAY = "#F3F5F7"
STAMP_RED = "#B0443E"

BUYER_NAME = "株式会社サンプル商事"
BUYER_DEPT = "管理本部 総務部"
BUYER_ADDRESS = "〒100-0005 東京都千代田区丸の内1-1-1"
VENDOR_JA = "株式会社東京オフィスサプライ"
VENDOR_ADDRESS = "東京都千代田区神田神保町2-12"
VENDOR_TEL = "TEL 03-1234-5678"
REGISTRATION_NO = "T1234567890123"


def line_item(amount: int = 100000, quantity: int = 100) -> dict[str, Any]:
    return {
        "description": "Office supplies bundle",
        "quantity": quantity,
        "unit_price": amount / quantity,
        "amount": amount,
        "tax_code": "JP10",
    }


def invoice_fields(
    *,
    invoice_number: str,
    po_number: str,
    total_amount: int,
    bank_account: str = "0001-1234567",
    vendor_id: str = "V-1001",
    invoice_date: str = "2026-06-20",
    quantity: int = 100,
    subtotal_amount: int | None = None,
    tax_amount: int | None = None,
) -> dict[str, Any]:
    subtotal = subtotal_amount if subtotal_amount is not None else round(total_amount / 1.1)
    tax = tax_amount if tax_amount is not None else total_amount - subtotal
    due_date = (date.fromisoformat(invoice_date) + timedelta(days=30)).isoformat()
    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "vendor_name": "Tokyo Office Supply Co.",
        "vendor_id": vendor_id,
        "po_number": po_number,
        "currency": "JPY",
        "subtotal_amount": subtotal,
        "tax_amount": tax,
        "total_amount": total_amount,
        "bank_account": bank_account,
        "tax_code": "JP10",
        "cost_center": "CC-ADMIN",
        "line_items": [line_item(subtotal, quantity)],
    }


def po_fields(*, po_number: str, total_amount: int = 110000) -> dict[str, Any]:
    subtotal = round(total_amount / 1.1)
    return {
        "po_number": po_number,
        "vendor_id": "V-1001",
        "currency": "JPY",
        "total_amount": total_amount,
        "approved": True,
        "remaining_balance": total_amount,
        "line_items": [line_item(subtotal, 100)],
    }


def grn_fields(*, receipt_number: str, po_number: str, quantity: int = 100) -> dict[str, Any]:
    return {
        "receipt_number": receipt_number,
        "po_number": po_number,
        "received": True,
        "received_quantity": quantity,
        "receipt_date": "2026-06-18",
    }


def write_document_pdf(path: Path, *, document_type: str, fields: dict[str, Any]) -> None:
    image = Image.new("RGB", PAGE_SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    _draw_page_frame(draw)
    if document_type == "invoice":
        _draw_invoice(draw, fields)
    elif document_type == "purchase_order":
        _draw_purchase_order(draw, fields)
    else:
        _draw_goods_receipt(draw, fields)
    _draw_ocr_metadata(draw, document_type, fields)
    buffer = BytesIO()
    image.save(
        buffer,
        format="PDF",
        resolution=150.0,
        creationDate=PDF_METADATA_DATE,
        modDate=PDF_METADATA_DATE,
    )
    path.write_bytes(buffer.getvalue())


def _draw_invoice(draw: ImageDraw.ImageDraw, fields: dict[str, Any]) -> None:
    item = fields["line_items"][0]
    _title(draw, "請 求 書", "INVOICE")
    _right_info_box(
        draw,
        805,
        138,
        [
            ("請求書番号", fields["invoice_number"]),
            ("発行日", _jp_date(fields["invoice_date"])),
            ("支払期日", _jp_date(fields["due_date"])),
            ("取引先ID", fields["vendor_id"]),
        ],
    )
    _text(draw, 92, 174, f"{BUYER_NAME}", _font(34, bold=True))
    _text(draw, 92, 222, f"{BUYER_DEPT} 御中", _font(28))
    _text(draw, 92, 268, BUYER_ADDRESS, _font(21), MUTED)

    _section_label(draw, 92, 342, "ご請求金額")
    draw.rounded_rectangle((92, 386, 690, 476), radius=4, fill=PALE_BLUE, outline=RULE_DARK, width=2)
    _text(draw, 120, 414, _yen(fields["total_amount"]), _font(46, bold=True), INK)
    _text(draw, 430, 432, "(税込)", _font(24), MUTED)

    _vendor_block(draw, 760, 312, include_bank=False)

    headers = ["品番", "品名", "数量", "単価", "税区分", "金額"]
    rows = [
        [
            "OS-100",
            "A4コピー用紙・事務用品一式",
            _format_number(item["quantity"]),
            _yen(item["unit_price"]),
            "10%",
            _yen(item["amount"]),
        ]
    ]
    _table(draw, 92, 560, [110, 455, 120, 150, 120, 180], headers, rows, row_height=72)
    _summary_box(
        draw,
        760,
        760,
        [
            ("小計", _yen(fields["subtotal_amount"])),
            ("消費税（10%）", _yen(fields["tax_amount"])),
            ("合計", _yen(fields["total_amount"])),
        ],
    )
    _info_panel(
        draw,
        92,
        840,
        610,
        210,
        "振込先",
        [
            ("銀行", "東京銀行 神田支店"),
            ("口座", f"普通 {fields['bank_account']}"),
            ("名義", "カ）トウキョウオフィスサプライ"),
        ],
    )
    _info_panel(
        draw,
        92,
        1100,
        1045,
        180,
        "備考",
        [
            ("発注番号", fields["po_number"]),
            ("部門", fields["cost_center"]),
            ("お願い", "期日までに上記口座へお振込みください。"),
        ],
    )


def _draw_purchase_order(draw: ImageDraw.ImageDraw, fields: dict[str, Any]) -> None:
    item = fields["line_items"][0]
    _po_header(draw, fields)
    _text(draw, 128, 222, f"{VENDOR_JA} 御中", _font(34, bold=True))
    _text(draw, 128, 276, "下記の通り発注いたします。納期・納入場所をご確認ください。", _font(22), MUTED)
    _info_panel(
        draw,
        128,
        362,
        530,
        214,
        "発注者",
        [
            ("会社名", BUYER_NAME),
            ("部署", BUYER_DEPT),
            ("担当", "佐藤 一郎"),
            ("住所", "東京都千代田区丸の内1-1-1"),
        ],
    )
    _po_approval_grid(draw, 720, 340)
    _section_label(draw, 128, 650, "発注金額")
    draw.rounded_rectangle((128, 694, 660, 774), radius=0, fill="#EEF7F1", outline="#6FA47B", width=3)
    _text(draw, 158, 720, _yen(fields["total_amount"]), _font(42, bold=True), INK)
    _text(draw, 430, 735, "(税込)", _font(23), MUTED)
    _text(draw, 735, 718, f"発注残高  {_yen(fields['remaining_balance'])}", _font(26, bold=True), "#24543A")

    headers = ["明細番号", "品名・仕様", "数量", "単価", "税区分", "発注金額"]
    rows = [
        [
            "1",
            "A4コピー用紙 / 事務用品一式",
            _format_number(item["quantity"]),
            _yen(item["unit_price"]),
            "10%",
            _yen(item["amount"]),
        ]
    ]
    _table(draw, 128, 850, [120, 440, 110, 145, 110, 190], headers, rows, row_height=72)
    _summary_box(draw, 760, 1050, [("発注合計", _yen(fields["total_amount"]))])
    _info_panel(
        draw,
        128,
        1136,
        985,
        214,
        "納入条件",
        [
            ("納入場所", f"{BUYER_NAME} 丸の内オフィス"),
            ("支払条件", "月末締め翌月末払い"),
            ("備考", "納品時に納品書を同封してください。"),
        ],
    )


def _draw_goods_receipt(draw: ImageDraw.ImageDraw, fields: dict[str, Any]) -> None:
    _receipt_header(draw, fields)
    _text(draw, 92, 250, f"納入先  {BUYER_NAME} / {BUYER_DEPT}", _font(24, bold=True))
    _text(draw, 92, 296, "現品確認・数量確認・外観確認の記録です。請求照合時の証跡として保管します。", _font(20), MUTED)
    _vendor_block(draw, 92, 366, include_bank=False, title="納入業者")
    _inspection_boxes(draw, 720, 360)

    headers = ["確認項目", "内容", "結果", "確認者"]
    rows = [
        ["数量", f"発注数 100 / 納品数 {_format_number(fields['received_quantity'])}", "OK" if fields["received_quantity"] == 100 else "要確認", "山田"],
        ["外観", "外装破損なし、汚損なし", "OK", "山田"],
        ["書類", f"発注番号 {fields['po_number']} と照合", "OK", "山田"],
    ]
    _check_table(draw, 92, 630, [150, 570, 160, 160], headers, rows)
    _info_panel(
        draw,
        92,
        940,
        1045,
        210,
        "検収記録",
        [
            ("受領確認", "はい" if fields["received"] else "いいえ"),
            ("受領数量", _format_number(fields["received_quantity"])),
            ("確認者", "山田 花子"),
            ("備考", "外装破損なし。数量を確認済み。"),
        ],
    )
    _info_panel(
        draw,
        92,
        1194,
        1045,
        146,
        "照合情報",
        [
            ("関連発注番号", fields["po_number"]),
            ("請求照合", "請求書・注文書・納品書の3点照合対象"),
        ],
    )


def _draw_page_frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((42, 42, 1198, 1712), fill=PAPER, outline=RULE_DARK, width=3)
    draw.rectangle((58, 58, 1182, 1696), outline="#D6DEE6", width=1)
    for x in range(92, 1150, 70):
        draw.point((x, 80), fill="#E7ECEF")
        draw.point((x, 1670), fill="#E7ECEF")


def _po_header(draw: ImageDraw.ImageDraw, fields: dict[str, Any]) -> None:
    draw.rectangle((42, 42, 1198, 170), fill="#2F6F4E")
    draw.rectangle((72, 72, 188, 142), outline="white", width=2)
    _center_text(draw, 72, 90, 116, "発注", _font(28, bold=True), "white")
    _text(draw, 226, 74, "注 文 書", _font(54, bold=True), "white")
    _text(draw, 230, 134, "PURCHASE ORDER", _font(18), "#DDEFE4")
    _right_info_box(
        draw,
        820,
        202,
        [
            ("注文番号", fields["po_number"]),
            ("発行日", "2026年6月10日"),
            ("納入期限", "2026年6月18日"),
            ("承認状態", "承認済" if fields["approved"] else "未承認"),
        ],
        width=300,
    )


def _po_approval_grid(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    cols = ["申請", "部門長", "経理", "承認"]
    width = 100
    height = 116
    for index, label in enumerate(cols):
        xx = x + width * index
        draw.rectangle((xx, y, xx + width, y + height), fill="white", outline="#6FA47B", width=2)
        draw.rectangle((xx, y, xx + width, y + 34), fill="#EEF7F1")
        _center_text(draw, xx, y + 8, width, label, _font(16, bold=True), "#24543A")
        if label == "承認":
            _approval_stamp(draw, xx + 16, y + 42, "承認")


def _receipt_header(draw: ImageDraw.ImageDraw, fields: dict[str, Any]) -> None:
    draw.rectangle((42, 42, 1198, 196), fill="#F4F1EA", outline="#8A6A3E", width=2)
    _text(draw, 92, 76, "納品書 兼 検収記録", _font(48, bold=True), "#3A3024")
    _text(draw, 96, 134, "GOODS RECEIPT / INSPECTION REPORT", _font(17), "#7C6B56")
    _right_info_box(
        draw,
        805,
        72,
        [
            ("検収番号", fields["receipt_number"]),
            ("発注番号", fields["po_number"]),
            ("検収日", _jp_date(fields["receipt_date"])),
        ],
        width=330,
    )


def _inspection_boxes(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rounded_rectangle((x, y, x + 392, y + 178), radius=3, fill="white", outline="#8A6A3E", width=2)
    _text(draw, x + 16, y + 12, "検収チェック", _font(21, bold=True), "#3A3024")
    checks = [("数量", True), ("外観", True), ("書類", True), ("保留", False)]
    for index, (label, checked) in enumerate(checks):
        yy = y + 58 + index * 28
        draw.rectangle((x + 22, yy, x + 44, yy + 22), outline="#8A6A3E", width=2)
        if checked:
            draw.line((x + 25, yy + 10, x + 32, yy + 18), fill="#2F6F4E", width=3)
            draw.line((x + 32, yy + 18, x + 43, yy + 4), fill="#2F6F4E", width=3)
        _text(draw, x + 58, yy - 2, label, _font(18), INK)
    _approval_stamp(draw, x + 260, y + 58, "検収")


def _title(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    title_font = _font(56, bold=True)
    w = _text_width(draw, title, title_font)
    _text(draw, (1240 - w) // 2, 82, title, title_font, INK)
    sub_font = _font(18)
    sw = _text_width(draw, subtitle, sub_font)
    _text(draw, (1240 - sw) // 2, 148, subtitle, sub_font, MUTED)
    draw.line((430, 132, 810, 132), fill=RULE_DARK, width=2)


def _right_info_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    rows: list[tuple[str, Any]],
    width: int = 330,
) -> None:
    row_h = 46
    draw.rounded_rectangle((x, y, x + width, y + row_h * len(rows)), radius=3, fill="white", outline=RULE_DARK, width=2)
    for index, (label, value) in enumerate(rows):
        yy = y + index * row_h
        if index:
            draw.line((x, yy, x + width, yy), fill=RULE, width=1)
        draw.rectangle((x, yy, x + 116, yy + row_h), fill=PALE_GRAY)
        _text(draw, x + 12, yy + 12, str(label), _font(18, bold=True), MUTED)
        _text(draw, x + 128, yy + 11, str(value), _font(20), INK)


def _vendor_block(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    *,
    include_bank: bool,
    title: str = "請求者",
) -> None:
    rows = [
        ("会社名", VENDOR_JA),
        ("登録番号", REGISTRATION_NO),
        ("住所", VENDOR_ADDRESS),
        ("電話", VENDOR_TEL),
    ]
    if include_bank:
        rows.append(("振込先", "東京銀行 神田支店 普通 0001-1234567"))
    _info_panel(draw, x, y, 378, 220 if include_bank else 190, title, rows)
    stamp_x = x + 430 if x < 500 else x + 292
    _draw_stamp(draw, stamp_x, y + 70)


def _info_panel(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    rows: list[tuple[str, Any]],
) -> None:
    draw.rounded_rectangle((x, y, x + width, y + height), radius=3, fill="white", outline=RULE, width=2)
    draw.rectangle((x, y, x + width, y + 38), fill=PALE_GRAY)
    _text(draw, x + 14, y + 9, title, _font(20, bold=True), INK)
    yy = y + 54
    for label, value in rows:
        _text(draw, x + 18, yy, str(label), _font(17, bold=True), MUTED)
        _text(draw, x + 112, yy, str(value), _font(18), INK)
        yy += 34


def _section_label(draw: ImageDraw.ImageDraw, x: int, y: int, label: str) -> None:
    draw.rectangle((x, y, x + 12, y + 34), fill=RULE_DARK)
    _text(draw, x + 24, y + 1, label, _font(27, bold=True), INK)


def _table(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    widths: list[int],
    headers: list[str],
    rows: list[list[Any]],
    *,
    row_height: int,
) -> None:
    header_h = 46
    total_w = sum(widths)
    draw.rectangle((x, y, x + total_w, y + header_h + row_height * len(rows)), fill="white", outline=RULE_DARK, width=2)
    draw.rectangle((x, y, x + total_w, y + header_h), fill=PALE_BLUE)
    cx = x
    for width, header in zip(widths, headers):
        draw.line((cx, y, cx, y + header_h + row_height * len(rows)), fill=RULE, width=1)
        _center_text(draw, cx, y + 13, width, header, _font(18, bold=True), INK)
        cx += width
    draw.line((x + total_w, y, x + total_w, y + header_h + row_height * len(rows)), fill=RULE, width=1)
    draw.line((x, y + header_h, x + total_w, y + header_h), fill=RULE_DARK, width=2)
    for row_index, row in enumerate(rows):
        yy = y + header_h + row_height * row_index
        if row_index:
            draw.line((x, yy, x + total_w, yy), fill=RULE, width=1)
        cx = x
        for col_index, (width, value) in enumerate(zip(widths, row)):
            align_right = col_index in {2, 3, 5}
            text = str(value)
            if align_right:
                _right_text(draw, cx + width - 16, yy + 24, text, _font(20), INK)
            else:
                _text(draw, cx + 14, yy + 24, text, _font(20), INK)
            cx += width


def _check_table(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    widths: list[int],
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    header_h = 44
    row_h = 70
    total_w = sum(widths)
    total_h = header_h + row_h * len(rows)
    draw.rectangle((x, y, x + total_w, y + total_h), fill="white", outline="#8A6A3E", width=2)
    draw.rectangle((x, y, x + total_w, y + header_h), fill="#F4F1EA")
    cx = x
    for width, header in zip(widths, headers):
        draw.line((cx, y, cx, y + total_h), fill="#C9BAA4", width=1)
        _center_text(draw, cx, y + 12, width, header, _font(18, bold=True), "#3A3024")
        cx += width
    draw.line((x + total_w, y, x + total_w, y + total_h), fill="#C9BAA4", width=1)
    for row_index, row in enumerate(rows):
        yy = y + header_h + row_h * row_index
        draw.line((x, yy, x + total_w, yy), fill="#C9BAA4", width=1)
        cx = x
        for col_index, (width, value) in enumerate(zip(widths, row)):
            font = _font(20, bold=col_index == 2)
            fill = "#A33A2F" if value == "要確認" else INK
            if col_index in {2, 3}:
                _center_text(draw, cx, yy + 24, width, str(value), font, fill)
            else:
                _text(draw, cx + 14, yy + 24, str(value), font, fill)
            cx += width


def _summary_box(draw: ImageDraw.ImageDraw, x: int, y: int, rows: list[tuple[str, str]]) -> None:
    row_h = 48
    width = 378
    draw.rectangle((x, y, x + width, y + row_h * len(rows)), fill="white", outline=RULE_DARK, width=2)
    for index, (label, value) in enumerate(rows):
        yy = y + index * row_h
        if index:
            draw.line((x, yy, x + width, yy), fill=RULE, width=1)
        fill = PALE_BLUE if index == len(rows) - 1 else "white"
        draw.rectangle((x, yy, x + 170, yy + row_h), fill=fill)
        _text(draw, x + 18, yy + 13, label, _font(20, bold=index == len(rows) - 1), INK)
        _right_text(draw, x + width - 18, yy + 13, value, _font(21, bold=index == len(rows) - 1), INK)


def _draw_stamp(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x, y, x + 94, y + 94), outline=STAMP_RED, width=4)
    draw.line((x + 12, y + 47, x + 82, y + 47), fill=STAMP_RED, width=2)
    _center_text(draw, x, y + 18, 94, "東京", _font(20, bold=True), STAMP_RED)
    _center_text(draw, x, y + 52, 94, "之印", _font(20, bold=True), STAMP_RED)


def _approval_stamp(draw: ImageDraw.ImageDraw, x: int, y: int, label: str) -> None:
    draw.rectangle((x, y, x + 112, y + 112), outline=STAMP_RED, width=4)
    _center_text(draw, x, y + 20, 112, label, _font(24, bold=True), STAMP_RED)
    _center_text(draw, x, y + 58, 112, "済", _font(30, bold=True), STAMP_RED)


def _draw_ocr_metadata(draw: ImageDraw.ImageDraw, document_type: str, fields: dict[str, Any]) -> None:
    # Keep compact English labels for deterministic OCR demos while the visible form stays Japanese.
    rows = _display_rows(document_type, fields)
    text = " / ".join(f"{label}: {value}" for label, value in rows if label != "Line Items")
    _text(draw, 92, 1516, "OCR reference line (demo):", _font(17, bold=True), MUTED)
    for index, chunk in enumerate(_wrap_text(text, 124), start=0):
        _text(draw, 92, 1545 + index * 25, chunk, _font(16), MUTED)
    _text(draw, 92, 1650, "※ この帳票は架空データによるAP Invoice OCRデモ用サンプルです。外部システムへの書き込みは行いません。", _font(17), MUTED)


def _display_rows(document_type: str, fields: dict[str, Any]) -> list[tuple[str, Any]]:
    if document_type == "invoice":
        item = fields["line_items"][0]
        return [
            ("Invoice No", fields["invoice_number"]),
            ("Invoice Date", fields["invoice_date"]),
            ("Due Date", fields["due_date"]),
            ("Vendor", fields["vendor_name"]),
            ("Vendor ID", fields["vendor_id"]),
            ("Bank Account", fields["bank_account"]),
            ("PO No", fields["po_number"]),
            ("Currency", fields["currency"]),
            ("Tax Code", fields["tax_code"]),
            ("Cost Center", fields["cost_center"]),
            ("Line Items", ""),
            ("Description", item["description"]),
            ("Quantity", _format_number(item["quantity"])),
            ("Unit Price", f"JPY {_format_number(item['unit_price'])}"),
            ("Amount", f"JPY {_format_number(item['amount'])}"),
            ("Subtotal", f"JPY {_format_number(fields['subtotal_amount'])}"),
            ("Tax", f"JPY {_format_number(fields['tax_amount'])}"),
            ("Total", f"JPY {_format_number(fields['total_amount'])}"),
        ]
    if document_type == "purchase_order":
        item = fields["line_items"][0]
        return [
            ("PO No", fields["po_number"]),
            ("Vendor ID", fields["vendor_id"]),
            ("Currency", fields["currency"]),
            ("Approved", "Yes" if fields["approved"] else "No"),
            ("Remaining Balance", f"JPY {_format_number(fields['remaining_balance'])}"),
            ("Line Items", ""),
            ("Description", item["description"]),
            ("Quantity", _format_number(item["quantity"])),
            ("Unit Price", f"JPY {_format_number(item['unit_price'])}"),
            ("Amount", f"JPY {_format_number(item['amount'])}"),
            ("Total", f"JPY {_format_number(fields['total_amount'])}"),
        ]
    return [
        ("Receipt No", fields["receipt_number"]),
        ("PO No", fields["po_number"]),
        ("Received", "Yes" if fields["received"] else "No"),
        ("Received Quantity", _format_number(fields["received_quantity"])),
        ("Receipt Date", fields["receipt_date"]),
        ("Item", "Office supplies bundle"),
    ]


def _format_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _yen(value: Any) -> str:
    return f"¥{_format_number(value)}"


def _jp_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.year}年{parsed.month}月{parsed.day}日"


def _font(size: int, *, bold: bool = False, serif: bool = False) -> Any:
    candidates = [
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc" if serif else "",
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: Any,
    fill: str = INK,
) -> None:
    draw.text((x, y), text, fill=fill, font=font)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: Any) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _center_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    text: str,
    font: Any,
    fill: str = INK,
) -> None:
    _text(draw, x + (width - _text_width(draw, text, font)) // 2, y, text, font, fill)


def _right_text(
    draw: ImageDraw.ImageDraw,
    right_x: int,
    y: int,
    text: str,
    font: Any,
    fill: str = INK,
) -> None:
    _text(draw, right_x - _text_width(draw, text, font), y, text, font, fill)


def _wrap_text(text: str, width: int) -> list[str]:
    return [text[index : index + width] for index in range(0, len(text), width)][:4]


CASES: dict[str, dict[str, Any]] = {
    "case-a-pay-ready": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0008",
            po_number="PO-2026-0001",
            total_amount=110000,
            invoice_date="2026-07-15",
        ),
        "purchase_order": po_fields(po_number="PO-2026-0001", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0001", po_number="PO-2026-0001"),
        "expected": {"recommendation": "PAY_READY_CANDIDATE", "rule_ids": []},
    },
    "case-b-po-mismatch": {
        "invoice": invoice_fields(invoice_number="INV-2026-0009", po_number="PO-2026-0002", total_amount=121000),
        "purchase_order": po_fields(po_number="PO-2026-0002", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0002", po_number="PO-2026-0002"),
        "expected": {"recommendation": "REFER_PO_MISMATCH", "rule_ids": ["AP-PO-001"]},
    },
    "case-c-duplicate": {
        "invoice": invoice_fields(invoice_number="INV-2026-0007", po_number="PO-2026-0003", total_amount=110000),
        "purchase_order": po_fields(po_number="PO-2026-0003", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0003", po_number="PO-2026-0003"),
        "expected": {"recommendation": "REFER_DUPLICATE_REVIEW", "rule_ids": ["AP-DUP-001"]},
    },
    "case-d-vendor-review": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0010",
            po_number="PO-2026-0004",
            total_amount=110000,
            bank_account="9999-9999999",
            invoice_date="2026-07-15",
        ),
        "purchase_order": po_fields(po_number="PO-2026-0004", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0004", po_number="PO-2026-0004"),
        "expected": {"recommendation": "REFER_VENDOR_REVIEW", "rule_ids": ["AP-VENDOR-002"]},
    },
    "case-e-grn-mismatch": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0011",
            po_number="PO-2026-0005",
            total_amount=110000,
            invoice_date="2026-07-15",
        ),
        "purchase_order": po_fields(po_number="PO-2026-0005", total_amount=110000),
        "goods_receipt": grn_fields(
            receipt_number="GRN-2026-0005",
            po_number="PO-2026-0005",
            quantity=60,
        ),
        "expected": {"recommendation": "REFER_GRN_MISMATCH", "rule_ids": ["AP-GRN-001"]},
    },
    "case-f-tax-review": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0012",
            po_number="PO-2026-0006",
            total_amount=108000,
            invoice_date="2026-07-15",
            subtotal_amount=100000,
            tax_amount=8000,
        ),
        "purchase_order": po_fields(po_number="PO-2026-0006", total_amount=108000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0006", po_number="PO-2026-0006"),
        "expected": {"recommendation": "REFER_TAX_REVIEW", "rule_ids": ["AP-TAX-001"]},
    },
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")


def write_case(base_dir: Path, case_name: str, payload: dict[str, Any]) -> None:
    case_dir = base_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    for document_type in ("invoice", "purchase_order", "goods_receipt"):
        write_document_pdf(
            case_dir / f"{document_type}.pdf",
            document_type=document_type,
            fields=payload[document_type],
        )


def main() -> None:
    for target in (ROOT_SAMPLES, PACK_SAMPLES):
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
    if PACK_TESTS.exists():
        shutil.rmtree(PACK_TESTS)
    PACK_TESTS.mkdir(parents=True, exist_ok=True)
    for target in (ROOT_SAMPLES, PACK_SAMPLES):
        for case_name, payload in CASES.items():
            write_case(target, case_name, payload)
    for index, (case_name, payload) in enumerate(CASES.items(), start=1):
        suffix = chr(ord("a") + index - 1)
        write_json(
            PACK_TESTS / f"expected-case-{suffix}.json",
            {
                "case": case_name,
                "recommendation": payload["expected"]["recommendation"],
                "rule_ids": payload["expected"]["rule_ids"],
                "write_performed": False,
            },
        )
    print(f"Generated {len(CASES)} AP fixture cases in {ROOT_SAMPLES}")


if __name__ == "__main__":
    main()
