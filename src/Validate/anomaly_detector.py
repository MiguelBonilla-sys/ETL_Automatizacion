"""Detección de anomalías cross-entidad.

Para agregar una nueva regla (R2):
  1. Define _check_<nombre>(clients, orders, invoices, payments) -> pd.DataFrame
  2. Agrégala a CHECKS al final del archivo.
"""
import re
import uuid
from datetime import datetime

import pandas as pd

from src.Config.config import ANOMALY_SEVERITY, THRESHOLDS
from src.Utils.logger import get_logger

logger = get_logger(__name__)

ANOMALY_COLS = ["anomaly_id", "entity", "record_id", "anomaly_type",
                "severity", "description", "detected_at"]


def _row(entity: str, record_id: str, atype: str, description: str) -> dict:
    return {
        "anomaly_id":  f"ANO-{uuid.uuid4().hex[:8].upper()}",
        "entity":      entity,
        "record_id":   str(record_id),
        "anomaly_type": atype,
        "severity":    ANOMALY_SEVERITY.get(atype, "LOW"),
        "description": description,
        "detected_at": datetime.now().isoformat(timespec="seconds"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Checks individuales — cada uno retorna un DataFrame con ANOMALY_COLS
# ─────────────────────────────────────────────────────────────────────────────

def _check_orphan_payments(clients, orders, invoices, payments) -> pd.DataFrame:
    """A1 — Pagos cuyo invoice_id no existe en invoices."""
    mask = ~payments["invoice_id"].isin(invoices["invoice_id"])
    rows = [
        _row("payments", r["payment_id"], "ORPHAN_PAYMENT",
             f"invoice_id '{r['invoice_id']}' no existe en invoices")
        for _, r in payments[mask].iterrows()
    ]
    logger.info(f"ORPHAN_PAYMENT: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_duplicate_invoices(clients, orders, invoices, payments) -> pd.DataFrame:
    """A2 — Mismo order_id con más de una factura no-VOID."""
    non_void = invoices[(invoices["status"] != "VOID") & invoices["order_id"].notna()]
    dups = non_void[non_void.duplicated("order_id", keep=False)]
    rows = [
        _row("invoices", r["invoice_id"], "DUPLICATE_INVOICE",
             f"order_id '{r['order_id']}' tiene múltiples facturas no-VOID")
        for _, r in dups.iterrows()
    ]
    logger.info(f"DUPLICATE_INVOICE: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_invalid_client_ref(clients, orders, invoices, payments) -> pd.DataFrame:
    """A3 — Órdenes con client_id que no existe en clients."""
    mask = ~orders["client_id"].isin(clients["client_id"])
    rows = [
        _row("orders", r["order_id"], "INVALID_CLIENT_REF",
             f"client_id '{r['client_id']}' no existe en clients")
        for _, r in orders[mask].iterrows()
    ]
    logger.info(f"INVALID_CLIENT_REF: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_invoice_math_error(clients, orders, invoices, payments) -> pd.DataFrame:
    """A4 — Facturas donde subtotal + tax ≠ total (tolerancia configurable)."""
    tol = THRESHOLDS["invoice_math_tolerance"]
    inv = invoices.dropna(subset=["subtotal", "tax", "total"])
    diff = (inv["subtotal"] + inv["tax"] - inv["total"]).abs()
    mask = diff > tol
    rows = [
        _row("invoices", r["invoice_id"], "INVOICE_MATH_ERROR",
             f"subtotal({r['subtotal']}) + tax({r['tax']}) = {r['subtotal']+r['tax']:.2f} ≠ total({r['total']})")
        for _, r in inv[mask].iterrows()
    ]
    logger.info(f"INVOICE_MATH_ERROR: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_overpayment(clients, orders, invoices, payments) -> pd.DataFrame:
    """A5 — Suma de pagos por factura supera el total de la factura."""
    tol = THRESHOLDS["overpayment_tolerance"]
    pay_sum = (payments.groupby("invoice_id")["amount"]
               .sum().reset_index(name="total_paid"))
    merged = invoices.merge(pay_sum, on="invoice_id", how="inner")
    mask = merged["total_paid"] > merged["total"] + tol
    rows = [
        _row("invoices", r["invoice_id"], "OVERPAYMENT",
             f"total_paid({r['total_paid']:.2f}) > invoice_total({r['total']:.2f})")
        for _, r in merged[mask].iterrows()
    ]
    logger.info(f"OVERPAYMENT: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_illogical_due_date(clients, orders, invoices, payments) -> pd.DataFrame:
    """A6 — Facturas donde due_date < issue_date."""
    inv = invoices.dropna(subset=["issue_date", "due_date"])
    mask = inv["due_date"] < inv["issue_date"]
    rows = [
        _row("invoices", r["invoice_id"], "ILLOGICAL_DUE_DATE",
             f"due_date({r['due_date'].date()}) < issue_date({r['issue_date'].date()})")
        for _, r in inv[mask].iterrows()
    ]
    logger.info(f"ILLOGICAL_DUE_DATE: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_illogical_order_date(clients, orders, invoices, payments) -> pd.DataFrame:
    """A7 — order_date posterior a issue_date de la factura correspondiente."""
    merged = invoices.dropna(subset=["order_id", "issue_date"]).merge(
        orders[["order_id", "order_date"]].dropna(), on="order_id", how="inner"
    )
    mask = merged["order_date"] > merged["issue_date"]
    rows = [
        _row("invoices", r["invoice_id"], "ILLOGICAL_ORDER_DATE",
             f"order_date({r['order_date'].date()}) > issue_date({r['issue_date'].date()})")
        for _, r in merged[mask].iterrows()
    ]
    logger.info(f"ILLOGICAL_ORDER_DATE: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_payment_before_invoice(clients, orders, invoices, payments) -> pd.DataFrame:
    """A8 — payment_date anterior a issue_date de la factura."""
    merged = payments.dropna(subset=["invoice_id", "payment_date"]).merge(
        invoices[["invoice_id", "issue_date"]].dropna(), on="invoice_id", how="inner"
    )
    mask = merged["payment_date"] < merged["issue_date"]
    rows = [
        _row("payments", r["payment_id"], "PAYMENT_BEFORE_INVOICE",
             f"payment_date({r['payment_date'].date()}) < issue_date({r['issue_date'].date()})")
        for _, r in merged[mask].iterrows()
    ]
    logger.info(f"PAYMENT_BEFORE_INVOICE: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_null_order_id(clients, orders, invoices, payments) -> pd.DataFrame:
    """A9 — Facturas sin order_id."""
    mask = invoices["order_id"].isna()
    rows = [
        _row("invoices", r["invoice_id"], "NULL_ORDER_ID",
             "Factura sin order_id asociado")
        for _, r in invoices[mask].iterrows()
    ]
    logger.info(f"NULL_ORDER_ID: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_suspicious_name(clients, orders, invoices, payments) -> pd.DataFrame:
    """A10 — Nombres de empresa con caracteres sospechosos (@ o dígitos)."""
    pattern = THRESHOLDS["name_suspicious_pattern"]
    mask = clients["company_name"].str.contains(pattern, na=False, regex=True)
    rows = [
        _row("clients", r["client_id"], "SUSPICIOUS_NAME",
             f"company_name contiene caracteres sospechosos: '{r['company_name']}'")
        for _, r in clients[mask].iterrows()
    ]
    logger.info(f"SUSPICIOUS_NAME: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


def _check_mixed_currency(clients, orders, invoices, payments) -> pd.DataFrame:
    """A11 — Divisa de factura distinta al default_currency del cliente."""
    inv_ord = invoices.merge(
        orders[["order_id", "client_id"]], on="order_id", how="left"
    )
    merged = inv_ord.merge(
        clients[["client_id", "default_currency"]], on="client_id", how="left"
    )
    mask = (
        merged["currency"].notna()
        & merged["default_currency"].notna()
        & (merged["currency"] != merged["default_currency"])
    )
    rows = [
        _row("invoices", r["invoice_id"], "MIXED_CURRENCY",
             f"invoice currency({r['currency']}) ≠ client default({r['default_currency']})")
        for _, r in merged[mask].iterrows()
    ]
    logger.info(f"MIXED_CURRENCY: {len(rows)} anomalies")
    return pd.DataFrame(rows, columns=ANOMALY_COLS)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO — agregar nueva regla aquí (R2)
# ─────────────────────────────────────────────────────────────────────────────
CHECKS = [
    _check_orphan_payments,
    _check_duplicate_invoices,
    _check_invalid_client_ref,
    _check_invoice_math_error,
    _check_overpayment,
    _check_illogical_due_date,
    _check_illogical_order_date,
    _check_payment_before_invoice,
    _check_null_order_id,
    _check_suspicious_name,
    _check_mixed_currency,
]


def detect_anomalies(
    clients: pd.DataFrame,
    orders: pd.DataFrame,
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
) -> pd.DataFrame:
    logger.info(f"Running {len(CHECKS)} anomaly checks")
    results = []
    for check in CHECKS:
        try:
            df = check(clients, orders, invoices, payments)
            if not df.empty:
                results.append(df)
        except Exception as e:
            logger.error(f"Check {check.__name__} failed: {e}")

    if not results:
        return pd.DataFrame(columns=ANOMALY_COLS)

    combined = pd.concat(results, ignore_index=True)
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    combined["_sev_order"] = combined["severity"].map(severity_order)
    combined = combined.sort_values("_sev_order").drop(columns="_sev_order")
    logger.info(f"Total anomalies detected: {len(combined)}")
    return combined
