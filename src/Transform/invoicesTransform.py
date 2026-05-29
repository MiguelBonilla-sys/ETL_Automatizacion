import pandas as pd
from src.Config.config import STATUS_NORMALIZATION
from src.Utils.validators import normalize_status, clean_amount, parse_date_flexible
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def transform_invoices(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Transforming invoices: {len(df)} rows")
    df = df.copy()

    df["issue_date"] = df["issue_date"].apply(parse_date_flexible)
    df["due_date"]   = df["due_date"].apply(parse_date_flexible)

    for col in ["subtotal", "tax", "total"]:
        df[col] = df[col].apply(clean_amount)

    df["currency"] = df["currency"].str.upper().str.strip()

    # UNPAID → PENDING (STATUS_NORMALIZATION["invoices"])
    mapping = STATUS_NORMALIZATION.get("invoices", {})
    df["status"] = df["status"].apply(lambda x: normalize_status(x, mapping))

    before = len(df)
    df = df.drop_duplicates(subset=["invoice_id"])
    if len(df) < before:
        logger.warning(f"Dropped {before - len(df)} duplicate invoice_id rows")

    logger.info(f"Invoices after transform: {len(df)} rows")
    return df
