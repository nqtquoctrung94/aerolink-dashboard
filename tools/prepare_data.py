"""Build data/flights.parquet from the source CSV (or an existing Parquet).

    python tools/prepare_data.py airline_alliance_performance_2022_2025.csv

Adds the derived columns and category types the app expects (fast start-up),
then writes data/flights.parquet. Restart the app afterwards; cached results
are invalidated automatically because the file changes.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import DATA_PATH, add_derived  # noqa: E402

src = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
df = pd.read_csv(src) if src.suffix.lower() == ".csv" else pd.read_parquet(src)
df = add_derived(df)
DATA_PATH.parent.mkdir(exist_ok=True)
tmp = DATA_PATH.with_suffix(".tmp")
df.to_parquet(tmp, index=False, compression="zstd")
tmp.replace(DATA_PATH)
print(f"Wrote {DATA_PATH} ({len(df):,} rows, {DATA_PATH.stat().st_size / 1e6:.1f} MB)")
