import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database Setup
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)
Base = declarative_base()

class PlayByPlay(Base):
    __tablename__ = 'play_by_play'
    id = Column(Integer, primary_key=True)
    game_id = Column(String(50))
    opponent = Column(String(100))
    inning = Column(String(20))
    half = Column(String(10))        # "Top" or "Bottom"
    batting_team = Column(String(100)) # Which team is batting
    player = Column(String(100))
    description = Column(String(500))
    hit_location = Column(String(50))
    hit_type = Column(String(50))    # single, double, triple, HR, groundout, flyout, etc.
    is_hit = Column(Integer)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class IUIndyScraper:
    """Scrapes PBP data from iuindyjags.com for IUPUI 2024 opponents."""

    BASE_URL = "https://iuindyjags.com"
    SCHEDULE_URL = f"{BASE_URL}/sports/softball/schedule/2024"

    def __init__(self):
        self.headers = {
            "User-Agent": os.getenv("USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        }

    # ── Extraction ──────────────────────────────────────────────

    def get_all_games(self):
        """Fetch list of (opponent_slug, game_id) from the 2024 schedule."""
        r = requests.get(self.SCHEDULE_URL, headers=self.headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(
            r'/sports/softball/stats/2024/.+/boxscore/\d+'))

        seen, games = set(), []
        for link in links:
            m = re.search(r'/stats/2024/(.+)/boxscore/(\d+)', link['href'])
            if m:
                key = (m.group(1), m.group(2))
                if key not in seen:
                    seen.add(key)
                    games.append(key)
        return games

    def scrape_pbp(self, opponent_slug, game_id):
        """Scrape PBP from a single box-score page."""
        url = f"{self.BASE_URL}/sports/softball/stats/2024/{opponent_slug}/boxscore/{game_id}"
        print(f"  Scraping: {url}")
        r = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(r.text, 'html.parser')

        pbp_section = soup.find(id='play-by-play')
        if not pbp_section:
            print(f"    ⚠ No PBP section found for game {game_id}")
            return pd.DataFrame()

        opponent_name = opponent_slug.replace('-', ' ').title()
        rows = []

        # Each half-inning is in its own table inside the PBP section
        tables = pbp_section.find_all('table')
        for table in tables:
            # The caption or preceding header tells us the half-inning
            caption = table.find('caption')
            header_text = ""
            if caption:
                header_text = caption.text.strip()
            else:
                prev = table.find_previous(['h3', 'h4', 'div'])
                if prev:
                    header_text = prev.text.strip()

            # Determine inning and batting team
            inning_match = re.search(r'(Top|Bottom)\s+of\s+(\d+)', header_text)
            if not inning_match:
                # Try alternative: "UAB - Top of 1st"
                inning_match = re.search(r'(Top|Bottom)\s+of\s+(\w+)', header_text)
            
            if inning_match:
                half = inning_match.group(1)
                inning_num = inning_match.group(2)
            else:
                half = "Unknown"
                inning_num = "?"

            # Determine batting team from header
            is_opponent_batting = False
            header_lower = header_text.lower()
            if "iupui" in header_lower or "iu indy" in header_lower or "iup" in header_lower:
                batting_team = "IUPUI"
            else:
                batting_team = opponent_name
                is_opponent_batting = True

            # Parse rows
            trs = table.find_all('tr')
            for tr in trs:
                tds = tr.find_all('td')
                if not tds:
                    continue
                desc = tds[0].text.strip()
                if not desc or desc == 'Play Description':
                    continue
                # Skip summary rows
                if desc.startswith('Runs') or desc.startswith('Hits') or desc.startswith('Errors'):
                    continue

                # Extract player name (first word or "Last, First" pattern)
                player = self._extract_player(desc)
                hit_loc = self._extract_location(desc)
                hit_type = self._extract_hit_type(desc)
                is_hit = 1 if hit_type in ['single', 'double', 'triple', 'home_run'] else 0

                rows.append({
                    'game_id': game_id,
                    'opponent': opponent_name,
                    'inning': inning_num,
                    'half': half,
                    'batting_team': batting_team,
                    'player': player,
                    'description': desc,
                    'hit_location': hit_loc,
                    'hit_type': hit_type,
                    'is_hit': is_hit,
                })

        return pd.DataFrame(rows)

    # ── Transformation helpers ──────────────────────────────────

    @staticmethod
    def _extract_player(desc):
        """Extract player name from play description."""
        # Patterns: "B. Wiggins walked" or "Calvert, Ken singled"
        m = re.match(r'^([A-Z][a-z]+,\s*[A-Z][a-z]+)', desc)
        if m:
            return m.group(1)
        m = re.match(r'^([A-Z]\.\s*[A-Z][a-z]+)', desc)
        if m:
            return m.group(1)
        # Fallback: first two words
        parts = desc.split()
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}".rstrip(',')
        return parts[0] if parts else "Unknown"

    @staticmethod
    def _extract_location(desc):
        d = desc.lower()
        if 'left center' in d:   return 'LCF'
        if 'right center' in d:  return 'RCF'
        if 'left field' in d or 'to lf' in d:  return 'LF'
        if 'center field' in d or 'to cf' in d: return 'CF'
        if 'right field' in d or 'to rf' in d:  return 'RF'
        if 'right side' in d:    return 'RF'
        if 'left side' in d:     return 'LF'
        if 'shortstop' in d or 'to ss' in d:    return 'SS'
        if 'second base' in d or 'to 2b' in d:  return '2B'
        if 'third base' in d or 'to 3b' in d:   return '3B'
        if 'first base' in d or 'to 1b' in d:   return '1B'
        if 'pitcher' in d or 'to p ' in d:      return 'P'
        if 'catcher' in d or 'to c ' in d:      return 'C'
        return 'Unknown'

    @staticmethod
    def _extract_hit_type(desc):
        d = desc.lower()
        if 'homered' in d or 'home run' in d:  return 'home_run'
        if 'tripled' in d:   return 'triple'
        if 'doubled' in d:   return 'double'
        if 'singled' in d:   return 'single'
        if 'walked' in d:    return 'walk'
        if 'struck out' in d: return 'strikeout'
        if 'grounded out' in d: return 'groundout'
        if 'flied out' in d or 'flyout' in d: return 'flyout'
        if 'fouled out' in d: return 'foulout'
        if 'popped up' in d or 'pop out' in d: return 'popout'
        if 'lined out' in d: return 'lineout'
        if 'reached on' in d: return 'reached'
        if 'hit by pitch' in d: return 'hbp'
        if 'stole' in d:     return 'stolen_base'
        if 'advanced' in d:  return 'advance'
        if 'picked off' in d: return 'pickoff'
        if 'out at' in d:    return 'out'
        if 'bunt' in d:      return 'bunt'
        return 'other'

    # ── Loading ─────────────────────────────────────────────────

    def run_pipeline(self, limit=None):
        """Execute the full ETL pipeline."""
        games = self.get_all_games()
        print(f"Found {len(games)} games on the 2024 schedule.\n")

        session = Session()
        # Clear old data
        session.execute(text("DELETE FROM play_by_play"))
        session.commit()

        total_plays = 0
        for i, (opp_slug, g_id) in enumerate(games):
            if limit and i >= limit:
                break
            print(f"[{i+1}/{len(games)}] {opp_slug} (game {g_id})")
            df = self.scrape_pbp(opp_slug, g_id)
            if df.empty:
                continue

            for _, row in df.iterrows():
                play = PlayByPlay(**row.to_dict())
                session.add(play)

            session.commit()
            total_plays += len(df)
            print(f"    ✓ Stored {len(df)} plays (total: {total_plays})\n")
            time.sleep(0.5)  # Be polite

        session.close()
        print(f"\n{'='*50}")
        print(f"Pipeline complete. Total plays stored: {total_plays}")


if __name__ == "__main__":
    scraper = IUIndyScraper()
    scraper.run_pipeline()
