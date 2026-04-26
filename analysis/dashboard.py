import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from modeling.heatmap_generator import generate_filtered_heat_map
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)

st.set_page_config(page_title="NCAA Softball Performance Dashboard", layout="wide")

st.title("🥎 NCAA Softball Performance Analytics")
st.markdown("##### IUPUI 2024 Opponents — Full Season Batted Ball Analysis")
st.markdown("---")

# ── Sidebar Filters ──────────────────────────────────────────

st.sidebar.header("🔍 Filters")

# Load opponent teams (source_team = the team whose full season we scraped)
try:
    teams_df = pd.read_sql(
        "SELECT DISTINCT source_team FROM play_by_play ORDER BY source_team", engine)
    teams = teams_df['source_team'].tolist()
except Exception:
    teams = []

if not teams:
    st.sidebar.error("No data. Run scraper first:\n`python pipelines/ncaa_pbp_scraper.py`")

selected_team = st.sidebar.selectbox("Select Team", ["All"] + teams)

# Load players — only for the selected team's batting data
try:
    pq = "SELECT DISTINCT player FROM play_by_play WHERE batting_team != 'IUPUI'"
    if selected_team != "All":
        pq += f" AND source_team = '{selected_team}' AND batting_team = '{selected_team}'"
    pq += " ORDER BY player"
    players_df = pd.read_sql(pq, engine)
    players = players_df['player'].tolist()
except Exception:
    players = []

selected_player = st.sidebar.selectbox("Select Player", ["All"] + players)

st.sidebar.markdown("---")
st.sidebar.info("Data from each team's Sidearm Sports PBP (2024 full season)")

# ── Main Content ─────────────────────────────────────────────

col1, col2 = st.columns([2, 1])

with col1:
    label_team = selected_team if selected_team != "All" else "All Teams"
    label_player = selected_player if selected_player != "All" else "All Players"
    st.subheader(f"Heat Map: {label_team} — {label_player}")
    fig = generate_filtered_heat_map(team=selected_team, player=selected_player)
    st.pyplot(fig)

with col2:
    st.subheader("📊 Quick Stats")

    sq = ("SELECT hit_location, hit_type, is_hit, player "
          "FROM play_by_play "
          "WHERE batting_team != 'IUPUI' AND hit_location != 'Unknown'")
    if selected_team != "All":
        sq += f" AND source_team = '{selected_team}' AND batting_team = '{selected_team}'"
    if selected_player != "All":
        sq += f" AND player = '{selected_player}'"

    try:
        stats_df = pd.read_sql(sq, engine)
        if not stats_df.empty:
            total_plays = len(stats_df)
            total_hits = int(stats_df['is_hit'].sum())
            avg = total_hits / total_plays if total_plays > 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("At Bats", total_plays)
            m2.metric("Hits", total_hits)
            m3.metric("BA", f"{avg:.3f}")

            st.markdown("---")
            st.markdown("**Hit Location Distribution**")
            loc_counts = stats_df['hit_location'].value_counts()
            st.bar_chart(loc_counts)

            st.markdown("**Hit Type Breakdown**")
            type_counts = stats_df['hit_type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']
            st.dataframe(type_counts, hide_index=True, use_container_width=True)
        else:
            st.warning("No data for selected filters.")
    except Exception as e:
        st.error(f"Run scraper first: `python pipelines/ncaa_pbp_scraper.py`")

st.markdown("---")
st.caption("Data source: Sidearm Sports — 2024 NCAA Softball Play-by-Play")
