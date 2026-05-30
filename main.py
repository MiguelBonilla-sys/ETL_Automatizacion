"""Orquestador del pipeline ETL — NovaFlow."""
import json
import sys
from datetime import datetime

from src.Utils.logger import get_logger
from src.Extract.clientsExtract  import extract_clients
from src.Extract.ordersExtract   import extract_orders
from src.Extract.invoicesExtract import extract_invoices
from src.Extract.paymentsExtract import extract_payments
from src.Transform.clientsTransform  import transform_clients
from src.Transform.ordersTransform   import transform_orders
from src.Transform.invoicesTransform import transform_invoices
from src.Transform.paymentsTransform import transform_payments
from src.Validate.anomaly_detector   import detect_anomalies
from src.Load.clientsLoad  import load_clients
from src.Load.ordersLoad   import load_orders
from src.Load.invoicesLoad import load_invoices
from src.Load.paymentsLoad import load_payments
from src.Load.db_loader    import load_to_sqlite
from src.Reports.financial_summary import generate_financial_summary
from src.Reports.anomalies_report  import generate_anomalies_report

logger = get_logger("pipeline")


def run() -> int:
    """Ejecuta el pipeline completo. Retorna 0 en éxito, 1 en error."""
    try:
        # ── EXTRACT ───────────────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STAGE 1 — EXTRACT")
        clients_raw  = extract_clients()
        orders_raw   = extract_orders()
        invoices_raw = extract_invoices()
        payments_raw = extract_payments()

        # ── TRANSFORM ─────────────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STAGE 2 — TRANSFORM")
        clients  = transform_clients(clients_raw)
        orders   = transform_orders(orders_raw)
        invoices = transform_invoices(invoices_raw)
        payments = transform_payments(payments_raw)

        # ── VALIDATE ──────────────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STAGE 3 — VALIDATE")
        anomalies = detect_anomalies(clients, orders, invoices, payments)

        # ── LOAD ──────────────────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STAGE 4 — LOAD")
        load_clients(clients)
        load_orders(orders)
        load_invoices(invoices)
        load_payments(payments)
        load_to_sqlite(clients, orders, invoices, payments)

        # ── REPORTS ───────────────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STAGE 5 — REPORTS")
        generate_financial_summary(clients, orders, invoices, payments)
        generate_anomalies_report(anomalies)

        # ── METADATA: guardar config usada para que el dashboard la muestre ───
        from src.Config.config import THRESHOLDS, OUTPUT_DIR
        ensure_dirs_meta = OUTPUT_DIR
        ensure_dirs_meta.mkdir(parents=True, exist_ok=True)

        counts = {
            "raw":   {"clients": len(clients_raw),  "orders": len(orders_raw),
                      "invoices": len(invoices_raw), "payments": len(payments_raw)},
            "clean": {"clients": len(clients),       "orders": len(orders),
                      "invoices": len(invoices),      "payments": len(payments)},
        }
        anomaly_by_type = anomalies["anomaly_type"].value_counts().to_dict() if not anomalies.empty else {}
        anomaly_by_entity = anomalies["entity"].value_counts().to_dict() if not anomalies.empty else {}

        last_run = {
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "thresholds_used": {
                "invoice_math_tolerance": THRESHOLDS["invoice_math_tolerance"],
                "overpayment_tolerance":  THRESHOLDS["overpayment_tolerance"],
            },
            "row_counts": counts,
            "anomaly_total": len(anomalies),
            "anomaly_by_severity": anomalies["severity"].value_counts().to_dict() if not anomalies.empty else {},
            "anomaly_by_type":   anomaly_by_type,
            "anomaly_by_entity": anomaly_by_entity,
        }
        (OUTPUT_DIR / "last_run.json").write_text(json.dumps(last_run, indent=2))
        logger.info(f"last_run.json saved → {OUTPUT_DIR / 'last_run.json'}")

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        return 0

    except Exception as e:
        logger.exception(f"PIPELINE FAILED: {e}")
        return 1


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
