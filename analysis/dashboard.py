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

# Load data for filters
try:
    query = "SELECT DISTINCT team, player FROM play_by_play"
    filter_df = pd.read_sql(query, engine)
except Exception:
    # Mock data for demonstration if DB is empty
    filter_df = pd.DataFrame({
        'team': ['Home', 'Away', 'Home', 'Away'],
        'player': ['Smith', 'Jones', 'Brown', 'Davis']
    })

teams = sorted(filter_df['team'].unique())
selected_team = st.sidebar.selectbox("Select Team", ["All"] + list(teams))

if selected_team != "All":
    players = sorted(filter_df[filter_df['team'] == selected_team]['player'].unique())
else:
    players = sorted(filter_df['player'].unique())

selected_player = st.sidebar.selectbox("Select Player", ["All"] + list(players))

st.sidebar.markdown("---")
st.sidebar.info("This dashboard visualizes batted ball metrics from PBP data.")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Heat Map: {selected_team} - {selected_player}")
    
    # Generate Heat Map with filters
    # Note: We need to modify heatmap_generator to accept filters
    from modeling.heatmap_generator import generate_filtered_heat_map
    
    fig = generate_filtered_heat_map(team=selected_team, player=selected_player)
    st.pyplot(fig)

with col2:
    st.subheader("Quick Stats")
    # Query stats
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
            
            st.metric("Total Plays", total_at_bats)
            st.metric("Total Hits", total_hits)
            st.metric("Batting Average", f"{avg:.3f}")
            
            st.write("Hit Distribution")
            st.bar_chart(stats_df['hit_location'].value_counts())
        else:
            st.warning("No data found for selected filters.")
    except Exception as e:
        st.error(f"Error loading stats: {e}")

st.markdown("---")
st.caption("Data source: NCAA Play-by-Play Scraper Pipeline")
