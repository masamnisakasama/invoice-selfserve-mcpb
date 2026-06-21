# AP Invoice Review Skill

Use this skill when a user asks to review an accounts payable invoice packet with an invoice, purchase order, and goods receipt or inspection report.

## Tool Order

1. Call `create_ap_review_case` with the tenant, workflow pack `ap-invoice-v1`, ruleset `ap-demo-2026-01`, and a short case label.
2. Call `upload_ap_document` once for each required document type:
   - `invoice`
   - `purchase_order`
   - `goods_receipt`
3. Call `start_ap_invoice_review`.
4. Call `get_ap_invoice_review_result` with the returned job ID.
5. If the user asks for an ERP/SaaS payload, call `build_erp_draft_payload` with `mode` set to `draft_only`.

## Response Rules

- Explain the recommendation, matched evidence, rule IDs, and any missing information.
- Treat `PAY_READY_CANDIDATE` as a human approval candidate, not as an automatic payment approval.
- Never claim that the tool wrote to freee, kintone, ERP, banking, or any external SaaS.
- Always preserve `write_performed: false` when showing draft payloads.

## Demo Cases

- `samples/case-a-pay-ready`: expected `PAY_READY_CANDIDATE`
- `samples/case-b-po-mismatch`: expected `REFER_PO_MISMATCH`
- `samples/case-c-duplicate`: expected `REFER_DUPLICATE_REVIEW`
- `samples/case-d-vendor-review`: expected `REFER_VENDOR_REVIEW`
