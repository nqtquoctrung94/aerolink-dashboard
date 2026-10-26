"""Layout pieces that recreate the AeroLink design (sidebar, navy header, cards, BANs)."""
import base64
import io
from datetime import date
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image

IMG_DIR = Path(__file__).parent / "assets" / "img"   # shapes decoded from the workbook

# Colours taken from the workbook / background images.
NAVY = "#0b173d"
BLUE = "#2a52be"        # 'Selected Month' / CM
GREY_BAR = "#d3d3d3"    # 'Others'
PM_DARK = "#2e2e2e"     # PM reference tick
PURPLE = "#702963"      # 2nd measure colour in 'Aircraft Utilization' (Measure Names map)
UP = "#49964f"
DOWN = "#e63946"
NEUTRAL = "#b3b7b8"
TEXT = "#333333"
MUTED = "#787878"
PAGE_BG = "#f5f6f8"
CARD_BG = "#fafafa"
BORDER = "#d7d9dd"
AIRLINE_COLORS = {"SkyConnect Airways": "#26aba4", "Pacific Wings": "#9a6a96",
                  "Global Star": "#cca000", "Atlantic Express": "#e4641e"}
# Op Profit dots: the workbook maps "Down" to #4e79a7 (Tableau default blue) on this one tile, while the legend
# and every other tile use red. Decision: use red. Set to "#4e79a7" to copy Tableau exactly.
OP_PROFIT_DOWN = DOWN
FONT = "Inter, Geist, 'Segoe UI', Arial, Helvetica, sans-serif"

