"""Helpers de validación y limpieza reutilizables en todos los módulos Transform."""
import re
import pandas as pd
from dateutil import parser as date_parser


def parse_date_flexible(val) -> pd.Timestamp:
    """Intenta parsear una fecha con múltiples formatos. Retorna NaT en fallo."""
    if pd.isna(val):
        return pd.NaT
    try:
        return pd.to_datetime(val)
    except Exception:
        pass
    try:
        return pd.Timestamp(date_parser.parse(str(val), dayfirst=False))
    except Exception:
        return pd.NaT


def clean_amount(val) -> float | None:
    """Elimina $, comas y espacios. Retorna float o None si no es parseable."""
    if pd.isna(val):
        return None
    cleaned = re.sub(r"[$,\s]", "", str(val))
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_status(val, mapping: dict | None = None) -> str:
    """Uppercase + strip. Aplica mapping de normalización si se provee."""
    if pd.isna(val):
        return val
    upper = str(val).strip().upper()
    if mapping:
        upper = mapping.get(upper, upper)
    return upper


def is_valid_email(val) -> bool:
    if pd.isna(val):
        return False
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, str(val)))
