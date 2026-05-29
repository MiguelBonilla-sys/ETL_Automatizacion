import pandas as pd

from src.Config.config import CLEANED_DIR, DATA_DIR, ensure_cleaned_dir


def read_csv(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / filename)


def write_csv(df: pd.DataFrame, filename: str) -> None:
    ensure_cleaned_dir()
    df.to_csv(CLEANED_DIR / filename, index=False)
