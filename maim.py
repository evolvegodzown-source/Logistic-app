import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ----------------------------------------------------------------------------
# PATH CONFIGURATION
# ----------------------------------------------------------------------------
DATA_PATH = r"https://drugstock-my.sharepoint.com/personal/it_drugstoc_com/Documents/OPERATIONS/LOGISTICS%20DASH/Logistics_DB.xlsx?web=1"
IMAGE_PATH = r"C:\Users\IT\OneDrive - DrugStoc\OPERATIONS\LOGISTICS DASH\images (1).png"

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
# PHARMACEUTICAL BRANDING & CUSTOM CSS WITH HIGH-VISIBILITY KPIs
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Pharma Clean Palette */
        :root {
            --pharma-navy: #0B192C;
            --pharma-blue: #1E3E62;
            --pharma-teal: #00A86B;
            --pharma-bg: #F4F7F9;
            --card-border: #CBD5E1;
        }

        .main { background-color: var(--pharma-bg); }

        /* High-Visibility Metric Cards Design */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-top: 4px solid #00A86B !important;
            border-radius: 10px !important;
            padding: 16px 18px !important;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Pure Black High-Contrast KPI Label & Value Colors */
        div[data-testid="stMetricLabel"] > div { 
            font-weight: 800 !important; 
            color: #000000 !important; /* Pure Black for Maximum Visibility */
            font-size: 0.9rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }
        div[data-testid="stMetricLabel"] label {
            color: #000000 !important; /* Secondary target for Streamlit label element */
        }
        div[data-testid="stMetricValue"] > div { 
            font-size: 1.7rem !important; 
            font-weight: 800 !important;
            color: #0F172A !important; 
        }
        div[data-testid="stMetricDelta"] {
            font-weight: 700 !important;
        }

        /* Sidebar Medical Dark Theme */
        section[data-testid="stSidebar"] { 
            background-color: #0B192C !important; 
        }
        section[data-testid="stSidebar"] * { 
            color: #F1F5F9 !important; 
        }
        
        /* Headers and Tabs */
        h1, h2, h3 { color: #0B192C; font-weight: 700; }
        .block-container { padding-top: 1.2rem; }
        
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff; 
            border-radius: 8px 8px 0 0;
            padding: 10px 20px; 
            border: 1px solid var(--card-border);
            font-weight: 600;
            color: #1E293B;
        }
        .stTabs [aria-selected="true"] {
            background-color: #00A86B !important;
            color: #ffffff !important;
        }
        
        /* Pharma Badge Header */
        .pharma-badge {
            background-color: #E6F4EA;
            color: #00875A;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading pharmaceutical distribution records...")
def load_data(path=None, uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.read_excel(path)

def find_col(df, candidates):
    """Best-effort match of a target column against common header variants."""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower().strip() in cols_lower:
            return cols_lower[cand.lower().strip()]
    for cand in candidates:
        for col in df.columns:
            if cand.lower().strip() in col.lower().strip():
                return col
    return None

# ----------------------------------------------------------------------------
# SIDEBAR HEADER & LOGO INTEGRATION
# ----------------------------------------------------------------------------
if os.path.exists(IMAGE_PATH):
    st.sidebar.image(IMAGE_PATH, use_container_width=True)
else:
    st.sidebar.title("💊 DrugStoc Logistics")
    st.sidebar.caption("Pharmaceutical Supply Chain")

st.sidebar.markdown("<span style='font-size:0.8rem; opacity:0.8;'>Rx Cold-Chain & Distribution Operations</span>", unsafe_allow_html=True)
st.sidebar.markdown("---")

uploaded = st.sidebar.file_uploader("Upload Logistics_DB.xlsx (override)", type=["xlsx", "xls"])

df_raw = None
load_error = None
try:
    df_raw = load_data(DATA_PATH if uploaded is None else None, uploaded)
except Exception as e:
    load_error = e

if df_raw is None:
    st.error(
        f"Could not load dataset from:\n\n`{DATA_PATH}`\n\n"
        f"Error Details: {load_error}\n\n"
        "Please use the file uploader in the sidebar to upload `Logistics_DB.xlsx`."
    )
    st.stop()

df_raw.columns = [str(c).strip() for c in df_raw.columns]

# ----------------------------------------------------------------------------
# COLUMN AUTO-DETECTION & MAPPING
# ----------------------------------------------------------------------------
auto = {
    "client":        find_col(df_raw, ["Client Name", "Client", "Customer Name", "Customer", "Pharmacy", "Hospital"]),
    "value":         find_col(df_raw, ["Order Value", "Value", "Amount", "Sales Value", "Total Value"]),
    "qty":           find_col(df_raw, ["Qty CTN", "Quantity CTN", "Qty (CTN)", "Quantity", "Qty", "Cartons"]),
    "date":          find_col(df_raw, ["Order Date", "Date", "Dispatch Date"]),
    "region":        find_col(df_raw, ["Region", "Zone", "State", "Territory"]),
    "status":        find_col(df_raw, ["Delivery Status", "Status"]),
    "captain":       find_col(df_raw, ["Captain", "Rider", "Driver", "Captain Name", "Dispatcher"]),
    "order_type":    find_col(df_raw, ["Order Type", "Type", "Category", "Channel", "Order_Type"]),
    "ship_date":     find_col(df_raw, ["Ship Date", "Dispatch Date", "Pickup Date", "Date"]),
    "dispatch_time": find_col(df_raw, ["Dispatch Time", "Ship Time", "Time Dispatched", "Departure Time", "Time Out"]),
    "deliv_date":    find_col(df_raw, ["Delivery Date", "Delivered Date", "Date Delivered"]),
    "delivery_time": find_col(df_raw, ["Delivery Time", "Time Delivered", "Arrival Time", "Time In"]),
    "duration":      find_col(df_raw, ["Shipping Duration", "Delivery Duration", "Duration", "Lead Time"]),
}

with st.sidebar.expander("⚙️ Data Column Mapping", expanded=any(v is None for k, v in auto.items() if k not in ("ship_date", "deliv_date", "duration", "dispatch_time", "delivery_time"))):
    options = ["(none)"] + list(df_raw.columns)

    def picker(label, key):
        default = auto[key] if auto[key] in df_raw.columns else "(none)"
        idx = options.index(default) if default in options else 0
        choice = st.selectbox(label, options, index=idx, key=f"map_{key}")
        return None if choice == "(none)" else choice

    col_client        = picker("Facility/Client Name", "client")
    col_value         = picker("Order Value (₦)", "value")
    col_qty           = picker("Quantity (CTN)", "qty")
    col_date          = picker("Order Date", "date")
    col_region        = picker("Delivery Zone/Region", "region")
    col_status        = picker("Delivery Status", "status")
    col_captain       = picker("Logistics Captain", "captain")
    col_order_type    = picker("Order Type", "order_type")
    col_ship          = picker("Dispatch Date", "ship_date")
    col_dispatch_time = picker("Dispatch Time", "dispatch_time")
    col_deliv         = picker("Delivery Date", "deliv_date")
    col_delivery_time = picker("Delivery Time", "delivery_time")
    col_duration      = picker("Pre-calculated Duration (Optional)", "duration")

required_missing = [n for n, v in [("Client Name", col_client), ("Order Value", col_value),
                                    ("Qty CTN", col_qty), ("Order Date", col_date),
                                    ("Region", col_region), ("Delivery Status", col_status)]
                     if v is None]
if required_missing:
    st.error(f"Missing required mapping for: **{', '.join(required_missing)}**. "
             "Please assign them under 'Data Column Mapping' in the sidebar.")
    st.stop()

df = df_raw.copy()

# ----------------------------------------------------------------------------
# DATA CLEANING & TIMESTAMPS FOR DISPATCH DURATION IN HOURS
# ----------------------------------------------------------------------------
df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
df = df.dropna(subset=[col_date])
df["Week"] = df[col_date].dt.isocalendar().week.astype(int)
df["Year"] = df[col_date].dt.year.astype(int)
df["Week Label"] = "W" + df["Week"].astype(str).str.zfill(2) + " - " + df["Year"].astype(str)

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)

# Helper function to parse date and time combined
def build_timestamp(data_df, date_c, time_c):
    if not date_c or date_c not in data_df.columns:
        return pd.Series(pd.NaT, index=data_df.index)
    
    dates = pd.to_datetime(data_df[date_c], errors="coerce")
    if time_c and time_c in data_df.columns:
        times = data_df[time_c].astype(str).str.strip().replace(["nan", "None", "<NaT>", ""], "00:00:00")
        combined_str = dates.dt.strftime("%Y-%m-%d") + " " + times
        return pd.to_datetime(combined_str, errors="coerce")
    return dates

# Calculate Dispatch & Delivery Timestamps
dispatch_date_col = col_ship if (col_ship and col_ship in df.columns) else col_date
df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)
df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)

