# AeroLink — Airline Alliance Activity Dashboard

An interactive dashboard of airline alliance performance from 2022 to 2025, built with
[Streamlit](https://streamlit.io) and [Plotly](https://plotly.com/python/). It is a Python version of the
Tableau Public dashboard
[*Airline Alliance Activity Dashboard*](https://public.tableau.com/app/profile/neto.anyama/viz/AirlineAllianceActivityDashboard/AlliancePage)
(#VOTD), designed by Stephanie Anyama; the original idea, design and data come from there.

| Page | What it shows |
|---|---|
| Home | Alliance-wide KPIs by month, airline comparisons, top destinations, flight times, aircraft utilization |
| Airlines | One airline's traffic, cargo, revenue and cost trends with a monthly summary |
| Flights | Recent flights as a timeline; click one to see its route on a map |
| Fleet | Each aircraft type's usage, emissions and fuel cost, plus its recent flights |

Filters (year, month, region, airline) are in the sidebar. Everything runs offline except the optional
satellite map.

## Run

**Windows:** double-click `run_dashboard.bat`. The first run creates a virtual environment and installs the
packages (needs Python 3.10+ and internet once), then opens http://localhost:8501.

**Any OS:**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

**Docker:**

```bash
docker build -t aerolink-dashboard .
docker run -d -p 8501:8501 aerolink-dashboard
```

## Update the data

Rebuild `data/flights.parquet` from a CSV with the same columns, then restart the app:

```bash
python tools/prepare_data.py airline_alliance_performance_2022_2025.csv
```

If the data covers new years, extend `YEARS` in `data.py`.

## Project layout

```
app.py      navigation, sidebar filters
data.py     data loading and filter defaults
calcs.py    metrics (the original dashboard's calculated fields)
charts.py   Plotly charts and the flight map
ui.py       theme and shared components
views/      one module per page
assets/     logo, aircraft images, icons, help text
static/     offline world outlines for the map
```
