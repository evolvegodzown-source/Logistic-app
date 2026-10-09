"""Pillometer Complaints Tracker — live dashboard fed by the IT Task Tracker workbook."""

from __future__ import annotations
import base64
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st
from data_loader import WORKBOOK_PATH, fetch_from_sharepoint_via_browser, load_workbook
st.set_page_config(
    page_title="Pillometer Customer Feedback Tracker",
    page_icon=str(Path(__file__).parent / "pillometer_logo.png"),
    layout="wide",
)
@st.cache_data(ttl=300, show_spinner=False)
def _load(path_str: str, mtime: float) -> dict[str, pd.DataFrame]:
    return load_workbook(Path(path_str))
def _mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0
def _filter_by_status(df: pd.DataFrame, statuses: list[str]) -> pd.DataFrame:
    if "Status" not in df.columns or not statuses:
        return df
    return df[df["Status"].isin(statuses)]
def _filter_by_period(
    df: pd.DataFrame,
    months: list[pd.Period] | None,
    weeks: list[int] | None,
) -> pd.DataFrame:
    """Keep rows whose Start date falls in the chosen months and/or ISO weeks."""
    if "Start date" not in df.columns:
        return df
    out = df
    if months:
        out = out[out["Start date"].dt.to_period("M").isin(months)]
    if weeks:
        out = out[out["Start date"].dt.isocalendar().week.isin(weeks)]
    return out
def _week_numbers(df: pd.DataFrame) -> pd.Series:
    if "Start date" not in df.columns or df.empty:
        return pd.Series(dtype=int)
    return df["Start date"].dropna().dt.isocalendar().week.astype(int)
def _wow_delta(dfs: list[pd.DataFrame], latest: int, previous: int) -> str | None:
    """Formatted week-over-week change: rows in the latest ISO week vs the prior one."""
    weeks = pd.concat([_week_numbers(d) for d in dfs])
    if weeks.empty:
        return None
    cur = int((weeks == latest).sum())
    prev = int((weeks == previous).sum())
    return f"{cur - prev:+d}"


def _avg_resolution_wow(df: pd.DataFrame, latest: int, previous: int) -> str | None:
    if "Start date" not in df.columns or df.empty:
        return None
    wk = df["Start date"].dt.isocalendar().week
    cur = _avg_resolution(df[wk == latest])
    prev = _avg_resolution(df[wk == previous])
    if cur is None or prev is None:
        return None
    return f"{cur - prev:+.1f}"


def _avg_resolution(df: pd.DataFrame) -> float | None:
    resolved = df.get("Resolution Days")
    if resolved is None:
        return None
    resolved = resolved.dropna()
    resolved = resolved[resolved >= 0]
    return float(resolved.mean()) if len(resolved) else None


CARD_PALETTE = ["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899", "#64748b"]
STATUS_COLORS = {
    "Resolved": "#10b981", "Executed": "#10b981",
    "Pending": "#f59e0b", "Evaluating": "#f59e0b",
    "In Progress": "#3b82f6", "Escalated": "#ef4444",
}


