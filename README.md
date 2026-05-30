# NovaFlow ETL Pipeline

Pipeline de limpieza, validación y consolidación financiera para datos de facturación de NovaFlow.

## Requisitos

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias)

## Instalación

```bash
git clone <repo>
cd ETL_Automatizacion
uv sync
```

## Preparar los datos

Coloca los 4 archivos CSV dentro de la carpeta `data/`:

```
data/
├── clients.csv
├── orders.csv
├── invoices.csv
└── payments.csv
```

## Ejecutar el pipeline

```bash
uv run python main.py
```

Esto genera automáticamente:

```
clean_data/          ← datos limpios por entidad
reports/
  ├── financial_summary.csv   ← consolidado financiero
  ├── anomalies_report.csv    ← anomalías detectadas
  └── last_run.json           ← metadata de la corrida
db/
  └── novaflow.db             ← base de datos SQLite (se crea sola)
logs/
  └── pipeline.log            ← log completo
```

No hay que crear ninguna carpeta manualmente. El pipeline las genera en la primera corrida.

## Ver los resultados de forma visual

```bash
uv run streamlit run app.py
```

Abre `http://localhost:8501`. Desde ahí puedes:
- Ver el resumen financiero con filtros por divisa
- Explorar las anomalías detectadas por tipo y severidad
- Ajustar los thresholds con sliders y re-ejecutar el pipeline en vivo
- Revisar los datos limpios por entidad
- Ver la arquitectura del sistema y cómo extenderlo

## Cambiar thresholds sin tocar código

```bash
INVOICE_MATH_TOL=0.05 OVERPAYMENT_TOL=0.10 uv run python main.py
```

O desde los sliders del dashboard de Streamlit.

## Estructura del proyecto

```
ETL_Automatizacion/
├── data/                          # Coloca aquí los 4 CSV de entrada
├── src/
│   ├── Config/config.py           # Constantes, thresholds y severidades
│   ├── Extract/                   # Lectura y validación de schema
│   ├── Transform/                 # Normalización por entidad
│   ├── Validate/                  # 11 reglas de detección de anomalías
│   ├── Load/                      # Escritura a clean_data/ y SQLite
│   ├── Reports/                   # Generadores de reportes
│   └── Utils/                     # logger, validators, data_io
├── main.py                        # Orquestador del pipeline (CLI)
├── app.py                         # Dashboard Streamlit
└── docs/
    ├── enfoque_tecnico.md
    └── enfoque_tecnico.pdf
```

## Cómo extender el sistema

**Agregar una regla de anomalía:**
1. Define `_check_nombre(clients, orders, invoices, payments)` en `src/Validate/anomaly_detector.py`
2. Agrégala a la lista `CHECKS` — nada más cambia

**Cambiar severidad de una anomalía o agregar una divisa:**
```python
# src/Config/config.py
ANOMALY_SEVERITY = {"OVERPAYMENT": "MEDIUM"}
VALID_CURRENCIES  = ["MXN", "USD", "EUR", "COP", "BRL"]
```

**Agregar un KPI al consolidado:**
1. Define `_kpi_nombre(clients, invoices, payments)` en `src/Reports/financial_summary.py`
2. Agrégala a `KPI_FUNCTIONS`

## Supuestos y decisiones

- Los montos se agrupan por divisa — no se convierten entre sí.
- Facturas sin `order_id` o con cliente inválido aparecen etiquetadas (`[Sin order_id]`) en el consolidado — el saldo es real aunque el cliente no esté asignado.
- `UNPAID` en invoices se normaliza a `PENDING`.
- La validación de impuesto es coherencia matemática (`subtotal + tax ≈ total`), no tasa fija.

## Limitaciones

- Sin conversión de divisas entre monedas.
- Sin tests unitarios formales.
- El parseo de fechas usa `dateutil` como fallback — formatos muy inusuales quedan como `NaT`.
