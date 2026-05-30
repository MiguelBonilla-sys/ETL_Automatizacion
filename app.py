"""Dashboard Streamlit — NovaFlow ETL Pipeline."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Importar config y registros en tiempo real (no hardcodeado)
from src.Config.config import (
    ANOMALY_SEVERITY, STATUS_NORMALIZATION,
    THRESHOLDS, VALID_CURRENCIES, VALID_STATUSES,
)
from src.Reports.financial_summary import KPI_FUNCTIONS
from src.Validate.anomaly_detector import CHECKS

REPORTS_DIR       = ROOT / "reports"
FINANCIAL_SUMMARY = REPORTS_DIR / "financial_summary.csv"
ANOMALIES_REPORT  = REPORTS_DIR / "anomalies_report.csv"
LAST_RUN_JSON     = REPORTS_DIR / "last_run.json"
CLEAN_DIR         = ROOT / "clean_data"
DATA_DIR          = ROOT / "data"
LOG_FILE          = ROOT / "logs" / "pipeline.log"

ENTITIES = ["clients", "orders", "invoices", "payments"]
CLEAN_FILES = {e: CLEAN_DIR / f"{e}_clean.csv" for e in ENTITIES}
RAW_FILES   = {e: DATA_DIR  / f"{e}.csv"       for e in ENTITIES}

st.set_page_config(page_title="NovaFlow — ETL", page_icon="⚡", layout="wide")

# ── Sidebar: thresholds + ejecución ──────────────────────────────────────────
with st.sidebar:
    st.title("⚡ NovaFlow ETL")
    st.markdown("---")
    st.subheader("⚙️ Thresholds")

    math_tol = st.slider(
        "Tolerancia cálculo impuesto", 0.0, 1.0, 0.01, 0.01,
        help="INVOICE_MATH_TOL — |subtotal+tax−total| > valor → anomalía HIGH",
    )
    overpay_tol = st.slider(
        "Tolerancia sobrepago", 0.0, 0.5, 0.01, 0.01,
        help="OVERPAYMENT_TOL — total_pagado > total_factura + valor → anomalía HIGH",
    )
    st.caption(f"math={math_tol} | overpay={overpay_tol}")
    st.markdown("---")

    run_btn = st.button("▶ Ejecutar Pipeline", type="primary", use_container_width=True)

    if run_btn:
        env = os.environ.copy()
        env["INVOICE_MATH_TOL"] = str(math_tol)
        env["OVERPAYMENT_TOL"]  = str(overpay_tol)
        with st.spinner("Ejecutando pipeline..."):
            result = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True, text=True, cwd=ROOT, env=env,
            )
        if result.returncode == 0:
            st.success("Pipeline completado")
        else:
            st.error("Pipeline terminó con errores")
        with st.expander("Ver logs de ejecución"):
            st.code(result.stdout + result.stderr, language="text")
        st.rerun()

# ── Datos (cargados una vez, cacheados 30 s) ─────────────────────────────────
outputs_ready = FINANCIAL_SUMMARY.exists() and ANOMALIES_REPORT.exists()


@st.cache_data(ttl=30)
def load_reports():
    return pd.read_csv(FINANCIAL_SUMMARY), pd.read_csv(ANOMALIES_REPORT)


summary = anomalies = None
if outputs_ready:
    summary, anomalies = load_reports()

# ── Tabs ──────────────────────────────────────────────────────────────────────
(tab_pipeline, tab_summary, tab_anomalies,
 tab_clean, tab_arch, tab_logs) = st.tabs([
    "🔄 Pipeline",
    "📊 Resumen Financiero",
    "🚨 Anomalías",
    "🗂️ Datos Limpios",
    "🏗️ Arquitectura",
    "📋 Logs",
])

# ── 1. PIPELINE ───────────────────────────────────────────────────────────────
with tab_pipeline:
    st.header("Pipeline ETL — NovaFlow")

    stages = [
        ("1 — EXTRACT",   "Lee y valida schema de los 4 CSV fuente"),
        ("2 — TRANSFORM", "Normaliza fechas, montos, estados, deduplication"),
        ("3 — VALIDATE",  f"Detecta anomalías cross-entidad ({len(CHECKS)} reglas)"),
        ("4 — LOAD",      "Escribe clean_data/ y SQLite (novaflow.db)"),
        ("5 — REPORTS",   "Genera financial_summary.csv y anomalies_report.csv"),
    ]
    cols = st.columns(5)
    for col, (stage, desc) in zip(cols, stages):
        col.markdown(f"**{stage}**")
        col.caption(desc)

    st.markdown("---")

    if not outputs_ready:
        st.info("Ejecuta el pipeline desde la barra lateral para ver métricas.", icon="ℹ️")
    else:
        # ── Leer metadata de la última corrida ────────────────────────────────
        last_run = {}
        if LAST_RUN_JSON.exists():
            last_run = json.loads(LAST_RUN_JSON.read_text())

        # ── Thresholds usados ─────────────────────────────────────────────────
        if last_run:
            used = last_run.get("thresholds_used", {})
            math_used     = used.get("invoice_math_tolerance", "?")
            overpay_used  = used.get("overpayment_tolerance", "?")
            ran_at        = last_run.get("ran_at", "?")

            th_col1, th_col2, th_col3 = st.columns(3)
            th_col1.metric("Tolerancia impuesto (usada)",  math_used,
                           delta=f"{math_used - 0.01:+.3f}" if isinstance(math_used, float) else None)
            th_col2.metric("Tolerancia sobrepago (usada)", overpay_used,
                           delta=f"{overpay_used - 0.01:+.3f}" if isinstance(overpay_used, float) else None)
            th_col3.info(f"Última corrida: **{ran_at}**\n\nCambia los sliders y re-ejecuta para ver el efecto en las anomalías.", icon="⚙️")
            st.caption("El delta muestra la desviación respecto al default (0.01). "
                       "Un overpay_tolerance alto → menos OVERPAYMENT detectados.")

        st.markdown("---")

        # ── KPI cards ─────────────────────────────────────────────────────────
        sev = last_run.get("anomaly_by_severity", {})
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Registros extraídos",  f"{sum(last_run.get('row_counts',{}).get('raw',{}).values()):,}")
        c2.metric("Registros cargados",   f"{sum(last_run.get('row_counts',{}).get('clean',{}).values()):,}")
        c3.metric("Anomalías 🔴 HIGH",    sev.get("HIGH",   len(anomalies[anomalies["severity"]=="HIGH"])))
        c4.metric("Anomalías 🟡 MEDIUM",  sev.get("MEDIUM", len(anomalies[anomalies["severity"]=="MEDIUM"])))
        c5.metric("Anomalías 🟢 LOW",     sev.get("LOW",    len(anomalies[anomalies["severity"]=="LOW"])))

        st.markdown("---")

        # ── Tabla por entidad con anomalías reales ────────────────────────────
        st.subheader("Registros por entidad")
        st.caption("'Deduplicados' = filas eliminadas por ID duplicado. "
                   "Este dataset tiene IDs únicos, por eso es 0. "
                   "Las anomalías de datos se capturan en la pestaña Anomalías.")

        raw_counts   = last_run.get("row_counts", {}).get("raw",   {})
        clean_counts = last_run.get("row_counts", {}).get("clean", {})
        entity_anoms = last_run.get("anomaly_by_entity", {})

        rows = []
        for e in ENTITIES:
            raw_n   = raw_counts.get(e,   len(pd.read_csv(RAW_FILES[e]))   if RAW_FILES[e].exists()   else 0)
            clean_n = clean_counts.get(e, len(pd.read_csv(CLEAN_FILES[e])) if CLEAN_FILES[e].exists() else 0)
            rows.append({
                "Entidad":             e,
                "Extraídos (raw)":     raw_n,
                "Cargados (clean)":    clean_n,
                "Deduplicados (ID)":   raw_n - clean_n,
                "Anomalías detectadas": entity_anoms.get(e, 0),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Efecto de thresholds ──────────────────────────────────────────────
        if last_run:
            st.markdown("---")
            st.subheader("Efecto de los thresholds en esta corrida")
            type_counts = last_run.get("anomaly_by_type", {})
            threshold_types = ["INVOICE_MATH_ERROR", "OVERPAYMENT"]
            cols_th = st.columns(2)
            for col, atype in zip(cols_th, threshold_types):
                count = type_counts.get(atype, 0)
                col.metric(atype, count,
                           help=f"Sube el slider correspondiente → este número baja. "
                                f"Con tolerance=9999 → 0 anomalías de este tipo.")
            st.caption("Para demostrarlo: mueve 'Tolerancia sobrepago' a 0.5, re-ejecuta y observa cómo OVERPAYMENT baja.")

# ── 2. RESUMEN FINANCIERO ─────────────────────────────────────────────────────
with tab_summary:
    st.header("Consolidado Financiero")

    if not outputs_ready:
        st.info("Ejecuta el pipeline para ver el resumen.", icon="ℹ️")
    else:
        total_inv   = summary["total_invoiced"].sum()
        total_paid  = summary["total_paid"].sum()
        balance     = summary["balance_pending"].sum()
        inv_count   = summary["invoice_count"].sum()
        pct_overdue = (summary["overdue_count"].sum() / inv_count * 100) if inv_count > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Facturado",     f"${total_inv:,.2f}")
        c2.metric("Total Pagado",        f"${total_paid:,.2f}")
        c3.metric("Saldo Pendiente",     f"${balance:,.2f}")
        c4.metric("% Facturas Vencidas", f"{pct_overdue:.1f}%")

        st.markdown("---")
        st.subheader("Top Deudores")
        currencies = ["Todas"] + sorted(summary["currency"].dropna().unique().tolist())
        sel = st.selectbox("Filtrar por divisa", currencies)
        df_view = summary if sel == "Todas" else summary[summary["currency"] == sel]
        top = df_view.sort_values("balance_pending", ascending=False).head(20)

        st.dataframe(
            top[["company_name", "currency", "total_invoiced", "total_paid",
                 "balance_pending", "invoice_count", "overdue_count", "pct_overdue"]],
            use_container_width=True, hide_index=True,
        )
        if not top.empty:
            st.subheader("Balance pendiente — Top 15")
            st.bar_chart(top.head(15).set_index("company_name")["balance_pending"])

# ── 3. ANOMALÍAS ──────────────────────────────────────────────────────────────
with tab_anomalies:
    st.header("Reporte de Anomalías")

    if not outputs_ready:
        st.info("Ejecuta el pipeline para ver anomalías.", icon="ℹ️")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total",     len(anomalies))
        c2.metric("🔴 HIGH",   len(anomalies[anomalies["severity"] == "HIGH"]))
        c3.metric("🟡 MEDIUM", len(anomalies[anomalies["severity"] == "MEDIUM"]))
        c4.metric("🟢 LOW",    len(anomalies[anomalies["severity"] == "LOW"]))

        st.markdown("---")

        if anomalies.empty:
            st.success("✅ Sin anomalías detectadas. Los datos son consistentes.", icon="✅")
        else:
            st.subheader("Distribución por tipo")
            by_type = (anomalies.groupby(["anomaly_type", "severity"])
                       .size().reset_index(name="count")
                       .sort_values("count", ascending=False))
            col_tbl, col_bar = st.columns([1, 2])
            with col_tbl:
                st.dataframe(by_type, use_container_width=True, hide_index=True)
            with col_bar:
                st.bar_chart(by_type.set_index("anomaly_type")["count"])

            st.markdown("---")
            st.subheader("Detalle")
            col_sev, col_type = st.columns(2)
            with col_sev:
                sev_filter = st.multiselect(
                    "Severidad", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"]
                )
            with col_type:
                types = sorted(anomalies["anomaly_type"].unique().tolist())
                type_filter = st.multiselect("Tipo", types, default=types)

            filtered = anomalies[
                anomalies["severity"].isin(sev_filter) &
                anomalies["anomaly_type"].isin(type_filter)
            ]
            st.dataframe(
                filtered[["severity", "anomaly_type", "entity",
                           "record_id", "description", "detected_at"]],
                use_container_width=True, hide_index=True,
            )
            st.caption(f"Mostrando {len(filtered)} de {len(anomalies)} anomalías")

# ── 4. DATOS LIMPIOS ──────────────────────────────────────────────────────────
with tab_clean:
    st.header("Preview — Datos Limpios")
    entity = st.selectbox("Entidad", ENTITIES)
    path   = CLEAN_FILES[entity]
    if path.exists():
        df = pd.read_csv(path)
        st.caption(f"{len(df)} registros | {path.name}")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Ejecuta el pipeline primero.")

# ── 5. ARQUITECTURA ───────────────────────────────────────────────────────────
with tab_arch:
    st.header("Arquitectura del Pipeline")
    st.caption("Todo lo que ves aquí se lee en tiempo real desde el código fuente — "
               "cualquier cambio al pipeline se refleja aquí al recargar.")

    col_checks, col_kpis = st.columns(2)

    with col_checks:
        st.subheader(f"Reglas de anomalías — {len(CHECKS)} registradas")
        for i, fn in enumerate(CHECKS, 1):
            first_line = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else fn.__name__
            st.markdown(f"**{i}.** `{fn.__name__}`")
            st.caption(first_line)
        st.info(
            "**Agregar una regla:** define `_check_nombre()` en "
            "`src/Validate/anomaly_detector.py` y agrégala a `CHECKS`.",
            icon="➕",
        )

    with col_kpis:
        st.subheader(f"KPIs financieros — {len(KPI_FUNCTIONS)} registrados")
        for i, fn in enumerate(KPI_FUNCTIONS, 1):
            st.markdown(f"**{i}.** `{fn.__name__}`")
        st.info(
            "**Agregar un KPI:** define `_kpi_nombre()` en "
            "`src/Reports/financial_summary.py` y agrégalo a `KPI_FUNCTIONS`.",
            icon="➕",
        )

    st.markdown("---")
    st.subheader("Configuración activa")
    st.caption("Fuente: `src/Config/config.py`. Los sliders de la barra lateral "
               "sobreescriben `THRESHOLDS` vía env vars al lanzar el subprocess.")

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        st.markdown("**Thresholds (defaults en config.py)**")
        st.json({k: v for k, v in THRESHOLDS.items() if k != "name_suspicious_pattern"})

        st.markdown("**Severidades de anomalías**")
        st.json(ANOMALY_SEVERITY)

    with col_cfg2:
        st.markdown("**Divisas válidas**")
        st.write(", ".join(VALID_CURRENCIES))

        st.markdown("**Estados válidos por entidad**")
        st.json(VALID_STATUSES)

        st.markdown("**Normalización de estados**")
        st.json(STATUS_NORMALIZATION)

    st.markdown("---")
    st.subheader("Recetas de extensión")

    with st.expander("Agregar nueva regla de anomalía"):
        st.code("""\
