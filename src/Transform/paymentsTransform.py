import pandas as pd
from src.Utils.validators import clean_amount, parse_date_flexible
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def transform_payments(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Transforming payments: {len(df)} rows")
    df = df.copy()

    df["payment_date"] = df["payment_date"].apply(parse_date_flexible)
    df["amount"]       = df["amount"].apply(clean_amount)
    df["method"]       = df["method"].str.upper().str.strip()

    before = len(df)
    df = df.drop_duplicates(subset=["payment_id"])
    if len(df) < before:
        logger.warning(f"Dropped {before - len(df)} duplicate payment_id rows")

    logger.info(f"Payments after transform: {len(df)} rows")
    return df