def _legend_card_html(
    title: str,
    big_html: str,
    counts: pd.Series,
    accent: str,
    bg: str,
) -> str:
    """KPI card with a proportion bar and a color-dotted legend of counts/shares."""
    total = int(counts.sum())
    dot = lambda i, k: STATUS_COLORS.get(k, CARD_PALETTE[i % len(CARD_PALETTE)])
    if total:
        bar = "".join(
            f'<div style="width:{100 * n / total:.1f}%;background:{dot(i, k)};"></div>'
            for i, (k, n) in enumerate(counts.items()) if n
        )
        rows = "".join(
            f'<div style="display:flex;justify-content:space-between;margin-top:2px;">'
            f'<span><span style="color:{dot(i, k)};">&#9679;</span> {k}</span>'
            f'<span style="font-weight:600;">{int(n)} &middot; {100 * n / total:.1f}%</span></div>'
            for i, (k, n) in enumerate(counts.items())
        )
    else:
        bar, rows = "", '<div style="color:#64748b;">No data</div>'
    return f"""
    <div style="background:{bg}; border-top:5px solid {accent}; border-radius:14px;
         box-shadow:0 2px 6px rgba(15,23,42,.10); padding:16px; height:100%;">
        <div style="color:#16324F; font-size:14px; font-weight:600;">{title}</div>
        <div style="color:#16324F; font-size:24px; font-weight:700; line-height:1.15;">{big_html}</div>
        <div style="display:flex; height:7px; border-radius:4px; overflow:hidden; margin:10px 0 6px 0; background:#e2e8f0;">{bar}</div>
        <div style="font-size:13px; color:#334155;">{rows}</div>
    </div>
    """


def _top_counts(series: pd.Series, top: int = 5) -> pd.Series:
    counts = series.dropna().astype(str).str.strip().value_counts()
    if len(counts) > top:
        counts = pd.concat([counts.head(top), pd.Series({"Other": int(counts.iloc[top:].sum())})])
    return counts


def _counts_df(counts: pd.Series, label: str = "Label") -> pd.DataFrame:
    return counts.rename_axis(label).reset_index(name="Count")


def _labeled_line(counts: pd.Series, color: str, x_title: str) -> alt.Chart:
    """Line + points + count labels; x keeps the (time-ordered) row order."""
    df = _counts_df(counts, "Period")
    line = (
        alt.Chart(df)
        .mark_line(color=color, point=True, interpolate="monotone")
        .encode(
            x=alt.X("Period:O", sort=None, title=x_title),
            y=alt.Y("Count:Q", axis=alt.Axis(tickMinStep=1)),
            tooltip=["Period", "Count"],
        )
    )
    labels = (
        alt.Chart(df)
        .mark_text(dy=-10, color="#16324F", fontSize=12)
        .encode(x=alt.X("Period:O", sort=None), y="Count:Q", text="Count:Q")
    )
    return (line + labels).configure_view(stroke=None)


def _labeled_bars(counts: pd.Series, color: str) -> alt.Chart:
    """Horizontal bar chart ranked by count (largest on top), with count labels."""
    df = _counts_df(counts)
    bars = (
        alt.Chart(df)
        .mark_bar(color=color)
        .encode(
            y=alt.Y("Label:N", sort="-x", axis=alt.Axis(labelLimit=200)),
            x=alt.X("Count:Q", axis=alt.Axis(tickMinStep=1)),
            tooltip=["Label", "Count"],
        )
    )
    labels = (
        alt.Chart(df)
        .mark_text(align="left", baseline="middle", dx=3, color="#16324F", fontSize=12)
        .encode(y=alt.Y("Label:N", sort="-x"), x="Count:Q", text="Count:Q")
    )
    return (bars + labels).configure_view(stroke=None)


def _rep_photo(name: str, accent: str) -> str:
    """Representative headshot from the reps/ folder, or an initials avatar."""
    reps_dir = Path(__file__).parent / "reps"
    mimes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    for ext, mime in mimes.items():
        f = reps_dir / f"{name}{ext}"
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            return (
                f'<img src="data:{mime};base64,{b64}" alt="{name}" '
                f'style="width:56px;height:56px;border-radius:50%;object-fit:cover;'
                f'border:3px solid {accent};"/>'
            )
    initials = "".join(p[0] for p in name.split()[:2]).upper() or "?"
    return (
        f'<div style="width:56px;height:56px;border-radius:50%;background:{accent};color:#FFFFFF;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-weight:700;font-size:18px;flex-shrink:0;">{initials}</div>'
    )


