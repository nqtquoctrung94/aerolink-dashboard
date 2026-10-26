"""Tableau dashboard 'Alliance Page' (Home)."""
import streamlit as st

import calcs
import charts
import fmt
import ui
from data import AIRCRAFT, AIRLINES


def params() -> calcs.Params:
    return calcs.params_from_state(st.session_state)


# key, BAN title, formatter, unit, bars tooltip, airline-compare tooltip
TILES = [
    ("comp_flights", "Completed Flights", fmt.integer, "",
     "All member airlines of Aerolink Alliance completed<br>{value} flights in {month} {year}.",
     "{airline} completed {value} flights"),
    ("ontime_pct", "On-Time Performance", fmt.pct1, "",
     "All member airlines of Aerolink Alliance recorded<br>an on-time performance of {value} in {month} {year}.",
     "{airline} recorded {value} On-Time Performance"),
    ("rpk", "Revenue Passenger Kilometres (RPK)", fmt.billions, "km",
     "All member airlines of Aerolink Alliance completed<br>{value} km in revenue passenger kilometres (RPK)"
     "<br>in {month} {year}.<br><i>*RPK = Passengers Carried × Distance Covered*</i>",
     "{airline} completed {value} km<br>in revenue passenger kilometres (RPK)"),
    ("csat", "Avg. Satisfaction Score", fmt.dec1, "",
     "All member airlines of Aerolink Alliance recorded an<br>average customer satisfaction score of {value}"
     "<br>in {month} {year}.",
     "{airline} recorded an average<br>customer satisfaction score of {value}"),
]


def kpi_tile(key, title, f, unit, bars_tip, air_tip, p, month_lbl):
    cm, pm = calcs.value(key, "CM", p), calcs.value(key, "PM", p)
    chg, kind = calcs.mom(cm, pm)
    c1, c2, c3 = st.columns([0.78, 1.05, 1.25], gap="small")
    with c1:
        ui.ban(title, f(cm), chg, kind, unit)
    with c2:
        st.plotly_chart(charts.kpi_trend(calcs.monthly(key, p), f, bars_tip, p.year, height=150),
                        config=charts.CONFIG, key=f"trend_{key}")
    with c3:
        st.plotly_chart(charts.airline_compare(calcs.by(key, "CM", p, "airline_name"),
                                               calcs.by(key, "PM", p, "airline_name"), f,
                                               air_tip + f"<br>in {month_lbl}.", height=150, airlines=AIRLINES),
                        config=charts.CONFIG, key=f"air_{key}")


def render():
    p = params()
    month_lbl = f"{fmt.MONTH_NAMES[p.month - 1]} {p.year}"
    ui.header(None, "Welcome! Follow all of AeroLink Alliance's activities dashboard from 2022 to 2025.")
    ui.legend()

    # Row by row, so each KPI tile lines up with its right-hand card (same order as the workbook).
    for i, tile in enumerate(TILES):
        left, right = st.columns([1.29, 1], gap="medium")
        with left, st.container(key=f"card_home_kpi_{i}"):
            kpi_tile(*tile, p, month_lbl)
        with right, st.container(key=f"card_home_r{i}"):
            if i == 0:
                ui.section(f"Top Flight Destinations - {p.region}")
                td = calcs.top_destinations(p)
                if td.empty:
                    st.caption("No completed flights for this selection.")
                else:
                    st.plotly_chart(charts.top_destinations(td, month_lbl, n=6, height=150),
                                    config=charts.CONFIG, key="dest")
            elif i == 1:
                ui.section("Major Flight Times")
                st.plotly_chart(charts.flight_times(calcs.flight_times(p), p.year, height=155),
                                config=charts.CONFIG, key="times")
            elif i == 2:
                ui.section("Aircraft Utilization")
                h1, h2 = st.columns(2, gap="small")
                h1.markdown(f"<div style='font-size:12px;color:#444;text-align:center'>By <b style='color:{ui.BLUE}'>"
                            f"Completed Flights</b> <span style='font-size:10px'>(vs PM)</span></div>",
                            unsafe_allow_html=True)
                h2.markdown(f"<div style='font-size:12px;color:#444;text-align:center'>By <b style='color:{ui.PURPLE}'>"
                            f"Avg. Load Factor</b> <span style='font-size:10px'>(vs PM)</span></div>",
                            unsafe_allow_html=True)
                st.plotly_chart(charts.aircraft_utilization(
                    calcs.by("comp_flights", "CM", p, "aircraft_type").reindex(AIRCRAFT),
                    calcs.by("comp_flights", "PM", p, "aircraft_type").reindex(AIRCRAFT),
                    calcs.by("load_factor", "CM", p, "aircraft_type").reindex(AIRCRAFT),
                    calcs.by("pax_alliance", "PM", p, "aircraft_type").reindex(AIRCRAFT),
                    p.airline, fmt.integer, fmt.pct1, height=140), config=charts.CONFIG, key="util")
            else:
                a, b = st.columns([0.95, 1.4], gap="small")
                with a:
                    ui.section("Flights with Baggage Mishandling")
                    pct = calcs.value("mishandled_pct", "CM", p)
                    st.plotly_chart(charts.mishandling_donut(calcs.mishandling_split(p), fmt.pct1(pct), size=112),
                                    config=charts.CONFIG, key="donut", width="content")
                with b:
                    st.plotly_chart(charts.airline_compare(
                        calcs.by("mishandled_pct", "CM", p, "airline_name"),
                        calcs.by("mishandled_pct", "PM", p, "airline_name"), fmt.pct1,
                        "{value} of {airline}'s flights had at least<br>1 piece of mishandled baggage in "
                        + month_lbl + ".", height=160, airlines=AIRLINES), config=charts.CONFIG, key="bag")
