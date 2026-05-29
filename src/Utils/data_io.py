import pandas as pd
from src.Config.config import CLEAN_DIR, DATA_DIR, ensure_dirs


def read_csv(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / filename)


def write_csv(df: pd.DataFrame, filename: str) -> None:
    ensure_dirs()
    df.to_csv(CLEAN_DIR / filename, index=False)
