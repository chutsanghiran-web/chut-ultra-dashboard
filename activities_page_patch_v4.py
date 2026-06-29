
# PATCH INSTRUCTIONS FOR ACTIVITIES PAGE
# Replace the Activities section in your current streamlit_dashboard_app.py with:

elif page == "Activities":
    st.header("Garmin Activities")
    if not activities.empty:
        activities_plot = activities.copy()

        def classify_activity(row):
            sport = str(row.get("sport", ""))
            name = str(row.get("activity_name", "")).lower()

            trail_keywords = [
                "kc", "khao chalak", "trail",
                "mountain", "hill", "hike",
                "climb", "ascent", "descent"
            ]

            if any(k in name for k in trail_keywords):
                return "KC/Trail"

            if "cycl" in sport.lower():
                return "Cycling"

            if "swim" in sport.lower():
                return "Swimming"

            return "Running"

        activities_plot["sport_display"] = activities_plot.apply(
            classify_activity, axis=1
        )

        fig = px.scatter(
            activities_plot,
            x="date",
            y="distance_km",
            size="duration_min",
            color="sport_display",
            color_discrete_map={
                "Running": "#2ECC71",
                "Cycling": "#FF69B4",
                "Swimming": "#FFD700",
                "KC/Trail": "#8E44AD"
            },
            hover_data=[
                "avg_hr",
                "ascent_m",
                "avg_pace_min_km"
            ]
        )

        fig.update_layout(
            legend_title_text="Activity",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(activities, use_container_width=True)
