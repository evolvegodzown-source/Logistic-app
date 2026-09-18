 import io

import textwrap

from datetime import datetime

import numpy as np

import pandas as pd

import plotly.express as px

import plotly.graph_objects as go

import requests

import streamlit as st



# ----------------------------------------------------------------------------

# PAGE CONFIG

# ----------------------------------------------------------------------------

st.set_page_config(

    page_title="DrugStoc Pharma Logistics Dashboard",

    page_icon="💊",

    layout="wide",

    initial_sidebar_state="expanded",

)



# ----------------------------------------------------------------------------

# ASSET CONFIGURATION

# ----------------------------------------------------------------------------

DATA_PATH = r"https://drugstock-my.sharepoint.com/:x:/g/personal/it_drugstoc_com/IQA5yp0kdh82Ra7YcCr-be0vAXufIjkPsYHD4yoBbt6byhs?e=MFF4su&download=1"

COVER_LOGO_URL = r"https://drugstock-my.sharepoint.com/:i:/g/personal/it_drugstoc_com/IQCURjcRKFhMQ4HunFjm4IxrAfQqHn3s3TDz3jUrWgzgw5g?e=dNiGIh&download=1"

BRAND = {

    "blue": "#1686D9",

    "blue_dark": "#0B5FA5",

    "green": "#10B981",

    "navy": "#071A2D",

    "teal": "#14B8A6",

    "amber": "#F59E0B",

    "red": "#EF4444",

}



# ----------------------------------------------------------------------------

# THEME (PERMANENT DARK MODE)

# ----------------------------------------------------------------------------

DARK = True

THEME = {

    "page": "#071421",

    "surface": "#0E2236",

    "surface_2": "#132B42",

    "text": "#F4F8FC",

    "muted": "#A9BCD0",

    "border": "rgba(255,255,255,.10)",

    "grid": "rgba(255,255,255,.10)",

    "plot_bg": "#0E2236",

    "accent_soft": "rgba(22,134,217,.18)",

}



