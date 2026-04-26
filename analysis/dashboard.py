import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from modeling.heatmap_generator import generate_filtered_heat_map
from dotenv import load_dotenv

load_dotenv()

def get_db_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
    if "database.windows.net" in url:
        return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)
    return create_engine(url)

engine = get_db_engine()
Base = declarative_base()

st.set_page_config(page_title="NCAA Softball Performance Dashboard", layout="wide")

# ── Navigation ──────────────────────────────────────────────

nav = st.sidebar.radio("📂 Menu", ["Performance Analytics", "Transfer Portal"])
st.sidebar.markdown("---")

if nav == "Performance Analytics":
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

    # Load players — only for the selected team's batting data with > 20 at-bats
    try:
        pq = """
        SELECT player 
        FROM play_by_play 
        WHERE batting_team != 'IUPUI' AND hit_location != 'Unknown'
        """
        if selected_team != "All":
            pq += f" AND source_team = '{selected_team}' AND batting_team = '{selected_team}'"
        
        pq += " GROUP BY player HAVING COUNT(*) > 20 ORDER BY player"
        
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

else:  # Transfer Portal
    st.title("🔄 Transfer Portal Wire")
    st.markdown("##### 2024 NCAA Softball Transfer Insights")
    st.markdown("---")

    try:
        portal_df = pd.read_sql("SELECT * FROM transfer_portal", engine)
        if not portal_df.empty:
            # Filters
            pos_filter = st.sidebar.multiselect("Filter by Position", 
                                              sorted(portal_df['position'].unique()))
            status_filter = st.sidebar.multiselect("Filter by Status", 
                                                 sorted(portal_df['status'].unique()))
            
            df_display = portal_df.copy()
            if pos_filter:
                df_display = df_display[df_display['position'].isin(pos_filter)]
            if status_filter:
                df_display = df_display[df_display['status'].isin(status_filter)]

            # Summary metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Entries", len(portal_df))
            committed = portal_df[portal_df['status'] == 'Committed']
            m2.metric("Committed", len(committed))
            entered = portal_df[portal_df['status'] == 'Entered']
            m3.metric("Still Available", len(entered))

            st.markdown("---")

            # Display columns
            display_cols = ['player_name', 'position', 'year', 'previous_team', 
                          'new_team', 'status', 'hometown', 'high_school', 'on3_rating']
            available_cols = [c for c in display_cols if c in df_display.columns]
            
            st.dataframe(
                df_display[available_cols].rename(columns={
                    'player_name': 'Player',
                    'position': 'Position',
                    'year': 'Year',
                    'previous_team': 'From',
                    'new_team': 'To',
                    'status': 'Status',
                    'hometown': 'Hometown',
                    'high_school': 'High School',
                    'on3_rating': 'On3 Rating',
                }),
                use_container_width=True, hide_index=True)
            
            # Analytics
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Position Breakdown")
                st.bar_chart(portal_df['position'].value_counts())
            with c2:
                st.subheader("Status Breakdown")
                st.bar_chart(portal_df['status'].value_counts())
                
        else:
            st.warning("No portal data found. Run the scraper first:\n`python pipelines/portal_scraper.py`")
    except Exception as e:
        st.error("Error loading portal data. Make sure the database is initialized.")

st.markdown("---")
st.caption("Developed by Antigravity AI — Data Insights for NCAA Softball")
