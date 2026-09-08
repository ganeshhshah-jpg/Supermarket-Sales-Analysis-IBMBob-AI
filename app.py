import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Supermarket Sales Analysis",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .main { background-color: #f7f9fc; }

    /* Metric card style */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    div[data-testid="metric-container"] > label {
        font-size: 13px !important;
        color: #57606a !important;
        font-weight: 600;
        letter-spacing: 0.4px;
    }
    div[data-testid="metric-container"] > div {
        font-size: 26px !important;
        font-weight: 700;
        color: #1f2328 !important;
    }

    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 700;
        color: #1f2328;
        margin-top: 8px;
        margin-bottom: 4px;
        padding-bottom: 6px;
        border-bottom: 2px solid #3b82d4;
        display: inline-block;
    }

    /* Insight box */
    .insight-box {
        background: #eef4ff;
        border-left: 4px solid #3b82d4;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0 16px 0;
        font-size: 14px;
        color: #1f2328;
        line-height: 1.6;
    }

    /* Warning box */
    .warn-box {
        background: #fff8e6;
        border-left: 4px solid #f59e0b;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0 16px 0;
        font-size: 14px;
        color: #1f2328;
        line-height: 1.6;
    }

    /* Success box */
    .success-box {
        background: #ecfdf5;
        border-left: 4px solid #10b981;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0 16px 0;
        font-size: 14px;
        color: #1f2328;
        line-height: 1.6;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #1f2328;
        color: #ffffff;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label {
        color: #c9d1d9 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    /* Dataframe */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Tab active */
    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 3px solid #3b82d4 !important;
        color: #3b82d4 !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# STEP 1 — LOAD & ENRICH DATA
# ─────────────────────────────────────────────
REQUIRED_COLUMNS = {
    "Invoice ID", "Date", "Branch", "City", "Customer Type",
    "Gender", "Product", "Category", "Quantity", "Unit Price",
    "Payment", "Rating", "Sales",
}

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return _enrich(df)


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Month_Name"] = df["Date"].dt.strftime("%b %Y")
    df["Day_of_Week"] = df["Date"].dt.day_name()
    df["Calculated_Sales"] = df["Quantity"] * df["Unit Price"]
    df["Sales_Match"] = np.isclose(df["Sales"], df["Calculated_Sales"], atol=0.02)
    return df


DATA_PATH = "supermarket_sales.csv"
_base_df = load_data(DATA_PATH)


# ─────────────────────────────────────────────
# SIDEBAR — UPLOAD + FILTERS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛒 Supermarket Sales")

    # ── Upload CSV ────────────────────────────
    st.markdown("### 📂 Upload Additional Data")
    uploaded_file = st.file_uploader(
        "Add CSV to dataset (max 200 MB)",
        type=["csv"],
        help="Upload a CSV with the same columns as the base dataset. "
             "Duplicate Invoice IDs are automatically removed.",
    )

    if uploaded_file is not None:
        # Enforce 200 MB size limit
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > 200:
            st.error(f"❌ File is {file_size_mb:.1f} MB — limit is 200 MB.")
            uploaded_df = None
        else:
            try:
                raw_upload = pd.read_csv(uploaded_file)
                missing_cols = REQUIRED_COLUMNS - set(raw_upload.columns)
                if missing_cols:
                    st.error(
                        f"❌ Missing columns in uploaded file:\n\n"
                        + ", ".join(sorted(missing_cols))
                    )
                    uploaded_df = None
                else:
                    uploaded_df = _enrich(raw_upload[list(_base_df.columns.intersection(raw_upload.columns))])
                    new_rows = len(uploaded_df)
                    st.success(f"✅ Loaded **{new_rows:,}** rows from `{uploaded_file.name}`")
            except Exception as e:
                st.error(f"❌ Could not parse file: {e}")
                uploaded_df = None
    else:
        uploaded_df = None

    # Merge base + uploaded
    if uploaded_df is not None:
        combined = pd.concat([_base_df, uploaded_df], ignore_index=True)
        # Drop duplicate Invoice IDs — keep last (uploaded takes precedence)
        before_dedup = len(combined)
        combined = combined.drop_duplicates(subset=["Invoice ID"], keep="last")
        dupes_removed = before_dedup - len(combined)
        if dupes_removed:
            st.info(f"ℹ️ {dupes_removed} duplicate Invoice ID(s) removed.")
        df_raw = combined.reset_index(drop=True)
    else:
        df_raw = _base_df.copy()

    total_rows = len(df_raw)

    st.markdown("---")
    # ── Filters ──────────────────────────────
    st.markdown("### Filters")

    all_branches = sorted(df_raw["Branch"].unique())
    sel_branches = st.multiselect("Branch", all_branches, default=all_branches)

    all_cities = sorted(df_raw["City"].unique())
    sel_cities = st.multiselect("City", all_cities, default=all_cities)

    all_cats = sorted(df_raw["Category"].unique())
    sel_cats = st.multiselect("Category", all_cats, default=all_cats)

    all_ctypes = sorted(df_raw["Customer Type"].unique())
    sel_ctypes = st.multiselect("Customer Type", all_ctypes, default=all_ctypes)

    all_pay = sorted(df_raw["Payment"].unique())
    sel_pay = st.multiselect("Payment Method", all_pay, default=all_pay)

    date_min = df_raw["Date"].min().date()
    date_max = df_raw["Date"].max().date()
    date_range = st.date_input("Date Range", value=(date_min, date_max),
                                min_value=date_min, max_value=date_max)

    st.markdown("---")
    uploaded_label = (
        f"Base: {len(_base_df):,} rows &nbsp;|&nbsp; Uploaded: {len(uploaded_df):,} rows"
        if uploaded_df is not None
        else f"Data: {total_rows:,} rows"
    )
    st.markdown(
        f"<small style='color:#8b949e;'>{uploaded_label} | 13 Columns</small>",
        unsafe_allow_html=True,
    )

# Apply filters
start_date, end_date = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_min, date_max)
df = df_raw[
    df_raw["Branch"].isin(sel_branches) &
    df_raw["City"].isin(sel_cities) &
    df_raw["Category"].isin(sel_cats) &
    df_raw["Customer Type"].isin(sel_ctypes) &
    df_raw["Payment"].isin(sel_pay) &
    (df_raw["Date"].dt.date >= start_date) &
    (df_raw["Date"].dt.date <= end_date)
].copy()


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# 🛒 Supermarket Sales Analysis Dashboard")
st.markdown(
    f"<p style='color:#57606a;font-size:14px;margin-top:-10px;'>Analysing <b>{len(df):,}</b> transactions "
    f"from <b>{start_date}</b> to <b>{end_date}</b></p>",
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tabs = st.tabs([
    "📋 Data Overview",
    "📊 Sales Summary",
    "🏷️ Category Analysis",
    "🏙️ Branch & City",
    "👥 Customer Insights",
    "💳 Payment & Rating",
    "📅 Time Trends",
    "💡 Business Insights",
])

tab_overview, tab_summary, tab_cat, tab_branch, tab_cust, tab_pay, tab_time, tab_biz = tabs


# ═══════════════════════════════════════════════
# TAB 1 — DATA OVERVIEW
# ═══════════════════════════════════════════════
with tab_overview:
    st.markdown('<span class="section-header">Step 1 & 2 — Data Loading & Quality Check</span>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rows", f"{len(df_raw):,}")
    col2.metric("Columns", f"{len(df_raw.columns)}")
    col3.metric("Missing Values", f"{df_raw.isnull().sum().sum()}")
    col4.metric("Duplicate Rows", f"{df_raw.duplicated().sum()}")

    st.markdown("#### Dataset Schema")
    schema_data = []
    for col_name in df_raw.columns:
        null_count = df_raw[col_name].isnull().sum()
        unique_count = df_raw[col_name].nunique()
        schema_data.append({
            "Column": col_name,
            "Data Type": str(df_raw[col_name].dtype),
            "Null Count": null_count,
            "Unique Values": unique_count,
            "Sample": str(df_raw[col_name].iloc[0]),
        })
    st.dataframe(pd.DataFrame(schema_data), use_container_width=True, hide_index=True)

    # Sales calculation verification
    st.markdown("#### Step 3 — Sales Verification (Qty × Unit Price)")
    mismatches = df_raw[~df_raw["Sales_Match"]]
    if len(mismatches) == 0:
        st.markdown(
            f'<div class="success-box">✅ <b>All {len(df_raw):,} Sales values match</b> the recalculated '
            'Quantity × Unit Price (within ₹0.02 rounding tolerance).</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="warn-box">⚠️ <b>{len(mismatches)} rows</b> have a mismatch between '
            f'Sales column and Quantity × Unit Price.</div>',
            unsafe_allow_html=True
        )
        st.dataframe(mismatches[["Invoice ID", "Quantity", "Unit Price", "Sales", "Calculated_Sales"]],
                     use_container_width=True)

    st.markdown("#### Preview — First 20 Rows")
    display_cols = ["Invoice ID", "Date", "Branch", "City", "Customer Type",
                    "Gender", "Product", "Category", "Quantity", "Unit Price",
                    "Sales", "Payment", "Rating"]
    st.dataframe(
        df_raw[display_cols].head(20).style.format({
            "Unit Price": "₹{:.2f}",
            "Sales": "₹{:.2f}",
            "Rating": "{:.1f}",
        }),
        use_container_width=True, hide_index=True
    )

    st.markdown("#### Descriptive Statistics")
    num_cols = ["Quantity", "Unit Price", "Sales", "Rating"]
    st.dataframe(
        df_raw[num_cols].describe().T.style.format("{:.2f}"),
        use_container_width=True
    )


# ═══════════════════════════════════════════════
# TAB 2 — SALES SUMMARY (KPIs + Step 4)
# ═══════════════════════════════════════════════
with tab_summary:
    st.markdown('<span class="section-header">Step 4 — Group & Summarize</span>', unsafe_allow_html=True)

    total_sales = df["Sales"].sum()
    total_qty = df["Quantity"].sum()
    avg_order = df["Sales"].mean()
    avg_rating = df["Rating"].mean()
    total_txn = len(df)
    avg_unit_price = df["Unit Price"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Revenue", f"₹{total_sales:,.2f}")
    c2.metric("📦 Total Quantity Sold", f"{total_qty:,}")
    c3.metric("🧾 Total Transactions", f"{total_txn:,}")

    c4, c5, c6 = st.columns(3)
    c4.metric("🧮 Avg Order Value", f"₹{avg_order:,.2f}")
    c5.metric("💲 Avg Unit Price", f"₹{avg_unit_price:,.2f}")
    c6.metric("⭐ Avg Customer Rating", f"{avg_rating:.2f} / 5")

    st.markdown("#### Revenue by Category — Summary Table")
    cat_summary = df.groupby("Category").agg(
        Transactions=("Invoice ID", "count"),
        Total_Qty=("Quantity", "sum"),
        Total_Sales=("Sales", "sum"),
        Avg_Order=("Sales", "mean"),
        Avg_Unit_Price=("Unit Price", "mean"),
        Avg_Rating=("Rating", "mean"),
    ).reset_index().sort_values("Total_Sales", ascending=False)
    cat_summary["% of Revenue"] = (cat_summary["Total_Sales"] / cat_summary["Total_Sales"].sum() * 100).round(2)

    st.dataframe(
        cat_summary.style.format({
            "Total_Sales": "₹{:,.2f}",
            "Avg_Order": "₹{:,.2f}",
            "Avg_Unit_Price": "₹{:,.2f}",
            "Avg_Rating": "{:.2f}",
            "% of Revenue": "{:.1f}%",
        }).bar(subset=["Total_Sales"], color="#93c5fd"),
        use_container_width=True, hide_index=True
    )

    st.markdown("#### Branch-wise Summary")
    branch_summary = df.groupby(["Branch", "City"]).agg(
        Transactions=("Invoice ID", "count"),
        Total_Sales=("Sales", "sum"),
        Avg_Order=("Sales", "mean"),
        Avg_Rating=("Rating", "mean"),
    ).reset_index().sort_values("Total_Sales", ascending=False)

    st.dataframe(
        branch_summary.style.format({
            "Total_Sales": "₹{:,.2f}",
            "Avg_Order": "₹{:,.2f}",
            "Avg_Rating": "{:.2f}",
        }).bar(subset=["Total_Sales"], color="#6ee7b7"),
        use_container_width=True, hide_index=True
    )

    # ── Download Summary as CSV ───────────────────
    st.markdown("---")
    st.markdown("#### 📥 Download Summary")

    @st.cache_data
    def build_summary_csv(cat_df: pd.DataFrame, branch_df: pd.DataFrame) -> bytes:
        """Combine category and branch summaries into one downloadable CSV."""
        cat_export = cat_df.copy()
        cat_export.insert(0, "Summary Type", "Category")
        cat_export.rename(columns={"Category": "Group"}, inplace=True)

        branch_export = branch_df.copy()
        branch_export.insert(0, "Summary Type", "Branch")
        branch_export["Group"] = branch_export["Branch"] + " — " + branch_export["City"]
        branch_export.drop(columns=["Branch", "City"], inplace=True)
        branch_export["Total_Qty"] = ""
        branch_export["Avg_Unit_Price"] = ""
        branch_export["% of Revenue"] = ""

        # Align columns
        all_cols = [
            "Summary Type", "Group", "Transactions", "Total_Qty",
            "Total_Sales", "Avg_Order", "Avg_Unit_Price", "Avg_Rating", "% of Revenue",
        ]
        cat_export = cat_export.reindex(columns=all_cols)
        branch_export = branch_export.reindex(columns=all_cols)

        combined = pd.concat([cat_export, branch_export], ignore_index=True)
        return combined.to_csv(index=False).encode("utf-8")

    # Build the summaries needed for export (plain DataFrames, not styled)
    cat_sum_export = df.groupby("Category").agg(
        Transactions=("Invoice ID", "count"),
        Total_Qty=("Quantity", "sum"),
        Total_Sales=("Sales", "sum"),
        Avg_Order=("Sales", "mean"),
        Avg_Unit_Price=("Unit Price", "mean"),
        Avg_Rating=("Rating", "mean"),
    ).reset_index().sort_values("Total_Sales", ascending=False)
    cat_sum_export["% of Revenue"] = (
        cat_sum_export["Total_Sales"] / cat_sum_export["Total_Sales"].sum() * 100
    ).round(2)

    branch_sum_export = df.groupby(["Branch", "City"]).agg(
        Transactions=("Invoice ID", "count"),
        Total_Sales=("Sales", "sum"),
        Avg_Order=("Sales", "mean"),
        Avg_Rating=("Rating", "mean"),
    ).reset_index().sort_values("Total_Sales", ascending=False)

    csv_bytes = build_summary_csv(cat_sum_export, branch_sum_export)

    dl_col1, dl_col2 = st.columns([1, 3])
    with dl_col1:
        st.download_button(
            label="⬇️ Download Summary as CSV",
            data=csv_bytes,
            file_name="supermarket_sales_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dl_col2:
        st.markdown(
            "<p style='color:#57606a;font-size:13px;padding-top:8px;'>"
            "Downloads the combined Category &amp; Branch summary table "
            f"({len(cat_sum_export) + len(branch_sum_export)} rows) "
            "reflecting the current filters.</p>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════
# TAB 3 — CATEGORY ANALYSIS
# ═══════════════════════════════════════════════
with tab_cat:
    st.markdown('<span class="section-header">Step 5 — Category Charts</span>', unsafe_allow_html=True)

    cat_rev = df.groupby("Category")["Sales"].sum().reset_index().sort_values("Sales", ascending=False)
    cat_qty = df.groupby("Category")["Quantity"].sum().reset_index().sort_values("Quantity", ascending=False)
    cat_avg = df.groupby("Category")["Sales"].mean().reset_index().sort_values("Sales", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_bar = px.bar(
            cat_rev, x="Category", y="Sales",
            title="Total Revenue by Category",
            color="Sales",
            color_continuous_scale="Blues",
            text=cat_rev["Sales"].apply(lambda x: f"₹{x:,.0f}"),
            labels={"Sales": "Revenue (₹)"}
        )
        fig_bar.update_traces(textposition="outside", textfont_size=11)
        fig_bar.update_layout(
            xaxis_tickangle=-30, showlegend=False,
            coloraxis_showscale=False, height=420,
            plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
            font_family="system-ui",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        fig_pie = px.pie(
            cat_rev, names="Category", values="Sales",
            title="Revenue Share by Category",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.4,
        )
        fig_pie.update_traces(textposition="outside", textinfo="percent+label")
        fig_pie.update_layout(height=420, font_family="system-ui",
                               paper_bgcolor="#ffffff")
        st.plotly_chart(fig_pie, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig_qty = px.bar(
            cat_qty, x="Category", y="Quantity",
            title="Total Quantity Sold by Category",
            color="Quantity", color_continuous_scale="Purples",
            text="Quantity", labels={"Quantity": "Units Sold"},
        )
        fig_qty.update_traces(textposition="outside")
        fig_qty.update_layout(xaxis_tickangle=-30, showlegend=False,
                               coloraxis_showscale=False, height=400,
                               plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                               font_family="system-ui")
        st.plotly_chart(fig_qty, use_container_width=True)

    with col4:
        fig_avg = px.bar(
            cat_avg, x="Category", y="Sales",
            title="Average Order Value by Category",
            color="Sales", color_continuous_scale="Oranges",
            text=cat_avg["Sales"].apply(lambda x: f"₹{x:,.0f}"),
            labels={"Sales": "Avg Order (₹)"},
        )
        fig_avg.update_traces(textposition="outside")
        fig_avg.update_layout(xaxis_tickangle=-30, showlegend=False,
                               coloraxis_showscale=False, height=400,
                               plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                               font_family="system-ui")
        st.plotly_chart(fig_avg, use_container_width=True)

    # Product-level breakdown
    st.markdown("#### Top 15 Products by Revenue")
    prod_rev = (df.groupby(["Product", "Category"])["Sales"]
                .sum().reset_index()
                .sort_values("Sales", ascending=True).tail(15))
    fig_prod = px.bar(
        prod_rev, x="Sales", y="Product", orientation="h",
        color="Category", title="Top 15 Products by Revenue",
        labels={"Sales": "Revenue (₹)", "Product": ""},
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_prod.update_layout(height=500, plot_bgcolor="#f7f9fc",
                            paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_prod, use_container_width=True)


# ═══════════════════════════════════════════════
# TAB 4 — BRANCH & CITY
# ═══════════════════════════════════════════════
with tab_branch:
    st.markdown('<span class="section-header">Branch & City Performance</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    branch_sales = df.groupby("Branch")["Sales"].sum().reset_index().sort_values("Sales", ascending=False)
    city_sales = df.groupby("City")["Sales"].sum().reset_index().sort_values("Sales", ascending=False)

    with col1:
        fig_b = px.bar(
            branch_sales, x="Branch", y="Sales",
            title="Revenue by Branch",
            color="Branch", text=branch_sales["Sales"].apply(lambda x: f"₹{x:,.0f}"),
            color_discrete_sequence=["#3b82d4", "#7c5cd8", "#10b981", "#f59e0b"],
            labels={"Sales": "Revenue (₹)"},
        )
        fig_b.update_traces(textposition="outside")
        fig_b.update_layout(showlegend=False, height=380, plot_bgcolor="#f7f9fc",
                             paper_bgcolor="#ffffff", font_family="system-ui")
        st.plotly_chart(fig_b, use_container_width=True)

    with col2:
        fig_c = px.bar(
            city_sales, x="City", y="Sales",
            title="Revenue by City",
            color="City", text=city_sales["Sales"].apply(lambda x: f"₹{x:,.0f}"),
            color_discrete_sequence=["#3b82d4", "#7c5cd8", "#10b981", "#f59e0b"],
            labels={"Sales": "Revenue (₹)"},
        )
        fig_c.update_traces(textposition="outside")
        fig_c.update_layout(showlegend=False, height=380, plot_bgcolor="#f7f9fc",
                             paper_bgcolor="#ffffff", font_family="system-ui")
        st.plotly_chart(fig_c, use_container_width=True)

    # Category breakdown per branch
    st.markdown("#### Category Revenue Breakdown per Branch")
    bc = df.groupby(["Branch", "Category"])["Sales"].sum().reset_index()
    fig_bc = px.bar(
        bc, x="Branch", y="Sales", color="Category",
        title="Category Revenue per Branch (Stacked)",
        barmode="stack", labels={"Sales": "Revenue (₹)"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_bc.update_layout(height=430, plot_bgcolor="#f7f9fc",
                          paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_bc, use_container_width=True)

    # Treemap
    st.markdown("#### Revenue Treemap — City → Category")
    treemap_df = df.groupby(["City", "Category"])["Sales"].sum().reset_index()
    fig_tm = px.treemap(
        treemap_df, path=["City", "Category"], values="Sales",
        title="Revenue Treemap: City → Category",
        color="Sales", color_continuous_scale="RdYlGn",
    )
    fig_tm.update_layout(height=460, paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_tm, use_container_width=True)


# ═══════════════════════════════════════════════
# TAB 5 — CUSTOMER INSIGHTS
# ═══════════════════════════════════════════════
with tab_cust:
    st.markdown('<span class="section-header">Customer Insights</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # Member vs Normal
    ctype_sales = df.groupby("Customer Type").agg(
        Total_Sales=("Sales", "sum"),
        Transactions=("Invoice ID", "count"),
        Avg_Order=("Sales", "mean"),
    ).reset_index()

    with col1:
        fig_ct = px.pie(
            ctype_sales, names="Customer Type", values="Total_Sales",
            title="Revenue: Member vs Normal",
            color_discrete_sequence=["#3b82d4", "#7c5cd8"],
            hole=0.45,
        )
        fig_ct.update_traces(textinfo="percent+label+value",
                              texttemplate="%{label}<br>₹%{value:,.0f} (%{percent})")
        fig_ct.update_layout(height=380, font_family="system-ui",
                               paper_bgcolor="#ffffff")
        st.plotly_chart(fig_ct, use_container_width=True)

    with col2:
        gender_sales = df.groupby("Gender")["Sales"].sum().reset_index()
        fig_g = px.pie(
            gender_sales, names="Gender", values="Sales",
            title="Revenue by Gender",
            color_discrete_sequence=["#10b981", "#f59e0b"],
            hole=0.45,
        )
        fig_g.update_traces(textinfo="percent+label+value",
                              texttemplate="%{label}<br>₹%{value:,.0f} (%{percent})")
        fig_g.update_layout(height=380, font_family="system-ui",
                              paper_bgcolor="#ffffff")
        st.plotly_chart(fig_g, use_container_width=True)

    # Gender × Category heatmap
    st.markdown("#### Category Preference by Gender")
    gc = df.groupby(["Gender", "Category"])["Sales"].sum().reset_index()
    fig_gc = px.bar(
        gc, x="Category", y="Sales", color="Gender",
        barmode="group", title="Category Revenue by Gender",
        labels={"Sales": "Revenue (₹)"},
        color_discrete_sequence=["#10b981", "#f59e0b"],
    )
    fig_gc.update_layout(xaxis_tickangle=-30, height=400,
                          plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                          font_family="system-ui")
    st.plotly_chart(fig_gc, use_container_width=True)

    # Customer type × Category
    st.markdown("#### Category Spend: Members vs Normal")
    ctc = df.groupby(["Customer Type", "Category"])["Sales"].sum().reset_index()
    fig_ctc = px.bar(
        ctc, x="Category", y="Sales", color="Customer Type",
        barmode="group", title="Category Revenue: Member vs Normal",
        labels={"Sales": "Revenue (₹)"},
        color_discrete_sequence=["#3b82d4", "#7c5cd8"],
    )
    fig_ctc.update_layout(xaxis_tickangle=-30, height=400,
                           plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                           font_family="system-ui")
    st.plotly_chart(fig_ctc, use_container_width=True)

    # Scatter: Rating vs Sales
    st.markdown("#### Rating vs Order Value")
    fig_sc = px.scatter(
        df, x="Rating", y="Sales", color="Category",
        title="Customer Rating vs Order Value",
        hover_data=["Product", "Branch", "Quantity"],
        opacity=0.7, size_max=10,
        color_discrete_sequence=px.colors.qualitative.Set1,
        labels={"Sales": "Order Value (₹)"},
    )
    fig_sc.update_layout(height=430, plot_bgcolor="#f7f9fc",
                          paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_sc, use_container_width=True)


# ═══════════════════════════════════════════════
# TAB 6 — PAYMENT & RATING
# ═══════════════════════════════════════════════
with tab_pay:
    st.markdown('<span class="section-header">Payment Methods & Ratings</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    pay_sales = df.groupby("Payment").agg(
        Total_Sales=("Sales", "sum"),
        Transactions=("Invoice ID", "count"),
        Avg_Order=("Sales", "mean"),
    ).reset_index().sort_values("Total_Sales", ascending=False)

    with col1:
        fig_pay = px.bar(
            pay_sales, x="Payment", y="Total_Sales",
            title="Revenue by Payment Method",
            color="Payment", text=pay_sales["Total_Sales"].apply(lambda x: f"₹{x:,.0f}"),
            color_discrete_sequence=["#3b82d4", "#7c5cd8", "#10b981", "#f59e0b", "#ef4444"],
            labels={"Total_Sales": "Revenue (₹)"},
        )
        fig_pay.update_traces(textposition="outside")
        fig_pay.update_layout(showlegend=False, height=380,
                               plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                               font_family="system-ui")
        st.plotly_chart(fig_pay, use_container_width=True)

    with col2:
        fig_pay_pie = px.pie(
            pay_sales, names="Payment", values="Transactions",
            title="Transaction Share by Payment Method",
            color_discrete_sequence=["#3b82d4", "#7c5cd8", "#10b981", "#f59e0b", "#ef4444"],
            hole=0.4,
        )
        fig_pay_pie.update_layout(height=380, font_family="system-ui",
                                   paper_bgcolor="#ffffff")
        st.plotly_chart(fig_pay_pie, use_container_width=True)

    st.markdown("#### Average Rating by Category")
    cat_rating = df.groupby("Category")["Rating"].mean().reset_index().sort_values("Rating", ascending=False)
    fig_cr = px.bar(
        cat_rating, x="Category", y="Rating",
        title="Average Customer Rating by Category",
        color="Rating", color_continuous_scale="RdYlGn",
        text=cat_rating["Rating"].apply(lambda x: f"{x:.2f}"),
        range_y=[0, 5.5],
        labels={"Rating": "Avg Rating"},
    )
    fig_cr.update_traces(textposition="outside")
    fig_cr.update_layout(xaxis_tickangle=-30, height=400, coloraxis_showscale=False,
                          plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                          font_family="system-ui")
    st.plotly_chart(fig_cr, use_container_width=True)

    st.markdown("#### Rating Distribution")
    fig_hist = px.histogram(
        df, x="Rating", nbins=20,
        title="Distribution of Customer Ratings",
        color_discrete_sequence=["#3b82d4"],
        labels={"Rating": "Customer Rating", "count": "Frequency"},
    )
    fig_hist.update_layout(height=380, plot_bgcolor="#f7f9fc",
                            paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_hist, use_container_width=True)


# ═══════════════════════════════════════════════
# TAB 7 — TIME TRENDS
# ═══════════════════════════════════════════════
with tab_time:
    st.markdown('<span class="section-header">Sales Trends Over Time</span>', unsafe_allow_html=True)

    # Monthly trend
    monthly = df.groupby("Month").agg(
        Total_Sales=("Sales", "sum"),
        Transactions=("Invoice ID", "count"),
    ).reset_index().sort_values("Month")

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=monthly["Month"], y=monthly["Total_Sales"],
        mode="lines+markers+text",
        name="Revenue",
        line=dict(color="#3b82d4", width=2.5),
        marker=dict(size=7),
        text=monthly["Total_Sales"].apply(lambda x: f"₹{x:,.0f}"),
        textposition="top center", textfont=dict(size=10),
    ))
    fig_line.update_layout(
        title="Monthly Revenue Trend",
        xaxis_title="Month", yaxis_title="Revenue (₹)",
        height=400, plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
        font_family="system-ui",
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # Monthly revenue by category
    st.markdown("#### Monthly Revenue by Category")
    mc = df.groupby(["Month", "Category"])["Sales"].sum().reset_index()
    fig_mc = px.line(
        mc, x="Month", y="Sales", color="Category",
        title="Monthly Revenue per Category",
        markers=True,
        labels={"Sales": "Revenue (₹)"},
        color_discrete_sequence=px.colors.qualitative.Set1,
    )
    fig_mc.update_layout(height=440, plot_bgcolor="#f7f9fc",
                          paper_bgcolor="#ffffff", font_family="system-ui",
                          xaxis_tickangle=-30)
    st.plotly_chart(fig_mc, use_container_width=True)

    # Day of week
    st.markdown("#### Revenue by Day of Week")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = df.groupby("Day_of_Week")["Sales"].sum().reindex(day_order).reset_index()
    fig_dow = px.bar(
        dow, x="Day_of_Week", y="Sales",
        title="Total Revenue by Day of Week",
        color="Sales", color_continuous_scale="Blues",
        text=dow["Sales"].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else ""),
        labels={"Sales": "Revenue (₹)", "Day_of_Week": "Day"},
    )
    fig_dow.update_traces(textposition="outside")
    fig_dow.update_layout(coloraxis_showscale=False, height=400,
                           plot_bgcolor="#f7f9fc", paper_bgcolor="#ffffff",
                           font_family="system-ui")
    st.plotly_chart(fig_dow, use_container_width=True)

    # Cumulative sales
    st.markdown("#### Cumulative Revenue Over Time")
    daily = df.groupby("Date")["Sales"].sum().reset_index().sort_values("Date")
    daily["Cumulative_Sales"] = daily["Sales"].cumsum()
    fig_cum = px.area(
        daily, x="Date", y="Cumulative_Sales",
        title="Cumulative Revenue Growth",
        labels={"Cumulative_Sales": "Cumulative Revenue (₹)", "Date": "Date"},
        color_discrete_sequence=["#3b82d4"],
    )
    fig_cum.update_layout(height=380, plot_bgcolor="#f7f9fc",
                           paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_cum, use_container_width=True)


# ═══════════════════════════════════════════════
# TAB 8 — BUSINESS INSIGHTS
# ═══════════════════════════════════════════════
with tab_biz:
    st.markdown('<span class="section-header">Step 6 — Business Decisions & Recommendations</span>', unsafe_allow_html=True)

    # Compute key facts
    top_cat = df.groupby("Category")["Sales"].sum().idxmax()
    top_cat_val = df.groupby("Category")["Sales"].sum().max()
    top_city = df.groupby("City")["Sales"].sum().idxmax()
    top_city_val = df.groupby("City")["Sales"].sum().max()
    top_product = df.groupby("Product")["Sales"].sum().idxmax()
    top_product_val = df.groupby("Product")["Sales"].sum().max()
    top_branch = df.groupby("Branch")["Sales"].sum().idxmax()
    best_day = df.groupby("Day_of_Week")["Sales"].sum().idxmax()
    best_payment = df.groupby("Payment")["Transactions"].apply(lambda x: x.sum() if hasattr(x, '__len__') else x).idxmax() if "Transactions" in df.columns else df.groupby("Payment")["Invoice ID"].count().idxmax()
    top_cust_type = df.groupby("Customer Type")["Sales"].sum().idxmax()
    bottom_cat = df.groupby("Category")["Sales"].sum().idxmin()
    low_rated_cat = df.groupby("Category")["Rating"].mean().idxmin()
    low_rated_val = df.groupby("Category")["Rating"].mean().min()
    high_rated_cat = df.groupby("Category")["Rating"].mean().idxmax()
    high_rated_val = df.groupby("Category")["Rating"].mean().max()

    st.markdown("### 🔑 Key Findings")

    st.markdown(f"""
    <div class="success-box">
    <b>🏆 Top Performing Category:</b> <b>{top_cat}</b> — generating ₹{top_cat_val:,.2f} in total revenue. 
    Focus on stocking this category adequately and running targeted promotions to sustain momentum.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="success-box">
    <b>🏙️ Top City:</b> <b>{top_city}</b> — ₹{top_city_val:,.2f} in revenue.
    Prioritise inventory replenishment and staff deployment in {top_city} to match demand.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="success-box">
    <b>🥇 Best-Selling Product:</b> <b>{top_product}</b> — ₹{top_product_val:,.2f} revenue.
    Keep this product in a prominent aisle position and ensure it is never out of stock.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="insight-box">
    <b>💳 Preferred Payment:</b> <b>{best_payment}</b> is the most-used payment method.
    Ensure reliable infrastructure for this channel and consider exclusive cashback deals to encourage repeat visits.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="insight-box">
    <b>👥 Customer Loyalty:</b> <b>{top_cust_type}</b> customers account for the higher share of revenue.
    A loyalty programme with exclusive discounts can convert Normal customers into Members and increase lifetime value.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="insight-box">
    <b>📅 Best Sales Day:</b> <b>{best_day}</b> records the highest footfall.
    Schedule flash sales, extra staff, and restocking runs on {best_day}s to capitalise on peak traffic.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="warn-box">
    <b>⚠️ Lowest-Rated Category:</b> <b>{low_rated_cat}</b> has an average rating of {low_rated_val:.2f}/5.
    Investigate product quality, freshness, or pricing issues in this category and gather targeted customer feedback.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="success-box">
    <b>⭐ Best-Rated Category:</b> <b>{high_rated_cat}</b> scores {high_rated_val:.2f}/5.
    Leverage this satisfaction in marketing collateral and use it as a benchmark for other categories.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="warn-box">
    <b>📉 Underperforming Category:</b> <b>{bottom_cat}</b> has the lowest total revenue.
    Evaluate whether this category should be repriced, repositioned, or replaced with higher-demand products.
    </div>
    """, unsafe_allow_html=True)

    # Summary table
    st.markdown("### 📊 Decision Summary Table")
    decisions = pd.DataFrame({
        "Business Area": [
            "Inventory & Stocking",
            "City-Level Expansion",
            "Product Placement",
            "Payment Infrastructure",
            "Customer Retention",
            "Staff Scheduling",
            "Quality Improvement",
            "Category Strategy",
        ],
        "Observation": [
            f"{top_cat} is the top revenue category",
            f"{top_city} is the highest revenue city",
            f"{top_product} is the best-selling product",
            f"{best_payment} dominates payment transactions",
            f"{top_cust_type} customers drive more revenue",
            f"{best_day} records highest sales",
            f"{low_rated_cat} has lowest avg rating ({low_rated_val:.2f})",
            f"{bottom_cat} has the lowest total revenue",
        ],
        "Recommended Action": [
            f"Increase stock levels for {top_cat}; run promotions",
            f"Scale up operations and inventory in {top_city}",
            f"Ensure {top_product} is always available; front-aisle placement",
            f"Maintain {best_payment} uptime; launch cashback campaigns",
            f"Introduce or expand membership loyalty programme",
            f"Run {best_day} flash sales and deploy extra staff",
            f"Audit {low_rated_cat} quality and pricing; gather feedback",
            f"Reprice or reduce shelf space for {bottom_cat}",
        ],
    })
    st.dataframe(decisions, use_container_width=True, hide_index=True)

    # Revenue vs Rating quadrant chart
    st.markdown("### 📈 Revenue vs. Rating — Category Quadrant")
    quad_df = df.groupby("Category").agg(
        Revenue=("Sales", "sum"),
        Avg_Rating=("Rating", "mean"),
        Transactions=("Invoice ID", "count"),
    ).reset_index()
    rev_median = quad_df["Revenue"].median()
    rat_median = quad_df["Avg_Rating"].median()

    fig_quad = px.scatter(
        quad_df, x="Avg_Rating", y="Revenue",
        size="Transactions", color="Category",
        text="Category", title="Revenue vs. Avg Rating per Category",
        labels={"Revenue": "Total Revenue (₹)", "Avg_Rating": "Avg Customer Rating"},
        color_discrete_sequence=px.colors.qualitative.Safe,
        size_max=45,
    )
    fig_quad.add_vline(x=rat_median, line_dash="dash", line_color="#57606a",
                        annotation_text="Median Rating", annotation_position="top right")
    fig_quad.add_hline(y=rev_median, line_dash="dash", line_color="#57606a",
                        annotation_text="Median Revenue", annotation_position="top right")
    fig_quad.update_traces(textposition="top center")
    fig_quad.update_layout(height=480, plot_bgcolor="#f7f9fc",
                            paper_bgcolor="#ffffff", font_family="system-ui")
    st.plotly_chart(fig_quad, use_container_width=True)

    st.markdown("""
    <div class="insight-box">
    <b>📌 How to read the quadrant:</b><br>
    • <b>Top-Right</b>: High Revenue + High Rating → <em>Star categories — invest and promote aggressively.</em><br>
    • <b>Top-Left</b>: High Revenue + Low Rating → <em>Cash cows with quality issues — improve satisfaction to protect revenue.</em><br>
    • <b>Bottom-Right</b>: Low Revenue + High Rating → <em>Hidden gems — customers love them; increase visibility and marketing.</em><br>
    • <b>Bottom-Left</b>: Low Revenue + Low Rating → <em>Problem categories — reassess or discontinue.</em>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;font-size:12px;color:#8b949e;'>"
    "🛒 Supermarket Sales Analysis Dashboard &nbsp;|&nbsp; Built with Streamlit & Plotly"
    "</p>",
    unsafe_allow_html=True
)