st.markdown(

    f"""

    <style>

        :root {{

            --ds-blue: {BRAND["blue"]};

            --ds-green: {BRAND["green"]};

            --ds-red: {BRAND["red"]};

            --ds-navy: {BRAND["navy"]};

            --ds-page: {THEME["page"]};

            --ds-surface: {THEME["surface"]};

            --ds-surface-2: {THEME["surface_2"]};

            --ds-text: {THEME["text"]};

            --ds-muted: {THEME["muted"]};

            --ds-border: {THEME["border"]};

            --ds-accent-soft: {THEME["accent_soft"]};

        }}

        .stApp {{

            background:

                radial-gradient(circle at 10% 0%, rgba(22,134,217,.10), transparent 28%),

                radial-gradient(circle at 90% 0%, rgba(16,185,129,.08), transparent 25%),

                var(--ds-page);

            color: var(--ds-text);

        }}

        [data-testid="stHeader"] {{

            background: transparent !important;

        }}

        .block-container {{

            padding-top: 1.4rem;

            padding-bottom: 3rem;

            max-width: 1500px;

        }}

        h1, h2, h3, h4, h5, h6,

        [data-testid="stMarkdownContainer"] p,

        [data-testid="stMarkdownContainer"] li,

        label {{

            color: var(--ds-text) !important;

        }}

        h1 {{

            font-size: clamp(2rem, 3vw, 3rem) !important;

            letter-spacing: -1.5px !important;

            margin-bottom: .25rem !important;

        }}

        h2 {{

            font-size: 1.55rem !important;

            letter-spacing: -.4px !important;

        }}

        h3 {{

            font-size: 1.15rem !important;

            letter-spacing: -.2px !important;

        }}

        [data-testid="stCaptionContainer"] {{

            color: var(--ds-muted) !important;

        }}

        section[data-testid="stSidebar"] {{

            background: linear-gradient(180deg, #06182A 0%, #0A2339 100%) !important;

            border-right: 1px solid rgba(255,255,255,.08);

        }}

        section[data-testid="stSidebar"] * {{

            color: #F1F7FC !important;

        }}

        section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,

        section[data-testid="stSidebar"] .stButton button {{

            background: rgba(255,255,255,.08) !important;

            border: 1px solid rgba(255,255,255,.14) !important;

            border-radius: 10px !important;

        }}

        section[data-testid="stSidebar"] .stButton button {{

            width: 100%;

            font-weight: 700;

        }}

        section[data-testid="stSidebar"] .stButton button:hover {{

            border-color: var(--ds-blue) !important;

            background: rgba(22,134,217,.18) !important;

        }}

        .sidebar-brand {{

            padding: 6px 0 18px 0;

            text-align: center;

            border-bottom: 1px solid rgba(255,255,255,.12);

            margin-bottom: 16px;

        }}

        .sidebar-brand img {{

            width: 86%;

            max-height: 84px;

            object-fit: contain;

            margin-bottom: 8px;

        }}

        .sidebar-brand .brand-title {{

            font-size: .76rem;

            font-weight: 800;

            letter-spacing: .14em;

            color: #B9D7EE;

            text-transform: uppercase;

        }}

        .hero {{

            background: linear-gradient(135deg, rgba(22,134,217,.17), rgba(16,185,129,.10));

            border: 1px solid var(--ds-border);

            border-radius: 22px;

            padding: 24px 28px;

            margin-bottom: 18px;

            box-shadow: 0 12px 35px rgba(7,26,45,.08);

        }}

        .hero-top {{

            display: flex;

            align-items: center;

            gap: 18px;

        }}

        .hero-logo {{

            width: 76px;

            height: 76px;

            border-radius: 18px;

            object-fit: contain;

            background: rgba(255,255,255,.92);

            padding: 8px;

            box-shadow: 0 8px 20px rgba(7,26,45,.10);

        }}

        .eyebrow {{

            display: inline-block;

            padding: 5px 12px;

            border-radius: 999px;

            background: var(--ds-accent-soft);

            color: #1686D9 !important;

            font-size: .72rem;

            font-weight: 900;

            letter-spacing: .10em;

            text-transform: uppercase;

            margin-bottom: 8px;

        }}

        .hero-title {{

            color: var(--ds-text) !important;

            font-size: 2rem;

            line-height: 1.1;

            font-weight: 900;

            margin: 0;

        }}

        .hero-subtitle {{

            color: var(--ds-muted) !important;

            margin: 6px 0 0 0;

            font-size: .95rem;

        }}

        .status-pill {{

            display: inline-flex;

            align-items: center;

            gap: 7px;

            padding: 7px 11px;

            border-radius: 999px;

            background: rgba(16,185,129,.12);

            color: #10B981 !important;

            font-weight: 800;

            font-size: .76rem;

            margin-top: 12px;

        }}

        .status-dot {{

            width: 8px;

            height: 8px;

            border-radius: 50%;

            background: #10B981;

            box-shadow: 0 0 0 4px rgba(16,185,129,.12);

        }}

        .kpi-card {{

            position: relative;

            overflow: hidden;

            height: 154px;

            min-height: 154px;

            box-sizing: border-box;

            background: var(--ds-surface);

            border: 1px solid var(--ds-border);

            border-radius: 17px;

            padding: 17px 18px 15px 18px;

            box-shadow: 0 8px 25px rgba(7,26,45,.07);

            transition: transform .18s ease, box-shadow .18s ease;

        }}

        .kpi-card:hover {{

            transform: translateY(-3px);

            box-shadow: 0 14px 32px rgba(7,26,45,.12);

        }}

        .kpi-card::before {{

            content: "";

            position: absolute;

            left: 0;

            top: 0;

            bottom: 0;

            width: 5px;

            background: var(--kpi-accent);

        }}

        .kpi-top {{

            display: flex;

            justify-content: space-between;

            align-items: center;

            gap: 10px;

        }}

        .kpi-label {{

            color: var(--ds-muted) !important;

            font-size: .73rem;

            font-weight: 900;

            letter-spacing: .06em;

            text-transform: uppercase;

        }}

        .kpi-icon {{

            width: 34px;

            height: 34px;

            display: grid;

            place-items: center;

            border-radius: 10px;

            background: var(--kpi-soft);

            font-size: 1rem;

        }}

        .kpi-value {{

            color: var(--ds-text) !important;

            font-size: clamp(1.35rem, 1.7vw, 1.72rem);

            font-weight: 900;

            line-height: 1.05;

            white-space: nowrap;

            overflow: hidden;

            text-overflow: ellipsis;

            margin-top: 11px;

        }}

        .kpi-description {{

            color: var(--ds-muted) !important;

            font-size: .75rem;

            line-height: 1.32;

            margin-top: 7px;

            display: -webkit-box;

            -webkit-line-clamp: 2;

            -webkit-box-orient: vertical;

            overflow: hidden;

        }}

        .section-head {{

            display: flex;

            align-items: center;

            justify-content: space-between;

            gap: 12px;

            margin: 20px 0 8px 0;

        }}

        .section-title {{

            color: var(--ds-text) !important;

            font-size: 1.05rem;

            font-weight: 900;

            margin: 0;

        }}

        .section-note {{

            color: var(--ds-muted) !important;

            font-size: .76rem;

        }}

        .comparison-legend {{

            display: flex;

            flex-wrap: wrap;

            gap: 16px;

            color: var(--ds-muted);

            font-size: .76rem;

            margin: 4px 0 12px 0;

        }}

        .comparison-legend span {{

            display: inline-flex;

            align-items: center;

            gap: 6px;

        }}

        .comparison-legend i {{

            width: 11px;

            height: 11px;

            display: inline-block;

            border-radius: 2px;

        }}

        .legend-current {{ background: var(--ds-blue); }}

        .legend-previous {{ background: #587896; }}

        .legend-increase {{ background: var(--ds-green); }}

        .legend-decrease {{ background: var(--ds-red, #EF4444); }}

        .comparison-period {{

            margin: 14px 0 8px 0 !important;

            color: var(--ds-text) !important;

        }}

        .comparison-grid {{

            display: grid;

            grid-template-columns: repeat(4, minmax(0, 1fr));

            gap: 12px;

        }}

        .comparison-card {{

            background: var(--ds-surface);

            border: 1px solid var(--ds-border);

            border-radius: 12px;

            padding: 14px;

        }}

        .comparison-title {{

            color: var(--ds-text);

            font-size: .78rem;

            font-weight: 800;

            min-height: 2.2em;

        }}

        .comparison-values {{

            display: grid;

            grid-template-columns: 1fr 1fr;

            gap: 10px;

            margin-top: 12px;

        }}

        .comparison-values div {{

            display: flex;

            flex-direction: column;

            gap: 3px;

        }}

        .comparison-label {{

            color: var(--ds-muted);

            font-size: .68rem;

        }}

        .comparison-values strong {{

            color: var(--ds-text);

            font-size: 1rem;

        }}

        .comparison-change {{

            font-size: .72rem;

            font-weight: 800;

            margin-top: 12px;

        }}

        .comparison-change.increase {{ color: var(--ds-green); }}

        .comparison-change.decrease {{ color: var(--ds-red, #EF4444); }}

        @media (max-width: 900px) {{

            .comparison-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}

        }}

        @media (max-width: 520px) {{

            .comparison-grid {{ grid-template-columns: 1fr; }}

        }}

        .stTabs [data-baseweb="tab-list"] {{

            gap: 8px;

            background: transparent;

        }}

        .stTabs [data-baseweb="tab"] {{

            color: var(--ds-muted) !important;

            background: var(--ds-surface-2);

            border: 1px solid var(--ds-border);

            border-radius: 11px;

            padding: 9px 17px;

            font-weight: 800;

        }}

        .stTabs [aria-selected="true"] {{

            background: #1686D9 !important;

            color: #FFFFFF !important;

            border-color: #1686D9 !important;

        }}

        div[data-testid="stDataFrame"] {{

            border: 1px solid var(--ds-border);

            border-radius: 14px;

            overflow: hidden;

        }}

    </style>

    """,

    unsafe_allow_html=True,

)



