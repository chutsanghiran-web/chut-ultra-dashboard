import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Chut's Ultra Trail Command Center", page_icon="🏔️", layout="wide")

@st.cache_data
def load_data():
    activities = pd.read_csv("garmin_june_activities_parsed.csv", parse_dates=["date"])
    plan = pd.read_csv("plan_vs_actual.csv", parse_dates=["date"])
    health = pd.read_csv("garmin_health_june_parsed.csv", parse_dates=["date"])
    sleep = pd.read_csv("garmin_sleep_june_parsed.csv", parse_dates=["date"])
    try:
        load = pd.read_csv("garmin_training_load_june_parsed.csv", parse_dates=["date"])
    except FileNotFoundError:
        load = pd.DataFrame(columns=["date", "acute_load", "chronic_load", "acwr", "load_status", "load_percent"])
    return activities, plan, health, sleep, load

activities, plan, health, sleep, load = load_data()

races = pd.DataFrame([
    {"Race": "Korat X Trail 50K", "Date": "2026-08-23", "Priority": "Build"},
    {"Race": "Phuket Trail 75K", "Date": "2026-09-12", "Priority": "Build"},
    {"Race": "Nan Mountain Trail 60K", "Date": "2026-10-10", "Priority": "Build"},
    {"Race": "Pattana Triathlon", "Date": "2026-10-18", "Priority": "B Race"},
    {"Race": "Pocari Sweat Ultra Trail 100K", "Date": "2026-11-15", "Priority": "A Race"},
])
races["Date"] = pd.to_datetime(races["Date"])
races["Days to go"] = (races["Date"].dt.date - date.today()).apply(lambda x: x.days)

# Sidebar
st.title("🏔️ Chut's Ultra Trail Command Center")
st.caption("Phase 2.2 Streamlit prototype: dashboard, training plan status, recovery insights, readiness, countdown, AI coaching logic, and custom activity colors.")
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Training Plan", "Activities", "Recovery", "Race Readiness", "AI Coach"])

# Helpers
run_activities = activities[activities["sport"].str.contains("Run", case=False, na=False)] if not activities.empty else pd.DataFrame()
run_km = run_activities["distance_km"].sum() if not run_activities.empty else 0
training_hours = activities["duration_min"].sum() / 60 if not activities.empty else 0
longest_run = run_activities["distance_km"].max() if not run_activities.empty else 0
completed = (plan["status"] == "Done").sum() if "status" in plan.columns else 0
planned_sessions = len(plan[~plan["type"].isin(["Rest", "Busy", "No Plan"])]) if "type" in plan.columns else len(plan)
adherence = round(completed / planned_sessions * 100, 1) if planned_sessions else 0

# Clean plan table: removed actual_sports because it is not useful for your dashboard
plan_display_cols = ["date", "planned_session", "type", "planned_run_km", "actual_km", "status"]
plan_display = plan[[c for c in plan_display_cols if c in plan.columns]].copy()
plan_display["date"] = plan_display["date"].dt.strftime("%d %b %Y")

# Recovery insights helpers
def latest_non_null(df, col):
    if df.empty or col not in df.columns:
        return None
    s = df[["date", col]].dropna().sort_values("date")
    if s.empty:
        return None
    return s.iloc[-1][col]

def mean_last(df, col, n=7):
    if df.empty or col not in df.columns:
        return None
    s = df[["date", col]].dropna().sort_values("date").tail(n)
    if s.empty:
        return None
    return float(s[col].mean())