CSS = f"""
<style>
html, body, [class*="css"], .stApp, button, input, select {{ font-family: {FONT}; }}
.stApp {{ background: {PAGE_BG}; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 1rem; max-width: 1500px;
    padding-left: 1.5rem !important; padding-right: 1.5rem !important; }}
[data-testid="stSidebar"] {{ background: #fdfdfd; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarUserContent"] {{ padding-top: .5rem; }}
[data-testid="stSidebarHeader"] {{ display:none; }}

/* navy header band */
.al-header {{ background:{NAVY}; color:#fff; margin: 0 0 12px 0; padding: 22px 26px 18px 26px; border-radius: 0 0 4px 4px;
              display:flex; justify-content:space-between; align-items:flex-end; }}
.al-header h1 {{ font-size: 26px; font-weight: 500; margin:0; padding:0; color:#fff; letter-spacing:-.2px; }}
.al-header h1 .sep {{ font-weight:300; opacity:.8; margin: 0 6px; }}
.al-header h1 .sub {{ font-size: 20px; font-weight: 400; }}
.al-header h1 .strong {{ font-weight: 700; }}
.al-header p {{ font-style: italic; font-size: 12.5px; margin: 4px 0 0 0; color:#dfe3ee; }}
.al-user {{ text-align:right; font-size: 11.5px; color:#dfe3ee; line-height:1.5; }}

/* cards */
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > .al-card-marker),
.st-key-card, [class*="st-key-card"] {{ background:{CARD_BG}; }}
[class*="st-key-card"] {{ border:1px solid {BORDER}; border-radius: 2px; padding: 10px 12px; }}
.al-section {{ font-size: 12.5px; font-weight: 600; color:{TEXT}; margin: 0 0 2px 0; }}
.al-legend {{ font-size: 11px; font-style: italic; color:#3d4459; margin: 0 0 6px 2px; }}
.al-legend .dot {{ font-style: normal; font-size: 13px; }}

/* BAN */
.ban {{ line-height: 1.25; padding-top: 4px; }}
.ban .t {{ color:#666; font-size: 12px; }}
.ban .v {{ color:{TEXT}; font-size: 22px; font-weight: 700; margin: 6px 0 4px; white-space: nowrap; }}
.ban .v small {{ font-size: 13px; color:#666; font-weight:700; }}
.ban .m {{ font-size: 12px; font-weight:600; }}
.ban .vs {{ color:#898989; font-size: 10.5px; }}
.pos {{ color:{UP}; }} .neg {{ color:{DOWN}; }} .neut {{ color:#898989; }}

/* summary band (Airlines / Fleet) */
.sumitem {{ border-left: 3px solid {BLUE}; padding: 2px 0 2px 10px; margin: 4px 0; }}
.sumitem .t {{ color:#666; font-size: 12px; }}
.sumitem .v {{ color:{TEXT}; font-size: 16px; font-weight: 700; }}
.sumitem .v .m {{ font-size: 12px; font-weight:600; }}

/* sidebar navigation */
.al-side-h {{ font-size: 12px; letter-spacing: 1.4px; font-weight: 600; color:#4a5160; margin: 14px 0 6px 2px; }}
.al-foot {{ font-size: 11px; color:#333; margin-top: 18px; }}
[class*="st-key-nav"] button > div, [class*="st-key-nav"] button p {{ justify-content:flex-start !important; text-align:left; width:100%; }}
[class*="st-key-nav"] button {{ justify-content:flex-start; border: none; background: transparent;
    color:#3d4459; font-size: 13.5px; padding: 2px 10px; min-height: 30px; box-shadow:none; }}
[class*="st-key-nav"] button:hover {{ background:#eef0f3; color:{TEXT}; }}
[class*="st-key-nav"] button[kind="primary"], [class*="st-key-nav"] button[data-testid="stBaseButton-primary"] {{
    background:#e5e7ea; color:{TEXT}; font-weight: 700; }}
[class*="st-key-navsub"] {{ border-left: 1px solid #c9ccd2; margin-left: 18px; padding-left: 4px; }}
[class*="st-key-navsub"] button {{ font-size: 13px; }}
[class*="st-key-nav"] {{ gap: 0 !important; }}
[class*="st-key-nav"] [data-testid="stElementContainer"] {{ margin: 0; }}

/* month / year pickers: layout */
[class*="st-key-pick"] [data-testid="stHorizontalBlock"] {{ gap: 6px; }}
[class*="st-key-pick"] [data-testid="stColumn"] {{ width: 34px !important; flex: 0 0 34px !important; min-width: 34px !important; }}

/* fleet cards */
[class*="st-key-plane"] {{ text-align:center; }}
[class*="st-key-plane"] button {{ width: 100%; }}
div[data-testid="stDataFrame"] {{ font-size: 12px; }}

/* tooltips float over neighbouring content instead of being cut at the chart edge */
[class*="st-key-card_home"], [class*="st-key-card_col"], [class*="st-key-card_summary"],
[data-testid="stElementContainer"]:has(> [data-testid="stPlotlyChart"]), [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]),
[data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] > div,
.js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot .svg-container, .js-plotly-plot .main-svg {{
    overflow: visible !important; }}
[class*="st-key-card_home"]:hover, [class*="st-key-card_col"]:hover, [data-testid="stPlotlyChart"]:hover {{ position: relative; z-index: 50; }}
[data-testid="stColumn"]:hover, [data-testid="stHorizontalBlock"]:hover {{ position: relative; z-index: 40; }}
.hoverlayer .hovertext {{ filter: drop-shadow(0 2px 4px rgba(0,0,0,.18)); }}

/* equal-height tiles on Home */
[class*="st-key-card_home"] {{ min-height: 192px; }}

/* sidebar date pickers, styled like the workbook's circle/box buttons */
[class*="st-key-pick"] button {{ min-height: 30px; padding: 0; width: 30px; height: 30px; border-radius: 50%;
    border: 1px solid #b9bcc2; background: #fff; color: {TEXT}; font-weight: 600; font-size: 11.5px; box-shadow:none; }}
[class*="st-key-pick_year"] button {{ border-radius: 3px; width: 34px; height: 24px; min-height: 24px;
    background: #f3f4f6; color: #9aa0a8; border-color: #e3e5e9; font-weight: 500; font-size: 11px; }}
[class*="st-key-pick"] button:hover {{ border-color: {BLUE}; color: {BLUE}; }}
[class*="st-key-pick"] button[kind="primary"], [class*="st-key-pick"] button[data-testid="stBaseButton-primary"] {{
    background: {BLUE} !important; color: #fff !important; border-color: {BLUE} !important; }}

/* summary items with icons */
.sumicon {{ display:flex; align-items:center; gap:10px; margin: 6px 0; }}
.sumicon img {{ width: 34px; height: 34px; object-fit: contain; flex: 0 0 34px; }}
.sumicon .t {{ color:#666; font-size: 12.5px; line-height:1.2; }}
.sumicon .v {{ color:{TEXT}; font-size: 15px; font-weight: 700; line-height:1.25; }}
.sumicon .v .m {{ font-size: 11.5px; font-weight:600; }}

/* fleet cards */
[class*="st-key-card_plane"] {{ text-align:left; padding: 6px 14px 12px; }}
[class*="st-key-card_plane_sel"] {{ background:#eceaf0 !important; border-color:#c9c4d3 !important; }}
.plane img {{ width:100%; height:auto; aspect-ratio: 2.6 / 1; object-fit:contain; margin: 10px 0 8px; display:block; }}
.plane .n {{ font-weight:700; font-size:15px; color:{TEXT}; margin-top:2px; }}
.plane .s {{ font-size:12px; color:#666; font-style:italic; line-height:1.4; }}
.plane .s b {{ font-style:normal; color:{TEXT}; }}
.plane_big {{ padding: 0 24px; margin: 14px 0 20px; }}
.plane_big img {{ width:100%; height:140px; object-fit:contain; display:block; }}
[class*="st-key-fleet_stats"] {{ gap: 10px; margin-bottom: 22px; }}
/* selected-aircraft panel stretches to the grid's height; the flights list takes what's left and scrolls */
[data-testid="stColumn"]:has(.st-key-card_selected) {{ display: flex; flex-direction: column; }}
[data-testid="stColumn"]:has(.st-key-card_selected) > [data-testid="stVerticalBlock"],
[data-testid="stLayoutWrapper"]:has(> .st-key-card_selected) {{ flex: 1 1 auto; display: flex; flex-direction: column; }}
.st-key-card_selected {{ flex: 1 1 auto; }}
[data-testid="stLayoutWrapper"]:has(> .st-key-fleet_flist) {{ flex: 1 1 0; min-height: 200px; overflow: hidden; }}
.st-key-fleet_flist {{ height: 100%; overflow-y: auto; }}
[class*="st-key-show_"] button {{ min-height: 28px; padding: 0 22px; font-weight:600; font-size:12.5px; }}

/* flight timeline cards */
.fl {{ display:grid; grid-template-columns: 70px 22px 1fr; gap: 0 8px; padding: 10px 6px 12px; color:#8a8f98;
       font-size: 11.5px; line-height: 1.35; border-bottom: 1px solid #e6e7ea; }}
.fl .meta {{ text-align:right; font-size: 10.5px; }}
.fl .meta b {{ font-weight: 500; }}
.fl .line {{ position:relative; }}
.fl .line:before {{ content:""; position:absolute; left:10px; top:6px; bottom:6px; width:2px; background:#d6d8dc; }}
.fl .line .o, .fl .line .d {{ position:absolute; left:5px; width:12px; height:12px; border-radius:50%; }}
.fl .line .o {{ top:0; background:#fff; border:2px solid #c9ccd2; }}
.fl .line .d {{ bottom:0; background:#c9ccd2; }}
.fl .stats {{ display:flex; flex-wrap: wrap; gap: 2px 14px; margin: 6px 0; }}
.fl > div {{ min-width: 0; overflow-wrap: anywhere; }}
[class*="st-key-card_flist"] {{ overflow-x: hidden; }}
/* the flight cards need ~330px; the map column gives way on narrow screens */
@media (min-width: 640px) {{
  [data-testid="stHorizontalBlock"]:has(.st-key-card_flist) {{ flex-wrap: nowrap; }}
  [data-testid="stColumn"]:has(.st-key-card_flist) {{ min-width: 330px; }}
  [data-testid="stColumn"]:has(.st-key-card_map) {{ min-width: 0; }}
}}
.fl .stats span {{ display:block; }}
.fl.sel {{ color:{TEXT}; border-left: 3px solid {NAVY}; background:#fff; }}
.fl.sel .line:before {{ background:{NAVY}; }}
.fl.sel .line .o {{ border-color:{NAVY}; }}
.fl.sel .line .d {{ background:{NAVY}; }}
[class*="st-key-fltcard"] {{ position: relative; }}
[class*="st-key-fltbtn"] {{ position: absolute !important; inset: 0; z-index: 5; width: 100% !important; }}
[class*="st-key-fltbtn"] .stButton {{ width: 100%; height: 100%; }}
[class*="st-key-fltbtn"] button {{ width:100%; height:100%; opacity:0; cursor:pointer; }}
[class*="st-key-fltcard"]:hover .fl {{ background:#f2f4f8; }}
.route-line {{ font-size: 12.5px; color:{TEXT}; line-height: 1.5; }}
.route-line b {{ font-weight: 600; color:#666; }}
.route-line .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin: 0 6px 0 0; vertical-align:-1px; }}
.route-line .arr {{ margin: 0 10px; color:#8a8f98; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(page_title: str | None, subtitle: str):
    if page_title:
        right = f'<span class="sep">|</span><span class="strong">{escape(page_title)}</span>'
    else:
        right = '<span class="sep">|</span><span class="sub">2022 - 2025</span>'
    d = date.today()   # 'Today' = TODAY() in the 'Logged in' sheet
    today = f"{d.day} {d:%b %Y}"
    st.markdown(
        f"""<div class="al-header"><div><h1>Airline Alliance Activity Dashboard{right}</h1>
        <p>{escape(subtitle)}</p></div>
        <div class="al-user">Hello, Guest!<br>Last Login: {today}</div></div>""",
        unsafe_allow_html=True)


def legend(airline_page: bool = False):
    if airline_page:
        txt = (f'<span class="dot" style="color:{UP}">●</span>Month of CY &gt; Month of PY '
               f'(<span class="dot" style="color:{DOWN}">●</span> for Costs), '
               f'<span class="dot" style="color:{DOWN}">●</span>Month of CY &lt; Month of PY '
               f'(<span class="dot" style="color:{UP}">●</span> for Costs), '
               f'<span class="dot" style="color:{NEUTRAL}">●</span>Month of CY = Month of PY')
    else:
        txt = (f'<span class="dot" style="color:{UP}">●</span>Month of CY &gt; Month of PY, '
               f'<span class="dot" style="color:{DOWN}">●</span>Month of CY &lt; Month of PY, '
               f'<span class="dot" style="color:{NEUTRAL}">●</span>Month of CY = Month of PY ; '
               f'<span class="dot" style="color:{BLUE}">■</span> Current Month '
               f'<b style="color:{PM_DARK};font-style:normal">|</b> Prev Month')
    st.markdown(f'<div class="al-legend">{txt}</div>', unsafe_allow_html=True)


def section(title: str):
    st.markdown(f'<div class="al-section">{escape(title)}</div>', unsafe_allow_html=True)


def _mom_html(chg, kind, with_vs=True, short=False):
    from fmt import mom as fmom
    vs = "vs. PM" if short else "vs. Prev. Month"
    if kind == "none":
        return f'<span class="neut">–</span>' + (f' <span class="vs">{vs}</span>' if with_vs else "")
    cls = {"pos": "pos", "neg": "neg", "neut": "neut"}[kind]
    return f'<span class="m {cls}">{fmom(chg)}</span>' + (f' <span class="vs">{vs}</span>' if with_vs else "")


def ban(title: str, value: str, chg, kind: str, unit: str = ""):
    """'<X> BAN' sheet: title, CM value, Pos/Neg/Neut MoM coloured, 'vs. Prev. Month'."""
    from fmt import mom as fmom
    u = f" <small>{unit}</small>" if unit else ""
    m = "" if kind == "none" else f'<span class="m {kind}">{fmom(chg)}</span>'
    st.markdown(
        f'<div class="ban"><div class="t">{escape(title)}</div>'
        f'<div class="v">{escape(value) or "–"}{u}</div>'
        f'<div>{m}</div><div class="vs">vs. Prev. Month</div></div>',
        unsafe_allow_html=True)


def summary_item(title: str, value_html: str, color: str = BLUE):
    st.markdown(f'<div class="sumitem" style="border-left-color:{color}"><div class="t">{escape(title)}</div>'
                f'<div class="v">{value_html}</div></div>', unsafe_allow_html=True)


def mom_inline(chg, kind):
    return "(" + _mom_html(chg, kind, with_vs=True, short=True) + ")"


# ---------------------------------------------------------------- images (decoded from the workbook)
@lru_cache(maxsize=None)
def img_uri(name: str, tint: str | None = None, max_px: int = 300) -> str:
    """data: URI for assets/img/<name>.png, optionally re-coloured (Tableau colours shape marks by a field,
    e.g. the summary icons take the selected airline's colour)."""
    im = Image.open(IMG_DIR / f"{name}.png").convert("RGBA")
    bbox = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if bbox:                                   # trim transparent margins (photos sit small in 300x300)
        im = im.crop(bbox)
    if tint:
        rgb = tuple(int(tint.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        solid = Image.new("RGBA", im.size, rgb + (255,))
        solid.putalpha(im.getchannel("A"))
        im = solid
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def icon_item(icon: str, title: str, value_html: str, color: str | None = None):
    """Summary item with the workbook's icon (Airline Summary 1/2, Aircraft Summary 1–3)."""
    src = img_uri(icon, color, 96)
    st.markdown(f'<div class="sumicon"><img src="{src}" alt=""><div><div class="t">{escape(title)}</div>'
                f'<div class="v">{value_html}</div></div></div>', unsafe_allow_html=True)


def flight_card_html(r, selected: bool = False) -> str:
    """One flight in the workbook's timeline style ('Recent Flights' / 'Sel Aircraft Flights')."""
    import fmt
    d = r.date
    return (
        f'<div class="fl{" sel" if selected else ""}">'
        f'<div class="meta">{d.month}/{d.day}/{d.year}<br><b>{escape(str(r.flight_id))}</b><br><br>'
        f'Duration:<br>{r.flight_duration_hours:g} hrs</div>'
        f'<div class="line"><span class="o"></span><span class="d"></span></div>'
        f'<div><div>{escape(r.origin_city)}, {escape(r.origin_country)} ({escape(r.origin_airport)})</div>'
        f'<div class="stats"><span>Model<br>{escape(r.aircraft_type)}</span>'
        f'<span>Fare<br>{fmt.usd2(r.average_fare_usd)}</span>'
        f'<span>Passengers<br>{int(r.passengers_carried):,}</span></div>'
        f'<div>{escape(r.destination_city)}, {escape(r.destination_country)} ({escape(r.destination_airport)})</div>'
        f'</div></div>')
