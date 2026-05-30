"""Consolidado financiero por cliente y divisa.

Para agregar un nuevo KPI al dashboard (R2):
  1. Define _kpi_<nombre>(clients, invoices, payments) -> dict con clave descriptiva
  2. Agrégala a KPI_FUNCTIONS al final del archivo.
"""
from datetime import date

import pandas as pd

from src.Config.config import OUTPUT_DIR
from src.Utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# KPI globales (para cards en Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

def _kpi_total_invoiced(clients, invoices, payments) -> dict:
    active = invoices[invoices["status"] != "VOID"]
    return {"total_invoiced": active["total"].sum()}


def _kpi_total_paid(clients, invoices, payments) -> dict:
    inv_ids = invoices[invoices["status"] != "VOID"]["invoice_id"]
    paid = payments[payments["invoice_id"].isin(inv_ids)]
    return {"total_paid": paid["amount"].sum()}


def _kpi_balance_pending(clients, invoices, payments) -> dict:
    inv = _kpi_total_invoiced(clients, invoices, payments)["total_invoiced"]
    pay = _kpi_total_paid(clients, invoices, payments)["total_paid"]
    return {"balance_pending": inv - pay}


def _kpi_pct_overdue(clients, invoices, payments) -> dict:
    active = invoices[invoices["status"] != "VOID"]
    if active.empty:
        return {"pct_overdue": 0.0}
    today = pd.Timestamp(date.today())
    overdue = active[
        (active["status"] == "OVERDUE") |
        (active["due_date"].notna() & (active["due_date"] < today) & (active["status"] != "PAID"))
    ]
    return {"pct_overdue": round(len(overdue) / len(active) * 100, 2)}


def _kpi_anomaly_count(clients, invoices, payments) -> dict:
    return {"anomaly_count": None}  # completado en main.py con datos reales


# REGISTRO de KPIs globales — agregar nuevo KPI aquí (R2)
KPI_FUNCTIONS = [
    _kpi_total_invoiced,
    _kpi_total_paid,
    _kpi_balance_pending,
    _kpi_pct_overdue,
]


def compute_global_kpis(
    clients: pd.DataFrame,
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
) -> dict:
    kpis = {}
    for fn in KPI_FUNCTIONS:
        kpis.update(fn(clients, invoices, payments))
    return kpis


# ─────────────────────────────────────────────────────────────────────────────
# Consolidado por (client_id, currency)
# ─────────────────────────────────────────────────────────────────────────────

def generate_financial_summary(
    clients: pd.DataFrame,
    orders: pd.DataFrame,
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Generating financial summary")

    today = pd.Timestamp(date.today())
    active_inv = invoices[invoices["status"] != "VOID"].copy()

    # Pagos por factura
    pay_sum = (
        payments.groupby("invoice_id")["amount"]
        .sum()
        .reset_index(name="total_paid_invoice")
    )
    inv_pay = active_inv.merge(pay_sum, on="invoice_id", how="left")
    inv_pay["total_paid_invoice"] = inv_pay["total_paid_invoice"].fillna(0)

    # Vincular cliente via order
    inv_ord = inv_pay.merge(
        orders[["order_id", "client_id"]], on="order_id", how="left"
    )

    # Marcar vencidas
    inv_ord["is_overdue"] = (
        (inv_ord["status"] == "OVERDUE") |
        (inv_ord["due_date"].notna() & (inv_ord["due_date"] < today) & (inv_ord["status"] != "PAID"))
    )

    # Agrupar por (client_id, currency)
    grp = (
        inv_ord.groupby(["client_id", "currency"], dropna=False)
        .agg(
            total_invoiced    = ("total", "sum"),
            total_paid        = ("total_paid_invoice", "sum"),
            invoice_count     = ("invoice_id", "count"),
            overdue_count     = ("is_overdue", "sum"),
        )
        .reset_index()
    )

    grp["balance_pending"] = grp["total_invoiced"] - grp["total_paid"]
    grp["pct_overdue"] = (grp["overdue_count"] / grp["invoice_count"] * 100).round(2)

    # Agregar nombre del cliente
    grp = grp.merge(clients[["client_id", "company_name"]], on="client_id", how="left")

    # Etiquetar filas sin company_name en lugar de dejarlas como None
    def _label(row) -> str:
        if pd.notna(row["company_name"]):
            return row["company_name"]
        if pd.isna(row["client_id"]):
            return "[Sin order_id]"
        return f"[ID inválido: {row['client_id']}]"

    grp["company_name"] = grp.apply(_label, axis=1)

    cols = ["client_id", "company_name", "currency", "total_invoiced",
            "total_paid", "balance_pending", "invoice_count", "overdue_count", "pct_overdue"]
    grp = grp[cols].sort_values("balance_pending", ascending=False)

    out_path = OUTPUT_DIR / "financial_summary.csv"
    grp.to_csv(out_path, index=False)
    logger.info(f"financial_summary.csv saved → {out_path} ({len(grp)} rows)")
    return grp
