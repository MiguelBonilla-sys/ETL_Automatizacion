"""Configuracion central del proyecto ETL."""
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CLEANED_DIR = PROJECT_ROOT / "cleaned_data"


def ensure_cleaned_dir() -> None:
	CLEANED_DIR.mkdir(parents=True, exist_ok=True)