# ----------------------------------------------------------------------------

# HELPERS

# ----------------------------------------------------------------------------

def money(value):

    return f"₦{value:,.0f}"



def fmt_num(value):

    return f"{value:,.0f}"



def comparison_periods(data_df):

    dated = data_df["Created_DT"].dropna()

    if dated.empty:

        return None



    latest_date = dated.max().normalize()

    current_week_start = latest_date - pd.Timedelta(days=latest_date.weekday())

    current_month_start = latest_date.replace(day=1)

    previous_month_end = current_month_start - pd.Timedelta(days=1)

    return {

        "WoW": (

            data_df["Created_DT"].ge(current_week_start)

            & data_df["Created_DT"].lt(current_week_start + pd.Timedelta(days=7)),

            data_df["Created_DT"].ge(current_week_start - pd.Timedelta(days=7))

            & data_df["Created_DT"].lt(current_week_start),

        ),

        "MoM": (

            data_df["Created_DT"].ge(current_month_start)

            & data_df["Created_DT"].lt(current_month_start + pd.offsets.MonthBegin(1)),

            data_df["Created_DT"].ge(previous_month_end.replace(day=1))

            & data_df["Created_DT"].lt(current_month_start),

        ),

    }



def comparison_metrics(data_df, mask):

    period = data_df.loc[mask]

    orders = len(period)

    return {

        "Order Volume": float(orders),

        "Fulfillment Rate": float(period["Is Delivered"].mean() * 100) if orders else 0.0,

        "TAT: Order to Delivery": float(period["Creation_Delivery_TAT"].mean()) if orders else 0.0,

        "TAT: Dispatch to Delivery": float(period["Shipping_TAT"].mean()) if orders else 0.0,

    }



