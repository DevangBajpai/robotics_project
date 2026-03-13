import streamlit as st
import pandas as pd
import plotly.express as px
import os
from databricks import sql
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Robotics Inspection Dashboard",
    page_icon="🤖",
    layout="wide",
)

# ── Databricks SQL connection ──────────────────────────────────────────────
# DATABRICKS_HOST and DATABRICKS_TOKEN are injected automatically by
# Databricks Apps.  You only need to add DATABRICKS_WAREHOUSE_HTTP_PATH
# in: Apps → your app → Edit → Environment variables.
CATALOG = "main"
SCHEMA  = "robotics_poc"
TABLE   = f"{CATALOG}.{SCHEMA}.equipment_readings"


@st.cache_resource(show_spinner="Connecting to Databricks…")
def get_connection():
    host      = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip("/")
    http_path = os.environ.get("DATABRICKS_WAREHOUSE_HTTP_PATH", "")
    token     = os.environ.get("DATABRICKS_TOKEN", "")
    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )


@st.cache_data(ttl=120, show_spinner="Loading data…")
def load_data() -> pd.DataFrame:
    conn = get_connection()
    query = f"""
        SELECT
            er_name, er_value, er_angle, er_confidence_score,
            photo_volume_path, reviewer_value, reviewer_comment,
            mission_id, site,
            CAST(date AS STRING) AS date
        FROM {TABLE}
        ORDER BY date DESC, site, er_name
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


# ── Load data ──────────────────────────────────────────────────────────────
try:
    df = load_data()
except Exception as exc:
    st.error(f"**Could not connect to Databricks:** {exc}")
    st.info(
        "Make sure the app environment variable **DATABRICKS_WAREHOUSE_HTTP_PATH** "
        "is set to your SQL Warehouse HTTP Path  "
        "(Databricks workspace → SQL Warehouses → your warehouse → Connection details)."
    )
    st.stop()

if df.empty:
    st.warning("No data found. Please run the **setup_data** notebook first.")
    st.stop()

# ── Sidebar filters ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍  Filters")

    sites = ["All"] + sorted(df["site"].unique().tolist())
    sel_site = st.selectbox("Site", sites)

    missions = ["All"] + sorted(df["mission_id"].unique().tolist())
    sel_mission = st.selectbox("Mission", missions)

    min_conf = st.slider("Min confidence score", 0.0, 1.0, 0.0, 0.01)

    if st.button("🔄  Refresh data"):
        st.cache_data.clear()
        st.rerun()

fdf = df.copy()
if sel_site    != "All": fdf = fdf[fdf["site"]       == sel_site]
if sel_mission != "All": fdf = fdf[fdf["mission_id"] == sel_mission]
fdf = fdf[fdf["er_confidence_score"] >= min_conf]

# ── Header ─────────────────────────────────────────────────────────────────
st.title("🤖  Robotics Inspection Dashboard")
st.caption(f"Source: `{TABLE}`  •  Last loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.divider()

# ── KPI row ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Readings",   len(fdf))
k2.metric("Sites",            fdf["site"].nunique())
k3.metric("Missions",         fdf["mission_id"].nunique())
k4.metric("Avg AI Confidence", f"{fdf['er_confidence_score'].mean():.1%}")
delta_val = round(fdf["er_value"].mean() - fdf["reviewer_value"].mean(), 2)
k5.metric("Avg AI vs Reviewer Δ", f"{delta_val:+.2f}")

st.divider()

# ── Readings table ─────────────────────────────────────────────────────────
st.subheader("Equipment Readings")

display_df = fdf[[
    "er_name", "site", "mission_id", "date",
    "er_value", "reviewer_value", "er_confidence_score", "reviewer_comment"
]].rename(columns={
    "er_name":             "Equipment",
    "site":                "Site",
    "mission_id":          "Mission",
    "date":                "Date",
    "er_value":            "AI Reading",
    "reviewer_value":      "Reviewer Reading",
    "er_confidence_score": "Confidence",
    "reviewer_comment":    "Comment",
})

st.dataframe(
    display_df.style.background_gradient(
        subset=["Confidence"], cmap="RdYlGn", vmin=0.0, vmax=1.0
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Manometer images grid ──────────────────────────────────────────────────
st.subheader("📷  Manometer Photos")

img_rows = fdf[fdf["photo_volume_path"].notna()].head(9)

if img_rows.empty:
    st.info("No images available for the current filter selection.")
else:
    cols = st.columns(3)
    for i, (_, row) in enumerate(img_rows.iterrows()):
        with cols[i % 3]:
            try:
                with open(row["photo_volume_path"], "rb") as f:
                    img_bytes = f.read()
                st.image(img_bytes, use_column_width=True)
                st.caption(
                    f"**{row['er_name']}** — AI: `{row['er_value']}`  "
                    f"Reviewer: `{row['reviewer_value']}`  "
                    f"Conf: `{row['er_confidence_score']:.1%}`"
                )
            except FileNotFoundError:
                st.warning(f"Image not found:\n`{row['photo_volume_path']}`")

st.divider()

# ── Analytics charts ───────────────────────────────────────────────────────
st.subheader("📊  Analytics")

left, right = st.columns(2)

with left:
    site_avg = (
        fdf.groupby("site")[["er_value", "reviewer_value"]]
        .mean()
        .reset_index()
        .melt(id_vars="site", var_name="Source", value_name="Avg Reading")
    )
    site_avg["Source"] = site_avg["Source"].map(
        {"er_value": "AI Reading", "reviewer_value": "Reviewer Reading"}
    )
    fig1 = px.bar(
        site_avg, x="site", y="Avg Reading", color="Source", barmode="group",
        title="Average Reading — AI vs Reviewer by Site",
        color_discrete_map={"AI Reading": "#3498db", "Reviewer Reading": "#2ecc71"},
    )
    st.plotly_chart(fig1, use_container_width=True)

with right:
    fig2 = px.histogram(
        fdf, x="er_confidence_score", nbins=20,
        title="Confidence Score Distribution",
        color_discrete_sequence=["#9b59b6"],
        labels={"er_confidence_score": "Confidence Score"},
    )
    fig2.add_vline(x=0.85, line_dash="dash", line_color="red",
                   annotation_text="Threshold 0.85")
    st.plotly_chart(fig2, use_container_width=True)

# ── Scatter: AI vs Reviewer ────────────────────────────────────────────────
fig3 = px.scatter(
    fdf, x="er_value", y="reviewer_value", color="site",
    hover_data=["er_name", "mission_id", "er_confidence_score"],
    title="AI Reading vs Reviewer Reading (ideal = diagonal line)",
    labels={"er_value": "AI Reading", "reviewer_value": "Reviewer Reading"},
    opacity=0.8,
)
min_v = min(fdf["er_value"].min(), fdf["reviewer_value"].min())
max_v = max(fdf["er_value"].max(), fdf["reviewer_value"].max())
fig3.add_shape(type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v,
               line=dict(dash="dot", color="gray"))
st.plotly_chart(fig3, use_container_width=True)
