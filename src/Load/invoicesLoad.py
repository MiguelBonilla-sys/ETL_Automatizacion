import pandas as pd

from src.Ultils.data_io import write_csv


def load_invoices(df: pd.DataFrame) -> None:
    write_csv(df, "invoices.csv")
