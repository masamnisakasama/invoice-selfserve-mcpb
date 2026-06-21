VENV ?= .venv
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3)
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: venv install lint typecheck test generate-ap-samples test-ap-rules \
        test-ap-fixtures test-ap-golden package-ap-mcpb verify-ap-data-boundary \
        verify-mcpb-contents verify-ocr-smoke-gate smoke-ap-mcp dev-mcp

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e ".[dev]"

generate-ap-samples:
	$(PY) scripts/generate_ap_samples.py

lint:
	$(PY) -m ruff check ap_invoice_core ap_invoice_mcp scripts tests

typecheck:
	$(PY) -m mypy ap_invoice_core ap_invoice_mcp scripts

test:
	$(PY) -m pytest

test-ap-rules:
	$(PY) -m pytest tests/unit

test-ap-fixtures:
	$(PY) -m pytest tests/fixtures

test-ap-golden:
	$(PY) -m pytest tests/golden

package-ap-mcpb:
	$(PY) scripts/package_ap_mcpb.py

verify-ap-data-boundary:
	$(PY) scripts/verify_ap_data_boundary.py dist/ap-invoice-review.mcpb

verify-mcpb-contents:
	$(PY) scripts/verify_mcpb_contents.py dist/ap-invoice-review.mcpb

verify-ocr-smoke-gate:
	$(PY) scripts/verify_ocr_smoke_gate.py dist/ap-invoice-review.mcpb

smoke-ap-mcp:
	$(PY) scripts/smoke_ap_mcp.py

dev-mcp:
	$(PY) -m ap_invoice_mcp
