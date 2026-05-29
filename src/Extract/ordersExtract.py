import pandas as pd
from src.Config.config import DATA_DIR, EXPECTED_COLUMNS
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def extract_orders() -> pd.DataFrame:
    path = DATA_DIR / "orders.csv"
    logger.info(f"Extracting orders from {path}")
    df = pd.read_csv(path)
    _validate_schema(df, "orders")
    logger.info(f"Extracted {len(df)} rows | nulls: {df.isnull().sum()[df.isnull().sum() > 0].to_dict()}")
    return df


def _validate_schema(df: pd.DataFrame, entity: str) -> None:
    missing = set(EXPECTED_COLUMNS[entity]) - set(df.columns)
    if missing:
        raise ValueError(f"{entity}.csv missing columns: {missing}")
