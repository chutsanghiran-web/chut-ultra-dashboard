import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date, datetime

st.set_page_config(page_title="Chut's Ultra Trail Command Center", page_icon="🏔️", layout="wide")

@st.cache_data
def load_data():
    activities = pd.read_csv("garmin_june_activities_parsed.csv", parse_dates=["date"])
    plan = pd.read_csv("plan_vs_actual.csv", parse_dates=["date"])
    health = pd.read_csv("garmin_health_june_parsed.csv", parse_dates=["date"])
    sleep = pd.read_csv("garmin_sleep_june_parsed.csv", parse_dates=["date"])
    return activities, plan, health, sleep

activities, plan, health, sleep = load_data()

SPORT_COLORS = {
    "Running": "#2ECC71",   # green
    "Cycling": "#FF69B4",   # pink
    "Swimming": "#FFD700",  # yellow
}


races = pd.DataFrame([
    {"Race": "Korat X Trail 50K", "Date": "2026-08-23", "Priority": "Build"},
    {"Race": "Phuket Trail 75K", "Date": "2026-09-12", "Priority": "Build"},
    {"Race": "Nan Mountain Trail 60K", "Date": "2026-10-10", "Priority": "Build"},
    {"Race": "Pattana Triathlon", "Date": "2026-10-18", "Priority": "B Race"},
    {"Race": "Pocari Sweat Ultra Trail 100K", "Date": "2026-11-15", "Priority": "A Race"},
])
races["Date"] = pd.to_datetime(races["Date"])
races["Days to go"] = (races["Date"].dt.date - date.today()).apply(lambda x: x.days)

st.title("🏔️ Chut's Ultra Trail Command Center")
st.caption("Phase 2 Streamlit prototype: plan vs actual, race readiness, countdown, and AI coaching logic.")

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Training Plan", "Activities", "Recovery", "Race Readiness", "AI Coach"])

# Helper metrics
run_activities = activities[activities["sport"].str.contains("Run", case=False, na=False)]
run_km = run_activities["distance_km"].sum()
training_hours = activities["duration_min"].sum() / 60
longest_run = run_activities["distance_km"].max() if not run_activities.empty else 0
completed = (plan["status"] == "Done").sum() if "status" in plan.columns else 0
planned_sessions = len(plan[~plan["type"].isin(["Rest", "Busy", "No Plan"])]) if "type" in plan.columns else len(plan)
adherence = round(completed / planned_sessions * 100, 1) if planned_sessions else 0

if page == "Home":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("June running", f"{run_km:.1f} km")
    c2.metric("Training time", f"{training_hours:.1f} h")
    c3.metric("Longest run", f"{longest_run:.1f} km")
    c4.metric("Plan adherence", f"{adherence}%")
    c5.metric("A Race", "Pocari 100K")

    st.subheader("1. Training Plan vs Actual")
    home_cols = ["date", "planned_session", "type", "planned_run_km", "actual_km", "status"]
    st.dataframe(plan[[c for c in home_cols if c in plan.columns]], use_container_width=True)

    st.subheader("2. Race Countdown")
    st.dataframe(races[["Date", "Race", "Priority", "Days to go"]], use_container_width=True)

    st.subheader("3. June Training Mix")
    sport_summary = activities.groupby("sport", as_index=False).agg(distance_km=("distance_km", "sum"), duration_min=("duration_min", "sum"))
    fig = px.bar(sport_summary, x="sport", y="distance_km", color="sport", text="distance_km", title="Distance by sport", color_discrete_map=SPORT_COLORS)
    st.plotly_chart(fig, use_container_width=True)

elif page == "Training Plan":
    st.header("Training Plan Status")
    col1, col2, col3 = st.columns(3)
    col1.metric("Planned sessions", planned_sessions)
    col2.metric("Completed", completed)
    col3.metric("Adherence", f"{adherence}%")
    st.dataframe(plan, use_container_width=True)

elif page == "Activities":
    st.header("Garmin Activities")
    fig = px.scatter(
        activities,
        x="date",
        y="distance_km",
        size="duration_min",
        color="sport",
        color_discrete_map=SPORT_COLORS,
        hover_data=["sport", "distance_km", "duration_min", "avg_hr", "max_hr", "ascent_m", "avg_pace_min_km"],
        title="Garmin Activities by Distance"
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="white"), opacity=0.9))
    fig.update_layout(legend_title_text="Sport")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(activities, use_container_width=True)

elif page == "Recovery":
    st.header("Recovery Metrics")
    st.info("Recovery is based on the full Garmin export. This prototype will improve after each full-export refresh.")
    if not sleep.empty:
        fig = px.line(sleep, x="date", y=sleep.select_dtypes("number").columns, title="Sleep metrics")
        st.plotly_chart(fig, use_container_width=True)
    if not health.empty:
        fig2 = px.line(health, x="date", y=health.select_dtypes("number").columns, title="Health metrics")
        st.plotly_chart(fig2, use_container_width=True)

elif page == "Race Readiness":
    st.header("Race Readiness")
    readiness = pd.DataFrame([
        {"Race": "Korat X Trail 50K", "Readiness": 35},
        {"Race": "Phuket Trail 75K", "Readiness": 25},
        {"Race": "Nan Mountain Trail 60K", "Readiness": 20},
        {"Race": "Pattana Triathlon", "Readiness": 50},
        {"Race": "Pocari 100K", "Readiness": 15},
    ])
    fig = px.bar(readiness, x="Race", y="Readiness", range_y=[0,100], text="Readiness")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Readiness values are starter estimates. Phase 3 will calculate these from long runs, weekly hours, elevation, sleep/HRV, and plan adherence.")

elif page == "AI Coach":
    st.header("AI Coach & Assessment")
    st.success("Strength: You have a clear race calendar and consistent long-run structure.")
    st.warning("Watchlist: July has multiple 21K runs but no longer simulation before Korat yet.")
    st.info("Recommendation: Keep uploading FIT files after each workout so plan-vs-actual and readiness can update.")
    st.write("Next key dashboard upgrade: automatic matching between your planned KC/Skylane sessions and Garmin activity names/routes.")
