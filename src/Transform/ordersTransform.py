import pandas as pd
from src.Config.config import STATUS_NORMALIZATION
from src.Utils.validators import normalize_status, clean_amount, parse_date_flexible
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def transform_orders(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Transforming orders: {len(df)} rows")
    df = df.copy()

    df["order_date"] = df["order_date"].apply(parse_date_flexible)
    invalid_dates = df["order_date"].isna().sum()
    if invalid_dates:
        logger.warning(f"{invalid_dates} orders with unparseable order_date")

    df["amount"] = df["amount"].apply(clean_amount)

    mapping = STATUS_NORMALIZATION.get("orders", {})
    df["status"] = df["status"].apply(lambda x: normalize_status(x, mapping))

    before = len(df)
    df = df.drop_duplicates(subset=["order_id"])
    if len(df) < before:
        logger.warning(f"Dropped {before - len(df)} duplicate order_id rows")

    logger.info(f"Orders after transform: {len(df)} rows")
    return df
