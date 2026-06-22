import plotly.express as px 
import streamlit as st
import pandas as pd
from pathlib import Path

def format_currency(value):

    if value >= 10000000:
        return f"₹{value/10000000:.2f} Cr"

    elif value >= 100000:
        return f"₹{value/100000:.2f} L"

    else:
        return f"₹{value:,.0f}"

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Restaurant Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Restaurant Analytics Dashboard")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
# --------------------------------------------------
# LOAD DATA (UPDATED FOR LOCAL PARQUET)
# --------------------------------------------------
from pathlib import Path

@st.cache_data
def load_data():
    # Look for the 'data' folder right next to app.py
    data_folder = Path("data")
    all_frames = []

    # Automatically scan for all .parquet files in the folder
    for file in data_folder.glob("*.parquet"):
        try:
            # Read the local parquet file
            df = pd.read_parquet(file)

            # Clean column spaces
            df.columns = df.columns.str.strip()

            # Extract Outlet and Year from filename (e.g., "CHANDANAGAR-26")
            filename = file.stem.upper()
            parts = filename.rsplit("-", 1)

            outlet = parts[0]
            year = parts[1]

            df["Outlet"] = outlet
            df["Year"] = year

            all_frames.append(df)

        except Exception as e:
            st.error(f"Error loading local file {file.name}: {e}")

    if len(all_frames) == 0:
        return pd.DataFrame()

    return pd.concat(all_frames, ignore_index=True)

# Run the local loader
df = load_data()



# --------------------------------------------------
# CLEAN DATA
# --------------------------------------------------

if len(df) > 0:

    numeric_cols = [
        "Item Quantity",
        "Item Price",
        "Discount",
        "Total Tax",
        "Final Total",
        "Cover"
    ]

    for col in numeric_cols:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    if "Cover" in df.columns:

        df["Covers"] = df["Cover"]

    if "Date" in df.columns:

        df["Date"] = pd.to_datetime(
            df["Date"],
            format="%d-%m-%Y",
            errors="coerce"
        )

        df["Month"] = (
            df["Date"]
            .dt.month_name()
        )

        df["Weekday"] = (
            df["Date"]
            .dt.day_name()
        )

    if "Timestamp" in df.columns:

        df["Timestamp"] = pd.to_datetime(
            df["Timestamp"],
            errors="coerce"
        )

        df["Hour"] = (
            df["Timestamp"]
            .dt.hour
        )


# FIX DUPLICATE INVOICE NUMBERS

df["Invoice_Key"] = (
    df["Outlet"].astype(str)
    + "_"
    + df["Date"].dt.strftime("%Y-%m-%d")
    + "_"
    + df["Invoice No"].astype(str)
)


# --------------------------------------------------
# TABS
# --------------------------------------------------

outlet_names = [
    "CHANDANAGAR",
    "COURTYARD",
    "GACHIBOWLI",
    "INDIRANAGAR",
    "KITCHEN&BAR",
    "KOMPALLY",
    "MARATHALLI",
    "NAGOLE"
]

tabs = st.tabs(
    ["📊 Executive Summary"] +
    [f"🏢 {outlet}" for outlet in outlet_names]
)

# --------------------------------------------------
# EXECUTIVE SUMMARY
# --------------------------------------------------


