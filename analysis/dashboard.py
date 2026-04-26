import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from modeling.heatmap_generator import generate_filtered_heat_map
from dotenv import load_dotenv

load_dotenv()

# Database Setup
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)

st.set_page_config(page_title="NCAA Softball Performance Dashboard", layout="wide")

st.title("🥎 NCAA Softball Performance Analytics")
st.markdown("##### IUPUI 2024 — Opponent Batted Ball Analysis")
st.markdown("---")

# ── Sidebar Filters ──────────────────────────────────────────

st.sidebar.header("🔍 Filters")

# Load opponent teams
try:
    teams_df = pd.read_sql(
        "SELECT DISTINCT opponent FROM play_by_play WHERE batting_team != 'IUPUI' ORDER BY opponent",
        engine)
    teams = teams_df['opponent'].tolist()
except Exception:
    teams = []

if not teams:
    st.sidebar.warning("No data found. Run the scraper first:\n`python pipelines/ncaa_pbp_scraper.py`")
    teams = []

selected_team = st.sidebar.selectbox("Select Opponent", ["All"] + teams)

# Load players for selected team
try:
    player_query = "SELECT DISTINCT player FROM play_by_play WHERE batting_team != 'IUPUI'"
    if selected_team != "All":
        player_query += f" AND opponent = '{selected_team}'"
    player_query += " ORDER BY player"
    players_df = pd.read_sql(player_query, engine)
    players = players_df['player'].tolist()
except Exception:
    players = []

selected_player = st.sidebar.selectbox("Select Player", ["All"] + players)

st.sidebar.markdown("---")
st.sidebar.info("Data scraped from iuindyjags.com 2024 PBP")

# ── Main Content ─────────────────────────────────────────────

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Heat Map: {selected_team} — {selected_player}")
    fig = generate_filtered_heat_map(team=selected_team, player=selected_player)
    st.pyplot(fig)

with col2:
    st.subheader("📊 Quick Stats")

    stat_query = ("SELECT hit_location, hit_type, is_hit, player "
                  "FROM play_by_play "
                  "WHERE batting_team != 'IUPUI' AND hit_location != 'Unknown'")
    if selected_team != "All":
        stat_query += f" AND opponent = '{selected_team}'"
    if selected_player != "All":
        stat_query += f" AND player = '{selected_player}'"

    try:
        stats_df = pd.read_sql(stat_query, engine)
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
            type_counts = stats_df['hit_type'].value_counts()
            st.dataframe(type_counts.reset_index().rename(
                columns={'index': 'Type', 'hit_type': 'Count'}),
                hide_index=True, use_container_width=True)
        else:
            st.warning("No data for selected filters.")
    except Exception as e:
        st.error(f"Run scraper first: `python pipelines/ncaa_pbp_scraper.py`")

st.markdown("---")
st.caption("Data source: iuindyjags.com — 2024 Softball Play-by-Play")
