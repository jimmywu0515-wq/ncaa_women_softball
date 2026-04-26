import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import time

load_dotenv()

# Database Setup
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)
Base = declarative_base()

class PlayByPlay(Base):
    __tablename__ = 'play_by_play'
    id = Column(Integer, primary_key=True)
    game_id = Column(String(50))
    inning = Column(String(10))
    team = Column(String(100))
    player = Column(String(100)) # New Column
    description = Column(String(500))
    hit_location = Column(String(50))
    is_hit = Column(Integer)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class NCAAScraper:
    def __init__(self, team_id="572238", year="2024"):
        self.team_id = team_id
        self.year = year
        self.base_url = "https://stats.ncaa.org"
        self.headers = {
            "User-Agent": os.getenv("USER_AGENT")
        }

    def get_game_ids(self):
        """Fetches all game IDs for the season from the team schedule page."""
        url = f"{self.base_url}/teams/{self.team_id}"
        print(f"Fetching schedule from: {url}")
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        game_links = soup.find_all('a', href=re.compile(r'/contests/\d+/box_score'))
        game_ids = [re.search(r'/contests/(\d+)/box_score', link['href']).group(1) for link in game_links]
        return list(set(game_ids))

    def scrape_pbp(self, game_id):
        """Scrapes play-by-play data for a specific game."""
        url = f"{self.base_url}/contests/{game_id}/play_by_play"
        print(f"Scraping PBP: {url}")
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get team names from page header or similar
        team_headers = soup.find_all('div', class_='team-name') # Placeholder, will adapt
        team1_name = "Home"
        team2_name = "Away"
        
        tables = soup.find_all('table', class_='mytable')
        pbp_data = []
        
        for table in tables:
            rows = table.find_all('tr')
            current_inning = ""
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 1 and 'Inning' in cols[0].text:
                    current_inning = cols[0].text.strip()
                    continue
                
                if len(cols) >= 3:
                    team1_play = cols[1].text.strip()
                    team2_play = cols[2].text.strip() if len(cols) > 2 else ""
                    
                    if team1_play:
                        player = team1_play.split(' ')[0] # Basic heuristic: first word is player
                        pbp_data.append({
                            "game_id": game_id,
                            "inning": current_inning,
                            "team": team1_name,
                            "player": player,
                            "description": team1_play
                        })
                    if team2_play:
                        player = team2_play.split(' ')[0]
                        pbp_data.append({
                            "game_id": game_id,
                            "inning": current_inning,
                            "team": team2_name,
                            "player": player,
                            "description": team2_play
                        })
        
        return pd.DataFrame(pbp_data)

    def transform_pbp(self, df):
        """Feature engineering: Extract hit location from play description."""
        def extract_location(desc):
            desc = desc.lower()
            if 'left field' in desc: return 'LF'
            if 'center field' in desc: return 'CF'
            if 'right field' in desc: return 'RF'
            if 'shortstop' in desc or 'to ss' in desc: return 'SS'
            if 'second base' in desc or 'to 2b' in desc: return '2B'
            if 'third base' in desc or 'to 3b' in desc: return '3B'
            if 'first base' in desc or 'to 1b' in desc: return '1B'
            if 'pitcher' in desc or 'to p' in desc: return 'P'
            if 'catcher' in desc or 'to c' in desc: return 'C'
            return 'Unknown'

        df['hit_location'] = df['description'].apply(extract_location)
        df['is_hit'] = df['description'].apply(lambda x: 1 if any(h in x.lower() for h in ['singled', 'doubled', 'tripled', 'homered']) else 0)
        return df

    def run_pipeline(self, limit=5):
        """Executes the full ETL pipeline."""
        game_ids = self.get_game_ids()
        print(f"Found {len(game_ids)} games.")
        
        session = Session()
        for g_id in game_ids[:limit]: # Limit for demonstration
            raw_data = self.scrape_pbp(g_id)
            if raw_data.empty: continue
            
            clean_data = self.transform_pbp(raw_data)
            
            for _, row in clean_data.iterrows():
                play = PlayByPlay(
                    game_id=row['game_id'],
                    inning=row['inning'],
                    team=row['team'],
                    player=row['player'],
                    description=row['description'],
                    hit_location=row['hit_location'],
                    is_hit=row['is_hit']
                )
                session.add(play)
            
            session.commit()
            print(f"Stored {len(clean_data)} plays for game {g_id}")
            time.sleep(1) # Be respectful to servers
        
        session.close()

if __name__ == "__main__":
    scraper = NCAAScraper()
    scraper.run_pipeline()
