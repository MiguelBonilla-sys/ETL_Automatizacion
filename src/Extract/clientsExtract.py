import pandas as pd

from src.Ultils.data_io import read_csv


def extract_clients() -> pd.DataFrame:
	return read_csv("clients.csv")
