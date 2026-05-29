import pandas as pd

from src.Ultils.data_io import read_csv


def extract_orders() -> pd.DataFrame:
    return read_csv("orders.csv")