def recovery_assessment(sleep_avg, sleep_latest, hrv_avg, hrv_latest, load_latest, acwr_latest, load_status):
    notes = []
    guidelines = []
    risk = 0

    if sleep_avg is not None:
        if sleep_avg >= 7.0:
            notes.append("Sleep volume is in a good range for endurance training.")
        elif sleep_avg >= 6.0:
            notes.append("Sleep is acceptable, but slightly low for ultra-trail build weeks.")
            guidelines.append("Aim for 7+ hours on nights before KC, Skylane, and long-run days.")
            risk += 1
        else:
            notes.append("Sleep is currently the main recovery limiter.")
            guidelines.append("Prioritize an earlier bedtime and avoid adding extra training volume until sleep improves.")
            risk += 2

    if hrv_avg is not None and hrv_latest is not None:
        hrv_delta = hrv_latest - hrv_avg
        if hrv_delta >= -5:
            notes.append("HRV looks stable versus your recent average.")
        elif hrv_delta >= -12:
            notes.append("HRV is a little suppressed versus your recent average.")
            guidelines.append("Keep the next workout easy unless you feel unusually fresh.")
            risk += 1
        else:
            notes.append("HRV is noticeably suppressed, which can mean fatigue or stress is building.")
            guidelines.append("Swap intensity for Zone 2, mobility, or swim recovery until HRV rebounds.")
            risk += 2

    if acwr_latest is not None:
        if 0.8 <= acwr_latest <= 1.3:
            notes.append("Garmin training load balance is in a productive/controlled range.")
        elif acwr_latest > 1.3:
            notes.append("Training load is rising quickly compared with your recent base.")
            guidelines.append("Avoid stacking hard days; protect sleep and fueling after long sessions.")
            risk += 2
        else:
            notes.append("Training load is relatively low versus your recent base.")
            guidelines.append("Build back with consistency rather than one huge catch-up workout.")
            risk += 1

    if load_status and str(load_status).upper() not in ["OPTIMAL", "MAINTAINING"]:
        notes.append(f"Garmin load status is {load_status}.")

    if not guidelines:
        guidelines.append("Keep following the plan. Do not add bonus volume unless sleep and legs feel good.")
        guidelines.append("For Pocari 100K, consistency matters more than one heroic workout.")

    if risk >= 4:
        headline = "🔴 Recovery risk is elevated"
    elif risk >= 2:
        headline = "🟡 Recovery needs attention"
    else:
        headline = "🟢 Recovery looks manageable"

    return headline, notes, guidelines

def classify_activity(row):
    sport = str(row.get("sport", ""))
    name = str(row.get("activity_name", "")).lower()
    ascent = row.get("ascent_m", 0)

    trail_keywords = [
        "kc",
        "khao chalak",
        "trail",
        "mountain",
        "hill",
        "hike",
        "climb",
        "ascent",
        "descent"
    ]

    # KC / trail detection:
    # 1. Activity name contains trail keywords
    # 2. Or it is a run with large elevation gain
    if any(k in name for k in trail_keywords):
        return "KC/Trail"

    try:
        if "run" in sport.lower() and float(ascent) >= 300:
            return "KC/Trail"
    except (TypeError, ValueError):
        pass

    if "cycl" in sport.lower():
        return "Cycling"

    if "swim" in sport.lower():
        return "Swimming"

    return "Running"

SPORT_COLORS = {
    "Running": "#2ECC71",     # green
    "Cycling": "#FF69B4",     # pink
    "Swimming": "#FFD700",    # yellow
    "KC/Trail": "#8E44AD"     # purple
}

sleep_latest = latest_non_null(sleep, "sleep_hours")
sleep_avg7 = mean_last(sleep, "sleep_hours", 7)
sleep_score_avg7 = mean_last(sleep, "sleep_score", 7)
hrv_latest = latest_non_null(health, "HRV")
hrv_avg7 = mean_last(health, "HRV", 7)
hrv_status = latest_non_null(health, "HRV_status")
load_latest = latest_non_null(load, "acute_load")
chronic_latest = latest_non_null(load, "chronic_load")
acwr_latest = latest_non_null(load, "acwr")
load_status = latest_non_null(load, "load_status")
headline, recovery_notes, recovery_guidelines = recovery_assessment(sleep_avg7, sleep_latest, hrv_avg7, hrv_latest, load_latest, acwr_latest, load_status)

