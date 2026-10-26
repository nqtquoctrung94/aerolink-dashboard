"""Tableau dashboard 'Airlines Page' (one per airline, chosen from the sidebar)."""
from html import escape

import streamlit as st

import calcs
import charts
import fmt
import ui
from views.home import params

# key, BAN title, formatter, unit, bars tooltip
COLUMNS = [
    ("Passenger Traffic Metrics", [
        ("pax", "All Passengers", fmt.integer, "", "{airline}<br>No of Passengers ({month} {year})<br><b>{value}</b>"),
        ("rpk_a", "Revenue Passenger Kilometres (RPK)", fmt.billions, "km",
         "{airline}<br>RPK ({month} {year})<br><b>{value} km</b><br><i>*RPK = Passengers Carried × Distance Covered*</i>"),
        ("load_factor", "Passenger Load Factor (PLF)", fmt.pct1, "",
         "{airline}<br>Passenger Load Factor ({month} {year})<br><b>{value}</b>"
         "<br><i>*PLF = Passengers Carried / Passenger Carrying Capacity*</i>"),
    ]),
    ("Cargo Traffic Metrics", [
        ("freight_t", "Freight Tonnes", fmt.dec1, "tonnes",
         "{airline}<br>Freight Tonnes ({month} {year})<br><b>{value} tonnes</b>"),
        ("ctk", "Cargo Tonnes Kilometres (CTK)", fmt.millions, "km",
         "{airline}<br>CTK ({month} {year})<br><b>{value} km</b><br><i>*CTK = Cargo Weight Carried × Distance Covered*</i>"),
        ("clf", "Cargo Load Factor (CLF)", fmt.pct1, "",
         "{airline}<br>Cargo Load Factor ({month} {year})<br><b>{value}</b>"),
    ]),
    ("Cost & Revenue Metrics", [
        ("revenue", "Total Revenue", fmt.usd_m, "", "{airline}<br>Total Revenue ({month} {year})<br><b>{value}</b>"),
        ("op_profit", "Total Operating Profit", fmt.usd_m, "",
         "{airline}<br>Operating Profit ({month} {year})<br><b>{value}</b>"),
        ("costs", "Total Operating Cost", fmt.usd_m, "", "{airline}<br>Total Cost ({month} {year})<br><b>{value}</b>"),
    ]),
]

# Dot colours per tile (workbook colour maps). Costs: reversed (a rise is bad). Op Profit: see ui.OP_PROFIT_DOWN.
CIRCLES = {
    "costs": {"Up": ui.DOWN, "Down": ui.UP, "No": ui.NEUTRAL},
    "op_profit": {"Up": ui.UP, "Down": ui.OP_PROFIT_DOWN, "No": ui.NEUTRAL},
}


def _sum_metric(key, p, f, unit=""):
    cm, pm = calcs.value(key, "CM", p), calcs.value(key, "PM", p)
    chg, kind = calcs.mom(cm, pm)
    u = f" {unit}" if unit else ""
    return f"{escape(f(cm)) or '–'}{u} <span class='m'>{ui.mom_inline(chg, kind)}</span>"


def render():
    p = params()
    color = ui.AIRLINE_COLORS.get(p.airline, ui.BLUE)
    ui.header(p.airline, "Welcome! Follow all of AeroLink Alliance's activities dashboard from 2022 to 2025.")

    # ---- 'Airline Summary 1' + 'Airline Summary 2' (icons = workbook shapes, coloured by airline)
    with st.container(key="card_summary"):
        ui.section(f"Airline Summary — {fmt.MONTH_NAMES[p.month - 1]} {p.year}")
        r1 = st.columns(3)
        with r1[0]:
            ui.icon_item("departures", "Completed Flights", _sum_metric("comp_flights_a", p, fmt.integer), color)
        with r1[1]:
            ui.icon_item("distance", "Avg. Distance Covered", _sum_metric("distance_a", p, fmt.dec2, "km"), color)
        with r1[2]:
            ui.icon_item("clock", "On-Time Performance", _sum_metric("ontime_pct_a", p, fmt.pct1), color)
        r2 = st.columns(3)
        city, country, airport = calcs.airline_hub(p)
        route, desc = calcs.major_route(p)
        with r2[0]:
            ui.icon_item("routes", "Airline Hub", escape(f"{city}, {country} ({airport})"), color)
        with r2[1]:
            ui.icon_item("map", "Major Flight Route",
                         f"{escape(desc)} <span style='font-size:11px'>({escape(route)})</span>", color)
        with r2[2]:
            ui.icon_item("satisfaction", "Avg. CSAT Score", _sum_metric("csat_a", p, fmt.dec1), color)

    ui.legend(airline_page=True)
    cols = st.columns(3, gap="medium")
    for col, (heading, tiles) in zip(cols, COLUMNS):
        with col, st.container(key=f"card_col_{heading[:5]}"):
            ui.section(heading)
            for key, title, f, unit, tip in tiles:
                cm, pm = calcs.value(key, "CM", p), calcs.value(key, "PM", p)
                chg, kind = calcs.mom(cm, pm)
                a, b = st.columns([0.85, 1.15], gap="small")
                with a:
                    ui.ban(title, f(cm), chg, kind, unit)
                with b:
                    # 'Airline Bar Colours': the selected month takes the airline's colour
                    st.plotly_chart(
                        charts.kpi_trend(calcs.monthly(key, p), f, tip.replace("{airline}", p.airline),
                                         p.year, sel_color=color, circle_colors=CIRCLES.get(key), height=150),
                        config=charts.CONFIG, key=f"a_{key}")
