"""Tableau dashboard 'Fleet Page'."""
import streamlit as st

import calcs
import fmt
import ui
from data import AIRCRAFT
from views.home import params


def maker(t):  # Aircraft Name = IF LEFT([Aircraft Type],1)='A' THEN 'Airbus' ELSE 'Boeing' END
    return "Airbus" if t.startswith("A") else "Boeing"


def render():
    ss = st.session_state
    p = params()
    ui.header("Fleet", "Select any aircraft in AeroLink Alliance's fleet to view more information on its utilization.")
    cards = calcs.fleet_cards(p)
    left, right = st.columns([1.22, 1], gap="medium")

    with left:
        for row in range(3):
            cols = st.columns(2, gap="small")
            for c, t in zip(cols, AIRCRAFT[row * 2:(row + 1) * 2]):
                sel = t == ss.aircraft
                fl = int(cards["flights"].get(t, 0)) if not cards.empty else 0
                px_ = int(cards["passengers"].get(t, 0)) if not cards.empty else 0
                with c, st.container(key=f"card_plane_{'sel_' if sel else ''}{t}"):
                    # aircraft photo = the workbook's custom shape
                    st.markdown(
                        f"<div class='plane'><img src='{ui.img_uri(t.lower())}' alt='{t}'>"
                        f"<div class='n'>{maker(t)} {t}</div>"
                        f"<div class='s'><b>{fmt.integer(fl)}</b> completed flights<br>"
                        f"<b>{fmt.integer(px_)}</b> passengers</div></div>", unsafe_allow_html=True)
                    st.button("Details", key=f"show_{t}", type="primary" if sel else "secondary",
                              on_click=lambda t=t: ss.update(aircraft=t))  # 'Show A320…' parameter action

    with right, st.container(key="card_selected"):
        st.markdown(f"<div style='font-size:21px;font-weight:600;color:{ui.TEXT}'>{maker(ss.aircraft)} {ss.aircraft}</div>"
                    f"<div style='font-size:12px;color:#666'>{ss.airline} · {ss.region}</div>"
                    f"<div class='plane_big'><img src='{ui.img_uri(ss.aircraft.lower())}' alt=''></div>",
                    unsafe_allow_html=True)
        s = calcs.fleet_selected(p)
        items = [("departures", "Completed Flights", fmt.integer(s["flights"])),
                 ("passenger", "All Passengers", fmt.millions(s["passengers"])),
                 ("distance", "Avg. Distance Covered", f"{fmt.integer(s['distance'])} km"),
                 ("load_factor", "Avg. Load Factor", fmt.pct2(s["load_factor"])),
                 ("carbon-dioxide", "Avg. CO₂ Emissions", f"{fmt.thousands(s['emissions'])} kg"),
                 ("financial-profit", "Total Fuel Cost", fmt.usd_b(s["fuel_costs"]))]
        with st.container(key="fleet_stats"):
            for i in range(0, 6, 2):
                a, b = st.columns(2)
                with a:
                    ui.icon_item(*items[i], color=ui.NAVY)
                with b:
                    ui.icon_item(*items[i + 1], color=ui.NAVY)
        ui.section("Recent Completed Flights")
        rf = calcs.recent_aircraft_flights(p)
        if rf.empty:
            st.caption("No completed flights for this selection.")
        else:
            # fills the rest of the panel so it ends level with the aircraft grid (CSS: st-key-fleet_flist)
            with st.container(key="fleet_flist", border=False):
                st.markdown("".join(ui.flight_card_html(r) for r in rf.itertuples()), unsafe_allow_html=True)
