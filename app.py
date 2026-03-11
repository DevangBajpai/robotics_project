import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(
    page_title="Robotics Dashboard POC",
    page_icon="🤖",
    layout="wide"
)

# --- Title ---
st.title("🤖 Robotics Operations Dashboard")
st.caption("Proof of Concept — Real-time Robot Monitoring")

st.divider()

# --- Dummy Robot Data ---
ROBOTS = ["Robot-01", "Robot-02", "Robot-03", "Robot-04", "Robot-05"]
STATUSES = ["Active", "Active", "Active", "Idle", "Maintenance"]
LOCATIONS = ["Zone A", "Zone B", "Zone C", "Zone D", "Charging Bay"]

def generate_robot_data():
    return pd.DataFrame({
        "Robot ID": ROBOTS,
        "Status": STATUSES,
        "Location": LOCATIONS,
        "Battery (%)": [random.randint(20, 100) for _ in ROBOTS],
        "Tasks Completed Today": [random.randint(0, 50) for _ in ROBOTS],
        "Last Ping": [
            (datetime.now() - timedelta(seconds=random.randint(0, 120))).strftime("%H:%M:%S")
            for _ in ROBOTS
        ]
    })

def generate_task_log():
    tasks = []
    task_types = ["Pick & Place", "Navigation", "Inspection", "Charging", "Idle"]
    for i in range(20):
        tasks.append({
            "Task ID": f"T-{1000 + i}",
            "Robot": random.choice(ROBOTS),
            "Type": random.choice(task_types),
            "Duration (s)": random.randint(10, 300),
            "Status": random.choice(["Completed", "Completed", "In Progress", "Failed"]),
            "Timestamp": (datetime.now() - timedelta(minutes=i * 5)).strftime("%H:%M:%S")
        })
    return pd.DataFrame(tasks)

# --- KPI Row ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Robots", len(ROBOTS))
col2.metric("Active Robots", STATUSES.count("Active"))
col3.metric("Tasks Completed Today", random.randint(120, 200), delta="+12 vs yesterday")
col4.metric("Alerts", random.randint(0, 3), delta_color="inverse")

st.divider()

# --- Robot Status Table ---
st.subheader("Robot Fleet Status")
robot_df = generate_robot_data()

# Colour-code status
def highlight_status(val):
    colours = {"Active": "background-color: #d4edda", "Idle": "background-color: #fff3cd", "Maintenance": "background-color: #f8d7da"}
    return colours.get(val, "")

st.dataframe(
    robot_df.style.applymap(highlight_status, subset=["Status"]),
    use_container_width=True,
    hide_index=True
)

st.divider()

# --- Task Log & Battery Chart Side by Side ---
left, right = st.columns([3, 2])

with left:
    st.subheader("Recent Task Log")
    task_df = generate_task_log()
    st.dataframe(task_df, use_container_width=True, hide_index=True)

with right:
    st.subheader("Battery Levels")
    battery_df = robot_df[["Robot ID", "Battery (%)"]].set_index("Robot ID")
    st.bar_chart(battery_df)

st.divider()

# --- Filter by Robot ---
st.subheader("Filter Tasks by Robot")
selected_robot = st.selectbox("Select Robot", ["All"] + ROBOTS)

filtered = task_df if selected_robot == "All" else task_df[task_df["Robot"] == selected_robot]
st.dataframe(filtered, use_container_width=True, hide_index=True)

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
