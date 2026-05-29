import pandas as pd
from src.Utils.data_io import write_csv
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def load_clients(df: pd.DataFrame) -> None:
    write_csv(df, "clients_clean.csv")
    logger.info(f"Loaded {len(df)} clients → clean_data/clients_clean.csv")