with tabs[0]:

    st.header("Executive Summary")

    invoice_level = (
        df
        .groupby("Invoice_Key")
        .agg({
            "Final Total":"first",
            "Covers":"max"
        })
    )

    total_revenue = (
        invoice_level["Final Total"]
        .sum()
    )

    total_orders = len(invoice_level)

    total_covers = (
        invoice_level["Covers"]
        .sum()
    )

    avg_bill = (
        total_revenue /
        total_orders
    )

    c1,c2,c3,c4 = st.columns(4)

    c1.metric(
        "Revenue",
        format_currency(total_revenue)
    )

    c2.metric(
        "Orders",
        f"{total_orders:,}"
    )

    c3.metric(
        "Covers",
        f"{total_covers:,.0f}"
    )
    

    c4.metric(
        "ABV",
        f"₹{avg_bill:,.0f}"
    )

    st.divider()

    st.subheader("Outlet Revenue Comparison")

    check_df = (
        df
        .groupby(
            ["Outlet", "Invoice_Key"]
        )["Final Total"]
        .first()
        .reset_index()
        .groupby("Outlet")["Final Total"]
        .sum()
        .reset_index()
    )

    
    
    invoice_outlet = (
        df
        .groupby(
            ["Outlet", "Invoice_Key"]
        )["Final Total"]
        .first()
        .reset_index()
    )

    outlet_revenue = (
        invoice_outlet
        .groupby("Outlet")
        ["Final Total"]
        .sum()
        .reset_index()
    )

    outlet_revenue = (
        outlet_revenue
        .sort_values(
            "Final Total",
            ascending=False
        )
    )

    fig_outlet = px.bar(
        outlet_revenue,
        x="Outlet",
        y="Final Total",
        title="Revenue by Outlet",
        text="Final Total"
    )
    fig_outlet.update_traces(
        texttemplate='₹%{y:,.0f}',
        textposition='outside'
    )

    st.plotly_chart(
        fig_outlet,
        use_container_width=True,
        key="outlet_revenue_chart"
    )

    outlet_revenue["Revenue Share %"] = (
        outlet_revenue["Final Total"]
        /
        outlet_revenue["Final Total"].sum()
        * 100
    ).round(1)

    outlet_revenue["Revenue"] = (
            outlet_revenue["Final Total"]
            .apply(format_currency)
        )
    
    st.dataframe(
        outlet_revenue[
            ["Outlet","Revenue", "Revenue Share %"]
        ]
    )

# --------------------------------------------------
# OUTLET TABS
# --------------------------------------------------

