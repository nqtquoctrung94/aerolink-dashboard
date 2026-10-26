"""Tableau calculated fields, reproduced in pandas.

The workbook has ~460 calculated fields, but almost all follow one template:

    AGG( IF <period test> AND <region test> [AND <airline test>] [AND completed=1] [AND …]
         THEN <expression> END )

with the period being one of
    CM  DATETRUNC('month',[Date]) = [Date From Params]                 (current month)
    PM  DATETRUNC('month',[Date]) = DATEADD('month',-1,[Date From Params])  (previous month)
    CY  YEAR([Date]) = [Year Parameter]                                (current year)
    PY  YEAR([Date]) = [Year Parameter] - 1                            (prior year)
where [Date From Params] = MAKEDATE([Year Parameter],[Month Parameter],1)
and the region test is
    ([Origin Region] = [Region Parameter] OR [Region Parameter] = 'Global').

So each family (e.g. CM RPK / PM RPK / CY RPK / PY RPK / Pos MoM RPK / …) is one
entry in METRICS below, evaluated for a period. Original formulas are kept in
each entry's `tableau` string so every number is traceable.

Aggregation semantics reproduced exactly:
  * COUNTD(IF … THEN [Flight Id] END)  -> number of DISTINCT flight numbers (not rows!)
  * COUNT(IF … THEN [Flight Id] END)   -> number of matching rows
  * SUM/AVG over no rows               -> null (shown blank)
  * COUNT/COUNTD over no rows          -> 0
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd
import streamlit as st

import data
from data import load

# The original "Costs Circle Col" compares CY vs PY *Operating Profit*, not Costs
# (likely a copy/paste slip in the workbook). Kept for parity; set True to compare Costs.
FIX_COST_CIRCLES = False

# Disk-persisted cache: results survive restarts; data.version() is in
# every key (via Params.v), so replacing the data file invalidates them automatically.
cache = st.cache_data(show_spinner=False, persist="disk")


@dataclass(frozen=True)
class Metric:
    agg: str                      # 'sum' | 'avg' | 'countd' | 'count'
    col: str                      # column THEN-ed into the aggregate
    airline: bool = False         # adds [Airline Name] = [Airline Name Parameter]
    completed: bool = False       # adds [Completed Flights] = 1
    extra: Optional[Callable[[pd.DataFrame], pd.Series]] = None   # any other row test
    scale: float = 1.0            # e.g. /1000 for tonnes
    tableau: str = ""             # original CM formula, for traceability


METRICS: dict[str, Metric] = {
    # ---------------- Alliance (Home) page: NOT filtered by airline ----------------
    "comp_flights": Metric("countd", "flight_id", completed=True,
        tableau="COUNTD(IF CM AND region AND [Completed Flights]=1 THEN [Flight Id] END)  -- 'CM No of Comp Flights'"),
    "all_flights": Metric("countd", "flight_id",
        tableau="COUNTD(IF CM AND region THEN [Flight Id] END)  -- 'CM All Flights'"),
    "ontime_count": Metric("countd", "flight_id", extra=lambda d: d["on_time_performance"] == 1,
        tableau="COUNTD(IF CM AND region AND [On Time Performance]=1 THEN [Flight Id] END)  -- 'CM Count On-Time Perf'"),
    "rpk": Metric("sum", "rpk", completed=True,
        tableau="SUM(IF CM AND region AND [Completed Flights]=1 THEN [Passengers Carried]*[Distance Km] END)  -- 'CM RPK'"),
    "csat": Metric("avg", "customer_satisfaction_score",
        tableau="AVG(IF CM AND region THEN [Customer Satisfaction Score] END)  -- 'CM Avg. CSAT'"),
    "mishandled_count": Metric("countd", "flight_id", completed=True,
        extra=lambda d: d["mishandled_baggage"] >= 1,
        tableau="COUNTD(IF CM AND region AND [Completed Flights]=1 AND [Mishandled Baggage]>=1 THEN [Flight Id] END)"),
    # NB: 'CM Load Factor' IS filtered by the airline parameter in the workbook, even though
    # it is shown on the alliance-wide 'Aircraft Utilization' chart. Kept for parity.
    "load_factor": Metric("avg", "load_factor", airline=True, completed=True,
        tableau="AVG(IF CM AND region AND [Airline Name]=[Airline Name Parameter] AND [Completed Flights]=1 THEN [Load Factor] END)  -- 'CM Load Factor'"),

    # 4th measure on 'Aircraft Utilization' (drawn as the tick on the load-factor panel, own axis)
    "pax_alliance": Metric("sum", "passengers_carried", completed=True,
        tableau="SUM(IF PM AND region AND [Completed Flights]=1 THEN [Passengers Carried] END)  -- 'PM No of Passengers'"),

    # ---------------- Airlines page: filtered by selected airline ----------------
    "pax": Metric("sum", "passengers_carried", airline=True, completed=True,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Passengers Carried] END)  -- 'CM Passenger Count'"),
    "rpk_a": Metric("sum", "rpk", airline=True, completed=True,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Passengers Carried]*[Distance Km] END)  -- 'CM RPK (A)'"),
    "freight_t": Metric("sum", "cargo_carried_kg", airline=True, completed=True, scale=1 / 1000,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Cargo Carried Kg] END)/1000  -- 'CM Freight Tonnes'"),
    "ctk": Metric("sum", "cargo_km", airline=True, completed=True, scale=1 / 1000,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Cargo Carried Kg]*[Distance Km] END)/1000  -- 'CM CTK'"),
    "clf": Metric("avg", "cargo_load_factor", airline=True, completed=True,
        tableau="AVG(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Cargo Load Factor] END)  -- 'CM Cargo Load Factor'"),
    "revenue": Metric("sum", "total_revenue_usd", airline=True, completed=True,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Total Revenue Usd] END)  -- 'CM Total Revenue'"),
    "op_profit": Metric("sum", "operating_profit_usd", airline=True, completed=True,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Operating Profit Usd] END)  -- 'CM Op Profit'"),
    "costs": Metric("sum", "total_costs_usd", airline=True, completed=True,
        tableau="SUM(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Total Costs Usd] END)  -- 'CM Costs'"),
    # Airline summary band ("(A)" fields) — note COUNT (rows), not COUNTD.
    "comp_flights_a": Metric("count", "flight_id", airline=True, completed=True,
        tableau="COUNT(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Flight Id] END)  -- 'CM Completed Flights (A)'"),
    "all_flights_a": Metric("count", "flight_id", airline=True,
        tableau="COUNT(IF CM AND region AND airline THEN [Flight Id] END)  -- 'CM All Flights (A)'"),
    "ontime_count_a": Metric("count", "flight_id", airline=True, extra=lambda d: d["on_time_performance"] == 1,
        tableau="COUNT(IF CM AND region AND airline AND [On Time Performance]=1 THEN [Flight Id] END)  -- 'CM On Time Count (A)'"),
    "distance_a": Metric("avg", "distance_km", airline=True, completed=True,
        tableau="AVG(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Distance Km] END)  -- 'CM Distance (A)'"),
    "csat_a": Metric("avg", "customer_satisfaction_score", airline=True, completed=True,
        tableau="AVG(IF CM AND region AND airline AND [Completed Flights]=1 THEN [Customer Satisfaction Score] END)  -- 'CM CSAT (A)'"),
}

# Ratio calcs: numerator / denominator, both metrics above.
RATIOS = {
    "ontime_pct": ("ontime_count", "all_flights"),        # [CM Count On-Time Perf]/[CM All Flights]
    "mishandled_pct": ("mishandled_count", "comp_flights"),  # [CM No of Mishandled Baggage]/[CM No of Comp Flights]
    "ontime_pct_a": ("ontime_count_a", "all_flights_a"),  # [CM On Time Count (A)]/[CM All Flights (A)]
}


@dataclass(frozen=True)
class Params:
    year: int
    month: int
    region: str
    airline: str
    aircraft: str = "A330"
    v: float = 0.0          # data version (file mtime) -> part of every cache key


def params_from_state(ss) -> Params:
    return Params(ss.year, ss.month, ss.region, ss.airline, ss.aircraft, data.version())


def prev_month(year: int, month: int) -> tuple[int, int]:
    """DATEADD('month', -1, [Date From Params])."""
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _period_frame(period, p: Params) -> pd.DataFrame:
    """The period test, applied by picking the pre-split slice."""
    if period == "CM":
        return data.by_month(p.year, p.month)
    if period == "PM":
        return data.by_month(*prev_month(p.year, p.month))
    if period == "CY":
        return data.by_year(p.year)
    if period == "PY":
        return data.by_year(p.year - 1)
    if period == "ALL":          # "(F)" fleet fields have no date test
        return load()
    raise ValueError(period)


def _region_mask(df, region):
    if region == "Global":
        return pd.Series(True, index=df.index)
    return df["origin_region"] == region


def _row_mask(df, m: Metric, p: Params, aircraft: bool = False):
    mask = _region_mask(df, p.region)
    if m.airline:
        mask &= df["airline_name"] == p.airline
    if m.completed:
        mask &= df["completed_flights"] == 1
    if m.extra is not None:
        mask &= m.extra(df)
    if aircraft:
        mask &= df["aircraft_type"] == p.aircraft
    return mask


def _str_index(out):
    if isinstance(out, pd.Series) and isinstance(out.index.dtype, pd.CategoricalDtype):
        out.index = out.index.astype(str)
    return out


def _aggregate(sub: pd.DataFrame, m: Metric, by):
    s = sub if by is None else sub.groupby(by, observed=True)
    col = s[m.col]
    if m.agg == "sum":
        out = col.sum(min_count=1)
    elif m.agg == "avg":
        out = col.mean()
    elif m.agg == "countd":
        out = col.nunique()
    elif m.agg == "count":
        out = col.count()
    else:
        raise ValueError(m.agg)
    out = out * m.scale if m.scale != 1 else out
    return _str_index(out)


def _compute(key, period, p: Params, by=None, aircraft=False):
    if key in RATIOS:
        num, den = RATIOS[key]
        a = _compute(num, period, p, by, aircraft)
        b = _compute(den, period, p, by, aircraft)
        if by is None:
            return np.nan if not b else a / b
        return (a / b.replace(0, np.nan)).astype(float)
    m = METRICS[key]
    df = _period_frame(period, p)
    sub = df.loc[_row_mask(df, m, p, aircraft)]
    return _aggregate(sub, m, by)


@cache
def value(key: str, period: str, p: Params, aircraft: bool = False) -> float:
    """Scalar, e.g. value('rpk','CM',p) == [CM RPK]."""
    v = _compute(key, period, p, None, aircraft)
    return float(v) if v is not None and not pd.isna(v) else np.nan


@cache
def by(key: str, period: str, p: Params, dim: str) -> pd.Series:
    """Metric partitioned by a dimension on the view (e.g. airline rows, month columns)."""
    return _compute(key, period, p, dim)


# ---------------------------------------------------------------- KPI tile pieces
def mom(cm: float, pm: float) -> tuple[Optional[float], str]:
    """Pos/Neg/Neut MoM <X>:  IF CM>PM THEN CM/PM-1 END (and < / = variants).
    Returns (change, 'pos'|'neg'|'neut'|'none')."""
    if pd.isna(cm) or pd.isna(pm) or pm == 0:
        return None, "none"
    chg = cm / pm - 1
    return chg, "pos" if cm > pm else "neg" if cm < pm else "neut"


def monthly(key: str, p: Params) -> pd.DataFrame:
    """Data behind the '<X> Bars' + '<X> Circles' sheets.

    Bars:    CY <X> with MONTH([Date]) on columns -> value for each month of the selected year.
    Colour:  'Bar Colours' = DATETRUNC('month',[Date]) = [Date From Params] -> 'Selected Month'.
    Circles: '<X> Circle Col' = IF CY>PY THEN 'Up' ELSEIF CY<PY THEN 'Down' ELSE 'No' END, per month.
    """
    cy = by(key, "CY", p, "month").reindex(range(1, 13))
    py = by(key, "PY", p, "month").reindex(range(1, 13))
    if key == "costs" and not FIX_COST_CIRCLES:
        # parity with workbook's 'Costs Circle Col' (compares Op Profit; colours reversed in the view)
        cy_c = by("op_profit", "CY", p, "month").reindex(range(1, 13))
        py_c = by("op_profit", "PY", p, "month").reindex(range(1, 13))
    else:
        cy_c, py_c = cy, py
    # Tableau comparisons with NULL are false -> 'No'
    status = np.where(cy_c > py_c, "Up", np.where(cy_c < py_c, "Down", "No"))
    return pd.DataFrame({"month": range(1, 13), "cy": cy.values, "py": py.values,
                         "status": status, "selected": [m == p.month for m in range(1, 13)]})


def _completed_in_region(df, p: Params):
    return df.loc[_region_mask(df, p.region) & (df["completed_flights"] == 1)]


# ---------------------------------------------------------------- one-off sheets
@cache
def top_destinations(p: Params) -> pd.DataFrame:
    """'Top Destinations': rows = CM Main Destinations, cols = CM No of Comp Flights.

    CM Main Destinations = IF CM AND ([Destination Region]=param OR param='Global') THEN [Destination City] END
    (null rows filtered out). Combined with the measure's own origin-region test, both apply.
    """
    sub = _completed_in_region(_period_frame("CM", p), p)
    if p.region != "Global":
        sub = sub[sub["destination_region"] == p.region]
    g = sub.groupby("destination_city", observed=True).agg(
        flights=("flight_id", "nunique"),
        country=("destination_country", lambda s: str(s.iloc[0]) if s.nunique() == 1 else "*"))
    g.index = g.index.astype(str)
    return g.sort_values(["flights"], ascending=False).reset_index()


@cache
def flight_times(p: Params) -> pd.DataFrame:
    """'Main Flight Times': weekday x month heat-map of CY All Flights (COUNTD per cell)."""
    df = _period_frame("CY", p)
    g = df.loc[_region_mask(df, p.region)].groupby(["weekday", "month"])["flight_id"].nunique()
    return g.unstack("month").reindex(index=range(7), columns=range(1, 13))


@cache
def mishandling_split(p: Params) -> pd.Series:
    """'Mishandling' donut: COUNT rows by [Mishandled Baggage Groups] (CM, region, completed)."""
    sub = _completed_in_region(_period_frame("CM", p), p)
    grp = np.where(sub["mishandled_baggage"] == 0, "No Mishandling", "Mishandling")
    return pd.Series(grp).value_counts().reindex(["Mishandling", "No Mishandling"]).fillna(0)


def _airline_cm_completed(p: Params):
    df = _period_frame("CM", p)
    return df.loc[_row_mask(df, METRICS["comp_flights_a"], p)]


@cache
def airline_hub(p: Params) -> tuple[str, str, str]:
    """ATTR(CM Hub City/Country/Airport (A)) — '*' if more than one value."""
    sub = _airline_cm_completed(p)
    def attr(c):
        u = sub[c].dropna().unique()
        return str(u[0]) if len(u) == 1 else ("*" if len(u) else "—")
    return attr("hub_city"), attr("hub_country"), attr("hub_airport")


@cache
def major_route(p: Params) -> tuple[str, str]:
    """'Major Flight Route' — Design choice: the route the selected airline flew most in the
    selected month/region (COUNT of completed flights; ties -> alphabetical).

    The workbook's formula `IF [CM Completed Flights (A)] = WINDOW_MAX(...) THEN MAX([Route]) END` sits on a
    sheet with no Route dimension and no filters, so Tableau evaluates MAX([Route]) over the whole dataset and
    always shows ZUR-NRT. We intentionally do not copy that bug."""
    g = _airline_cm_completed(p).groupby(["route", "route_description"], observed=True)["flight_id"].count()
    if g.empty:
        return "—", "—"
    top = g[g == g.max()].sort_index().index[0]
    return str(top[0]), str(top[1])


# ---------------------------------------------------------------- Fleet page ("(F)" fields: no date test)
@cache
def fleet_cards(p: Params) -> pd.DataFrame:
    """A320…B787 cards: Comp Flights (F) = COUNT(rows) and All Passengers (F) = SUM(pax),
    region + airline + completed, all dates."""
    df = load()
    sub = _completed_in_region(df, p)
    sub = sub[sub["airline_name"] == p.airline]
    g = sub.groupby("aircraft_type", observed=True).agg(flights=("flight_id", "count"),
                                                         passengers=("passengers_carried", "sum"))
    g.index = g.index.astype(str)
    return g


@cache
def fleet_selected(p: Params) -> dict:
    """'Aircraft Summary 1–3' for [Aircraft Type Parameter]."""
    s = _selected_flights(load(), p, aircraft=True)
    return {
        "flights": int(s["flight_id"].count()),                       # Selected Comp Flights (F)
        "passengers": s["passengers_carried"].sum(min_count=1),       # Selected All Passengers (F)
        "distance": s["distance_km"].mean(),                          # Selected Distance (F)
        "load_factor": s["load_factor"].mean(),                       # Selected Load Factor (F)
        "emissions": s["co2_emissions_kg"].mean(),                    # Selected Emissions (F)
        "fuel_costs": s["fuel_cost_usd"].sum(min_count=1),            # Selected Fuel Costs (F)
    }


def _selected_flights(df, p: Params, aircraft=False):
    """[Selected Flight ID] etc. = IF region AND completed AND airline THEN … END (non-null rows)."""
    m = _region_mask(df, p.region) & (df["completed_flights"] == 1) & (df["airline_name"] == p.airline)
    if aircraft:
        m &= df["aircraft_type"] == p.aircraft
    return df.loc[m]


def _top_n_by_latest(sub, level, n):
    """Tableau Top-N set: members of `level` ordered by MAX([date]) DESC, first n (ties: by name)."""
    last = sub.groupby(level, observed=True)["date"].max().rename("_last").reset_index()
    last[level] = last[level].astype(str) if level != "date" else last[level]
    last = last.sort_values(["_last", level], ascending=[False, True])
    return set(last[level].head(n))


def _plain(df: pd.DataFrame) -> pd.DataFrame:
    """Small result frames: categories -> str so views can concatenate text freely."""
    df = df.copy()
    for c in df.columns:
        if isinstance(df[c].dtype, pd.CategoricalDtype):
            df[c] = df[c].astype(str)
    return df.reset_index(drop=True)


@cache
def recent_flights(p: Params, n: int = 9) -> pd.DataFrame:
    """'Recent Flights' (Flights page): rows Selected Flight ID x Selected Flight Date,
    filtered to the top-9 'Selected Flight ID Set' and top-9 'Selected Flight Date Set' (by latest date)."""
    s = _selected_flights(load(), p)
    ids = _top_n_by_latest(s, "flight_id", n)
    dates = _top_n_by_latest(s, "date", n)
    r = s[s["flight_id"].astype(str).isin(ids) & s["date"].isin(dates)]
    return _plain(r).sort_values(["date", "flight_id"], ascending=[False, True]).reset_index(drop=True)


@cache
def recent_aircraft_flights(p: Params, n: int = 10) -> pd.DataFrame:
    """'Sel Aircraft Flights' (Fleet page): most recent completed flights of the selected aircraft.
    The workbook used a 'Selected Flight ID (F) Set' (top 10 by latest date) plus a hand-picked month
    exclusion filter; we keep the top-10-latest intent."""
    s = _plain(_selected_flights(load(), p, aircraft=True))
    return s.sort_values(["date", "flight_id"], ascending=[False, True]).head(n).reset_index(drop=True)


def default_flight(flights: pd.DataFrame, param_flight: Optional[str]) -> Optional[str]:
    """Default Flight = IF ISNULL(param) OR param not in view THEN MIN([Selected Flight ID]) ELSE param END."""
    if flights.empty:
        return None
    if param_flight and (flights["flight_id"] == param_flight).any():
        return param_flight
    return min(flights["flight_id"])