def _rep_card_html(
    name: str, handled: int, closed: int, escalated: int,
    pending: int, avg_res: str, accent: str,
) -> str:
    pct = round(100 * closed / handled, 1) if handled else 0.0

    def seg(n: int, color: str) -> str:
        if not n or not handled:
            return ""
        return f'<div style="width:{100 * n / handled:.1f}%;background:{color};"></div>'

    def row(dot_color: str, label: str, value: str) -> str:
        return (
            f'<div style="display:flex;justify-content:space-between;margin-top:2px;">'
            f'<span><span style="color:{dot_color};">&#9679;</span> {label}</span>'
            f'<span style="font-weight:600;">{value}</span></div>'
        )

    rows = (
        row("#10b981", "Jobs Closed", f"{closed} &middot; {pct}%")
        + row("#ef4444", "Escalated", f"{escalated}")
        + row("#f59e0b", "Pending", f"{pending}")
        + row("#64748b", "Avg Resolution", f"{avg_res} days")
    )
    return f"""
    <div style="background:linear-gradient(135deg,#ffffff,#f8fafc); border-top:5px solid {accent};
         border-radius:14px; box-shadow:0 2px 6px rgba(15,23,42,.10); padding:16px; height:100%;">
        <div style="display:flex; align-items:center; gap:12px;">
            {_rep_photo(name, accent)}
            <div>
                <div style="color:#16324F; font-size:16px; font-weight:700;">{name}</div>
                <div style="color:#64748b; font-size:12px;">{handled} tickets &amp; incidents handled</div>
            </div>
        </div>
        <div style="color:#16324F; font-size:26px; font-weight:700; margin-top:10px;">
            {pct}% <span style="font-size:13px;font-weight:600;">Closed</span>
        </div>
        <div style="display:flex; height:7px; border-radius:4px; overflow:hidden; margin:10px 0 6px 0; background:#e2e8f0;">
            {seg(closed, "#10b981")}{seg(escalated, "#ef4444")}{seg(pending, "#f59e0b")}
        </div>
        <div style="font-size:13px; color:#334155;">{rows}</div>
    </div>
    """


def _rep_cards(column: str, empty_msg: str) -> None:
    """One performance card per person found in the given column."""
    ti_work = pd.concat([tickets_f, incidents_f], ignore_index=True)
    if column not in ti_work.columns or ti_work.empty:
        st.info(empty_msg)
        return
    work = ti_work.copy()
    work[column] = work[column].astype(str).str.strip()
    work = work[work[column] != ""]
    if work.empty:
        st.info(empty_msg)
        return
    reps = list(work[column].value_counts().index)
    per_row = 3
    for start in range(0, len(reps), per_row):
        cols = st.columns(per_row)
        for col, name in zip(cols, reps[start:start + per_row]):
            g = work[work[column] == name]
            handled = len(g)
            closed = int((g["Status"] == "Resolved").sum()) if "Status" in g else 0
            escalated = int((g["Status"] == "Escalated").sum()) if "Status" in g else 0
            pending = int((g["Status"] == "Pending").sum()) if "Status" in g else 0
            rd = g["Resolution Days"].dropna() if "Resolution Days" in g else pd.Series(dtype=float)
            rd = rd[rd >= 0]
            avg_res = f"{float(rd.mean()):.1f}" if len(rd) else "--"
            accent = CARD_PALETTE[reps.index(name) % len(CARD_PALETTE)]
            with col:
                st.markdown(
                    _rep_card_html(
                        name, handled, closed, escalated, pending, avg_res, accent
                    ),
                    unsafe_allow_html=True,
                )