# Calculate Dispatch Duration in Hours
if col_deliv and col_deliv in df.columns:
    duration_hrs = (df["Delivery_DT"] - df["Dispatch_DT"]).dt.total_seconds() / 3600.0
    # Clean up unrealistic negative durations
    duration_hrs = duration_hrs.apply(lambda x: x if (pd.notna(x) and x >= 0) else np.nan)
    df["Dispatch Duration (hrs)"] = duration_hrs
elif col_duration and col_duration in df.columns:
    # If duration exists in days, convert to hours as fallback
    df["Dispatch Duration (hrs)"] = pd.to_numeric(df[col_duration], errors="coerce") * 24.0
else:
    df["Dispatch Duration (hrs)"] = np.nan

df[col_status] = df[col_status].astype(str).str.strip().str.title()
DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)

# ----------------------------------------------------------------------------
# SIDEBAR DROPDOWN FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Operations Filters")

# Dropdown Filter 1: Week Selection
week_options = ["All Weeks"] + sorted(df["Week Label"].unique(), key=lambda w: (w.split(" - ")[1], w.split(" - ")[0]), reverse=True)
selected_week = st.sidebar.selectbox("Filter by Delivery Week", week_options)

# Dropdown Filter 2: Region Selection
region_options = ["All Regions"] + sorted(df[col_region].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Filter by Region / Hub", region_options)

# Dropdown Filter 3: Order Type Selection
if col_order_type and col_order_type in df.columns:
    order_type_options = ["All Order Types"] + sorted(df[col_order_type].dropna().astype(str).unique().tolist())
else:
    order_type_options = ["All Order Types"]
selected_order_type = st.sidebar.selectbox("Filter by Order Type", order_type_options)

# Dropdown Filter 4: Delivery Status Selection
status_options = ["All Statuses"] + sorted(df[col_status].dropna().unique().tolist())
selected_status = st.sidebar.selectbox("Filter by Order Status", status_options)

# Apply Filter Logic
filtered = df.copy()

if selected_week != "All Weeks":
    filtered = filtered[filtered["Week Label"] == selected_week]

if selected_region != "All Regions":
    filtered = filtered[filtered[col_region] == selected_region]

if selected_order_type != "All Order Types" and col_order_type and col_order_type in filtered.columns:
    filtered = filtered[filtered[col_order_type].astype(str) == selected_order_type]

if selected_status != "All Statuses":
    filtered = filtered[filtered[col_status] == selected_status]

if filtered.empty:
    st.warning("No pharmaceutical delivery records match the current filter criteria.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(f"📦 Total Records: **{len(df):,}** | Filtered Result: **{len(filtered):,}**")

# ----------------------------------------------------------------------------
# MAIN DASHBOARD HEADER
# ----------------------------------------------------------------------------
st.markdown('<div class="pharma-badge">HEALTHCARE SUPPLY CHAIN MONITOR</div>', unsafe_allow_html=True)
st.title("🚚 DrugStoc Logistics Dashboard")
st.caption(f"Live Operations Tracker | Last Refreshed: {datetime.now().strftime('%d %b %Y, %H:%M')} | "
           f"Week: **{selected_week}** | Zone: **{selected_region}** | Type: **{selected_order_type}**")

tab_overview, tab_captains, tab_data = st.tabs(["📊 Executive Overview", "🧑‍✈️ Captain & Rider Efficiency", "🗂️ Audit & Raw Data"])

# ============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ============================================================================
with tab_overview:
    total_orders = filtered[col_client].count()
    total_value = filtered[col_value].sum()
    avg_duration_hrs = filtered["Dispatch Duration (hrs)"].mean()
    total_qty = filtered[col_qty].sum()
    delivered_count = filtered["Is Delivered"].sum()
    delivery_pct = (delivered_count / total_orders * 100) if total_orders else 0
    avg_order_value = total_value / total_orders if total_orders else 0
    unique_clients = filtered[col_client].nunique()

    # Format Avg Delivery Duration for KPI
    if pd.notna(avg_duration_hrs):
        if avg_duration_hrs < 24:
            duration_str = f"{avg_duration_hrs:.1f} hrs"
        else:
            days = avg_duration_hrs / 24.0
            duration_str = f"{avg_duration_hrs:.1f} hrs ({days:.1f}d)"
    else:
        duration_str = "N/A"

    # Key Performance Indicators Row 1 (High Visibility)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Dispensed Orders", f"{total_orders:,}")
    c2.metric("Total Order Value", f"₦{total_value:,.0f}")
    c3.metric("Fulfillment Rate", f"{delivery_pct:.1f}%", f"{int(delivered_count)}/{int(total_orders)} Delivered")
    c4.metric("Average Delivery Duration", duration_str)

    st.markdown("<br>", unsafe_allow_html=True)
    c5, c6, c7 = st.columns(3)
    c5.metric("Total Volume Shipped", f"{total_qty:,.0f} CTN")
    c6.metric("Avg Order Value", f"₦{avg_order_value:,.0f}")
    c7.metric("Active Health Facilities", f"{unique_clients:,}")

    st.markdown("---")
    
    # Analytics Row 1
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Distribution Volume by Region")
        region_summary = filtered.groupby(col_region).agg(
            Orders=(col_client, "count"), Value=(col_value, "sum")
        ).reset_index().sort_values("Orders", ascending=False)
        
        fig = px.bar(
            region_summary, x=col_region, y="Orders", color=col_region,
            text="Orders", template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Dark2
        )
        fig.update_layout(showlegend=False, height=380, margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Fulfillment Status Breakdown")
        status_summary = filtered[col_status].value_counts().reset_index()
        status_summary.columns = ["Status", "Count"]
        
        fig = px.pie(
            status_summary, names="Status", values="Count", hole=0.5, 
            template="plotly_white",
            color_discrete_sequence=["#00A86B", "#1E3E62", "#E63946", "#FFB703"]
        )
        fig.update_layout(height=380, margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    # Analytics Row 2
    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Weekly Distribution Value Trend")
        week_summary = filtered.groupby(["Year", "Week", "Week Label"]).agg(
            Value=(col_value, "sum"), Orders=(col_client, "count")
        ).reset_index().sort_values(["Year", "Week"])
        
        fig = px.line(
            week_summary, x="Week Label", y="Value", markers=True, template="plotly_white",
            line_shape="spline"
        )
        fig.update_traces(line_color="#00A86B", line_width=3)
        fig.update_layout(height=380, xaxis_title="Week", yaxis_title="Value (₦)")
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.subheader("Weekly Carton Volume (CTN)")
        qty_week = filtered.groupby("Week Label")[col_qty].sum().reset_index()
        
        fig2 = px.area(qty_week, x="Week Label", y=col_qty, template="plotly_white")
        fig2.update_traces(fillcolor="rgba(0, 168, 107, 0.25)", line_color="#00A86B")
        fig2.update_layout(height=380, xaxis_title="Week", yaxis_title="Quantity (Cartons)")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 10 Health Facilities / Accounts by Value")
    top_clients = filtered.groupby(col_client).agg(
        Orders=(col_client, "count"), Value=(col_value, "sum")
    ).reset_index().sort_values("Value", ascending=False).head(10)
    
    fig = px.bar(
        top_clients, x="Value", y=col_client, orientation="h", text="Orders",
        template="plotly_white", color="Value", color_continuous_scale="Tealgrn"
    )
    fig.update_layout(height=420, yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 2: CAPTAIN PERFORMANCE
# ============================================================================
with tab_captains:
    if col_captain is None:
        st.info("No Delivery Captain/Rider column mapped. Select your rider column in sidebar settings.")
    else:
        cap_df = filtered.dropna(subset=[col_captain])
        st.subheader("Rider & Captain Performance Metrics")

        cap_summary = cap_df.groupby(col_captain).agg(
            Total_Orders=(col_client, "count"),
            Total_Value=(col_value, "sum"),
            Total_Qty=(col_qty, "sum"),
            Avg_Duration_Hrs=("Dispatch Duration (hrs)", "mean"),
            Delivered=("Is Delivered", "sum"),
        ).reset_index()
        cap_summary["Delivery Rate %"] = (cap_summary["Delivered"] / cap_summary["Total_Orders"] * 100).round(1)
        cap_summary = cap_summary.sort_values("Total_Orders", ascending=False)

        best_captain = cap_summary.iloc[0][col_captain] if not cap_summary.empty else "N/A"
        best_delivery = cap_summary.sort_values("Delivery Rate %", ascending=False).iloc[0]
        fastest = cap_summary.sort_values("Avg_Duration_Hrs", ascending=True).iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Active Fleet Captains", f"{cap_summary.shape[0]:,}")
        m2.metric("Highest Dispatch Captain", str(best_captain))
        m3.metric("Top Reliability Score", f"{best_delivery[col_captain]}", f"{best_delivery['Delivery Rate %']:.1f}%")
        m4.metric("Fastest Delivery Duration", f"{fastest[col_captain]}",
                  f"{fastest['Avg_Duration_Hrs']:.1f} hrs" if pd.notna(fastest['Avg_Duration_Hrs']) else "N/A")

        st.markdown("### ")
        col_e, col_f = st.columns(2)
        
        with col_e:
            st.subheader("Total Orders Handled per Captain")
            fig = px.bar(
                cap_summary, x=col_captain, y="Total_Orders", text="Total_Orders",
                color="Total_Orders", template="plotly_white", color_continuous_scale="Viridis"
            )
            fig.update_layout(height=400, coloraxis_showscale=False, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

        with col_f:
            st.subheader("Successful Delivery Rate (%)")
            fig = px.bar(
                cap_summary.sort_values("Delivery Rate %"), x="Delivery Rate %", y=col_captain,
                orientation="h", text="Delivery Rate %", template="plotly_white",
                color="Delivery Rate %", color_continuous_scale="Emrld"
            )
            fig.update_layout(height=400, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Comprehensive Captain Scorecard")
        display_cap = cap_summary.rename(columns={
            col_captain: "Captain / Rider", 
            "Total_Orders": "Total Dispatches", 
            "Total_Value": "Order Value",
            "Total_Qty": "Volume (CTN)", 
            "Avg_Duration_Hrs": "Avg Delivery Duration (Hrs)",
            "Delivered": "Completed Deliveries"
        })
        st.dataframe(
            display_cap.style.format({
                "Order Value": "₦{:,.0f}", 
                "Volume (CTN)": "{:,.0f}",
                "Avg Delivery Duration (Hrs)": "{:.1f}", 
                "Delivery Rate %": "{:.1f}%"
            }),
            use_container_width=True, hide_index=True
        )

# ============================================================================
# TAB 3: AUDIT & RAW DATA
# ============================================================================
with tab_data:
    st.subheader("Filtered Delivery Logs")
    st.dataframe(filtered, use_container_width=True, height=500)
    
    st.download_button(
        "⬇️ Download Filtered Audit Report (CSV)",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"DrugStoc_Logistics_Export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
