import pandas as pd

from src.Ultils.data_io import read_csv


def extract_invoices() -> pd.DataFrame:
	return read_csv("invoices.csv")