if page == "Home":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("June running", f"{run_km:.1f} km")
    c2.metric("Training time", f"{training_hours:.1f} h")
    c3.metric("Longest run", f"{longest_run:.1f} km")
    c4.metric("Plan adherence", f"{adherence}%")
    c5.metric("A Race", "Pocari 100K")

    st.subheader("1. Training Plan vs Actual")
    st.dataframe(plan_display, use_container_width=True)

    st.subheader("2. Race Countdown")
    st.dataframe(races[["Date", "Race", "Priority", "Days to go"]], use_container_width=True)

    st.subheader("3. June Training Mix")
    if not activities.empty:
        activities_home = activities.copy()
        activities_home["activity_group"] = activities_home.apply(classify_activity, axis=1)
        sport_summary = activities_home.groupby("activity_group", as_index=False).agg(
            distance_km=("distance_km", "sum"),
            duration_min=("duration_min", "sum")
        )
        fig = px.bar(
            sport_summary,
            x="activity_group",
            y="distance_km",
            text="distance_km",
            title="Distance by activity type",
            color="activity_group",
            color_discrete_map=SPORT_COLORS
        )
        fig.update_layout(
            legend_title_text="Activity",
            xaxis_title="Activity",
            yaxis_title="Distance (km)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "Training Plan":
    st.header("Training Plan Status")
    col1, col2, col3 = st.columns(3)
    col1.metric("Planned sessions", planned_sessions)
    col2.metric("Completed", completed)
    col3.metric("Adherence", f"{adherence}%")

    st.subheader("Plan vs Actual")
    st.caption("Removed the Actual Sports column. The focus here is whether the planned workout was completed, not an extra sport-category field.")
    st.dataframe(plan_display, use_container_width=True)

    st.subheader("Planned Run Volume by Week")
    p = plan.copy()
    p["week"] = p["date"].dt.to_period("W").astype(str)
    weekly = p.groupby("week", as_index=False).agg(planned_run_km=("planned_run_km", "sum"), actual_km=("actual_km", "sum"))
    fig = px.bar(weekly, x="week", y=["planned_run_km", "actual_km"], barmode="group", title="Planned vs Actual Running Kilometers")
    st.plotly_chart(fig, use_container_width=True)

elif page == "Activities":
    st.header("Garmin Activities")
    if not activities.empty:
        activities_plot = activities.copy()
        activities_plot["activity_group"] = activities_plot.apply(classify_activity, axis=1)

        fig = px.scatter(
            activities_plot,
            x="date",
            y="distance_km",
            size="duration_min",
            color="activity_group",
            color_discrete_map=SPORT_COLORS,
            hover_data=[
                "sport",
                "avg_hr",
                "ascent_m",
                "avg_pace_min_km"
            ],
            title="Activities by Distance and Duration"
        )

        fig.update_layout(
            legend_title_text="Activity",
            xaxis_title="Date",
            yaxis_title="Distance (km)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("KC/Trail is detected from activity name keywords or high-elevation runs over 300m ascent.")
        st.dataframe(activities_plot, use_container_width=True)

elif page == "Recovery":
    st.header("Recovery: AI Insight + Guidelines")
    st.info("Recovery is based on your full Garmin export. Daily FIT uploads update training; full Garmin exports refresh sleep, HRV, and load history.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("7-day avg sleep", f"{sleep_avg7:.1f} h" if sleep_avg7 is not None else "—")
    m2.metric("7-day avg HRV", f"{hrv_avg7:.0f}" if hrv_avg7 is not None else "—", delta=(f"Latest {hrv_latest:.0f}" if hrv_latest is not None else None))
    m3.metric("Acute load", f"{load_latest:.0f}" if load_latest is not None else "—")
    m4.metric("Load status", str(load_status).title() if load_status else "—")

    st.subheader(headline)
    st.markdown("**What the data suggests**")
    for note in recovery_notes:
        st.write(f"- {note}")

    st.markdown("**Guidelines to improve**")
    for guide in recovery_guidelines:
        st.write(f"- {guide}")

    st.markdown("**Simple recovery rules for your Pocari 100K build**")
    st.write("- If sleep is under 6 hours and HRV is below recent average: keep the next session easy.")
    st.write("- If acute load jumps sharply: do not add bonus training, even if motivation is high.")
    st.write("- Before long runs: prioritize carbs, hydration, and 7+ hours sleep over extra gym work.")
    st.write("- After KC or long trail days: the next day should feel like recovery, not another test.")

    if not sleep.empty:
        st.subheader("Sleep Trend")
        sleep_cols = [c for c in ["sleep_hours", "sleep_score", "recovery_score"] if c in sleep.columns]
        fig = px.line(sleep, x="date", y=sleep_cols, title="Sleep Hours / Sleep Score / Recovery Score")
        st.plotly_chart(fig, use_container_width=True)

    if not health.empty:
        st.subheader("HRV Trend")
        fig2 = px.line(health, x="date", y="HRV", title="HRV")
        st.plotly_chart(fig2, use_container_width=True)

    if not load.empty:
        st.subheader("Garmin Training Load")
        fig3 = px.line(load, x="date", y=["acute_load", "chronic_load"], title="Acute vs Chronic Training Load")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(load.sort_values("date", ascending=False), use_container_width=True)

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
    st.caption("Readiness values are starter estimates. Phase 3 will calculate these from long runs, weekly hours, elevation, sleep/HRV, Garmin load, and plan adherence.")

elif page == "AI Coach":
    st.header("AI Coach & Assessment")
    st.success("Strength: You have a clear race calendar and a structured build toward Pocari 100K.")
    st.warning("Watchlist: July has multiple 21K runs but no longer simulation before Korat yet.")
    st.info("Recommendation: Upload each FIT file the morning after training. The dashboard will update plan-vs-actual, adherence, and readiness.")
    st.subheader("Recovery Coach Snapshot")
    st.write(headline)
    for guide in recovery_guidelines[:3]:
        st.write(f"- {guide}")
