"""One function per Tableau worksheet (or per group of stacked worksheets)."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from fmt import MONTH_LETTERS, MONTH_NAMES, WEEKDAYS
from ui import BLUE, DOWN, FONT, GREY_BAR, NEUTRAL, PM_DARK, PURPLE, TEXT, UP

CONFIG = {"displayModeBar": False, "responsive": True}
MAP_CONFIG = CONFIG
HOVER = dict(bgcolor="white", bordercolor="#c9ccd2", font=dict(family=FONT, size=12, color=TEXT))


def _base(fig, height, margin=(0, 0, 0, 0)):
    l, r, t, b = margin
    fig.update_layout(height=height, margin=dict(l=l, r=r, t=t, b=b), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT, size=11, color=TEXT),
                      showlegend=False, hoverlabel=HOVER, bargap=0.25)
    return fig


def kpi_trend(mdf: pd.DataFrame, fmt_fn, hover_tpl: str, year: int, *, sel_color=BLUE,
              circle_colors=None, height=150):
    """'<X> Bars' + '<X> Circles' + '<X> Labels' stacked into one figure.

    hover_tpl: text with {value}, {month}, {year} placeholders (from the Tableau tooltip).
    """
    circle_colors = circle_colors or {"Up": UP, "Down": DOWN, "No": NEUTRAL}
    fig = make_subplots(rows=2, cols=1, row_heights=[0.78, 0.22], vertical_spacing=0.02, shared_xaxes=True)
    colors = [sel_color if s else GREY_BAR for s in mdf["selected"]]
    hover = [hover_tpl.format(value=fmt_fn(v), month=MONTH_NAMES[m - 1], year=year) if pd.notna(v) else ""
             for m, v in zip(mdf["month"], mdf["cy"])]
    fig.add_bar(x=mdf["month"], y=mdf["cy"], marker_color=colors, marker_line_width=0,
                hovertext=hover, hoverinfo="text", row=1, col=1)
    py_hover = [f"{MONTH_NAMES[m - 1]}: {year} vs {year - 1} → {s}" for m, s in zip(mdf["month"], mdf["status"])]
    fig.add_scatter(x=mdf["month"], y=[1] * 12, mode="markers+text",
                    marker=dict(size=8, color=[circle_colors[s] for s in mdf["status"]]),
                    text=MONTH_LETTERS, textposition="bottom center", textfont=dict(size=10, color="#787878"),
                    hovertext=py_hover, hoverinfo="text", row=2, col=1)
    fig.update_xaxes(visible=False, range=[0.4, 12.6])
    fig.update_yaxes(visible=False, row=1, col=1, rangemode="tozero")
    fig.update_yaxes(visible=False, row=2, col=1, range=[-1.2, 1.6])
    return _base(fig, height)


def _inside_labels(values, fmt_fn):
    """Tableau puts the value inside the bar, white and bold; small bars fall back to outside (dark)."""
    return dict(text=[fmt_fn(v) for v in values], textposition="auto", insidetextanchor="start",
                insidetextfont=dict(color="white", size=10.5, family=FONT),
                outsidetextfont=dict(color=TEXT, size=10.5, family=FONT),
                texttemplate="<b>%{text}</b>", cliponaxis=False)


def airline_compare(cm: pd.Series, pm: pd.Series, fmt_fn, hover_tpl: str, *, height=150, airlines=None):
    """'<X> Airlines': rows = Airline Name sorted by CM value DESC; CM bar (blue) with the
    value inside it, PM as a dark reference tick; axis ends just past the max."""
    airlines = airlines or sorted(set(cm.index) | set(pm.index))
    cm, pm = cm.reindex(airlines), pm.reindex(airlines)
    order = cm.astype(float).fillna(-np.inf).sort_values(ascending=True).index.tolist()  # bottom -> top
    cmv, pmv = cm.reindex(order), pm.reindex(order)
    fig = go.Figure()
    fig.add_bar(y=order, x=cmv.values, orientation="h", marker_color=BLUE, width=0.62,
                **_inside_labels(cmv.values, fmt_fn),
                hovertext=[hover_tpl.format(airline=a, value=fmt_fn(v)) + f"<br>Prev. month: {fmt_fn(p)}"
                           for a, v, p in zip(order, cmv.values, pmv.values)], hoverinfo="text")
    fig.add_scatter(y=order, x=pmv.values, mode="markers", hoverinfo="skip",
                    marker=dict(symbol="line-ns", size=24, line=dict(width=2.5, color=PM_DARK)))
    mx = np.nanmax(np.r_[cmv.values.astype(float), pmv.values.astype(float), 0]) or 1
    fig.update_xaxes(visible=False, range=[0, mx * 1.04])
    fig.update_yaxes(tickfont=dict(size=10.5, color="#555"), ticks="", showgrid=False)
    fig.update_layout(uniformtext=dict(minsize=10, mode="show"))
    return _base(fig, height, margin=(0, 6, 2, 2))


def top_destinations(td: pd.DataFrame, month_label: str, n: int = 10, height=170):
    td = td.head(n).iloc[::-1]
    fig = go.Figure(go.Bar(
        y=td["destination_city"], x=td["flights"], orientation="h", marker_color=BLUE, width=0.6,
        text=[f"{v:,}" for v in td["flights"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=10),
        hovertext=[f"There were {f:,} completed flights to {c}, {k} in {month_label}."
                   for c, k, f in zip(td["destination_city"], td["country"], td["flights"])],
        hoverinfo="text"))
    fig.update_xaxes(visible=False, range=[0, (td["flights"].max() if len(td) else 1) * 1.15])
    fig.update_yaxes(tickfont=dict(size=10.5, color="#555"))
    return _base(fig, height, margin=(0, 4, 0, 0))


def flight_times(grid: pd.DataFrame, year: int, height=170):
    """'Main Flight Times': square marks, weekday x month, colour = CY All Flights."""
    z = grid.values.astype(float)
    hover = [[f"{WEEKDAYS[r]}s in {MONTH_NAMES[c]} {year}<br>No of Booked Flights: "
              + ("" if np.isnan(z[r, c]) else f"{int(z[r, c]):,}") for c in range(12)] for r in range(7)]
    scale = ["#f1f1f1", "#d9deeb", "#c2cce6", "#acbbe1", "#97aadc", "#839ad7",
             "#708ad2", "#5d7bcd", "#4b6dc8", "#3a5fc3", "#2a52be"]
    fig = go.Figure(go.Heatmap(z=z, x=list(range(1, 13)), y=[w[:3] for w in WEEKDAYS], colorscale=scale,
                               showscale=False, xgap=3, ygap=3, hovertext=hover, hoverinfo="text"))
    fig.update_xaxes(tickvals=list(range(1, 13)), ticktext=MONTH_LETTERS, tickfont=dict(size=10, color="#787878"))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10, color="#787878"))
    return _base(fig, height, margin=(0, 0, 0, 0))


def aircraft_utilization(cm_f, pm_f, cm_lf, pm_pax, airline, fmt_int, fmt_pct, height=160):
    """'Aircraft Utilization'.

    Rows = aircraft sorted by CM No of Comp Flights DESC. Left: CM No of Comp Flights (blue) with a tick at
    PM No of Comp Flights. Right: CM Load Factor (purple #702963) — filtered to the selected airline, exactly
    like the workbook — with a tick at 'PM No of Passengers' on its own axis (the workbook's 4th measure;
    a quirk kept for parity). Values inside the bars, white bold."""
    order = cm_f.astype(float).fillna(-1).sort_values(ascending=True).index.tolist()
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.03)
    c, p = cm_f.reindex(order), pm_f.reindex(order)
    fig.add_bar(y=order, x=c.values, orientation="h", marker_color=BLUE, width=0.66, row=1, col=1,
                **_inside_labels(c.values, fmt_int),
                hovertext=[f"All member airlines of Aerolink Alliance completed {fmt_int(v)} flights with the "
                           f"{'Airbus' if a.startswith('A') else 'Boeing'} {a}<br>(prev. month {fmt_int(pv)})"
                           for a, v, pv in zip(order, c.values, p.values)], hoverinfo="text")
    fig.add_scatter(y=order, x=p.values, mode="markers", row=1, col=1, hoverinfo="skip",
                    marker=dict(symbol="line-ns", size=16, line=dict(width=2, color=PM_DARK)))
    mx = np.nanmax(np.r_[c.values.astype(float), p.values.astype(float), 0]) or 1
    fig.update_xaxes(visible=False, range=[0, mx * 1.04], row=1, col=1)

    lf, pp = cm_lf.reindex(order), pm_pax.reindex(order)
    fig.add_bar(y=order, x=lf.values, orientation="h", marker_color=PURPLE, width=0.66, row=1, col=2,
                **_inside_labels(lf.values, fmt_pct),
                hovertext=[f"{airline} recorded an average load factor of {fmt_pct(v)} on the {a}"
                           f"<br><i>*Load Factor = % of aircraft carrying capacity used*</i>"
                           for a, v in zip(order, lf.values)], hoverinfo="text")
    fig.update_xaxes(visible=False, range=[0, (np.nanmax(np.r_[lf.values.astype(float), 0]) or 1) * 1.04],
                     row=1, col=2)
    # PM passengers tick on an independent axis overlaying the load-factor panel
    fig.add_scatter(y=order, x=pp.values, mode="markers", xaxis="x3", yaxis="y2", hoverinfo="skip",
                    marker=dict(symbol="line-ns", size=16, line=dict(width=2, color=PM_DARK)))
    fig.update_layout(xaxis3=dict(overlaying="x2", visible=False,
                                  range=[0, (np.nanmax(np.r_[pp.values.astype(float), 0]) or 1) * 1.04]))
    fig.update_yaxes(tickfont=dict(size=10.5, color="#555"), ticks="")
    fig.update_layout(uniformtext=dict(minsize=9.5, mode="show"), bargap=0.2)
    return _base(fig, height, margin=(0, 4, 2, 2))


def mishandling_donut(split: pd.Series, pct_label: str, size=130):
    """'Mishandling' donut: square figure so the ring is never clipped; Tableau grey."""
    fig = go.Figure(go.Pie(labels=split.index, values=split.values, hole=0.62, sort=False, direction="clockwise",
                           marker=dict(colors=[BLUE, GREY_BAR]), textinfo="none",
                           hovertemplate="%{label}: %{value:,} flights<extra></extra>"))
    fig.add_annotation(text=f"<b>{pct_label}</b>", showarrow=False, font=dict(size=14, color=TEXT))
    fig = _base(fig, size)
    fig.update_layout(width=size)
    return fig


def flat_arc(lon1, lat1, lon2, lat2, bulge=0.12, n=48):
    """A gentle curve between two airports, drawn flat on the map (used instead of the great
    circle, which looks like a tall arch on Mercator tiles). Takes the shorter way round in
    longitude and bows slightly towards the pole."""
    if lon2 - lon1 > 180:
        lon2 -= 360
    elif lon1 - lon2 > 180:
        lon2 += 360
    p0, p2 = np.array([lon1, lat1]), np.array([lon2, lat2])
    d = p2 - p0
    normal = np.array([-d[1], d[0]])
    if normal[1] * (1 if (lat1 + lat2) >= 0 else -1) < 0:
        normal = -normal                                   # bow poleward, like a real route would
    p1 = (p0 + p2) / 2 + bulge * normal
    t = np.linspace(0, 1, n)[:, None]
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2   # quadratic Bézier
    return pts[:, 0], np.clip(pts[:, 1], -85, 85)


ESRI_IMAGERY = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_LABELS = ("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/"
               "World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}")
WORLD_TOPOJSON = Path(__file__).parent / "static" / "topojson" / "world_110m.json"
ROUTE_DEST = "#ffd23f"   # destination dot on the satellite view


@lru_cache(maxsize=1)
def world_countries() -> dict:
    """Country outlines as GeoJSON, decoded from the bundled Natural Earth TopoJSON (offline, no extra packages)."""
    topo = json.loads(WORLD_TOPOJSON.read_text(encoding="utf-8"))
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:                       # quantized + delta-encoded -> lon/lat
        xy = np.cumsum(np.array(arc, dtype=float), axis=0)
        # latitudes clamped to ±85: Web Mercator can't project the poles (Antarctica reaches -90)
        arcs.append(np.round(np.c_[xy[:, 0] * sx + tx, np.clip(xy[:, 1] * sy + ty, -85, 85)], 2).tolist())

    def ring(idx):
        pts = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        if pts:   # Russia/Fiji cross ±180: keep the ring continuous so it doesn't draw a line across the world
            lon = np.degrees(np.unwrap(np.radians([p[0] for p in pts])))
            if abs(lon[-1] - lon[0]) > 1:   # wraps round the pole (Antarctica): no flights there, drop it
                return []
            pts = [[round(float(x), 2), p[1]] for x, p in zip(lon, pts)]
        return pts

    def polygon(rings):
        return [r for r in map(ring, rings) if len(r) >= 4]

    feats = []
    for g in topo["objects"]["countries"]["geometries"]:
        if g["type"] == "Polygon":
            geom = {"type": "Polygon", "coordinates": polygon(g["arcs"])}
        elif g["type"] == "MultiPolygon":
            geom = {"type": "MultiPolygon", "coordinates": [p for p in map(polygon, g["arcs"]) if p]}
        else:
            continue
        if not geom["coordinates"]:
            continue
        feats.append({"type": "Feature", "properties": {}, "geometry": geom})
    return {"type": "FeatureCollection", "features": feats}


def flight_map(rows: pd.DataFrame, selected: str | None, height=640, style="minimal"):
    """'Flight Map': the route (MAKELINE(origin, destination)) of the highlighted flight.

    Both styles are tile maps that fill their frame and fit the route at any width (fitbounds).
    style="minimal":   plain background + the bundled Natural Earth country outlines -> works with no internet.
    style="satellite": Esri World Imagery tiles + place labels (like Tableau's satellite basemap) -> needs internet.
    The route is a gentle curve (flat_arc) rather than Tableau's great circle, which looks like a tall arch on
    these flat maps. City names sit above the map (views/flights.py): map text needs an
    online font, so only the satellite view also labels the dots.
    """
    sel = rows[rows["flight_id"] == selected].head(1)
    r = sel.iloc[0] if not sel.empty else None
    sat = style == "satellite"
    fig = go.Figure()
    view = dict(zoom=1, center=dict(lon=0, lat=20))
    if r is not None:
        lon, lat = flat_arc(r.origin_longitude, r.origin_latitude, r.destination_longitude, r.destination_latitude)
        hover = (f"Route: {r.origin_city}, {r.origin_country} - {r.destination_city}, {r.destination_country} "
                 f"({r.route})<br>Route Category: {r.route_category}")
        fig.add_scattermap(lon=lon, lat=lat, mode="lines", line=dict(width=3 if sat else 2.5,
                           color="#ffffff" if sat else BLUE), hovertext=hover, hoverinfo="text")
        ends = dict(lon=[lon[0], lon[-1]], lat=[lat[0], lat[-1]], hoverinfo="skip",
                    marker=dict(size=[10, 13], color=["#ffffff", ROUTE_DEST] if sat else [TEXT, BLUE]))
        if sat:
            fig.add_scattermap(**ends, mode="markers+text", text=[r.origin_city, r.destination_city],
                               textposition="top center", textfont=dict(size=13, color="#ffffff"))
        else:
            fig.add_scattermap(**ends, mode="markers")
        # frame = whole arc + padding: invisible corner points, and the browser fits the
        # view to them at whatever size the map has
        pad_lo = max(6, (lon.max() - lon.min()) * 0.18)
        pad_la = max(5, (lat.max() - lat.min()) * 0.25)
        fig.add_scattermap(lon=[lon.min() - pad_lo, lon.max() + pad_lo],
                           lat=[max(-85, lat.min() - pad_la), min(85, lat.max() + pad_la)],
                           mode="markers", marker=dict(opacity=0), hoverinfo="skip")
        view = dict(fitbounds="locations")
    if sat:
        layers = [dict(below="traces", sourcetype="raster", source=[ESRI_IMAGERY],
                       sourceattribution="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics"),
                  dict(below="traces", sourcetype="raster", source=[ESRI_LABELS])]
    else:
        land = world_countries()
        layers = [dict(below="traces", sourcetype="geojson", source=land, type="fill", color="#e3e5e9"),
                  dict(below="traces", sourcetype="geojson", source=land, type="line", color="#ffffff",
                       line=dict(width=0.8))]
    fig.update_layout(map=dict(style="white-bg", **view, layers=layers))
    return _base(fig, height)
