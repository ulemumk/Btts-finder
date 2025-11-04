# app.py
import streamlit as st
import pandas as pd
import requests
from datetime import date
from io import BytesIO
import altair as alt

# ===== CONFIGURATION =====
API_KEY = "YOUR_API_KEY_HERE"  # Replace with your API-Football key
HEADERS = {"x-apisports-key": API_KEY}
SEASON = 2025

# ===== LEAGUE MAPPING =====
LEAGUES = {
    "Premier League (ENG)": 39,
    "La Liga (ESP)": 140,
    "Serie A (ITA)": 135,
    "Bundesliga (GER)": 78,
    "Ligue 1 (FRA)": 61,
    "Eredivisie (NED)": 88,
    "Primeira Liga (POR)": 94,
    "Turkish Super Lig (TUR)": 203,
    "MLS (USA)": 253,
    "Brasileirão Serie A (BRA)": 71,
    "Argentine Primera (ARG)": 128,
    "Saudi Pro League (KSA)": 307,
    "A-League (AUS)": 188,
}

# ===== PAGE SETTINGS =====
st.set_page_config(page_title="BTTS Finder + Daily 3 Odds", page_icon="⚽", layout="wide")
st.title("⚽ Global BTTS Finder & Daily 3-Odds Picks")

# ===== SIDEBAR FILTERS =====
st.sidebar.header("⚙️ Settings")
season = st.sidebar.number_input("Season", min_value=2015, max_value=2100, value=SEASON)
min_btts = st.sidebar.slider("Minimum BTTS %", 0, 100, 60)
selected_leagues = st.sidebar.multiselect(
    "Select Leagues",
    options=list(LEAGUES.keys()),
    default=["Premier League (ENG)", "La Liga (ESP)", "Serie A (ITA)"],
)

if not selected_leagues:
    st.warning("Please select at least one league.")
    st.stop()

# ===== FUNCTIONS =====
def get_today_fixtures(league_id):
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&date={today}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return res.json().get("response", [])
    except Exception:
        pass
    return []

def get_team_btts(league_id, team_id):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            d = r.json().get("response", {})
            yes = d.get("both_teams_to_score", {}).get("yes", 0)
            no = d.get("both_teams_to_score", {}).get("no", 0)
            total = yes + no if yes + no > 0 else 1
            return round(100 * yes / total, 1)
    except Exception:
        pass
    return None

# ===== STYLING =====
def color_btts(val):
    if val >= 80:
        color = "lightgreen"
    elif val >= 60:
        color = "khaki"
    else:
        color = "#ff9999"
    return f"background-color: {color}; font-weight: bold;"

# ===== FETCH & ANALYZE =====
if st.button("🔍 Fetch BTTS Data & Daily Picks"):
    all_rows = []
    today_games = []

    progress = st.progress(0)
    total = len(selected_leagues)

    for i, league_name in enumerate(selected_leagues):
        league_id = LEAGUES[league_name]

        fixtures = get_today_fixtures(league_id)
        for f in fixtures:
            home = f["teams"]["home"]["id"]
            away = f["teams"]["away"]["id"]
            home_name = f["teams"]["home"]["name"]
            away_name = f["teams"]["away"]["name"]

            home_btts = get_team_btts(league_id, home)
            away_btts = get_team_btts(league_id, away)

            if home_btts is not None and away_btts is not None:
                avg_btts = round((home_btts + away_btts) / 2, 1)
                today_games.append([
                    league_name,
                    f"{home_name} vs {away_name}",
                    home_btts,
                    away_btts,
                    avg_btts
                ])
        progress.progress((i + 1) / total)

    progress.empty()

    if not today_games:
        st.error("No fixtures found for today or API limit reached.")
        st.stop()

    df = pd.DataFrame(today_games, columns=["League", "Match", "Home BTTS%", "Away BTTS%", "Avg BTTS%"])
    df = df[df["Avg BTTS%"] >= min_btts].sort_values("Avg BTTS%", ascending=False)

    st.subheader("📊 Today's BTTS Analysis")
    st.dataframe(df.style.applymap(color_btts, subset=["Avg BTTS%"]), use_container_width=True)

    # ===== BAR CHART =====
    if not df.empty:
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Match:N", sort="-y", title="Match"),
            y=alt.Y("Avg BTTS%:Q"),
            color="League:N",
            tooltip=["League", "Match", "Avg BTTS%"]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

    # ===== DAILY 3-ODDS PICK =====
    st.subheader("🎯 Daily 3-Odds Picks (Highest BTTS Probability)")
    top3 = df.head(3)
    if not top3.empty:
        st.table(top3[["League", "Match", "Avg BTTS%"]].reset_index(drop=True))
        total_odds = round(1.3 ** len(top3), 2)
        st.success(f"🔥 Suggested Combo: ~{total_odds}x odds (based on BTTS 'Yes')")
    else:
        st.info("No matches meet the BTTS threshold today.")

    # ===== DOWNLOAD =====
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="BTTS_Today")
    st.download_button(
        label="📥 Download BTTS Excel Report",
        data=buffer.getvalue(),
        file_name=f"BTTS_Report_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👆 Click the button above to fetch today's BTTS matches.")
