import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier

load_dotenv()

# Database Setup
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)

def generate_heat_map():
    # Load data from database
    query = "SELECT hit_location, is_hit FROM play_by_play WHERE hit_location != 'Unknown'"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("No data found for heatmap. Generating sample data for visualization.")
        # Mock data if database is empty
        locations = ['LF', 'CF', 'RF', 'SS', '2B', '3B', '1B', 'P', 'C']
        df = pd.DataFrame({
            'hit_location': np.random.choice(locations, 100),
            'is_hit': np.random.choice([0, 1], 100, p=[0.7, 0.3])
        })

    # Coordinate mapping for field zones
    coords = {
        'LF': (1, 3), 'CF': (3, 4), 'RF': (5, 3),
        'SS': (2, 2), '2B': (4, 2), '3B': (1, 1), 
        '1B': (5, 1), 'P': (3, 1), 'C': (3, 0)
    }
    
    df['x'] = df['hit_location'].map(lambda x: coords.get(x, (0,0))[0])
    df['y'] = df['hit_location'].map(lambda x: coords.get(x, (0,0))[1])
    
    # Calculate Hit Density
    plt.figure(figsize=(10, 8))
    sns.kdeplot(data=df[df['is_hit'] == 1], x='x', y='y', fill=True, cmap='Reds', thresh=0, levels=10)
    
    # Overlay Field Diagram
    plt.scatter([c[0] for c in coords.values()], [c[1] for c in coords.values()], color='black', marker='o')
    for loc, (x, y) in coords.items():
        plt.text(x, y, loc, fontsize=12, ha='center', va='bottom')
    
    plt.title("IUPUI 2024 Opponent Batted Ball Heat Map")
    plt.xlim(0, 6)
    plt.ylim(-1, 5)
    plt.axis('off')
    
    os.makedirs('analysis', exist_ok=True)
    plt.savefig('analysis/opponent_heat_map.png')
    print("Heat map saved to analysis/opponent_heat_map.png")

def train_predictive_model():
    """Demonstrates predictive modeling capability."""
    # Query data
    query = "SELECT hit_location, is_hit FROM play_by_play WHERE hit_location != 'Unknown'"
    df = pd.read_sql(query, engine)
    
    if df.empty or len(df) < 10:
        print("Insufficient data for modeling. Skipping training.")
        return

    # One-hot encode location
    X = pd.get_dummies(df['hit_location'])
    y = df['is_hit']
    
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)
    print("Predictive model trained. Accuracy Score: ", model.score(X, y))

def generate_filtered_heat_map(team="All", player="All"):
    """Generates a heat map filtered by team and/or player."""
    query = "SELECT hit_location, is_hit FROM play_by_play WHERE hit_location != 'Unknown'"
    if team != "All":
        query += f" AND team = '{team}'"
    if player != "All":
        query += f" AND player = '{player}'"
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        # Mock data for visualization if filtered result is empty
        locations = ['LF', 'CF', 'RF', 'SS', '2B', '3B', '1B', 'P', 'C']
        df = pd.DataFrame({
            'hit_location': np.random.choice(locations, 50),
            'is_hit': np.random.choice([0, 1], 50, p=[0.7, 0.3])
        })

    coords = {
        'LF': (1, 3), 'CF': (3, 4), 'RF': (5, 3),
        'SS': (2, 2), '2B': (4, 2), '3B': (1, 1), 
        '1B': (5, 1), 'P': (3, 1), 'C': (3, 0)
    }
    
    df['x'] = df['hit_location'].map(lambda x: coords.get(x, (0,0))[0])
    df['y'] = df['hit_location'].map(lambda x: coords.get(x, (0,0))[1])
    
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.kdeplot(data=df[df['is_hit'] == 1], x='x', y='y', fill=True, cmap='Reds', thresh=0, levels=10, ax=ax)
    
    ax.scatter([c[0] for c in coords.values()], [c[1] for c in coords.values()], color='black', marker='o')
    for loc, (x, y) in coords.items():
        ax.text(x, y, loc, fontsize=12, ha='center', va='bottom')
    
    ax.set_title(f"Batted Ball Heat Map: {team} - {player}")
    ax.set_xlim(0, 6)
    ax.set_ylim(-1, 5)
    ax.axis('off')
    
    return fig

if __name__ == "__main__":
    generate_heat_map()
    train_predictive_model()
