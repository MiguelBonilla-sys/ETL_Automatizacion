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

## Cómo correr

### Opción A — CLI

```bash
python main.py
```

Genera todos los outputs en una sola corrida. Salida de logs en consola y en `logs/pipeline.log`.

### Opción B — Dashboard Streamlit

```bash
streamlit run app.py
```

Abre `http://localhost:8501`. Desde la barra lateral usa el botón **▶ Ejecutar Pipeline** para correr el ETL y ver los resultados en pantalla.

## Estructura del proyecto

```
ETL_Automatizacion/
├── data/                    # CSVs de entrada (fuente sucia)
├── clean_data/              # CSVs limpios (generado en runtime)
├── db/                      # novaflow.db SQLite (generado en runtime)
├── logs/                    # Logs de ejecución (generado en runtime)
├── src/
│   ├── Config/config.py     # Todas las constantes, thresholds y severidades
│   ├── Extract/             # Lectura y validación de schema por entidad
│   ├── Transform/           # Limpieza por entidad
│   ├── Validate/            # Detección de anomalías cross-entidad
│   ├── Load/                # Escritura a clean_data/ y SQLite
│   ├── Reports/             # financial_summary y anomalies_report
│   └── Utils/               # logger, validators, data_io
├── main.py                  # Orquestador del pipeline
├── app.py                   # Dashboard Streamlit
├── financial_summary.csv    # Output: consolidado financiero (generado en runtime)
└── anomalies_report.csv     # Output: reporte de anomalías (generado en runtime)
```

## Outputs generados

| Archivo | Descripción |
|---------|-------------|
| `clean_data/clients_clean.csv` | Clientes normalizados |
| `clean_data/orders_clean.csv` | Órdenes limpias |
| `clean_data/invoices_clean.csv` | Facturas normalizadas (UNPAID → PENDING) |
| `clean_data/payments_clean.csv` | Pagos limpios |
| `financial_summary.csv` | Total facturado, pagado, saldo pendiente y % vencidas por cliente y divisa |
| `anomalies_report.csv` | 864 anomalías detectadas con severidad HIGH / MEDIUM / LOW |
| `db/novaflow.db` | Tablas limpias en SQLite |
| `logs/pipeline.log` | Log completo de la corrida |

## Anomalías detectadas (sobre los datos de prueba)

| Tipo | Cantidad | Severidad |
|------|----------|-----------|
| ILLOGICAL_DUE_DATE | 569 | MEDIUM |
| NULL_ORDER_ID | 80 | MEDIUM |
| MIXED_CURRENCY | 65 | LOW |
| ORPHAN_PAYMENT | 52 | HIGH |
| INVALID_CLIENT_REF | 49 | HIGH |
| OVERPAYMENT | 34 | HIGH |
| SUSPICIOUS_NAME | 15 | LOW |
| **Total** | **864** | |

## Cómo extender el sistema

El sistema está diseñado para que cualquier modificación tome menos de 5 minutos.

**Agregar una nueva regla de anomalía:**
1. Escribe una función `_check_<nombre>(clients, orders, invoices, payments)` en `src/Validate/anomaly_detector.py`
2. Agrégala a la lista `CHECKS` al final del mismo archivo

**Cambiar severidad de una anomalía:**
```python
# src/Config/config.py
ANOMALY_SEVERITY = {
    "OVERPAYMENT": "MEDIUM",  # era HIGH
    ...
}
```

**Cambiar un threshold:**
```python
# src/Config/config.py
THRESHOLDS = {
    "invoice_math_tolerance": 0.05,  # tolerancia más holgada
    ...
}
```

**Agregar un nuevo KPI al dashboard:**
1. Escribe una función `_kpi_<nombre>(clients, invoices, payments)` en `src/Reports/financial_summary.py`
2. Agrégala a `KPI_FUNCTIONS`

**Agregar una nueva divisa aceptada:**
```python
# src/Config/config.py
VALID_CURRENCIES = ["MXN", "USD", "EUR", "COP", "BRL"]
```

## Supuestos

- Los montos en `financial_summary.csv` se agrupan por divisa — no se convierten entre sí. Un cliente con facturas en MXN y USD aparece en dos filas separadas.
- La validación de impuesto es de coherencia matemática (`subtotal + tax ≈ total`), no de tasa fija.
- Los estados `OVERDUE` se calculan dinámicamente: cualquier factura no pagada con `due_date` anterior a hoy se considera vencida.
- El estado `UNPAID` en invoices se normaliza a `PENDING` (inconsistencia encontrada en los datos de prueba).
- `STRIPE` se trata como método de pago válido (encontrado en los datos, no estaba en el set original).

## Decisiones técnicas

- **Patrón registro en anomaly_detector:** cada check es una función independiente en una lista `CHECKS`. Agregar una regla no requiere modificar lógica existente.
- **SQLite sobre CSV puro:** permite consultas ad-hoc y es migrable a Postgres sin cambiar el schema.
- **Streamlit como subprocess:** `app.py` no importa lógica de negocio. Llama a `main.py` y lee los outputs. El dashboard no falla si el pipeline cambia internamente.
- **config.py como única fuente de verdad:** thresholds, severidades y listas de valores válidos están en un solo lugar.

## Limitaciones conocidas

- Sin conversión de divisas: los totales globales en `financial_summary.csv` no son comparables entre monedas.
- Sin corrección automática de errores tipográficos en nombres de empresa (solo detección).
- Sin pruebas unitarias formales (pytest).
- El parseo de fechas usa `dateutil` como fallback; formatos muy inusuales pueden quedar como `NaT`.

## Mejoras futuras

- Tasa impositiva configurable por país para validación en `INVOICE_MATH_ERROR`
- Scheduler con `cron` o `APScheduler` para corridas automáticas
- Suite de tests con `pytest` y fixtures de datos sucios
- Soporte para múltiples divisas con conversión via API de tasas de cambio
- Exportación del reporte de anomalías a PDF
