import pandas as pd
from config.visit_list_params import OUTPUT_PATH, OUTPUT_FORMAT, FILE_NAME
from pathlib import Path
from datetime import datetime

def load(
    df: pd.DataFrame,
    date: datetime
    ) -> Path:
    """Write df to output_dir."""
    
    fmt = OUTPUT_FORMAT
    if fmt not in {"csv"}:
        raise ValueError(f"Unsupported output format '{fmt}'. Use 'csv'")

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    filename = f"{date.strftime('%Y%m%d')}_{FILE_NAME}.{fmt}"
    out_path  = OUTPUT_PATH / date.strftime("%Y-%m") / filename

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")
    return out_path
