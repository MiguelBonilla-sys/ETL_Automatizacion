"""Carga las 4 tablas limpias en SQLite (novaflow.db)."""
import sqlite3

import pandas as pd

from src.Config.config import DB_PATH, ensure_dirs
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def load_to_sqlite(
    clients: pd.DataFrame,
    orders: pd.DataFrame,
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
) -> None:
    ensure_dirs()
    logger.info(f"Loading all entities to SQLite → {DB_PATH}")

    # Serializar fechas a string para SQLite
    def prep(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
            df[col] = df[col].astype(str)
        return df

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        prep(clients).to_sql("clients",  conn, if_exists="replace", index=False)
        prep(orders).to_sql("orders",    conn, if_exists="replace", index=False)
        prep(invoices).to_sql("invoices", conn, if_exists="replace", index=False)
        prep(payments).to_sql("payments", conn, if_exists="replace", index=False)

    logger.info("SQLite load complete")
