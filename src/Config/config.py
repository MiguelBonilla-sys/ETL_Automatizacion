"""Configuracion central del proyecto ETL — todas las constantes viven aquí (R1)."""
import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR     = PROJECT_ROOT / "data"
CLEAN_DIR    = PROJECT_ROOT / "clean_data"
DB_DIR       = PROJECT_ROOT / "db"
DB_PATH      = DB_DIR / "novaflow.db"
LOG_DIR      = PROJECT_ROOT / "logs"
LOG_FILE     = LOG_DIR / "pipeline.log"
OUTPUT_DIR   = PROJECT_ROOT / "reports"


def ensure_dirs() -> None:
    for d in [CLEAN_DIR, DB_DIR, LOG_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL  = logging.INFO
LOG_FORMAT = "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s"

# ── Currencies & statuses ────────────────────────────────────────────────────
VALID_CURRENCIES = ["MXN", "USD", "EUR", "COP"]

VALID_STATUSES = {
    "clients":  ["ACTIVE", "INACTIVE", "PENDING", "SUSPENDED"],
    "orders":   ["COMPLETED", "CANCELLED", "PENDING", "IN_PROGRESS"],
    "invoices": ["PAID", "PARTIAL", "VOID", "OVERDUE", "PENDING"],
}

# Normalización de estados inconsistentes encontrados en los datos reales
STATUS_NORMALIZATION = {
    "invoices": {"UNPAID": "PENDING"},
    "clients":  {},
    "orders":   {},
}

VALID_PAYMENT_METHODS = ["PAYPAL", "BANK_TRANSFER", "CREDIT_CARD", "CRYPTO", "STRIPE"]

# ── Severidades de anomalías (cambiar aquí para ajustar alertas) ─────────────
ANOMALY_SEVERITY = {
    "ORPHAN_PAYMENT":         "HIGH",
    "DUPLICATE_INVOICE":      "HIGH",
    "INVALID_CLIENT_REF":     "HIGH",
    "INVOICE_MATH_ERROR":     "HIGH",
    "OVERPAYMENT":            "HIGH",
    "NULL_ORDER_ID":          "MEDIUM",
    "ILLOGICAL_DUE_DATE":     "MEDIUM",
    "ILLOGICAL_ORDER_DATE":   "MEDIUM",
    "PAYMENT_BEFORE_INVOICE": "MEDIUM",
    "SUSPICIOUS_NAME":        "LOW",
    "MIXED_CURRENCY":         "LOW",
}

# ── Thresholds numéricos — sobreescribibles via env vars (Streamlit slider → subprocess) ──
THRESHOLDS = {
    "invoice_math_tolerance":  float(os.environ.get("INVOICE_MATH_TOL", "0.01")),
    "overpayment_tolerance":   float(os.environ.get("OVERPAYMENT_TOL",  "0.01")),
    "name_suspicious_pattern": r"[@\d]",
}

# ── Schema esperado por entidad ──────────────────────────────────────────────
EXPECTED_COLUMNS = {
    "clients":  ["client_id", "company_name", "tax_id", "email",
                 "country", "default_currency", "status"],
    "orders":   ["order_id", "client_id", "order_date",
                 "service_type", "amount", "status"],
    "invoices": ["invoice_id", "order_id", "issue_date", "subtotal",
                 "tax", "total", "currency", "due_date", "status"],
    "payments": ["payment_id", "invoice_id", "payment_date",
                 "amount", "method", "reference"],
}