def comparison_value(metric, value):

    if metric == "Order Volume":

        return f"{value:,.0f}"

    if metric == "Fulfillment Rate":

        return f"{value:.1f}%"

    return f"{value:.1f} hrs"



def render_comparison_section(data_df):

    periods = comparison_periods(data_df)

    if periods is None:

        show_empty_chart("No dated records are available for WoW/MoM comparison.")

        return



    st.markdown(

        "<div class='comparison-legend'>"

        "<span><i class='legend-current'></i>Current period</span>"

        "<span><i class='legend-previous'></i>Previous period</span>"

        "<span><i class='legend-increase'></i>Increase</span>"

        "<span><i class='legend-decrease'></i>Decrease</span>"

        "</div>",

        unsafe_allow_html=True,

    )

    metric_order = [

        "Order Volume",

        "Fulfillment Rate",

        "TAT: Order to Delivery",

        "TAT: Dispatch to Delivery",

    ]

    for comparison_name, (current_mask, previous_mask) in periods.items():

        current = comparison_metrics(data_df, current_mask)

        previous = comparison_metrics(data_df, previous_mask)

        cards = []

        for metric in metric_order:

            current_value = current[metric]

            previous_value = previous[metric]

            change = current_value - previous_value

            change_pct = (change / previous_value * 100) if previous_value else 0.0

            change_class = "increase" if change >= 0 else "decrease"

            change_symbol = "▲" if change >= 0 else "▼"

            change_color = BRAND["green"] if change >= 0 else BRAND["red"]

            cards.append(

                textwrap.dedent(

                    f"""

                    <div class='comparison-card'>

                        <div class='comparison-title'>{metric}</div>

                        <div class='comparison-values'>

                            <div><span class='comparison-label'>Current</span><strong>{comparison_value(metric, current_value)}</strong></div>

                            <div><span class='comparison-label'>Previous</span><strong>{comparison_value(metric, previous_value)}</strong></div>

                        </div>

                        <div class='comparison-change {change_class}' style='color: {change_color} !important;'>{change_symbol} {abs(change_pct):.1f}% vs previous</div>

                    </div>

                    """

                ).strip()

            )

        st.markdown(f"<h3 class='comparison-period'>{comparison_name}</h3>", unsafe_allow_html=True)

        st.markdown("<div class='comparison-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)



def kpi_card(label, value, description, icon="•", accent=None):

    accent = accent or BRAND["blue"]

    soft = "rgba(22,134,217,.12)" if accent == BRAND["blue"] else ("rgba(16,185,129,.12)" if accent == BRAND["green"] else ("rgba(245,158,11,.13)" if accent == BRAND["amber"] else "rgba(239,68,68,.12)"))

    return f"""

        <div class="kpi-card" style="--kpi-accent:{accent};--kpi-soft:{soft};">

            <div class="kpi-top">

                <div class="kpi-label">{label}</div>

                <div class="kpi-icon">{icon}</div>

            </div>

            <div class="kpi-value">{value}</div>

            <div class="kpi-description">{description}</div>

        </div>

    """



def render_kpis(cards):

    for row_start in range(0, len(cards), 4):

        row = cards[row_start:row_start + 4]

        cols = st.columns(4)

        for col, card in zip(cols, row):

            label, value, description, icon, accent = card

            with col:

                st.markdown(

                    kpi_card(

                        label=label,

                        value=value,

                        description=description,

                        icon=icon,

                        accent=accent,

                    ),

                    unsafe_allow_html=True,

                )



def plotly_theme(fig):

    fig.update_layout(

        template="plotly_dark",

        paper_bgcolor=THEME["plot_bg"],

        plot_bgcolor=THEME["plot_bg"],

        font=dict(color=THEME["text"]),

        margin=dict(l=24, r=24, t=60, b=28),

        hoverlabel=dict(

            bgcolor=THEME["surface"],

            font_color=THEME["text"],

        ),

        autosize=True,

    )

    fig.update_xaxes(

        showgrid=False,

        color=THEME["muted"],

        tickfont=dict(color=THEME["muted"]),

    )

    fig.update_yaxes(

        gridcolor=THEME["grid"],

        color=THEME["muted"],

        tickfont=dict(color=THEME["muted"]),

    )

    return fig



def show_empty_chart(message):

    st.info(message)



def section_header(title, note=""):

    st.markdown(

        f"""

        <div class="section-head">

            <div class="section-title">{title}</div>

            <div class="section-note">{note}</div>

        </div>

        """,

        unsafe_allow_html=True,

    )



def render_performance_trend(data_df):

    trend_df = data_df.dropna(subset=["Created_DT"]).copy()

    if trend_df.empty:

        show_empty_chart("No dated records are available for the performance trend.")

        return



    control_date, control_metric = st.columns(2)

    with control_date:

        date_granularity = st.selectbox(

            "Order Date",

            ["Week", "Month"],

            key="performance_trend_date",

        )

    with control_metric:

        metric_label = st.selectbox(

            "Metric",

            [

                "Fulfillment",

                "TAT: Creation to Delivery",

                "TAT: Dispatch to Delivery",

            ],

            key="performance_trend_metric",

        )



    if date_granularity == "Week":

        trend_df["Period"] = trend_df["Created_DT"].dt.to_period("W").dt.start_time

        period_format = "%d %b %Y"

    else:

        trend_df["Period"] = trend_df["Created_DT"].dt.to_period("M").dt.start_time

        period_format = "%b %Y"



    metric_columns = {

        "Fulfillment": ("Is Delivered", "Fulfillment Rate (%)"),

        "TAT: Creation to Delivery": ("Creation_Delivery_TAT", "Average TAT (hrs)"),

        "TAT: Dispatch to Delivery": ("Shipping_TAT", "Average TAT (hrs)"),

    }

    value_column, y_axis_title = metric_columns[metric_label]

    trend = (

        trend_df.groupby("Period", as_index=False)[value_column]

        .mean()

        .rename(columns={value_column: "Value"})

        .sort_values("Period")

    )

    if metric_label == "Fulfillment":

        trend["Value"] = trend["Value"] * 100



    if trend.empty:

        show_empty_chart("No data is available for the selected trend.")

        return



    fig = px.line(

        trend,

        x="Period",

        y="Value",

        markers=True,

        title=f"{metric_label} by Order Date ({date_granularity})",

        labels={"Period": "Order Date", "Value": y_axis_title},

    )

    fig.update_traces(

        line=dict(color=BRAND["blue"], width=3),

        marker=dict(color=BRAND["green"], size=8),

        hovertemplate=(

            f"Order Date: %{{x|{period_format}}}<br>"

            f"{y_axis_title}: %{{y:.1f}}<extra></extra>"

        ),

    )

    fig.update_layout(showlegend=False, height=390)

    st.plotly_chart(plotly_theme(fig), use_container_width=True)



def find_col(df, candidates, exact_caps_only=False):

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:

        return None

    if exact_caps_only:

        for cand in candidates:

            if cand in df.columns:

                return cand



    cols_lower = {str(c).lower().strip(): c for c in df.columns}

    for cand in candidates:

        key = str(cand).lower().strip()

        if key in cols_lower:

            return cols_lower[key]

    for cand in candidates:

        key = str(cand).lower().strip()

        for col in df.columns:

            if key in str(col).lower().strip():

                return col

    return None



def build_timestamp(data_df, date_c, time_c):

    if not date_c or date_c not in data_df.columns:

        return pd.Series(pd.NaT, index=data_df.index)

    dates = pd.to_datetime(data_df[date_c], errors="coerce")

    if time_c and time_c in data_df.columns:

        times = (

            data_df[time_c]

            .astype(str)

            .str.strip()

            .replace(["nan", "None", "<NaT>", ""], "00:00:00")

        )

        combined = dates.dt.strftime("%Y-%m-%d") + " " + times

        return pd.to_datetime(combined, errors="coerce")

    return dates



# ----------------------------------------------------------------------------

# KPI PERIOD-COMPARISON HELPERS (WoW / MoM)

# ----------------------------------------------------------------------------

COMPARE_KPIS = [

    "Order Volume",

    "Fulfilment Rate",

    "TAT: Order to Delivery",

    "TAT: Dispatch to Delivery",

]



def compute_period_kpis(frame):

    """Compute the 4 core operational KPIs for a given dataframe slice."""

    orders = int(len(frame))

    delivered = int(frame["Is Delivered"].sum()) if orders else 0

    fulfil = (delivered / orders * 100.0) if orders else 0.0

    tat_order = frame["Creation_Delivery_TAT"].mean()

    tat_dispatch = frame["Shipping_TAT"].mean()

    return {

        "Order Volume": float(orders),

        "Fulfilment Rate": float(fulfil),

        "TAT: Order to Delivery": float(tat_order) if pd.notna(tat_order) else 0.0,

        "TAT: Dispatch to Delivery": float(tat_dispatch) if pd.notna(tat_dispatch) else 0.0,

    }



def pct_change(current, previous):

    """Percentage change between two values; None if not computable."""

    if previous is None or pd.isna(previous) or previous == 0:

        return None

    return ((current - previous) / abs(previous)) * 100.0



def format_kpi_value(kpi_name, value):

    """Human-readable formatting per KPI type."""

    if kpi_name == "Order Volume":

        return fmt_num(value)

    if kpi_name == "Fulfilment Rate":

        return f"{value:.1f}%"

    return f"{value:.1f} hrs"



def comparison_pie(kpi_name, current_val, previous_val, current_label, previous_label):

    """

    Build a donut pie chart comparing the current period against the previous

    period for a single KPI. Slice size = share of the combined total.

    """

    curr = max(float(current_val), 0.0)

    prev = max(float(previous_val), 0.0)

    delta = pct_change(curr, prev)



    # For TAT metrics a decrease is an improvement; for volume/rate an increase is.

    lower_is_better = kpi_name.startswith("TAT")

    if delta is None:

        delta_color = THEME["muted"]

        delta_text = "Δ N/A (no baseline)"

    else:

        improved = (delta < 0) if lower_is_better else (delta > 0)

        delta_color = BRAND["green"] if improved else BRAND["red"]

        arrow = "▲" if delta >= 0 else "▼"

        delta_text = f"{arrow} {abs(delta):.1f}% WoW" if "W" in current_label else f"{arrow} {abs(delta):.1f}% MoM"



    fig = go.Figure(

        data=[

            go.Pie(

                labels=[

                    f"Current · {current_label}",

                    f"Previous · {previous_label}",

                ],

                values=[curr, prev],

                hole=0.58,

                sort=False,

                direction="clockwise",

                marker=dict(colors=[BRAND["blue"], "#4C6A86"]),

                textinfo="label+percent",

                textfont=dict(color=THEME["text"], size=11),

                customdata=[

                    format_kpi_value(kpi_name, curr),

                    format_kpi_value(kpi_name, prev),

                ],

                hovertemplate=(

                    "%{label}<br>Value: %{customdata}<br>"

                    "Share of combined: %{percent}<extra></extra>"

                ),

            )

        ]

    )

    fig = plotly_theme(fig)

    fig.update_layout(

        title=dict(

            text=(

                f"{kpi_name}<br>"

                f"<span style='font-size:11px;color:{THEME['muted']}'>"

                f"Current: {format_kpi_value(kpi_name, curr)} &nbsp;·&nbsp; "

                f"Previous: {format_kpi_value(kpi_name, prev)} &nbsp;·&nbsp; "

                f"<span style='color:{delta_color};font-weight:800;'>{delta_text}</span>"

                f"</span>"

            ),

            font=dict(size=13, color=THEME["text"]),

        ),

        showlegend=True,

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=-0.25,

            x=0.5,

            xanchor="center",

            font=dict(size=10, color=THEME["muted"]),

        ),

        height=330,

        margin=dict(l=10, r=10, t=92, b=10),

    )

    return fig