# ---------------- Sidebar ----------------
with st.sidebar:
    logo = Path(__file__).parent / "pillometer_logo.png"
    if logo.exists():
        st.image(str(logo), width="stretch")
    st.title("Pillometer Tracker")
    st.caption("2026 customer feedback report across the Ticket, Request and Incident Report tabs.")

    path = Path(st.text_input("Workbook path", value=str(WORKBOOK_PATH)))
    col_a, col_b = st.columns(2)
    with col_a:
        refresh_clicked = st.button("🔄 Refresh", help="Re-pull from SharePoint via browser session")
    with col_b:
        if st.button("↻ Reload file"):
            st.cache_data.clear()

    if refresh_clicked:
        with st.spinner("Pulling latest workbook from SharePoint..."):
            try:
                fetch_from_sharepoint_via_browser(path)
                st.cache_data.clear()
                st.success("Refreshed!")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Refresh failed: {exc}")

    if not path.exists():
        st.error(f"Workbook not found at {path}")
        st.stop()

    data = _load(str(path), _mtime(path))
    REPORT_YEAR = 2026

    def _this_year(df: pd.DataFrame) -> pd.DataFrame:
        if "Start date" not in df.columns:
            return df.iloc[0:0].copy()
        return df[df["Start date"].dt.year == REPORT_YEAR].copy()

    tickets = _this_year(data["tickets"])
    requests = _this_year(data["requests"])
    incidents = _this_year(data["incidents"])

    st.divider()
    st.subheader("Filters")
    all_statuses = sorted(
        set(tickets.get("Status", pd.Series(dtype=str)).dropna())
        | set(incidents.get("Status", pd.Series(dtype=str)).dropna())
    )
    status_sel = st.multiselect("Status (tickets & incidents)", all_statuses, default=all_statuses)
    pharmacy_q = st.text_input("Search pharmacy / client", "")

    st.caption("Period (applies to all 3 feedback tabs, via Start date)")
    all_start_dates = pd.concat(
        [d["Start date"] for d in (tickets, requests, incidents) if "Start date" in d.columns]
    ).dropna()
    month_options = sorted(all_start_dates.dt.to_period("M").unique())
    month_labels = ["All"] + [p.strftime("%b %Y") for p in month_options]
    month_sel = st.selectbox("Month", month_labels)
    week_options = sorted(all_start_dates.dt.isocalendar().week.dropna().unique().astype(int))
    week_sel = st.selectbox("Week of year", ["All"] + [f"Week {w}" for w in week_options])

sel_months = (
    [month_options[month_labels.index(month_sel) - 1]] if month_sel != "All" else None
)
sel_weeks = (
    [int(week_sel.removeprefix("Week "))] if week_sel != "All" else None
)

tickets_f = _filter_by_period(_filter_by_status(tickets, status_sel), sel_months, sel_weeks)
incidents_f = _filter_by_period(_filter_by_status(incidents, status_sel), sel_months, sel_weeks)
requests_f = _filter_by_period(requests, sel_months, sel_weeks)
if pharmacy_q:
    if "Pharmacy Name" in tickets_f.columns:
        tickets_f = tickets_f[
            tickets_f["Pharmacy Name"].astype(str).str.contains(pharmacy_q, case=False, na=False)
        ]
    if "Pharmacy Name" in incidents_f.columns:
        incidents_f = incidents_f[
            incidents_f["Pharmacy Name"].astype(str).str.contains(pharmacy_q, case=False, na=False)
        ]
    if "Column 1" in requests_f.columns:
        requests_f = requests_f[
            requests_f["Column 1"].astype(str).str.contains(pharmacy_q, case=False, na=False)
        ]

# ---------------- Header + KPIs ----------------
hdr_logo, hdr_text, hdr_device = st.columns([1.1, 4.0, 0.8])
with hdr_logo:
    st.image(str(Path(__file__).parent / "pillometer_logo.png"), width="stretch")
with hdr_text:
    st.title("Customer Feedback Tracker")
    st.caption(
        f"Workbook: `{path.name}` · last modified {pd.Timestamp(_mtime(path), unit='s').strftime('%Y-%m-%d %H:%M')}"
        " · Feedback channels: Tickets, Requests, Incidents"
    )
    if month_sel != "All" or week_sel != "All":
        st.caption(f"Period filter: {month_sel if month_sel != 'All' else 'Any month'}"
                   f" · {week_sel if week_sel != 'All' else 'Any week'}")
