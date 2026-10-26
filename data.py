"""Data layer.

Replaces the Tableau extract `airline_alliance_performance_2022_2025_1` (Hyper)
with a local Parquet file. The workbook had a second, identical extract
(`airline_alliance_performance_2022_2025`) that no worksheet used; it was
verified row-for-row identical and dropped.

Column names are the raw CSV/Hyper names (snake_case). Tableau captions are
the Title Case versions (e.g. `origin_region` -> "Origin Region").

Performance:
  B  text columns stay `category` and derived columns are stored in the Parquet
     (built by tools/prepare_data.py), so start-up is just a file read.
  A  `by_month()` / `by_year()` hand calcs a pre-split slice instead of the whole table.
  C  calc results are cached on disk (see calcs.py); `version()` is part of every cache key,
     so replacing the data file automatically invalidates old results.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "flights.parquet"

# Parameter domains, copied from the workbook's Parameters datasource.
YEARS = [2022, 2023, 2024, 2025]
MONTHS = list(range(1, 13))
REGIONS = ["Global", "Africa", "Asia", "Europe", "Middle East",
           "North America", "Oceania", "South America"]
AIRLINES = ["Atlantic Express", "Global Star", "Pacific Wings", "SkyConnect Airways"]
AIRCRAFT = ["A320", "A330", "A350", "B737", "B777", "B787"]

# Parameter defaults as saved in the workbook.
DEFAULTS = {
    "year": 2023,
    "month": 7,
    "region": "North America",
    "airline": "SkyConnect Airways",
    "aircraft": "A330",
    "flight_id": "SC1358",
}

DERIVED = ["year", "month", "weekday", "rpk", "cargo_km", "route_description"]


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Row-level expressions reused by several calcs (also used by tools/prepare_data.py)."""
    df["date"] = pd.to_datetime(df["date"])
    # Tableau derives YEAR()/MONTH() from [date]; re-derive to stay faithful to the formulas.
    df["year"] = df["date"].dt.year.astype("int16")
    df["month"] = df["date"].dt.month.astype("int8")
    # Sunday-first weekday index, matching Tableau's default (US) week start.
    df["weekday"] = ((df["date"].dt.dayofweek + 1) % 7).astype("int8")
    df["rpk"] = df["passengers_carried"] * df["distance_km"]           # [Passengers Carried] * [Distance Km]
    df["cargo_km"] = df["cargo_carried_kg"] * df["distance_km"]        # [Cargo Carried Kg] * [Distance Km]
    df["route_description"] = (df["origin_city"].astype(str) + ", " + df["origin_country"].astype(str) + " - "
                               + df["destination_city"].astype(str) + ", " + df["destination_country"].astype(str))
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype("category")
    return df


def version() -> float:
    """Changes whenever the data file is replaced -> part of every cache key."""
    return DATA_PATH.stat().st_mtime


@st.cache_resource(show_spinner="Loading flight data…")
def _load(v: float) -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    if any(c not in df.columns for c in DERIVED):     # plain CSV-shaped file: derive on the fly
        df = add_derived(df)
    return df


def load() -> pd.DataFrame:
    return _load(version())


@st.cache_resource(show_spinner=False)
def _split(v: float):
    df = _load(v)
    months = {k: g for k, g in df.groupby(["year", "month"], sort=False)}
    years = {k: g for k, g in df.groupby("year", sort=False)}
    return months, years


def by_month(year: int, month: int) -> pd.DataFrame:
    months, _ = _split(version())
    return months.get((year, month), load().iloc[0:0])


def by_year(year: int) -> pd.DataFrame:
    _, years = _split(version())
    return years.get(year, load().iloc[0:0])
