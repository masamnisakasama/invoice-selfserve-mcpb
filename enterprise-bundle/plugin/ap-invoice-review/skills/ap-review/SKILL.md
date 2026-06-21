# AP Invoice Review Skill

Use this skill when the user asks to:

- review an AP invoice
- review a demo case such as `case-a`, `case-b`, `case-c`, or `case-d`
- determine whether an invoice is pay-ready
- explain an AP invoice exception
- build a draft ERP/SaaS payload
- create an approver brief
- use `/ap-review`, `/ap-demo`, `/ap-explain`, or `/ap-approval-brief`

## UX Rules

- Prefer high-level tools.
- If the user did not specify a case or file paths, call `list_ap_demo_cases` first.
- If the user specified a demo case, call `review_ap_demo_case`.
- If the user specified three PDFs, call `review_ap_invoice_packet`.
- Do not ask the user to manually call low-level tools.
- Do not search external connector registry.
- Use the installed AP Invoice Exception Review MCP tools.
- Never claim that an external ERP/SaaS write occurred.
- Always show `write_performed=false`.
- Treat `PAY_READY_CANDIDATE` as a human approval candidate, not as automatic payment approval.

## Main Entrypoints

### `/ap-demo`

Call `list_ap_demo_cases`, show the four bundled demo cases with business value, and ask the user to choose one. If the user already chose a case, call `review_ap_demo_case`.

### `/ap-review`

If the user says `case-aをレビューして` or similar, normalize the demo case and call `review_ap_demo_case`. If the user provides three sidecar-backed PDF paths, call `review_ap_invoice_packet`.

### `/ap-explain`

Call `explain_ap_exception` for the current or supplied job ID. Explain rule IDs, evidence, root causes, and next actions in Japanese.

### `/ap-approval-brief`

Call `build_ap_approval_brief` for the current or supplied job ID. Keep the response short and approver-focused.

## Response Format

1. 判定
2. 業務上の意味
3. 例外理由
4. 適用ルール
5. 根拠
6. 不足情報
7. 次アクション
8. draft payload summary
9. `write_performed=false`

## Demo Cases

- `case-a-pay-ready`: expected `PAY_READY_CANDIDATE`; normal 3-way match and pay-ready candidate sorting.
- `case-b-po-mismatch`: expected `REFER_PO_MISMATCH`; PO amount variance is detected before payment.
- `case-c-duplicate`: expected `REFER_DUPLICATE_REVIEW`; duplicate invoice risk is detected.
- `case-d-vendor-review`: expected `REFER_VENDOR_REVIEW`; bank account mismatch against vendor master is detected.

## Advanced Tools

The low-level tools remain available for debugging and backward compatibility:

- `create_ap_review_case`
- `upload_ap_document`
- `start_ap_invoice_review`
- `get_ap_invoice_review_result`
- `build_erp_draft_payload`

Do not explain this low-level sequence in normal user-facing responses unless the user explicitly asks for implementation details.
