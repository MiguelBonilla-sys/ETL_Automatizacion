import pandas as pd
from src.Utils.data_io import write_csv
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def load_payments(df: pd.DataFrame) -> None:
    write_csv(df, "payments_clean.csv")
    logger.info(f"Loaded {len(df)} payments → clean_data/payments_clean.csv")
