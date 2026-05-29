"""Dashboard Streamlit — NovaFlow ETL Pipeline.

R3: Este archivo no contiene lógica de negocio.
    Solo lee outputs de clean_data/ y llama a main.py como subproceso.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent

FINANCIAL_SUMMARY = ROOT / "financial_summary.csv"
ANOMALIES_REPORT  = ROOT / "anomalies_report.csv"
CLEAN_DIR         = ROOT / "clean_data"
LOG_FILE          = ROOT / "logs" / "pipeline.log"

CLEAN_FILES = {
    "Clients":  CLEAN_DIR / "clients_clean.csv",
    "Orders":   CLEAN_DIR / "orders_clean.csv",
    "Invoices": CLEAN_DIR / "invoices_clean.csv",
    "Payments": CLEAN_DIR / "payments_clean.csv",
}

SEVERITY_COLOR = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

st.set_page_config(
    page_title="NovaFlow — ETL Dashboard",
    page_icon="⚡",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚡ NovaFlow ETL")
    st.markdown("---")

    # ── Thresholds configurables (R1 — ajustables sin tocar código) ───────────
    st.subheader("⚙️ Parámetros del Pipeline")
    math_tol    = st.slider("Tolerancia cálculo impuesto", 0.0, 1.0, 0.01, 0.01,
                            help="invoice_math_tolerance en config.py")
    overpay_tol = st.slider("Tolerancia sobrepago", 0.0, 0.5, 0.01, 0.01,
                            help="overpayment_tolerance en config.py")
    st.markdown("---")

    run_btn = st.button("▶ Ejecutar Pipeline", type="primary", use_container_width=True)

    if run_btn:
        # Escribir thresholds al vuelo antes de correr (demo de extensibilidad)
        config_patch = (
            f"\n# --- Streamlit override ---\n"
            f"THRESHOLDS['invoice_math_tolerance'] = {math_tol}\n"
            f"THRESHOLDS['overpayment_tolerance']  = {overpay_tol}\n"
        )
        with st.spinner("Ejecutando pipeline..."):
            result = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
        if result.returncode == 0:
            st.success("Pipeline completado exitosamente")
        else:
            st.error("Pipeline terminó con errores")
        with st.expander("Ver logs de ejecución"):
            st.code(result.stdout + result.stderr, language="text")
        st.rerun()


# ── Verificar si outputs existen ─────────────────────────────────────────────
outputs_ready = FINANCIAL_SUMMARY.exists() and ANOMALIES_REPORT.exists()

if not outputs_ready:
    st.info(
        "El pipeline aún no ha sido ejecutado.\n\n"
        "Usa el botón **▶ Ejecutar Pipeline** en la barra lateral para generar los outputs.",
        icon="ℹ️",
    )
    st.stop()

# ── Cargar datos ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data():
    summary   = pd.read_csv(FINANCIAL_SUMMARY)
    anomalies = pd.read_csv(ANOMALIES_REPORT)
    return summary, anomalies

summary, anomalies = load_data()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_summary, tab_anomalies, tab_clean, tab_logs = st.tabs([
    "📊 Resumen Financiero",
    "🚨 Anomalías",
    "🗂️ Datos Limpios",
    "📋 Logs",
])

# ── Tab 1: Resumen Financiero ─────────────────────────────────────────────────
with tab_summary:
    st.header("Consolidado Financiero")

    total_inv   = summary["total_invoiced"].sum()
    total_paid  = summary["total_paid"].sum()
    balance     = summary["balance_pending"].sum()
    pct_overdue = (summary["overdue_count"].sum() / summary["invoice_count"].sum() * 100
                   if summary["invoice_count"].sum() > 0 else 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Facturado",  f"${total_inv:,.2f}")
    col2.metric("Total Pagado",     f"${total_paid:,.2f}")
    col3.metric("Saldo Pendiente",  f"${balance:,.2f}")
    col4.metric("% Facturas Vencidas", f"{pct_overdue:.1f}%")

    st.markdown("---")
    st.subheader("Top Deudores")

    currencies = ["Todas"] + sorted(summary["currency"].dropna().unique().tolist())
    sel_currency = st.selectbox("Filtrar por divisa", currencies)

    df_view = summary if sel_currency == "Todas" else summary[summary["currency"] == sel_currency]
    top = df_view.sort_values("balance_pending", ascending=False).head(20)

    st.dataframe(
        top[["company_name", "currency", "total_invoiced", "total_paid",
             "balance_pending", "invoice_count", "overdue_count", "pct_overdue"]],
        use_container_width=True,
        hide_index=True,
    )

    if not top.empty:
        st.subheader("Balance pendiente por cliente (Top 15)")
        chart_data = top.head(15).set_index("company_name")["balance_pending"]
        st.bar_chart(chart_data)

# ── Tab 2: Anomalías ──────────────────────────────────────────────────────────
with tab_anomalies:
    st.header("Reporte de Anomalías")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Anomalías", len(anomalies))
    c2.metric("🔴 HIGH",   len(anomalies[anomalies["severity"] == "HIGH"]))
    c3.metric("🟡 MEDIUM", len(anomalies[anomalies["severity"] == "MEDIUM"]))
    c4.metric("🟢 LOW",    len(anomalies[anomalies["severity"] == "LOW"]))

    st.markdown("---")

    col_sev, col_type = st.columns(2)
    with col_sev:
        sev_filter = st.multiselect(
            "Severidad", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"]
        )
    with col_type:
        types = sorted(anomalies["anomaly_type"].unique().tolist())
        type_filter = st.multiselect("Tipo de anomalía", types, default=types)

    filtered = anomalies[
        anomalies["severity"].isin(sev_filter) &
        anomalies["anomaly_type"].isin(type_filter)
    ]

    st.dataframe(
        filtered[["severity", "anomaly_type", "entity", "record_id", "description", "detected_at"]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Mostrando {len(filtered)} de {len(anomalies)} anomalías")

# ── Tab 3: Datos Limpios ──────────────────────────────────────────────────────
with tab_clean:
    st.header("Preview — Datos Limpios")

    entity = st.selectbox("Seleccionar entidad", list(CLEAN_FILES.keys()))
    path   = CLEAN_FILES[entity]

    if path.exists():
        df_clean = pd.read_csv(path)
        st.caption(f"{len(df_clean)} registros | {path.name}")
        st.dataframe(df_clean, use_container_width=True, hide_index=True)
    else:
        st.warning(f"{path.name} no encontrado. Ejecuta el pipeline primero.")

# ── Tab 4: Logs ───────────────────────────────────────────────────────────────
with tab_logs:
    st.header("Logs del Pipeline")

    if LOG_FILE.exists():
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        n = st.slider("Últimas N líneas", 20, 500, 100, 10)
        st.code("\n".join(lines[-n:]), language="text")
    else:
        st.info("No hay logs disponibles aún.")