# ----------------------------------------------------------------------------

# DATA LOADING

# ----------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Fetching live logistics data...")

def load_data(path=DATA_PATH):

    headers = {

        "User-Agent": (

            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

            "AppleWebKit/537.36 (KHTML, like Gecko) "

            "Chrome/120.0.0.0 Safari/537.36"

        )

    }

    response = requests.get(path, headers=headers, timeout=25)

    response.raise_for_status()

    source = io.BytesIO(response.content)



    all_sheets = pd.read_excel(source, sheet_name=None)

    combined_df = pd.concat(all_sheets.values(), ignore_index=True)

    return combined_df



# ----------------------------------------------------------------------------

# SIDEBAR HEADER & REFRESH BUTTON

# ----------------------------------------------------------------------------

st.sidebar.markdown(

    f"""

    <div class="sidebar-brand">

        <img src="{COVER_LOGO_URL}" alt="DrugStoc logo"/>

        <div class="brand-title">Pharma Logistics Intelligence</div>

    </div>

    """,

    unsafe_allow_html=True,

)



if st.sidebar.button("🔄 Refresh Data"):

    st.cache_data.clear()

    st.rerun()



# ----------------------------------------------------------------------------

# DATA PROCESSING

# ----------------------------------------------------------------------------

try:

    df_raw = load_data(DATA_PATH)

