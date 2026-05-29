import pandas as pd

from src.Ultils.data_io import write_csv


def load_payments(df: pd.DataFrame) -> None:
    write_csv(df, "payments.csv")
