"""Number formats translated from the workbook's default-format strings."""
import math

import pandas as pd

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
MONTH_LETTERS = [m[0] for m in MONTH_NAMES]
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _na(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v)


def integer(v):            # n#,##0
    return "" if _na(v) else f"{v:,.0f}"


def dec1(v):               # n#,##0.0
    return "" if _na(v) else f"{v:,.1f}"


def dec2(v):               # n#,##0.00
    return "" if _na(v) else f"{v:,.2f}"


def pct1(v):               # p0.0%
    return "" if _na(v) else f"{v:.1%}"


def pct2(v):               # p0.00%
    return "" if _na(v) else f"{v:.2%}"


def billions(v):           # n#,##0,,,.00B
    return "" if _na(v) else f"{v / 1e9:,.2f}B"


def millions(v):           # n#,##0,,.00M
    return "" if _na(v) else f"{v / 1e6:,.2f}M"


def usd_m(v):              # c"$"#,##0,,.00M
    if _na(v):
        return ""
    return f"-${abs(v) / 1e6:,.2f}M" if v < 0 else f"${v / 1e6:,.2f}M"


def usd_b(v):              # c"$"#,##0,,,.00B
    if _na(v):
        return ""
    return f"-${abs(v) / 1e9:,.2f}B" if v < 0 else f"${v / 1e9:,.2f}B"


def usd2(v):               # c"$"#,##0.00
    return "" if _na(v) else f"${v:,.2f}"


def thousands(v):          # n#,##0,.00K
    return "" if _na(v) else f"{v / 1e3:,.2f}K"


def mom(v):                # *▲0.0%;▼0.0%
    if _na(v):
        return ""
    return f"▼{abs(v):.1%}" if v < 0 else f"▲{v:.1%}"