except Exception as exc:

    st.error("Unable to load the logistics workbook.")

    st.info("Verify the live link contains valid Excel tables.")

    with st.expander("Technical details"):

        st.code(str(exc))

    st.stop()



df_raw = df_raw.copy()

df_raw.columns = [str(c).strip() for c in df_raw.columns]



# AUTOMATIC COLUMN MAPPING

col_client = find_col(df_raw, ["Client Name", "Client", "Customer Name", "Pharmacy", "Hospital"])

col_so = find_col(df_raw, ["SO", "Sales Order", "SO Number"])

col_value = find_col(df_raw, ["Order Value", "Value", "Amount", "Sales Value", "Total Value"])

col_qty = find_col(df_raw, ["N0 OF CTN'S", "NO OF CTN'S", "Qty CTN", "Quantity", "CTN"])

col_date = find_col(df_raw, ["Date Column", "Date", "Created Date", "Creation Date", "Order Date"])

col_create_time = find_col(df_raw, ["Created Time", "Creation Time", "Order Time"])

col_region = find_col(df_raw, ["Region", "Zone", "State", "Territory"])

col_status = find_col(df_raw, ["STATUS"], exact_caps_only=True) or find_col(df_raw, ["STATUS"])

col_captain = find_col(df_raw, ["Captain", "Rider", "Driver", "Captain Name"])

