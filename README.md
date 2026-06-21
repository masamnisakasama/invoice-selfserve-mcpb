# AP Invoice Exception Review MCPB

Self-serve MCPB demo for accounts payable invoice exception review. It performs
deterministic matching across invoice, purchase order, goods receipt, vendor
master, invoice history, tax code master, and payment rules. It generates draft
payloads only; no external SaaS or ERP write is performed.

買掛請求書の例外レビューを行う self-serve MCPB デモです。請求書、発注書、納品書/検収、取引先マスタ、過去請求、税区分、支払ルールを決定論的に照合します。生成するのは draft payload のみで、外部 SaaS / ERP への本書き込みは行いません。

## Quick Start

```bash
make install
make generate-ap-samples
make test
make package-ap-mcpb
make verify-ap-data-boundary
make verify-mcpb-contents
make smoke-ap-mcp
npx -y @anthropic-ai/mcpb validate manifest.json
```

Run the local MCP server:

```bash
make dev-mcp
```

## Demo Cases

```text
case-a-pay-ready       PAY_READY_CANDIDATE
case-b-po-mismatch     REFER_PO_MISMATCH
case-c-duplicate       REFER_DUPLICATE_REVIEW
case-d-vendor-review   REFER_VENDOR_REVIEW
case-e-grn-mismatch    REFER_GRN_MISMATCH
case-f-tax-review      REFER_TAX_REVIEW
```

## Package

```text
dist/ap-invoice-review.mcpb
```

The MCPB package contains no production secrets and all generated draft payloads
must include `write_performed=false`.

## MCP Tools

High-level UX tools:

```text
list_ap_demo_cases
review_ap_demo_case
review_ap_invoice_packet
explain_ap_exception
build_ap_approval_brief
```

Customer-ready folder tools:

```text
ap_invoice_setup_demo_workspace
ap_invoice_list_demo_cases
ap_invoice_preview_folder
ap_invoice_review_folder
ap_invoice_review_demo_case
ap_invoice_explain_exception
ap_invoice_build_approval_brief
```

Advanced/debug tools:

```text
create_ap_review_case
upload_ap_document
start_ap_invoice_review
get_ap_invoice_review_result
build_erp_draft_payload
```

All tools are draft-only. The project intentionally does not write to freee,
kintone, ERP, banking, or payment systems.

## Handoff

See `docs/AP_INVOICE_SELF_SERVE_MCPB_HANDOFF.md` for the implemented scope,
non-scope, verification commands, and expected fixture outcomes.

For the two-PC Claude Desktop demo flow, see
`docs/CLAUDE_DESKTOP_MULTI_PC_DEMO_RUNBOOK.md`.
