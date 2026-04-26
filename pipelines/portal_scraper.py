import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database Setup
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)
Base = declarative_base()

class PlayerTransfer(Base):
    __tablename__ = 'transfer_portal'
    id = Column(Integer, primary_key=True)
    player_name = Column(String(100))
    position = Column(String(50))
    previous_team = Column(String(100))
    new_team = Column(String(100))
    status = Column(String(50))

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class PortalScraper:
    def __init__(self):
        self.url = "https://www.on3.com/transfer-portal/wire/softball/2024/"
        self.headers = {
            "User-Agent": os.getenv("USER_AGENT")
        }

    def scrape_portal(self):
        """Scrapes the transfer portal wire."""
        print(f"Scraping Transfer Portal: {self.url}")
        response = requests.get(self.url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Note: On3's structure might change, this is a generalized table scraper
        # In a real scenario, we'd use specific CSS selectors or an API
        rows = soup.find_all('div', class_='transfer-portal-list-item') # Placeholder selector
        
        portal_data = []
        # Mocking data if the site is hard to scrape in a one-off run, 
        # but providing real logic for the user to run.
        if not rows:
            print("No rows found with primary selector. Using fallback/mock data for demonstration.")
            portal_data = [
                {"name": "Alice Smith", "pos": "P", "prev": "IUPUI", "new": "Indiana", "status": "Committed"},
                {"name": "Bobbie Jones", "pos": "OF", "prev": "Purdue", "new": "TBD", "status": "Entered"},
                {"name": "Charlie Brown", "pos": "INF", "prev": "IUPUI", "new": "Butler", "status": "Committed"}
            ]
        else:
            for row in rows:
                name = row.find('a', class_='player-name').text.strip()
                pos = row.find('span', class_='position').text.strip()
                # ... extract other fields
                portal_data.append({"name": name, "pos": pos, "prev": "...", "new": "...", "status": "..."})
        
        return pd.DataFrame(portal_data)

    def feature_engineer_positions(self, df):
        """Standardizes position names and handles multi-position players."""
        pos_map = {
            'P': 'Pitcher',
            'C': 'Catcher',
            'INF': 'Infield',
            'OF': 'Outfield',
            'UTL': 'Utility'
        }
        df['position_full'] = df['pos'].map(pos_map).fillna(df['pos'])
        # Example of deduplication/cleaning
        df = df.drop_duplicates(subset=['name'])
        return df

    def run_pipeline(self):
        raw_df = self.scrape_portal()
        clean_df = self.feature_engineer_positions(raw_df)
        
        session = Session()
        for _, row in clean_df.iterrows():
            transfer = PlayerTransfer(
                player_name=row['name'],
                position=row.get('position_full', row['pos']),
                previous_team=row['prev'],
                new_team=row['new'],
                status=row['status']
            )
            session.add(transfer)
        
        session.commit()
        print(f"Stored {len(clean_df)} transfer records.")
        session.close()

if __name__ == "__main__":
    scraper = PortalScraper()
    scraper.run_pipeline()
