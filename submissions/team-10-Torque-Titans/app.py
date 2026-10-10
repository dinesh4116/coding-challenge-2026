import math

import pandas as pd
import streamlit as st


def triage(row):
	clicks = max(0, float(row["clicks"]))
	conversions = max(0, float(row["conversions"]))
	cost = max(0, float(row["cost"]))
	value = max(0, float(row["conversion_value"]))

	# Use a conservative estimate of conversion rate to avoid trusting tiny samples.
	n = max(clicks, conversions)
	p = min(conversions / n, 1) if n else 0
	z = 1.96

	if n > 0:
		lower = (
			p + z * z / (2 * n)
			- z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
		) / (1 + z * z / n)
	else:
		lower = 0

	if clicks < 20:
		return pd.Series([
			"IGNORE", "Low",
			"Insufficient clicks for a reliable decision",
			"YES",
		])

	if clicks >= 30 and conversions >= 5 and value > cost and lower >= 0.03:
		return pd.Series([
			"PROMOTE", "High",
			"Sufficient conversion evidence and positive observed return",
			"NO",
		])

	if clicks >= 80 and conversions == 0 and cost > 0:
		return pd.Series([
			"BLOCK", "Medium",
			"High click volume with zero conversions; review before blocking",
			"YES",
		])

	return pd.Series([
		"IGNORE", "Low",
		"Evidence is insufficient or performance is inconclusive",
		"YES",
	])


def analyze(df):
	required = ["clicks", "cost", "conversions", "conversion_value"]
	missing = [column for column in required if column not in df.columns]
	if missing:
		raise ValueError("Missing columns: " + ", ".join(missing))

	result = df.copy()
	for column in required:
		result[column] = pd.to_numeric(result[column], errors="coerce")

	invalid = result[required].isna().any(axis=1)
	invalid |= (result[required] < 0).any(axis=1)
	invalid |= result["conversions"] > result["clicks"]

	safe = result.copy()
	safe[required] = safe[required].fillna(0).clip(lower=0)
	output_columns = ["decision", "confidence", "reason", "human_review"]

	if safe.empty:
		output = pd.DataFrame(index=safe.index, columns=output_columns)
	else:
		output = safe.apply(triage, axis=1)
		output.columns = output_columns

	result = pd.concat([result, output], axis=1)
	result.loc[invalid, "decision"] = "IGNORE"
	result.loc[invalid, "confidence"] = "Low"
	result.loc[invalid, "reason"] = "Invalid or missing metric values"
	result.loc[invalid, "human_review"] = "YES"
	return result


st.set_page_config(page_title="Search Term Triage", layout="wide")
st.title("Search Term Triage Engine")
st.write("PS-01 | Intelligent Google Ads Search Term Analysis")

uploaded_file = st.file_uploader("Upload Search Terms CSV", type=["csv"])

if uploaded_file is not None:
	try:
		df = pd.read_csv(uploaded_file)
		df.columns = (
			df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
		)
		result = analyze(df)

		st.success("Analysis completed successfully!")
		col1, col2, col3, col4 = st.columns(4)
		col1.metric("Total Terms", len(result))
		col2.metric("Promote", (result["decision"] == "PROMOTE").sum())
		col3.metric("Block", (result["decision"] == "BLOCK").sum())
		col4.metric("Human Review", (result["human_review"] == "YES").sum())

		st.subheader("Decision Summary")
		st.bar_chart(result["decision"].value_counts())

		st.subheader("Search Term Results")
		decision_filter = st.selectbox(
			"Filter by decision", ["ALL", "PROMOTE", "BLOCK", "IGNORE"]
		)
		displayed = result
		if decision_filter != "ALL":
			displayed = result[result["decision"] == decision_filter]
		st.dataframe(displayed, use_container_width=True)

		csv = result.to_csv(index=False).encode("utf-8")
		st.download_button(
			"Download Analysis CSV", csv, "triage_results.csv", "text/csv"
		)
	except Exception as error:
		st.error(f"Error: {error}")
else:
	st.info("Upload a CSV file to begin analysis.")