with hdr_device:
    st.image(str(Path(__file__).parent / "pillodevice.png"), width=130)

total_feedback = len(tickets_f) + len(requests_f) + len(incidents_f)

all_weeks = pd.concat([_week_numbers(d) for d in (tickets, requests, incidents)])
latest_wk = int(all_weeks.max()) if not all_weeks.empty else None
prev_wk = latest_wk - 1 if latest_wk else None
wow_help = (
    f"Week-over-week: ISO week {latest_wk} vs week {prev_wk} of {REPORT_YEAR} (unfiltered by dropdowns)"
    if latest_wk else "No dated rows this year"
)

status_series = pd.concat(
    [
        tickets_f["Status"] if "Status" in tickets_f else pd.Series(dtype=str),
        incidents_f["Status"] if "Status" in incidents_f else pd.Series(dtype=str),
    ]
).dropna()
n_resolved = int((status_series == "Resolved").sum())
pct_resolved = round(100 * n_resolved / len(status_series), 1) if len(status_series) else 0.0

tickets_by_raised = _top_counts(tickets_f["Ticket Raised For"]) if "Ticket Raised For" in tickets_f else pd.Series(dtype=int)
incidents_by_raised = _top_counts(incidents_f["Ticket Raised For"]) if "Ticket Raised For" in incidents_f else pd.Series(dtype=int)
incidents_by_cat = _top_counts(incidents_f["Incidence Category"]) if "Incidence Category" in incidents_f else pd.Series(dtype=int)

res_days = pd.concat(
    [d["Resolution Days"] for d in (tickets_f, incidents_f) if "Resolution Days" in d.columns]
).dropna()
res_days = res_days[res_days >= 0]
avg_res = float(res_days.mean()) if len(res_days) else None
ti_all = pd.concat([tickets, incidents], ignore_index=True)