# src/Validate/anomaly_detector.py

def _check_zero_amount(clients, orders, invoices, payments) -> pd.DataFrame:
    \"\"\"A12 — Facturas con total == 0.\"\"\"
    mask = invoices["total"] == 0
    rows = [
        _row("invoices", r["invoice_id"], "ZERO_AMOUNT", "Factura con total cero")
        for _, r in invoices[mask].iterrows()
    ]
    return pd.DataFrame(rows, columns=ANOMALY_COLS)

CHECKS = [
    ...,
    _check_zero_amount,   # ← solo agregar aquí
]
""", language="python")

    with st.expander("Cambiar threshold dinámicamente (sin tocar código)"):
        st.code("""\
# Opción A — slider en este dashboard → re-ejecutar pipeline
# Opción B — variable de entorno al lanzar
INVOICE_MATH_TOL=0.05 python main.py

# Opción C — editar directamente en config.py
THRESHOLDS = {
    "invoice_math_tolerance": 0.05,
    ...
}
""", language="bash")

    with st.expander("Soportar otra moneda"):
        st.code("""\
# src/Config/config.py
VALID_CURRENCIES = ["MXN", "USD", "EUR", "COP", "BRL"]  # agregar aquí
""", language="python")

    with st.expander("Agregar un KPI nuevo al consolidado"):
        st.code("""\
# src/Reports/financial_summary.py

def _kpi_avg_invoice(clients, invoices, payments) -> dict:
    active = invoices[invoices["status"] != "VOID"]
    return {"avg_invoice_amount": active["total"].mean()}

KPI_FUNCTIONS = [
    ...,
    _kpi_avg_invoice,   # ← solo agregar aquí
]
""", language="python")

    with st.expander("Cambiar severidad de una anomalía"):
        st.code("""\
# src/Config/config.py
ANOMALY_SEVERITY = {
    "OVERPAYMENT": "MEDIUM",   # era HIGH
    ...
}
""", language="python")

# ── 6. LOGS ───────────────────────────────────────────────────────────────────
with tab_logs:
    st.header("Logs del Pipeline")
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        n = st.slider("Últimas N líneas", 20, 500, 100, 10)
        st.code("\n".join(lines[-n:]), language="text")
    else:
        st.info("No hay logs disponibles aún.")
