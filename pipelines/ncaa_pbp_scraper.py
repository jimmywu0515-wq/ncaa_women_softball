"""
NCAA Softball PBP Scraper — Full Season ETL Pipeline
=====================================================
Scrapes Play-by-Play data for ALL 2024 games of every IUPUI opponent
from each team's official Sidearm Sports athletics website.

Demonstrates: ETL pipeline design, web scraping, regex-based feature
engineering, and SQLAlchemy data warehousing.
"""
import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ── Database Setup ──────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ncaa_softball.db")
engine = create_engine(DB_URL)
Base = declarative_base()


class PlayByPlay(Base):
    __tablename__ = 'play_by_play'
    id = Column(Integer, primary_key=True)
    game_id = Column(String(50))
    source_team = Column(String(100))     # Which team's site we scraped from
    opponent_in_game = Column(String(100)) # The other team in this game
    inning = Column(String(20))
    half = Column(String(10))
    batting_team = Column(String(100))
    player = Column(String(100))
    description = Column(String(500))
    hit_location = Column(String(50))
    hit_type = Column(String(50))
    is_hit = Column(Integer)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


# ── Team Site Registry ──────────────────────────────────────────
# Maps the opponent name (as it appears in IUPUI's schedule) to
# (sidearm_base_url, canonical_team_name).
TEAM_SITES = {
    'Uab':               ('https://uabsports.com',       'UAB'),
    'Mississippi State': ('https://hailstate.com',        'Mississippi State'),
    'Georgetown':        ('https://guhoyas.com',          'Georgetown'),
    'Furman':            ('https://furmanpaladins.com',    'Furman'),
    'Lipscomb':          ('https://lipscombsports.com',   'Lipscomb'),
    'Towson':            ('https://towsontigers.com',     'Towson'),
    'Toledo':            ('https://utrockets.com',        'Toledo'),
    'Murray State':      ('https://goracers.com',         'Murray State'),
    'Western Illinois':  ('https://goleathernecks.com',   'Western Illinois'),
    'Indiana State':     ('https://gosycamores.com',      'Indiana State'),
    'Ohio':              ('https://ohiobobcats.com',       'Ohio'),
    'Austin Peay':       ('https://letsgopeay.com',       'Austin Peay'),
    'Saint Louis':       ('https://slubillikens.com',     'Saint Louis'),
    'Butler':            ('https://butlersports.com',     'Butler'),
    'Dayton':            ('https://daytonflyers.com',     'Dayton'),
    'Indiana':           ('https://iuhoosiers.com',       'Indiana'),
    'Eastern Illinois':  ('https://eiupanthers.com',      'Eastern Illinois'),
    'Cleveland State':   ('https://csuvikings.com',       'Cleveland State'),
    'Robert Morris':     ('https://rmucolonials.com',     'Robert Morris'),
    'Detroit Mercy':     ('https://detroittitans.com',    'Detroit Mercy'),
    'Northern Kentucky': ('https://nkunorse.com',         'Northern Kentucky'),
    'Purdue Fort Wayne': ('https://gomastodons.com',      'Purdue Fort Wayne'),
    'Oakland':           ('https://goldengrizzlies.com',  'Oakland'),
    'Green Bay':         ('https://greenbayphoenix.com',  'Green Bay'),
    'Youngstown State':  ('https://ysusports.com',        'Youngstown State'),
}


