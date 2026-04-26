import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)


def _draw_field(ax):
    """Draw a simple softball field diagram."""
    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-1, 5.5)
    ax.set_facecolor('#2d5016')
    ax.set_aspect('equal')
    ax.axis('off')

    diamond_x = [3, 5, 3, 1, 3]
    diamond_y = [0, 1.5, 3, 1.5, 0]
    ax.plot(diamond_x, diamond_y, color='white', linewidth=1.5, alpha=0.5)
    ax.plot([3, 0], [0, 4.5], color='white', linewidth=1, alpha=0.3, linestyle='--')
    ax.plot([3, 6], [0, 4.5], color='white', linewidth=1, alpha=0.3, linestyle='--')


# Coordinate mapping for field zones
COORDS = {
    'LF': (0.8, 3.8), 'LCF': (1.8, 4.3), 'CF': (3, 4.5),
    'RCF': (4.2, 4.3), 'RF': (5.2, 3.8),
    'SS': (2, 2.2), '2B': (4, 2.2), '3B': (1.2, 1.5),
    '1B': (4.8, 1.5), 'P': (3, 1.5), 'C': (3, 0.2)
}


def generate_filtered_heat_map(team="All", player="All"):
    """Generates a heat map filtered by team and/or player."""
    query = ("SELECT hit_location, is_hit "
             "FROM play_by_play "
             "WHERE hit_location != 'Unknown' AND batting_team != 'IUPUI'")
    if team != "All":
        query += f" AND source_team = '{team}' AND batting_team = '{team}'"
    if player != "All":
        query += f" AND player = '{player}'"

    try:
        df = pd.read_sql(query, engine)
    except Exception:
        df = pd.DataFrame()

    fig, ax = plt.subplots(figsize=(8, 7))
    _draw_field(ax)

    if df.empty or len(df) < 3:
        ax.text(3, 2.5, 'Not enough data', ha='center', va='center',
                fontsize=14, color='white', alpha=0.7)
        title = "Batted Ball Heat Map"
        if team != "All":
            title += f" — {team}"
        if player != "All":
            title += f" — {player}"
        ax.set_title(title, fontsize=13, color='white', pad=12)
        fig.patch.set_facecolor('#0e1117')
        plt.tight_layout()
        return fig

    df['x'] = df['hit_location'].map(lambda x: COORDS.get(x, (3, 2.5))[0])
    df['y'] = df['hit_location'].map(lambda x: COORDS.get(x, (3, 2.5))[1])

    try:
        sns.kdeplot(data=df, x='x', y='y', fill=True,
                    cmap='YlOrRd', thresh=0.05, levels=12, ax=ax, alpha=0.7)
    except Exception:
        pass

    hits = df[df['is_hit'] == 1]
    outs = df[df['is_hit'] == 0]
    if not outs.empty:
        ax.scatter(outs['x'], outs['y'], color='white', alpha=0.3, s=15, zorder=3)
    if not hits.empty:
        ax.scatter(hits['x'], hits['y'], color='#00ff88', alpha=0.6,
                   s=30, edgecolors='white', linewidths=0.5, zorder=4)

    for loc, (x, y) in COORDS.items():
        ax.text(x, y - 0.25, loc, fontsize=9, ha='center', va='top',
                color='white', alpha=0.6, fontweight='bold')

    title = "Opponent Batted Ball Heat Map"
    if team != "All":
        title += f" — {team}"
    if player != "All":
        title += f" — {player}"
    ax.set_title(title, fontsize=13, color='white', pad=12)
    fig.patch.set_facecolor('#0e1117')
    plt.tight_layout()
    return fig


def generate_heat_map():
    fig = generate_filtered_heat_map()
    os.makedirs('analysis', exist_ok=True)
    fig.savefig('analysis/opponent_heat_map.png', dpi=150, facecolor=fig.get_facecolor())
    print("Heat map saved to analysis/opponent_heat_map.png")
    plt.close(fig)


if __name__ == "__main__":
    generate_heat_map()
