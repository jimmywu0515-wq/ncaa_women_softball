import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine
from modeling.heatmap_generator import generate_heat_map
from dotenv import load_dotenv

load_dotenv()

# Database Setup
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)

st.set_page_config(page_title="NCAA Softball Performance Dashboard", layout="wide")

st.title("🥎 NCAA Softball Performance Analytics")
st.markdown("---")

# Sidebar Filters
st.sidebar.header("Filters")

# Hardcoded team selection as requested
selected_team = st.sidebar.selectbox("Select Team", ["All", "Home", "Away"])

# Load players for filter
try:
    if selected_team != "All":
        query = f"SELECT DISTINCT player FROM play_by_play WHERE team = '{selected_team}'"
    else:
        query = "SELECT DISTINCT player FROM play_by_play"
    players_df = pd.read_sql(query, engine)
    players = sorted(players_df['player'].unique())
except Exception:
    players = ['Smith', 'Jones', 'Brown', 'Davis'] # Fallback

selected_player = st.sidebar.selectbox("Select Player", ["All"] + list(players))

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Quick Stats")

# Move Stats to Sidebar
stat_query = "SELECT hit_location, is_hit FROM play_by_play WHERE 1=1"
if selected_team != "All":
    stat_query += f" AND team = '{selected_team}'"
if selected_player != "All":
    stat_query += f" AND player = '{selected_player}'"

try:
    stats_df = pd.read_sql(stat_query, engine)
    if not stats_df.empty:
        total_at_bats = len(stats_df)
        total_hits = stats_df['is_hit'].sum()
        avg = total_hits / total_at_bats if total_at_bats > 0 else 0
        
        st.sidebar.metric("Total Plays", total_at_bats)
        st.sidebar.metric("Total Hits", total_hits)
        st.sidebar.metric("Batting Average", f"{avg:.3f}")
    else:
        st.sidebar.warning("No stats found for filters.")
except Exception as e:
    st.sidebar.error("Stats Error: Run Scraper First")

st.sidebar.markdown("---")
st.sidebar.info("This dashboard visualizes batted ball metrics from PBP data.")

# Main content
st.subheader(f"Heat Map: {selected_team} - {selected_player}")

# Generate Heat Map
from modeling.heatmap_generator import generate_filtered_heat_map
fig = generate_filtered_heat_map(team=selected_team, player=selected_player)
st.pyplot(fig)

st.markdown("---")
st.caption("Data source: NCAA Play-by-Play Scraper Pipeline")