WOW = "normal"  # green when up, red when down
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #DCEAF8 0%, #F2F7FC 220px, #F7FAFD 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #C9DFF5 0%, #E4F0FA 60%, #EAF4FB 100%);
        border-right: 1px solid #B7D4EE;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #16324F;
    }
    h1, h2, h3, [data-testid="stMetricLabel"] {
        color: #16324F;
    }
    .stButton > button {
        background: linear-gradient(135deg, #4A8FD9, #3B7DD8);
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3B7DD8, #2E6ABE);
        color: #FFFFFF;
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #1B5BBF;
        border-bottom-color: #3B7DD8;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        border-radius: 10px;
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #3B7DD8;
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        padding: 16px 16px 20px 16px;
        border-radius: 14px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.10);
    }
    [data-testid="stHorizontalBlock"] > div:nth-child(5) [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f5f3ff, #ede9fe); border-top: 5px solid #8b5cf6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

CH_COLORS = {"Tickets": "#3b82f6", "Requests": "#10b981", "Incidents": "#f43f5e"}
wow_total = _wow_delta([tickets, requests, incidents], latest_wk, prev_wk) if latest_wk else None
wow_color = "#dc2626" if (wow_total or "").startswith("-") else "#16a34a"
n_t, n_r, n_i = len(tickets_f), len(requests_f), len(incidents_f)

def _share(n: int) -> float:
    return round(100 * n / total_feedback, 1) if total_feedback else 0.0

bar_parts = "".join(
    f'<div style="width:{_share(n)}%; background:{CH_COLORS[k]};"></div>'
    for k, n in (("Tickets", n_t), ("Requests", n_r), ("Incidents", n_i)) if n
)
legend_rows = "".join(
    f'<div style="display:flex; justify-content:space-between; margin-top:2px;">'
    f'<span><span style="color:{CH_COLORS[k]};">&#9679;</span> {k}</span>'
    f'<span style="font-weight:600;">{n} &middot; {_share(n)}%</span></div>'
    for k, n in (("Tickets", n_t), ("Requests", n_r), ("Incidents", n_i))
)
with st.container(horizontal=True):
    st.markdown(
        f"""
        <div title="{wow_help}" style="background:linear-gradient(135deg,#eff6ff,#dbeafe);
             border-top:5px solid #3b82f6; border-radius:14px;
             box-shadow:0 2px 6px rgba(15,23,42,.10); padding:16px; height:100%;">
            <div style="color:#16324F; font-size:14px; font-weight:600;">Total Customer Feedback</div>
            <div style="color:#16324F; font-size:32px; font-weight:700; line-height:1.15;">
                {total_feedback}
                <span style="font-size:14px; font-weight:600; color:{wow_color};">{wow_total + ' WoW' if wow_total else ''}</span>
            </div>
            <div style="display:flex; height:7px; border-radius:4px; overflow:hidden; margin:10px 0 6px 0; background:#e2e8f0;">
                {bar_parts}
            </div>
            <div style="font-size:13px; color:#334155;">{legend_rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        _legend_card_html(
            "Tickets by Ticket Raised For",
            f"{int(tickets_by_raised.sum())} <span style=\"font-size:13px;font-weight:600;color:#64748b;\">tickets</span>",
            tickets_by_raised, "#06b6d4", "linear-gradient(135deg,#ecfeff,#cffafe)",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        _legend_card_html(
            "Incidents by Ticket Raised For",
            f"{int(incidents_by_raised.sum())} <span style=\"font-size:13px;font-weight:600;color:#64748b;\">incidents</span>",
            incidents_by_raised, "#f43f5e", "linear-gradient(135deg,#fff1f2,#ffe4e6)",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        _legend_card_html(
            "Ticket & Incident Status",
            f"{pct_resolved}% <span style=\"font-size:13px;font-weight:600;\">Resolved</span> "
            f"<span style=\"font-size:12px;color:#64748b;\">&middot; {n_resolved} of {len(status_series)}</span>",
            status_series.value_counts(), "#10b981", "linear-gradient(135deg,#ecfdf5,#d1fae5)",
        ),
        unsafe_allow_html=True,
    )
    st.metric(
        "Avg Resolution (days)", f"{avg_res:.1f}" if avg_res is not None else "--",
        delta=_avg_resolution_wow(ti_all, latest_wk, prev_wk) if latest_wk else None,
        delta_color="inverse", help=wow_help,
    )

# ---------------- Tabs ----------------
tab_overview, tab_tickets, tab_requests, tab_incidents, tab_raw = st.tabs(
    ["📊 Overview", "🎫 Tickets", "📨 Requests", "⚠️ Incidents", "🗂 Raw Data"]
)

with tab_overview:
    with st.container(border=True):
        st.subheader("Incidents by category")
        if len(incidents_by_cat):
            st.altair_chart(_labeled_bars(incidents_by_cat, "#f59e0b"), width="stretch")
        else:
            st.info("No incident category data.")

    left, right = st.columns([1.4, 1])
    with left:
        with st.container(border=True):
            grp = st.selectbox("Group by", ["Week", "Month"], key="wow_group")
            all_dates = pd.concat(
                [
                    d["Start date"]
                    for d in (tickets_f, requests_f, incidents_f)
                    if "Start date" in d.columns
                ]
            ).dropna()
            if all_dates.empty:
                st.info("No dated records to plot.")
            else:
                if grp == "Week":
                    periods = all_dates.dt.isocalendar().week.astype(int)
                    counts = periods.value_counts().sort_index()
                    counts.index = [f"W{int(i)}" for i in counts.index]
                else:
                    periods = all_dates.dt.to_period("M")
                    counts = periods.value_counts().sort_index()
                    counts.index = [p.strftime("%b %Y") for p in counts.index]
                st.subheader(f"Feedback progression by {grp.lower()} ({REPORT_YEAR})")
                st.altair_chart(
                    _labeled_line(counts, "#3b82f6", grp), width="stretch"
                )
    with right:
        with st.container(border=True):
            st.subheader("Top pharmacies (all tabs)")
            names = pd.concat(
                [
                    tickets_f["Pharmacy Name"] if "Pharmacy Name" in tickets_f else pd.Series(dtype=str),
                    incidents_f["Pharmacy Name"] if "Pharmacy Name" in incidents_f else pd.Series(dtype=str),
                    requests_f["Column 1"].rename("Pharmacy Name") if "Column 1" in requests_f else pd.Series(dtype=str),
                ]
            ).dropna().astype(str).str.strip()
            names = names[names != ""]
            if names.empty:
                st.info("No pharmacy data.")
            else:
                top = names.value_counts().head(10)
                st.altair_chart(_labeled_bars(top, "#06b6d4"), width="stretch")

    with st.container(border=True):
        st.subheader("Pending by priority")
        ti_pending = pd.concat([tickets_f, incidents_f], ignore_index=True)
        pending_pri = (
            ti_pending[ti_pending["Status"] == "Pending"]["Priority"]
            .dropna().astype(str).str.strip().value_counts()
            if "Status" in ti_pending and "Priority" in ti_pending else pd.Series(dtype=int)
        )
        if len(pending_pri):
            st.altair_chart(_labeled_bars(pending_pri, "#ef4444"), width="stretch")
        else:
            st.info("No pending records.")

    st.divider()
    st.subheader(f"Representative Performance ({REPORT_YEAR})")
    st.markdown("**🛠️ Jobs Handled — by Trobleshooted By**")
    st.caption("People who worked the ticket / incident.")
    _rep_cards("Trobleshooted By", "No troubleshoot data.")
    st.divider()
    st.markdown("**🚨 Escalations Owned — by Escalated To**")
    st.caption("People whom tickets / incidents were escalated to.")
    _rep_cards("Escalated To", "No escalation data.")

with tab_tickets:
    st.subheader(f"Ticket feedback ({len(tickets_f)} rows)")
    cols = [c for c in [
        "Pharmacy Name", "Priority", "Ticket Raised For", "Ticket Note",
        "Trobleshooted By", "Status", "Start date", "End date", "Resolution Days",
        "Escalated To",
    ] if c in tickets_f.columns]
    st.dataframe(tickets_f[cols], hide_index=True, width='stretch')

with tab_requests:
    st.subheader(f"Request feedback ({len(requests_f)} rows)")
    cols = [c for c in [
        "Start date", "Column 1", "Priority", "No of Request", "Feature Request",
        "Reviewed by", "Evaluating", "Notes", "End date",
    ] if c in requests_f.columns]
    st.dataframe(requests_f[cols], hide_index=True, width='stretch')

with tab_incidents:
    st.subheader(f"Incident feedback ({len(incidents_f)} rows)")
    cols = [c for c in [
        "Pharmacy Name", "Priority", "Ticket Raised For", "Incidence Category",
        "Ticket Note", "Trobleshooted By", "Status", "Escalated To",
        "Start date", "End date", "Resolution Days",
    ] if c in incidents_f.columns]
    st.dataframe(incidents_f[cols], hide_index=True, width='stretch')

with tab_raw:
    sheet = st.selectbox("Sheet", ["Ticket", "Request", "INCIDENCE REPORT"])
    st.dataframe(load_workbook(path)[
        {"Ticket": "tickets", "Request": "requests", "INCIDENCE REPORT": "incidents"}[sheet]
    ], hide_index=True, width='stretch')                                                                                                why am i getting this errorModuleNotFoundError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/pillometer-trackers/streamlit_app.py", line 12, in <module>
    from data_loader import WORKBOOK_PATH, fetch_from_sharepoint_via_browser, load_workbook
