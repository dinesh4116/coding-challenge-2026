import pandas as pd
import streamlit as st

st.title("Campaign Anomaly Alerting")
st.write("PS-04: Campaign Anomaly Alerting Without Alert Fatigue")

# Upload the campaign dataset
uploaded_file = st.file_uploader("Upload campaign CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = (df.columns.astype(str).str.strip().str.lower().str.replace(" ", "_"))
    st.write("Columns found in your CSV:",df.columns.tolist())

    # Dataset column names
    required_columns = [
        "date",
        "campaign_id",
        "campaign_name",
        "channel",
        "vertical",
        "landing_page_group",
        "spend",
        "impressions",
        "clicks",
        "conversions",
        "revenue"
    ]

    # Check columns
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
    else:
        # Convert data types
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        numeric_columns = [
            "spend", "impressions", "clicks",
            "conversions", "revenue"
        ]

        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["date", "campaign_id"])

        # Calculate campaign metrics
        df["CTR"] = (
            df["clicks"] / df["impressions"].replace(0, float("nan")) * 100
        )
        df["Conversion_Rate"] = (
            df["conversions"] / df["clicks"].replace(0, float("nan")) * 100
        )
        df["ROAS"] = (
            df["revenue"] / df["spend"].replace(0, float("nan"))
        )

        # Dashboard summary
        st.subheader("Campaign Overview")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Campaign Records", len(df))
        col2.metric("Unique Campaigns", df["campaign_id"].nunique())
        col3.metric("Total Spend", f"{df['spend'].sum():,.2f}")
        col4.metric("Total Revenue", f"{df['revenue'].sum():,.2f}")

        # Filter campaigns
        st.subheader("Filter Campaigns")

        channels = sorted(df["channel"].dropna().unique())
        selected_channel = st.selectbox(
            "Select Channel",
            ["All"] + channels
        )

        filtered_df = df.copy()

        if selected_channel != "All":
            filtered_df = filtered_df[
                filtered_df["channel"] == selected_channel
            ]

        # Display campaign data
        st.subheader("Campaign Dataset")
        st.dataframe(filtered_df, use_container_width=True)

        # Basic anomaly detection
        st.subheader("Campaign Anomaly Alerts")

        alerts = []

        for campaign_id, group in df.groupby("campaign_id"):
            group = group.sort_values("date")

            for metric in ["spend", "clicks", "conversions", "revenue"]:
                previous = group[metric].shift(1)
                change = (group[metric] - previous) / previous.abs().replace(
                    0, float("nan")
                ) * 100

                # Flag a change greater than 50%
                unusual = change.abs() > 50

                for index in group.index[unusual.fillna(False)]:
                    alerts.append({
                        "date": group.loc[index, "date"],
                        "campaign_id": campaign_id,
                        "campaign_name": group.loc[index, "campaign_name"],
                        "channel": group.loc[index, "channel"],
                        "metric": metric,
                        "previous_value": previous.loc[index],
                        "current_value": group.loc[index, metric],
                        "change_percent": round(change.loc[index], 2),
                        "alert": f"Unusual change in {metric}"
                    })

        if alerts:
            alerts_df = pd.DataFrame(alerts)

            # Avoid duplicate alerts for the same campaign/date/metric
            alerts_df = alerts_df.drop_duplicates(
                subset=["date", "campaign_id", "metric"]
            )

            st.warning(f"{len(alerts_df)} unusual changes detected")
            st.dataframe(alerts_df, use_container_width=True)

            st.download_button(
                "Download Alerts CSV",
                data=alerts_df.to_csv(index=False).encode("utf-8"),
                file_name="campaign_anomaly_alerts.csv",
                mime="text/csv"
            )
        else:
            st.success(
                "No unusual changes detected, or more historical data is needed."
            )

        # Performance chart
        st.subheader("Daily Campaign Performance")

        daily = df.groupby("date")[[
            "spend", "clicks", "conversions", "revenue"
        ]].sum()

        st.line_chart(daily)

else:
    st.info("Upload your daily_campaign_metrics.csv file to begin.")        