class SidearmScraper:
    """Generalised Sidearm-Sports PBP scraper."""

    def __init__(self):
        self.headers = {
            "User-Agent": os.getenv("USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        }

    # ── Extraction ──────────────────────────────────────────────

    def get_games(self, base_url):
        """Fetch list of (opponent_slug, game_id) from a Sidearm 2024 schedule."""
        url = f"{base_url}/sports/softball/schedule/2024"
        r = requests.get(url, headers=self.headers, timeout=15)
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

    def scrape_pbp(self, base_url, opp_slug, game_id, source_team):
        """Scrape PBP from one box-score page."""
        url = f"{base_url}/sports/softball/stats/2024/{opp_slug}/boxscore/{game_id}"
        r = requests.get(url, headers=self.headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')

        pbp_section = soup.find(id='play-by-play')
        if not pbp_section:
            return pd.DataFrame()

        opponent_in_game = opp_slug.replace('-', ' ').title()
        rows = []

        tables = pbp_section.find_all('table')
        for table in tables:
            # Determine half-inning from surrounding text
            caption = table.find('caption')
            header_text = caption.text.strip() if caption else ""
            if not header_text:
                prev = table.find_previous(['h3', 'h4', 'div'])
                if prev:
                    header_text = prev.text.strip()

            inning_match = re.search(r'(Top|Bottom)\s+of\s+(\w+)', header_text)
            half = inning_match.group(1) if inning_match else "Unknown"
            inning_num = inning_match.group(2) if inning_match else "?"

            # Determine batting team
            header_lower = header_text.lower()
            source_lower = source_team.lower()
            # The source team name might appear many ways in the header
            if any(tok in header_lower for tok in source_lower.split()):
                batting_team = source_team
            else:
                batting_team = opponent_in_game

            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if not tds:
                    continue
                desc = tds[0].text.strip()
                if not desc or desc == 'Play Description':
                    continue
                if desc in ('Runs', 'Hits', 'Errors', 'Left On Base'):
                    continue

                player = self._extract_player(desc)
                hit_loc = self._extract_location(desc)
                hit_type = self._extract_hit_type(desc)
                is_hit = 1 if hit_type in ('single', 'double', 'triple', 'home_run') else 0

                rows.append({
                    'game_id': game_id,
                    'source_team': source_team,
                    'opponent_in_game': opponent_in_game,
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

    # ── Transformation ──────────────────────────────────────────

    @staticmethod
    def _extract_player(desc):
        """
        Extract player name from Sidearm PBP description.

        Handles three formats:
          1. "CHIPPS,A walked ..."       → CHIPPS,A    (home team ALL-CAPS)
          2. "Calvert, Ken walked ..."   → Calvert, Ken (home team Title Case, space after comma)
          3. "B. Wiggins walked ..."     → B. Wiggins  (visitor Initial.Last)

        Also handles:
          - "pinch hit for SMITH,J, singled ..." → first player name before action
          - "McPhearson, struck out ..."         → name with no first-initial
        """
        # Strip leading/trailing whitespace
        desc = desc.strip()

        # Format 1: ALL-CAPS with comma, no space  "CHIPPS,A"
        m = re.match(r'^([A-Z]{2,},[A-Z])\b', desc)
        if m:
            return m.group(1)

        # Format 2: Title case with comma+space and abbreviated first name "Calvert, Ken"
        # Must ensure the second part is a name (capitalized) not an action verb
        m = re.match(r'^([A-Z][a-zA-Z\'-]+,\s*[A-Z][a-z]{1,3})\b', desc)
        if m:
            candidate = m.group(1)
            # Verify second part isn't an action word
            second_word = candidate.split(',')[1].strip().lower()
            action_words = {'walked', 'singled', 'doubled', 'tripled', 'homered',
                            'struck', 'grounded', 'flied', 'fouled', 'lined',
                            'popped', 'reached', 'stole', 'advanced', 'pinch',
                            'hit', 'out', 'picked', 'caught', 'intentionally',
                            'was', 'scored'}
            if second_word not in action_words:
                return candidate

        # Format 3: "F. LastName" (visitor format)
        m = re.match(r'^([A-Z]\.\s*[A-Za-z\'-]+)', desc)
        if m:
            return m.group(1)

        # Format 4: Single last name followed by comma but no valid first name
        # e.g. "McPhearson, struck out ..." → just "McPhearson"
        m = re.match(r'^([A-Z][a-zA-Z\'-]+),', desc)
        if m:
            return m.group(1)

        # Fallback: first word
        return desc.split()[0].rstrip(',') if desc else "Unknown"

    @staticmethod
    def _extract_location(desc):
        d = desc.lower()
        if 'left center' in d:                          return 'LCF'
        if 'right center' in d:                         return 'RCF'
        if 'down the lf line' in d:                     return 'LF'
        if 'down the rf line' in d:                     return 'RF'
        if 'left field' in d or 'to lf' in d:           return 'LF'
        if 'center field' in d or 'to cf' in d:         return 'CF'
        if 'right field' in d or 'to rf' in d:          return 'RF'
        if 'right side' in d or 'through the right' in d: return 'RF'
        if 'left side' in d or 'through the left' in d:   return 'LF'
        if 'up the middle' in d:                        return 'CF'
        if 'shortstop' in d or 'to ss' in d:            return 'SS'
        if 'second base' in d or 'to 2b' in d:         return '2B'
        if 'third base' in d or 'to 3b' in d:          return '3B'
        if 'first base' in d or 'to 1b' in d:          return '1B'
        if 'pitcher' in d or 'to p ' in d or 'to p.' in d: return 'P'
        if 'catcher' in d or 'to c ' in d or 'to c.' in d: return 'C'
        return 'Unknown'

    @staticmethod
    def _extract_hit_type(desc):
        d = desc.lower()
        # Handle "pinch hit for X, <actual result>" — skip to result
        if 'pinch hit' in d or 'pinch ran' in d:
            # Look for the actual result after the substitution
            after_comma = d.split(',', 1)
            if len(after_comma) > 1:
                d = after_comma[1]  # Re-parse the remainder
            else:
                return 'substitution'

        if 'homered' in d or 'home run' in d:    return 'home_run'
        if 'tripled' in d:                       return 'triple'
        if 'doubled' in d:                       return 'double'
        if 'singled' in d:                       return 'single'
        if 'walked' in d:                        return 'walk'
        if 'struck out' in d:                    return 'strikeout'
        if 'grounded out' in d:                  return 'groundout'
        if 'grounded into' in d:                 return 'groundout'
        if 'flied out' in d or 'flyout' in d:    return 'flyout'
        if 'fouled out' in d:                    return 'foulout'
        if 'popped up' in d or 'pop out' in d:   return 'popout'
        if 'lined out' in d:                     return 'lineout'
        if 'reached on' in d:                    return 'reached'
        if 'hit by pitch' in d:                  return 'hbp'
        if 'stole' in d:                         return 'stolen_base'
        if 'advanced' in d:                      return 'advance'
        if 'picked off' in d:                    return 'pickoff'
        if 'caught stealing' in d:               return 'caught_stealing'
        if 'out at' in d:                        return 'out'
        if 'bunt' in d:                          return 'bunt'
        if 'intentionally walked' in d:          return 'ibb'
        if 'scored' in d:                        return 'scored'
        return 'other'

    # ── Pipeline ────────────────────────────────────────────────

    def scrape_team(self, team_name, base_url, session, limit=None):
        """Scrape ALL 2024 games for a single team."""
        print(f"\n{'='*60}")
        print(f"  {team_name}  ({base_url})")
        print(f"{'='*60}")

        try:
            games = self.get_games(base_url)
        except Exception as e:
            print(f"  ⚠ Failed to fetch schedule: {e}")
            return 0

        print(f"  Found {len(games)} games\n")
        total = 0

        for i, (opp_slug, g_id) in enumerate(games):
            if limit and i >= limit:
                break
            try:
                df = self.scrape_pbp(base_url, opp_slug, g_id, team_name)
            except Exception as e:
                print(f"  [{i+1}] {opp_slug} #{g_id} — ERROR: {e}")
                continue

            if df.empty:
                continue

            for _, row in df.iterrows():
                session.add(PlayByPlay(**row.to_dict()))
            session.commit()
            total += len(df)
            print(f"  [{i+1}/{len(games)}] vs {opp_slug} — {len(df)} plays (team total: {total})")
            time.sleep(0.3)

        return total

    def run_pipeline(self, teams=None, limit_games=None):
        """Execute full ETL for all (or specified) opponent teams."""
        session = Session()
        session.execute(text("DELETE FROM play_by_play"))
        session.commit()

        if teams is None:
            teams = TEAM_SITES

        grand_total = 0
        for i, (key, (url, canonical)) in enumerate(teams.items()):
            print(f"\n[TEAM {i+1}/{len(teams)}]", end="")
            count = self.scrape_team(canonical, url, session, limit=limit_games)
            grand_total += count

        session.close()
        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETE — {grand_total} total plays stored")
        print(f"{'='*60}")


if __name__ == "__main__":
    scraper = SidearmScraper()
    scraper.run_pipeline()
