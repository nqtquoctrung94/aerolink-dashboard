"""Tableau dashboard 'Flight Page': Recent Flights list -> Flight Map."""
from html import escape

import streamlit as st

import calcs
import charts
import ui
from views.home import params

MAP_STYLES = {"Minimal map": "minimal", "Satellite view": "satellite"}


def _route_line(r, style):
    """Origin → destination above the map, with dots in the map's colours (city names live here because
    text drawn on the map needs an online font)."""
    o, d = (("#ffffff", charts.ROUTE_DEST) if style == "satellite" else (ui.TEXT, ui.BLUE))
    edge = "box-shadow:0 0 0 1px #9aa0a8;" if style == "satellite" else ""
    dot = "<span class='dot' style='background:{};{}'></span>"
    return (f"<div class='route-line'>{dot.format(o, edge)}{escape(r.origin_city)}, {escape(r.origin_country)} "
            f"<b>({escape(r.origin_airport)})</b><span class='arr'>→</span>{dot.format(d, edge)}"
            f"{escape(r.destination_city)}, {escape(r.destination_country)} <b>({escape(r.destination_airport)})</b></div>")


def _select(fid):
    st.session_state.flight_id = fid     # 'Select Flight' parameter action -> Flight Id Set Parameter


def render():
    ss = st.session_state
    ss.setdefault("map_style", "Minimal map")
    p = params()
    ui.header("Flights", "Select any of the alliance's most recent flights to view the route details.")
    rf = calcs.recent_flights(p)
    selected = calcs.default_flight(rf, ss.flight_id)       # 'Default Flight' fallback
    left, right = st.columns([1, 1.9], gap="medium")

    with left, st.container(key="card_flist", height=640):
        ui.section(f"Recent Flights — {p.airline}")
        if rf.empty:
            st.caption("No completed flights for this selection.")
        # Each flight is a timeline card; an invisible button over the card selects it.
        for i, r in enumerate(rf.itertuples()):
            with st.container(key=f"fltcard_{i}"):
                st.markdown(ui.flight_card_html(r, r.flight_id == selected), unsafe_allow_html=True)
                st.button(f"Select {r.flight_id}", key=f"fltbtn_{i}", on_click=_select, args=(r.flight_id,))

    with right, st.container(key="card_map", height=640):
        choice = st.segmented_control("Map style", list(MAP_STYLES), key="map_style",
                                      label_visibility="collapsed")
        style = MAP_STYLES.get(choice or "Minimal map")
        if style == "satellite":
            st.caption("Satellite imagery (Esri) needs internet; the minimal map works offline.")
        sel = rf[rf["flight_id"] == selected]
        if not sel.empty:
            st.markdown(_route_line(sel.iloc[0], style), unsafe_allow_html=True)
        # The satellite note and the route line take ~50px / ~40px; shrink the map so the card doesn't scroll.
        st.plotly_chart(charts.flight_map(rf, selected, height=455 if style == "satellite" else 520, style=style),
                        config=charts.MAP_CONFIG, key=f"map_{style}")
