# ----------------------------------------------------------------------------
# METRIC COMPUTATIONS & ENRICHMENT
# ----------------------------------------------------------------------------
def enrich_data(df):
    """Enriches data frame with parsed timestamps and calculated TAT columns."""
    df = df.copy()

    # Column identification
    col_inv_date = find_col(df, ["Invoice Date", "InvoiceDate", "Invoiced Date"])
    col_inv_time = find_col(df, ["Invoice Time", "InvoiceTime", "Invoiced Time"])
    col_disp_date = find_col(df, ["Dispatch Date", "DispatchDate", "Shipping Date"])
    col_disp_time = find_col(df, ["Dispatch Time", "DispatchTime", "Shipping Time"])
    col_del_date = find_col(df, ["Delivery Date", "DeliveryDate"])
    col_del_time = find_col(df, ["Delivery Time", "DeliveryTime"])
    col_created_date = find_col(df, ["Creation Date", "Created Date", "Order Date"])
    col_created_time = find_col(df, ["Creation Time", "Created Time", "Order Time"])

    # Build datetimes
    df["Created_DT"] = build_timestamp(df, col_created_date, col_created_time)
    df["Invoice_DT"] = build_timestamp(df, col_inv_date, col_inv_time)
    df["Dispatch_DT"] = build_timestamp(df, col_disp_date, col_disp_time)
    df["Delivery_DT"] = build_timestamp(df, col_del_date, col_del_time)

    # Calculate Turnaround Times (TATs) in hours
    df["Creation_Delivery_TAT"] = (
        (df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0
    )
    df["Shipping_TAT"] = (
        (df["Delivery_DT"] - df["Dispatch_DT"]).dt.total_seconds() / 3600.0
    )
    # NEW: TAT from Invoice Date/Time to Dispatch Date/Time
    df["Invoice_Dispatch_TAT"] = (
        (df["Dispatch_DT"] - df["Invoice_DT"]).dt.total_seconds() / 3600.0
    )

    return df


# ----------------------------------------------------------------------------
# WOW / MOM COMPARISON SECTION
# ----------------------------------------------------------------------------
def comparison_metrics(data_df, mask, fuel_bounds=None):
    period = data_df.loc[mask]
    orders = (
        int(period[col_client].count())
        if col_client and col_client in period.columns
        else len(period)
    )
    fuel_cost = 0.0
    if fuel_bounds and fuel is not None and col_fuel_date and col_fuel_cost:
        f_start, f_end = fuel_bounds
        f_mask = (fuel[col_fuel_date] >= f_start) & (fuel[col_fuel_date] < f_end)
        fuel_cost = float(fuel.loc[f_mask, col_fuel_cost].sum())

    return {
        "Order Volume": float(orders),
        "Fulfillment Rate": float(period["Is Delivered"].mean() * 100) if orders else 0.0,
        "TAT: Order to Delivery": float(period["Creation_Delivery_TAT"].mean()) if orders else 0.0,
        "TAT: Invoice to Dispatch": float(period["Invoice_Dispatch_TAT"].mean()) if orders else 0.0,
        "TAT: Dispatch to Delivery": float(period["Shipping_TAT"].mean()) if orders else 0.0,
        "Fuel Cost": fuel_cost,
    }


def render_comparison_section(data_df):
    periods = comparison_periods(data_df)
    if periods is None:
        show_empty_chart("No dated records are available for WoW/MoM comparison.")
        return

    st.markdown(
        "<div class='comparison-legend'>"
        "<span><i class='legend-current'></i>Current period</span>"
        "<span><i class='legend-previous'></i>Previous period</span>"
        "<span><i class='legend-increase'></i>Improvement (green)</span>"
        "<span><i class='legend-decrease'></i>Decline (red) — for TAT metrics lower is better</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    metric_order = [
        "Order Volume",
        "Fulfillment Rate",
        "TAT: Order to Delivery",
        "TAT: Invoice to Dispatch",
        "TAT: Dispatch to Delivery",
        "Fuel Cost",
    ]

    # Added "TAT: Invoice to Dispatch" so lower TAT highlights green as an improvement
    lower_is_better = (
        "TAT: Order to Delivery",
        "TAT: Invoice to Dispatch",
        "TAT: Dispatch to Delivery",
    )

    for comparison_name, (
        current_mask,
        previous_mask,
        curr_bounds,
        prev_bounds,
    ) in periods.items():
        current = comparison_metrics(data_df, current_mask, curr_bounds)
        previous = comparison_metrics(data_df, previous_mask, prev_bounds)
        cards = []
        for metric in metric_order:
            current_value = current[metric]
            previous_value = previous[metric]
            change = current_value - previous_value
            change_pct = (
                (change / previous_value * 100) if previous_value else 0.0
            )
            if change == 0:
                change_class, change_color = "", THEME["muted"]
            else:
                improved = (
                    (change < 0) if metric in lower_is_better else (change > 0)
                )
                change_class = "increase" if improved else "decrease"
                change_color = BRAND["green"] if improved else BRAND["red"]
            change_symbol = "▲" if change >= 0 else "▼"
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
        st.markdown(
            f"<h3 class='comparison-period'>{comparison_name}</h3>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='comparison-grid'>" + "".join(cards) + "</div>",
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------------------
# PERFORMANCE TREND CHART
# ----------------------------------------------------------------------------
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
                "TAT: Invoice to Dispatch",
                "TAT: Dispatch to Delivery",
            ],
            key="performance_trend_metric",
        )

    if date_granularity == "Week":
        trend_df["Period"] = (
            trend_df["Created_DT"]
            - pd.to_timedelta((trend_df["Created_DT"].dt.weekday + 1) % 7, unit="D")
        ).dt.normalize()
        period_format = "%d %b %Y"
    else:
        trend_df["Period"] = trend_df["Created_DT"].dt.to_period("M").dt.start_time
        period_format = "%b %Y"

    metric_columns = {
        "Fulfillment": ("Is Delivered", "Fulfillment Rate (%)"),
        "TAT: Creation to Delivery": ("Creation_Delivery_TAT", "Average TAT (hrs)"),
        "TAT: Invoice to Dispatch": ("Invoice_Dispatch_TAT", "Average TAT (hrs)"),
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


# ----------------------------------------------------------------------------
# EXECUTIVE KPI RENDERING EXAMPLE
# ----------------------------------------------------------------------------
def render_executive_kpis(df):
    avg_inv_dispatch_tat = df["Invoice_Dispatch_TAT"].mean()

    kpi_cards_data = [
        ("Total Orders", fmt_num(len(df)), "Total placed orders", "📦", BRAND["blue"]),
        ("Fulfillment", f"{df['Is Delivered'].mean()*100:.1f}%", "Delivered order ratio", "✅", BRAND["green"]),
        ("TAT: Order to Del.", f"{df['Creation_Delivery_TAT'].mean():.1f} hrs", "Avg creation to delivery", "⏱️", BRAND["amber"]),
        ("TAT: Inv. to Dispatch", f"{avg_inv_dispatch_tat:.1f} hrs", "Avg invoice to dispatch", "🏷️", BRAND["teal"]),
        ("TAT: Dispatch to Del.", f"{df['Shipping_TAT'].mean():.1f} hrs", "Avg dispatch to delivery", "🚚", BRAND["blue"]),
    ]
    render_kpis(kpi_cards_data)