for i, outlet in enumerate(outlet_names):

    with tabs[i + 1]:

        outlet_df = df[
            df["Outlet"] == outlet
        ]

        st.header(outlet)

        available_years = sorted(
            outlet_df["Year"]
            .astype(str)
            .unique()
        )

        st.write(
            f"Available Years: {', '.join(available_years)}"
        )

        year_option = st.radio(
            "Select Year",
            ["Combined", "25", "26"],
            horizontal=True,
            key=f"year_{outlet}"
        )

        if year_option == "Combined":

            selected_df = outlet_df
              

            

        else:

            selected_df = outlet_df[
                outlet_df["Year"].astype(str)
                == year_option
            ]

        if len(selected_df) == 0:

            st.warning(
                f"No {year_option} data available"
            )

            continue

        invoice_level = (
            selected_df
            .groupby("Invoice_Key")
            .agg({
                "Final Total":"first",
                "Covers":"max"
            })
        )

        total_revenue = (
            invoice_level["Final Total"]
            .sum()
        )

        total_orders = len(invoice_level)

        total_covers = (
            invoice_level["Covers"]
            .sum()
        )

        avg_bill = (
            total_revenue /
            total_orders
        )

        c1,c2,c3,c4 = st.columns(4)

        c1.metric(
            "Revenue",
            format_currency(total_revenue)
        )

        c2.metric(
            "Orders",
            f"{total_orders:,}"
        )

        if invoice_level["Covers"].notna().sum() == 0:

            c3.metric(
                "Covers",
                "N/A"
            )

        else:

            c3.metric(
                "Covers",
                f"{total_covers:,.0f}"
            )

        c4.metric(
            "ABV",
            f"₹{avg_bill:,.0f}"
        )

        

        st.divider()

        st.subheader("Daily Revenue Trend")

        invoice_daily = (
            selected_df
            .groupby(
                ["Year", "Date", "Invoice_Key"]
            )["Final Total"]
            .first()
            .reset_index()
        )

        daily_revenue = (
            invoice_daily
            .groupby(["Year", "Date"])
            ["Final Total"]
            .sum()
            .reset_index()
        )

        fig = px.line(
        
        daily_revenue,
            x="Date",
            y="Final Total",
            color="Year",
            markers=True,
            title="Daily Revenue"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"revenue_trend_{outlet}_{year_option}"
        )

        st.divider()

        st.subheader("Monthly Revenue (2025 vs 2026)")

        invoice_monthly = (
            selected_df
            .groupby(
                ["Year", "Month", "Invoice_Key"]
            )["Final Total"]
            .first()
            .reset_index()
        )

        monthly_revenue = (
            invoice_monthly
            .groupby(
                ["Year", "Month"]
            )["Final Total"]
            .sum()
            .reset_index()
        )

        month_order = [
            "March",
            "April",
            "May"
        ]

        monthly_revenue["Month"] = pd.Categorical(
            monthly_revenue["Month"],
            categories=month_order,
            ordered=True
        )

        monthly_revenue = (
            monthly_revenue
            .sort_values("Month")
        )

        fig_month = px.bar(
            monthly_revenue,
            x="Month",
            y="Final Total",
            color="Year",
            barmode="group",
            title="Monthly Revenue"
        )

        st.plotly_chart(
            fig_month,
            use_container_width=True,
            key=f"monthly_revenue_{outlet}_{year_option}"
        )
        
        st.divider()

        st.subheader("Top Selling Items")


        top_items = (
            selected_df
            .groupby("Item Name")
            ["Item Quantity"]
            .sum()
            .reset_index()
        )

        top_items = (
            top_items
            .sort_values(
                "Item Quantity",
                ascending=False
            )
            .head(10)
        )

        fig_items = px.bar(
            top_items,
            x="Item Quantity",
            y="Item Name",
            orientation="h",
            title="Top Selling Items"
        )

        st.plotly_chart(
            fig_items,
            use_container_width=True,
            key=f"top_items_{outlet}_{year_option}"
        )


        st.divider()

        st.subheader("Top Revenue Items")
        top_revenue_items = (
            selected_df
            .groupby("Item Name")["Final Total"]
            .sum()
            .reset_index()
        )

        top_revenue_items = (
            top_revenue_items
            .sort_values(
                "Final Total",
                ascending=False
            )
            .head(10)
        )

        fig_revenue_items = px.bar(
            top_revenue_items,
            x="Final Total",
            y="Item Name",
            orientation="h",
            title="Top Revenue Items"
        )

        st.plotly_chart(
            fig_revenue_items,
            use_container_width=True,
            key=f"top_revenue_items_{outlet}_{year_option}"
        )
        
        st.divider()

        st.subheader("Payment Analysis")

        payment_cols = [
            "Cash",
            "Card",
            "Online",
            "Wallet",
            "Credit",
            "Other"
        ]

        payment_data = []

        for col in payment_cols:

            if col in selected_df.columns:

                payment_data.append(
                    {
                        "Payment Type": col,
                        "Amount": pd.to_numeric(
                            selected_df[col],
                            errors="coerce"
                        ).fillna(0).sum()
                    }
                )

        payment_df = pd.DataFrame(
            payment_data
        )

        fig_payment = px.pie(
            payment_df,
            names="Payment Type",
            values="Amount",
            title="Payment Distribution"
        )

        st.plotly_chart(
            fig_payment,
            use_container_width=True,
            key=f"payment_{outlet}_{year_option}"
        )

        st.divider()

        st.subheader("Hourly Sales Analysis")

        hourly_invoice = (
            selected_df
            .groupby(
                ["Hour", "Invoice_Key"]
            )["Final Total"]
            .first()
            .reset_index()
        )

        hourly_sales = (
            hourly_invoice
            .groupby("Hour")
            ["Final Total"]
            .sum()
            .reset_index()
        )
        hourly_sales = hourly_sales.sort_values("Hour")

        fig_hourly = px.bar(
            hourly_sales,
            x="Hour",
            y="Final Total",
            title="Revenue by Hour"
        )

        st.plotly_chart(
            fig_hourly,
            use_container_width=True,
            key=f"hourly_sales_{outlet}_{year_option}"
        )

        st.divider()

        st.subheader("Weekday Revenue Analysis")

        weekday_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]

        weekday_df = (
            selected_df
            .groupby(
                ["Weekday", "Invoice_Key"]
            )["Final Total"]
            .first()
            .reset_index()
        )

        weekday_df = (
            weekday_df
            .groupby("Weekday")
            ["Final Total"]
            .sum()
            .reset_index()
        )

        weekday_df["Weekday"] = pd.Categorical(
            weekday_df["Weekday"],
            categories=weekday_order,
            ordered=True
        )

        weekday_df = weekday_df.sort_values("Weekday")

        fig_weekday = px.bar(
            weekday_df,
            x="Weekday",
            y="Final Total",
            title="Revenue by Weekday"
        )

        st.plotly_chart(
            fig_weekday,
            use_container_width=True,
            key=f"weekday_{outlet}_{year_option}"
        )