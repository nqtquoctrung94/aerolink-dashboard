"""AeroLink — Airline Alliance Activity Dashboard (Streamlit port of the Tableau #VOTD workbook).

Run:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="AeroLink · Airline Alliance Activity", page_icon="✈️",
                   layout="wide", initial_sidebar_state="expanded")

from data import AIRLINES, DEFAULTS, MONTHS, REGIONS, YEARS, load  # noqa: E402
from fmt import MONTH_LETTERS  # noqa: E402
import ui  # noqa: E402
from views import airlines, fleet, flights, home  # noqa: E402

ASSETS = Path(__file__).parent / "assets"
ss = st.session_state

# ---- Tableau parameters -> session state (defaults = values saved in the workbook)
for k, v in DEFAULTS.items():
    ss.setdefault(k, v)

ui.inject_css()
load()  # warm the cache

PAGES = {
    "home": st.Page(home.render, title="Home", url_path="home", default=True),
    "airlines": st.Page(airlines.render, title="Airlines", url_path="airlines"),
    "flights": st.Page(flights.render, title="Flights", url_path="flights"),
    "fleet": st.Page(fleet.render, title="Fleet", url_path="fleet"),
}
pg = st.navigation(list(PAGES.values()), position="hidden")
current = next(k for k, p in PAGES.items() if p.url_path == pg.url_path)


@st.dialog("AeroLink Airline Alliance Dashboard — User Guide", width="large")
def help_dialog():
    st.markdown((ASSETS / "guidelines.md").read_text(encoding="utf-8"))


def _set(**kw):
    for k, v in kw.items():
        ss[k] = v


def sidebar():
    with st.sidebar:
        st.image(str(ASSETS / "aerolink_logo.png"), width=150)
        st.markdown('<div class="al-side-h">NAVIGATION</div>', unsafe_allow_html=True)
        with st.container(key="nav_main"):
            if st.button("⌂  Home", key="nav_home", use_container_width=True,
                         type="primary" if current == "home" else "secondary"):
                st.switch_page(PAGES["home"])
            if st.button("✈  Airlines", key="nav_airlines_hdr", use_container_width=True):
                st.switch_page(PAGES["airlines"])
        with st.container(key="navsub"):
            for a in AIRLINES:
                label = "SkyConnect Air" if a == "SkyConnect Airways" else a
                active = current == "airlines" and ss.airline == a
                if st.button(label, key=f"nav_air_{a.split()[0].lower()}", use_container_width=True,
                             type="primary" if active else "secondary"):
                    ss.airline = a          # 'Select Airline' parameter action
                    st.switch_page(PAGES["airlines"])
        with st.container(key="nav_rest"):
            if st.button("🗺  Flights", key="nav_flights", use_container_width=True,
                         type="primary" if current == "flights" else "secondary"):
                st.switch_page(PAGES["flights"])
            if st.button("🛩  Fleet", key="nav_fleet", use_container_width=True,
                         type="primary" if current == "fleet" else "secondary"):
                st.switch_page(PAGES["fleet"])
            if st.button("ⓘ  Help", key="nav_help", use_container_width=True):
                help_dialog()

        st.markdown('<div class="al-side-h" style="margin-top:22px">VIEW SELECTIONS</div>', unsafe_allow_html=True)
        if current in ("home", "airlines"):
            st.caption("📅 Date")
            with st.container(key="pick_year"):
                cols = st.columns(4)
                for c, y in zip(cols, YEARS):
                    c.button(f"'{str(y)[2:]}", key=f"y{y}", on_click=_set, kwargs={"year": y},
                             type="primary" if ss.year == y else "secondary")
            with st.container(key="pick_month"):
                for row in range(3):
                    cols = st.columns(4)
                    for c, m in zip(cols, MONTHS[row * 4:(row + 1) * 4]):
                        c.button(MONTH_LETTERS[m - 1], key=f"m{m}", on_click=_set, kwargs={"month": m},
                                 type="primary" if ss.month == m else "secondary", help=f"Month {m}")
        if current in ("fleet", "flights"):
            ss.airline = st.selectbox("✈ Airline", AIRLINES, index=AIRLINES.index(ss.airline))
        ss.region = st.selectbox("📍 Region", REGIONS, index=REGIONS.index(ss.region))
        st.markdown('<div class="al-foot">Designed by Stephanie Anyama<br>'
                    '<span style="color:#888">Streamlit port</span></div>', unsafe_allow_html=True)


sidebar()
pg.run()
