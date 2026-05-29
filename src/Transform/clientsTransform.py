import pandas as pd
from src.Config.config import VALID_STATUSES, STATUS_NORMALIZATION
from src.Utils.validators import normalize_status
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def transform_clients(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Transforming clients: {len(df)} rows")
    df = df.copy()

    df["company_name"]       = df["company_name"].str.strip()
    df["email"]              = df["email"].str.lower().str.strip()
    df["default_currency"]   = df["default_currency"].str.upper().str.strip()
    df["country"]            = df["country"].str.strip()

    mapping = STATUS_NORMALIZATION.get("clients", {})
    df["status"] = df["status"].apply(lambda x: normalize_status(x, mapping))

    before = len(df)
    df = df.drop_duplicates(subset=["client_id"])
    if len(df) < before:
        logger.warning(f"Dropped {before - len(df)} duplicate client_id rows")

    logger.info(f"Clients after transform: {len(df)} rows")
    return df
