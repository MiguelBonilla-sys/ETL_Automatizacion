import pandas as pd

from src.Config.config import OUTPUT_DIR
from src.Utils.logger import get_logger

logger = get_logger(__name__)


def generate_anomalies_report(anomalies: pd.DataFrame) -> None:
    out_path = OUTPUT_DIR / "anomalies_report.csv"
    anomalies.to_csv(out_path, index=False)
    summary = anomalies["severity"].value_counts().to_dict()
    logger.info(f"anomalies_report.csv saved → {out_path} | {summary}")