col_order_type = find_col(df_raw, ["Order Type", "Type", "Category"])

col_ship = find_col(df_raw, ["Ship Date", "Dispatch Date", "Pickup Date"])

col_dispatch_time = find_col(df_raw, ["Dispatch Time", "Ship Time", "Time Dispatched"])

col_deliv = find_col(df_raw, ["Delivery Date", "Delivered Date"])

col_delivery_time = find_col(df_raw, ["Delivery Time", "Time Delivered"])



if not col_client:

    st.error("Unable to identify the Client column automatically in the dataset.")

    st.stop()



if not col_value:

    df_raw["__OrderValue"] = 0.0

    col_value = "__OrderValue"

if not col_qty:

    df_raw["__Quantity"] = 0.0

    col_qty = "__Quantity"

if not col_region:

    df_raw["__Region"] = "Unassigned"

    col_region = "__Region"



df = df_raw.copy()



# Date handling

if col_date and col_date in df.columns:

    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")

    df["Week"] = df[col_date].dt.isocalendar().week.fillna(0).astype(int)

    df["Year"] = df[col_date].dt.year.fillna(0).astype(int)

    df["Month"] = df[col_date].dt.month.fillna(0).astype(int)

    df["Month Label"] = df[col_date].dt.strftime("%B %Y").fillna("Unassigned Date")

    df["Week Label"] = "W" + df["Week"].astype(str).str.zfill(2) + " - " + df["Year"].astype(str)

else:

    df["Month Label"] = "Unassigned Date"

    df["Week Label"] = "Unassigned Date"



df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)

df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)

df["Created_DT"] = build_timestamp(df, col_date, col_create_time)

df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)

dispatch_date_col = col_ship if col_ship and col_ship in df.columns else col_date

df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)



df["Creation_Delivery_TAT"] = (

    (df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0

)

df["Creation_Delivery_TAT"] = df["Creation_Delivery_TAT"].apply(

    lambda x: x if pd.notna(x) and x >= 0 else np.nan

)

df["Shipping_TAT"] = (

    (df["Delivery_DT"] - df["Dispatch_DT"]).dt.total_seconds() / 3600.0

)

df["Shipping_TAT"] = df["Shipping_TAT"].apply(

    lambda x: x if pd.notna(x) and x >= 0 else np.nan

)



# 

