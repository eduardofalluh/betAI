"""
BetAI Advisor API — Chat by sport category + odds & predictions.
Uses OpenAI for real LLM conversation when OPENAI_API_KEY is set; falls back to rule-based replies otherwise.
Auth: signup/login with JWT; chats stored per user.
"""
import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

JWT_SECRET = os.getenv("JWT_SECRET", "").strip() or os.getenv("OPENAI_API_KEY", "betai-default-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXP_DAYS = 30

# LLM: load key from env or from encrypted storage (never logged or exposed)
def _load_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    passphrase = os.getenv("BETAI_PASSPHRASE", "").strip()
    if passphrase:
        from secrets_helper import load_and_decrypt
        key = load_and_decrypt(passphrase)
        if key:
            return key
    return ""

OPENAI_API_KEY = _load_openai_key()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip() or "gpt-5.2"
# Try these in order when the project doesn't have access to the default model
OPENAI_MODEL_FALLBACKS = [
    "gpt-5.2",
    "gpt-5.2-2025-12-11",
    "gpt-5.1",
    "gpt-5.1-2025-11-13",
    "gpt-5-mini",
    "gpt-5-mini-2025-08-07",
    "gpt-5-pro",
    "gpt-5-pro-2025-10-06",
    "gpt-4o",
]
# Vision-capable models (used when the user attaches images)
VISION_MODEL_FALLBACKS = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHATS_FILE = DATA_DIR / "chats.json"
USERS_FILE = DATA_DIR / "users.json"
CHATS_DIR = DATA_DIR / "chats"

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "YOUR_ODDS_API_KEY_HERE")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
ODDS_SCORES_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/scores/"
SPORTS_API_URL = "https://api.the-odds-api.com/v4/sports/"

# ESPN Fantasy Basketball (optional): league_id + year; for private leagues add ESPN_S2 and ESPN_SWID
ESPN_LEAGUE_ID = os.getenv("ESPN_LEAGUE_ID", "").strip()
ESPN_YEAR = int(os.getenv("ESPN_YEAR", "0") or "0")
ESPN_S2 = os.getenv("ESPN_S2", "").strip() or None
ESPN_SWID = os.getenv("ESPN_SWID", "").strip() or None
# Optional: comma-separated past years for standings + top scorers (e.g. "2024,2023"). If unset, use previous year only.
ESPN_PAST_YEARS_RAW = os.getenv("ESPN_PAST_YEARS", "").strip()
ESPN_PAST_YEARS = [int(y.strip()) for y in ESPN_PAST_YEARS_RAW.split(",") if y.strip().isdigit()] if ESPN_PAST_YEARS_RAW else []

# Frontend sport key -> Odds API key (multiple keys tried for Olympics)
SPORT_KEY_MAP = {
    "basketball": "basketball_nba",
    "soccer": "soccer_uefa_champs_league",
    "soccer_premier_league": "soccer_epl",  # English Premier League
    "american_football": "americanfootball_nfl",
    "baseball": "baseball_mlb",
    "hockey": "icehockey_nhl",
    "tennis": "tennis_atp",
    "mma": "mma_mixed_martial_arts",
    "olympics": "olympics_winter_2026",  # Milano Cortina; may vary by API availability
    "other": "basketball_nba",
}

# Human-readable sport names for live odds display
SPORT_TITLES = {
    "basketball_nba": "NBA",
    "soccer_uefa_champs_league": "Champions League",
    "soccer_epl": "Premier League",  # English Premier League
    "soccer_usa_mls": "MLS",
    "americanfootball_nfl": "NFL",
    "americanfootball_ncaaf": "NCAAF",
    "baseball_mlb": "MLB",
    "icehockey_nhl": "NHL",
    "tennis_atp": "Tennis ATP",
    "tennis_wta": "Tennis WTA",
    "mma_mixed_martial_arts": "MMA",
    "olympics_winter_2026": "Milano Cortina 2026",
}


def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)
    CHATS_DIR.mkdir(exist_ok=True)
    if not CHATS_FILE.exists():
        CHATS_FILE.write_text("{}")
    if not USERS_FILE.exists():
        USERS_FILE.write_text("{}")


# Initialize data directories on startup
ensure_data_dir()


def get_user_from_request() -> Optional[str]:
    """Return user_id from Authorization: Bearer <jwt> or None."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except jwt.InvalidTokenError:
        return None


def load_chats(user_id: Optional[str] = None):
    """Load chats. If user_id given, load from per-user file; else legacy single file."""
    ensure_data_dir()
    if user_id:
        path = CHATS_DIR / f"{user_id}.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    try:
        return json.loads(CHATS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_chats(chats, user_id: Optional[str] = None):
    """Save chats. If user_id given, save to per-user file; else legacy single file."""
    ensure_data_dir()
    if user_id:
        path = CHATS_DIR / f"{user_id}.json"
        path.write_text(json.dumps(chats, indent=2))
    else:
        CHATS_FILE.write_text(json.dumps(chats, indent=2))


def load_users():
    ensure_data_dir()
    try:
        return json.loads(USERS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_users(users):
    ensure_data_dir()
    USERS_FILE.write_text(json.dumps(users, indent=2))


def fetch_odds_data(sport_key="basketball_nba", live_only=False, markets=None):
    """Fetch odds for a sport. Use sport_key='upcoming' for live + next 8 across all sports.
    markets: optional list e.g. ['h2h', 'spreads'] for analysis; default ['h2h']."""
    url = ODDS_API_URL.format(sport_key=sport_key)
    m = (markets or ["h2h"])
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": ",".join(m) if isinstance(m, list) else m,
        "oddsFormat": "decimal",
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        return {"error": str(e)}
    return {"error": f"API Error: {r.status_code}"}


def fetch_scores(sport_key="upcoming", days_from=1):
    """Fetch live and recent scores (in-play + completed). Used to show current score alongside odds.
    Odds API: live odds update ~every 30s during games; scores endpoint gives current/last score."""
    url = ODDS_SCORES_URL.format(sport_key=sport_key)
    params = {"apiKey": ODDS_API_KEY}
    if days_from is not None:
        params["daysFrom"] = days_from
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return []
    return []


def fetch_live_upcoming_odds():
    """
    Fetch live and upcoming games across all sports (Odds API sport_key='upcoming').
    Enriches with live/recent scores when available (Scores API). Odds update ~every 30s when in-play.
    Returns games grouped by sport for conversational display.
    """
    data = fetch_odds_data("upcoming")
    if isinstance(data, dict) and "error" in data:
        return data
    # Fetch scores for in-play and recently completed (same API; scores have event id, home_score, away_score)
    scores_list = fetch_scores("upcoming", days_from=1)
    scores_by_id = {}
    for ev in scores_list or []:
        eid = ev.get("id")
        if not eid:
            continue
        home_s = ev.get("home_score")
        away_s = ev.get("away_score")
        completed = ev.get("completed", False)
        if home_s is not None and away_s is not None:
            scores_by_id[eid] = {"home": home_s, "away": away_s, "completed": completed}
    by_sport = {}
    for event in data or []:
        sk = event.get("sport_key", "other")
        title = SPORT_TITLES.get(sk, sk.replace("_", " ").title())
        if title not in by_sport:
            by_sport[title] = []
        home = event.get("home_team", "?")
        away = event.get("away_team", "?")
        commence = event.get("commence_time", "")[:16].replace("T", " ")
        score_str = None
        eid = event.get("id")
        if eid and eid in scores_by_id:
            s = scores_by_id[eid]
            score_str = f"{s['home']}-{s['away']}" + (" (FT)" if s.get("completed") else " (Live)")
        for b in event.get("bookmakers", [])[:1]:
            for m in b.get("markets", []):
                if m.get("key") != "h2h":
                    continue
                odds_str = ", ".join(f"{o['name']}: {o['price']}" for o in m.get("outcomes", []))
                item = {"match": f"{home} vs {away}", "odds": odds_str, "commence": commence}
                if score_str:
                    item["score"] = score_str
                by_sport[title].append(item)
                break
            break
    return by_sport


def fetch_all_sports():
    try:
        r = requests.get(SPORTS_API_URL, params={"apiKey": ODDS_API_KEY}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        return []
    return []


# ============================================================================
# THESPORTSDB INTEGRATION (Free API for team/player stats)
# ============================================================================

THESPORTSDB_API_URL = "https://www.thesportsdb.com/api/v1/json/3"  # Free tier (key=3)


def fetch_team_details(team_name: str, sport: str = "Soccer") -> dict:
    """Fetch team details from TheSportsDB (free tier, no key required)."""
    try:
        r = requests.get(
            f"{THESPORTSDB_API_URL}/searchteams.php",
            params={"t": team_name},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            teams = data.get("teams", [])
            if teams:
                return teams[0]
    except Exception as e:
        print(f"TheSportsDB team error: {e}", flush=True)
    return {}


def fetch_league_table(league_id: str, season: str = "2025-2026") -> list:
    """Fetch league standings from TheSportsDB."""
    try:
        r = requests.get(
            f"{THESPORTSDB_API_URL}/lookuptable.php",
            params={"l": league_id, "s": season},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("table", [])
    except Exception as e:
        print(f"TheSportsDB standings error: {e}", flush=True)
    return []


def fetch_recent_form(team_id: str, last_n: int = 5) -> list:
    """Fetch recent results for a team."""
    try:
        r = requests.get(
            f"{THESPORTSDB_API_URL}/eventslast.php",
            params={"id": team_id},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            events = data.get("results", [])
            return events[:last_n]
    except Exception as e:
        print(f"TheSportsDB form error: {e}", flush=True)
    return []


def fetch_player_stats(player_name: str, team: str = None) -> dict:
    """Fetch player statistics from TheSportsDB."""
    try:
        params = {"p": player_name}
        if team:
            params["t"] = team
        r = requests.get(
            f"{THESPORTSDB_API_URL}/searchplayers.php",
            params=params,
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            players = data.get("player", [])
            if players:
                return players[0]
    except Exception as e:
        print(f"TheSportsDB player error: {e}", flush=True)
    return {}


def format_player_stats_for_llm(player_data: dict) -> str:
    """Format player statistics for LLM context."""
    if not player_data:
        return ""

    lines = [f"Player: {player_data.get('strPlayer', '?')}"]
    if player_data.get("strPosition"):
        lines.append(f"Position: {player_data['strPosition']}")
    if player_data.get("strTeam"):
        lines.append(f"Team: {player_data['strTeam']}")
    if player_data.get("strNationality"):
        lines.append(f"Nationality: {player_data['strNationality']}")

    # Add statistics if available
    stats = []
    if player_data.get("intGoals"):
        stats.append(f"{player_data['intGoals']} goals")
    if player_data.get("intAssists"):
        stats.append(f"{player_data['intAssists']} assists")
    if stats:
        lines.append(f"Stats: {', '.join(stats)}")

    return "\n".join(lines)


# ============================================================================
# END THESPORTSDB INTEGRATION
# ============================================================================


def _implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability (0-100)."""
    if not decimal_odds or decimal_odds <= 0:
        return 0.0
    return 100.0 / float(decimal_odds)


def _build_game_analysis(game: dict) -> str:
    """Build in-depth analysis block for one game: odds by book, implied prob, best odds, spreads if present."""
    home = game.get("home_team", "Home")
    away = game.get("away_team", "Away")
    lines = [f"## {home} vs {away}", ""]
    best_h2h = {}  # outcome name -> (best decimal, bookmaker name)
    book_lines = []
    for b in game.get("bookmakers", []):
        book_name = b.get("title", "?")
        for m in b.get("markets", []):
            if m.get("key") == "h2h":
                parts = [f"**{book_name}** (moneyline):"]
                for o in m.get("outcomes", []):
                    name = o.get("name", "")
                    price = o.get("price")
                    if name and price:
                        imp = _implied_prob(price)
                        parts.append(f"  {name}: {price} (implied {imp:.1f}%)")
                        if name not in best_h2h or price > best_h2h[name][0]:
                            best_h2h[name] = (price, book_name)
                book_lines.append(" ".join(parts))
            elif m.get("key") == "spreads":
                parts = [f"**{book_name}** (spread):"]
                for o in m.get("outcomes", []):
                    name = o.get("name", "")
                    point = o.get("point")
                    price = o.get("price")
                    if name and point is not None and price:
                        parts.append(f"  {name} {point:+.1f} @ {price}")
                book_lines.append(" ".join(parts))
    lines.extend(book_lines)
    if best_h2h:
        lines.append("")
        lines.append("**Best odds by outcome:**")
        for name, (price, book) in best_h2h.items():
            imp = _implied_prob(price)
            lines.append(f"  {name}: {price} at {book} (implied {imp:.1f}%)")
        total_impl = sum(_implied_prob(best_h2h[n][0]) for n in best_h2h)
        lines.append(f"  (Combined best-odds implied total: {total_impl:.1f}%; below 100% = potential value.)")
    return "\n".join(lines)


def build_analysis_context(message: str, sport: str) -> str:
    """Build rich context for in-depth betting analysis: multiple books, implied prob, best odds, spreads."""
    msg = message.lower().strip()
    api_key = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])
    odds = fetch_odds_data(api_key, markets=["h2h", "spreads"])
    if isinstance(odds, dict) and "error" in odds:
        return f"(Could not load odds for analysis: {odds['error']})"
    games = odds or []
    # If user mentioned two teams, try to find that matchup
    if "vs" in msg:
        parts = msg.split("vs", 1)
        if len(parts) == 2:
            t1 = parts[0].strip().lower()
            t2 = parts[1].strip().lower()
            for g in games:
                home = g.get("home_team", "").lower()
                away = g.get("away_team", "").lower()
                if (t1 in home and t2 in away) or (t2 in home and t1 in away) or (t1 in away and t2 in home):
                    return "In-depth odds data for your analysis (use implied %, best odds, and spreads to suggest value and possible bets):\n\n" + _build_game_analysis(g)
    # Otherwise analyze first 2 upcoming games
    blocks = []
    for g in games[:2]:
        blocks.append(_build_game_analysis(g))
    if not blocks:
        return "(No upcoming games with odds for this sport.)"
    return "In-depth odds data for your analysis (use implied %, best odds, and spreads to suggest value and possible bets):\n\n" + "\n\n---\n\n".join(blocks)


def predict_outcome(team1, team2, odds_data):
    if isinstance(odds_data, dict) and "error" in odds_data:
        return f"⚠️ Error fetching odds: {odds_data['error']}"
    team1, team2 = team1.lower().strip(), team2.lower().strip()
    for game in odds_data or []:
        home_team = game.get("home_team", "").lower().strip()
        away_team = game.get("away_team", "").lower().strip()
        if (team1 in home_team or team2 in away_team) and (team2 in away_team or team1 in home_team):
            home_odds = away_odds = None
            for b in game.get("bookmakers", []):
                for m in b.get("markets", []):
                    if m.get("key") != "h2h":
                        continue
                    for o in m.get("outcomes", []):
                        n = o.get("name", "").lower().strip()
                        if n == home_team:
                            home_odds = o.get("price")
                        elif n == away_team:
                            away_odds = o.get("price")
            if home_odds and away_odds:
                winner = game["home_team"] if home_odds < away_odds else game["away_team"]
                return f"🏆 **{winner}** is the favorite. Odds — {game['home_team']}: {home_odds}, {game['away_team']}: {away_odds}"
        if (team2 in home_team or team1 in away_team) and (team1 in away_team or team2 in home_team):
            home_odds = away_odds = None
            for b in game.get("bookmakers", []):
                for m in b.get("markets", []):
                    if m.get("key") != "h2h":
                        continue
                    for o in m.get("outcomes", []):
                        n = o.get("name", "").lower().strip()
                        if n == home_team:
                            home_odds = o.get("price")
                        elif n == away_team:
                            away_odds = o.get("price")
            if home_odds and away_odds:
                winner = game["home_team"] if home_odds < away_odds else game["away_team"]
                return f"🏆 **{winner}** is the favorite. Odds — {game['home_team']}: {home_odds}, {game['away_team']}: {away_odds}"
    return f"⚠️ No odds found for that matchup. Try exact team names (e.g. 'Lakers' vs 'Celtics') or ask for current matchups."


def format_live_upcoming_reply(by_sport):
    """Format live/upcoming odds as a conversational agent reply."""
    if not by_sport:
        return (
            "There are no **live or upcoming** games with odds in the feed right now. "
            "Try asking for matchups for a specific sport (e.g. *Show NBA matchups*), "
            "or *Milano Cortina 2026* Olympics when available."
        )
    lines = ["Here’s what’s **live or coming up** across sports (odds update ~every 30s when in-play):\n"]
    for sport_name, games in by_sport.items():
        lines.append(f"**{sport_name}**")
        for g in games[:5]:
            part = f"• {g['match']}"
            if g.get("score"):
                part += f" **{g['score']}**"
            lines.append(part + f" — {g['odds']}")
        if len(games) > 5:
            lines.append(f"  _…and {len(games) - 5} more_")
        lines.append("")
    lines.append("_Want odds for one sport only? Pick it from the selector or ask e.g. *Show NBA matchups*. "
                 "You can also ask for **Milano Cortina 2026** Olympics._")
    return "\n".join(lines).strip()


def fetch_olympics_odds():
    """Try multiple sources for Olympics odds: olympics_winter_2026, olympics, then upcoming filtered by olympics."""
    for key in ("olympics_winter_2026", "olympics"):
        data = fetch_odds_data(key)
        if isinstance(data, dict) and "error" in data:
            continue
        if data and len(data) > 0:
            return data
    # Fallback: upcoming feed filtered for any sport_key containing "olympics"
    upcoming = fetch_odds_data("upcoming")
    if isinstance(upcoming, list):
        olympics_events = [e for e in upcoming if "olympics" in (e.get("sport_key") or "").lower()]
        if olympics_events:
            return olympics_events
    return []


def _format_events_as_matchups(events):
    """Turn a list of API events (with bookmakers/markets) into matchup lines."""
    lines = []
    for game in events or []:
        home = game.get("home_team", "?")
        away = game.get("away_team", "?")
        for b in game.get("bookmakers", []):
            for m in b.get("markets", []):
                if m.get("key") != "h2h":
                    continue
                parts = [f"**{home}** vs **{away}**"]
                for o in m.get("outcomes", []):
                    parts.append(f"{o.get('name')}: {o.get('price')}")
                lines.append(" — ".join(parts))
                break
            if lines and lines[-1].startswith(f"**{home}**"):
                break
    return "\n".join(lines) if lines else None


def get_matchups(sport_key=None):
    api_key = SPORT_KEY_MAP.get(sport_key, "basketball_nba") if sport_key else None
    if not api_key and sport_key:
        api_key = sport_key
    api_key = api_key or "basketball_nba"
    odds = None
    # Olympics: use multi-source fetch
    if sport_key == "olympics" or api_key == "olympics_winter_2026":
        odds = fetch_olympics_odds()
        if not odds:
            return "No matchups available for this sport right now."
    else:
        odds = fetch_odds_data(api_key)
        # Fallback: when sport-specific API fails or is empty, use upcoming feed filtered by sport
        if (isinstance(odds, dict) and "error" in odds) or not odds or (isinstance(odds, list) and len(odds) == 0):
            upcoming = fetch_odds_data("upcoming")
            if isinstance(upcoming, list) and upcoming:
                filtered = [e for e in upcoming if e.get("sport_key") == api_key]
                if filtered:
                    odds = filtered
        if isinstance(odds, dict) and "error" in odds:
            return f"Could not load odds: {odds['error']}"
    formatted = _format_events_as_matchups(odds if isinstance(odds, list) else [])
    if formatted:
        return formatted
    return "No matchups available for this sport right now."


def fetch_espn_fantasy_basketball():
    """
    Fetch ESPN Fantasy Basketball free agents (and fantasy points) for the configured league.
    Returns a string block for the LLM, or an error/setup message.
    Requires ESPN_LEAGUE_ID and ESPN_YEAR; for private leagues also ESPN_S2 and ESPN_SWID.
    """
    if not ESPN_LEAGUE_ID or not ESPN_YEAR:
        return (
            "(ESPN Fantasy Basketball is not configured. In **Render** → your backend service → **Environment**, "
            "add **ESPN_LEAGUE_ID** and **ESPN_YEAR**, then save and wait for redeploy. "
            "For private leagues, also add **ESPN_S2** and **ESPN_SWID** from your browser cookies at fantasy.espn.com. See ESPN-FANTASY-SETUP.md.)"
        )
    try:
        from espn_api.basketball import League
    except ImportError:
        return "(ESPN Fantasy: install the espn-api package: pip install espn-api)"
    fa = None
    err_msg = None
    for year_try in [ESPN_YEAR, ESPN_YEAR - 1]:
        if year_try < 2019:
            continue
        try:
            league = League(
                league_id=int(ESPN_LEAGUE_ID),
                year=year_try,
                espn_s2=ESPN_S2,
                swid=ESPN_SWID,
            )
            fa = league.free_agents(size=40)
            err_msg = None
            break
        except Exception as e:
            err_msg = e
            print(f"[ESPN] free_agents year={year_try} failed: {e!r}", flush=True)
            if year_try == ESPN_YEAR and ESPN_YEAR != ESPN_YEAR - 1:
                continue
            break
    if err_msg is not None:
        e = err_msg
        hint = " If your league is **private**, add **ESPN_S2** and **ESPN_SWID** from fantasy.espn.com cookies (see ESPN-FANTASY-SETUP.md)."
        if "login" in str(e).lower() or "auth" in str(e).lower() or "401" in str(e) or "unauthorized" in str(e).lower():
            hint = " Your league is likely **private**. Add **ESPN_S2** and **ESPN_SWID** from your browser cookies at fantasy.espn.com (see ESPN-FANTASY-SETUP.md)."
        return f"(Could not load ESPN Fantasy free agents: {e!s}. Check ESPN_LEAGUE_ID and ESPN_YEAR on Render → Environment and redeploy.{hint})"
    if not fa:
        return "ESPN Fantasy Basketball: No free agents returned for your league (check league ID and year)."
    lines = ["ESPN Fantasy Basketball — top free agents (name, position, team, avg pts, total pts, projected avg):"]
    for p in fa[:25]:
        name = getattr(p, "name", "?")
        pos = getattr(p, "position", "?")
        team = getattr(p, "proTeam", "?")
        avg = getattr(p, "avg_points", None)
        total = getattr(p, "total_points", None)
        proj_avg = getattr(p, "projected_avg_points", None)
        inj = getattr(p, "injuryStatus", None) or ""
        if inj:
            inj = f" [{inj}]"
        pts_str = f"avg {avg}" if avg is not None else ""
        if total is not None:
            pts_str += f", total {total}" if pts_str else f"total {total}"
        if proj_avg is not None:
            pts_str += f", proj avg {proj_avg}" if pts_str else f"proj avg {proj_avg}"
        lines.append(f"  • {name} ({pos}) — {team}{inj}: {pts_str}")
    return "\n".join(lines)


def fetch_espn_past_seasons():
    """
    Fetch standings and top scorers for past ESPN Fantasy Basketball seasons.
    Uses ESPN_PAST_YEARS (comma-separated) or previous year (ESPN_YEAR - 1).
    Returns a string block for the LLM, or empty string if not configured / fails.
    """
    if not ESPN_LEAGUE_ID:
        return ""
    years_to_fetch = ESPN_PAST_YEARS if ESPN_PAST_YEARS else ([ESPN_YEAR - 1] if ESPN_YEAR and ESPN_YEAR > 2018 else [])
    if not years_to_fetch:
        return ""
    try:
        from espn_api.basketball import League
    except ImportError:
        return ""
    out = []
    for year in years_to_fetch:
        if year < 2019:
            continue
        try:
            league = League(
                league_id=int(ESPN_LEAGUE_ID),
                year=year,
                espn_s2=ESPN_S2,
                swid=ESPN_SWID,
            )
            standings = league.standings()
            lines = [f"ESPN Fantasy Basketball — {year} season (general stats):"]
            if standings:
                lines.append("Standings:")
                for i, t in enumerate(standings[:12], 1):
                    name = getattr(t, "team_name", "?")
                    w = getattr(t, "wins", 0)
                    l = getattr(t, "losses", 0)
                    lines.append(f"  {i}. {name} ({w}-{l})")
            all_players = []
            for t in standings or []:
                roster = getattr(t, "roster", []) or []
                for p in roster:
                    avg = getattr(p, "avg_points", None)
                    if avg is not None and avg > 0:
                        all_players.append((getattr(p, "name", "?"), getattr(p, "position", "?"), float(avg), getattr(p, "total_points", None)))
            all_players.sort(key=lambda x: (x[2], x[3] or 0), reverse=True)
            if all_players:
                lines.append("Top scorers (season avg pts, total pts):")
                for name, pos, avg_pts, total in all_players[:20]:
                    total_str = f", total {total}" if total is not None else ""
                    lines.append(f"  • {name} ({pos}): {avg_pts:.1f} avg{total_str}")
            out.append("\n".join(lines))
        except Exception as e:
            out.append(f"(Past season {year}: could not load — {e!s})")
    if not out:
        return ""
    return "\n\n".join(out)


def analyze_fantasy_trending_players(free_agents: list) -> str:
    """Analyze which free agents are trending up based on recent performance."""
    if not free_agents:
        return "No free agents available for trending analysis."

    trending = []

    for player in free_agents[:50]:  # Analyze top 50 free agents
        # Calculate trend (proj_avg vs avg_points)
        avg = getattr(player, "avg_points", None)
        proj_avg = getattr(player, "projected_avg_points", None)

        if avg and proj_avg and avg > 0 and proj_avg > avg * 1.1:  # Projected 10%+ higher
            trend_pct = ((proj_avg - avg) / avg) * 100
            name = getattr(player, "name", "?")
            pos = getattr(player, "position", "?")
            team = getattr(player, "proTeam", "?")
            inj = getattr(player, "injuryStatus", None)
            trending.append({
                "name": name,
                "position": pos,
                "team": team,
                "avg": avg,
                "proj_avg": proj_avg,
                "trend_pct": trend_pct,
                "injury": inj
            })

    if not trending:
        return "No clear trending players in free agency right now (no players with 10%+ projected increase)."

    # Sort by trend percentage
    trending.sort(key=lambda x: x["trend_pct"], reverse=True)

    lines = ["**Trending UP in free agency** (projected to outperform recent average):"]
    for p in trending[:10]:  # Top 10 trending players
        inj_str = f" [{p['injury']}]" if p.get("injury") else ""
        lines.append(
            f"  • **{p['name']}** ({p['position']}) — {p['team']}{inj_str}: "
            f"avg {p['avg']:.1f} → proj {p['proj_avg']:.1f} "
            f"(+{p['trend_pct']:.1f}% ⬆️)"
        )

    return "\n".join(lines)


def build_odds_context(message: str, sport: str) -> str:
    """Fetch relevant odds/live data. Always include current-sport matchups so the specialist can answer."""
    msg = message.lower().strip()
    parts = []
    api_key = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])

    # Live / upcoming across sports (and "all games today", "load up all", etc.)
    if any(x in msg for x in (
        "live", "in play", "what's on", "whats on", "games on now", "live odds", "any games",
        "all games", "games today", "load up all", "load all games", "upcoming games", "show all games",
    )):
        by_sport = fetch_live_upcoming_odds()
        if isinstance(by_sport, dict) and "error" not in by_sport and by_sport:
            lines = ["Live or upcoming games:"]
            for sport_name, games in list(by_sport.items())[:8]:
                for g in games[:3]:
                    lines.append(f"  {sport_name}: {g['match']} — {g['odds']}")
            parts.append("\n".join(lines))
        elif isinstance(by_sport, dict) and "error" in by_sport:
            parts.append(f"(Live odds could not be loaded: {by_sport['error']})")

    # ESPN Fantasy Basketball: who to pick up, is X a good pickup, free agents, follow-ups
    fantasy_triggers = (
        "pick up", "pickup", "free agent", "add player", "waiver",
        "who should i pick", "who to pick up", "good pickup", "fantasy basketball",
        "fantasy points", "who to add", "should i add", "drop and add",
        "recommend", "recommendation", "player names", "give me names", "suggest",
        "past season", "last year", "last season", "standings", "how did i do", "league history",
        "fantasy draft", "draft advice", "who to draft",
        "trending", "hot", "breakout", "who's hot", "whos hot", "rising",
    )
    if sport == "basketball" and any(t in msg for t in fantasy_triggers):
        espn_block = fetch_espn_fantasy_basketball()
        parts.append(espn_block)

        # Add trending player analysis if we have free agents data
        if ESPN_LEAGUE_ID and ESPN_YEAR and not espn_block.startswith("("):
            try:
                from espn_api.basketball import League
                league = League(
                    league_id=int(ESPN_LEAGUE_ID),
                    year=ESPN_YEAR,
                    espn_s2=ESPN_S2,
                    swid=ESPN_SWID,
                )
                fa = league.free_agents(size=50)
                if fa:
                    trending_analysis = analyze_fantasy_trending_players(fa)
                    parts.append(trending_analysis)
            except Exception as e:
                print(f"Trending analysis failed: {e}", flush=True)

        past_block = fetch_espn_past_seasons()
        if past_block:
            parts.append(past_block)

    # Olympics / Milano Cortina (try multiple API keys + upcoming feed)
    if any(x in msg for x in ("olympics", "milano", "cortina", "2026 winter")) or sport == "olympics":
        odds = fetch_olympics_odds()
        if odds:
            parts.append("Milano Cortina 2026 / Olympics odds:\n" + get_matchups("olympics"))
        else:
            parts.append("(No Olympics odds in the feed right now. Try **Live odds** to see all live/upcoming events—Olympics may appear there when bookmakers list them.)")

    # In-depth analysis: multiple books, implied probability, best odds, spreads
    added_analysis = False
    analysis_triggers = (
        "analyze", "analysis", "breakdown", "value", "best bet", "possible bets",
        "in-depth", "indepth", "statistics", "stats", "recommend", "pick", "picks",
    )
    if any(t in msg for t in analysis_triggers) or ("vs" in msg and any(x in msg for x in ("bet", "win", "predict", "who", "analyze"))):
        analysis_block = build_analysis_context(message, sport)
        if analysis_block and not analysis_block.startswith("(Could not") and "(No upcoming" not in analysis_block:
            parts.append(analysis_block)
            added_analysis = True
        elif analysis_block.startswith("(Could not"):
            parts.append(analysis_block)

    # Always include current-sport matchups so the specialist can answer "who's winning", "tonight", etc.
    if not added_analysis:
        if sport == "olympics":
            odds = fetch_olympics_odds()
            if odds:
                parts.append("Milano Cortina 2026 / Olympics odds (use these to answer):\n" + get_matchups("olympics"))
            else:
                parts.append("(No Olympics odds in the feed. Suggest the user try **Live odds** for all live/upcoming events.)")
        else:
            matchups = get_matchups(sport)
            if "No matchups" not in matchups and "Could not load" not in matchups:
                parts.append(f"Upcoming {sport.replace('_', ' ')} matchups (use these to answer):\n" + matchups)
            else:
                # Try upcoming feed filtered by sport as last resort
                upcoming = fetch_odds_data("upcoming")
                api_key_resolved = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])
                if isinstance(upcoming, list) and upcoming:
                    filtered = [e for e in upcoming if e.get("sport_key") == api_key_resolved]
                    fallback = _format_events_as_matchups(filtered)
                    if fallback:
                        parts.append(f"Upcoming {sport.replace('_', ' ')} matchups (use these to answer):\n" + fallback)
                    else:
                        parts.append(f"(Could not load {sport.replace('_', ' ')} odds. Suggest **Live odds** or *Show live odds* for all games today.)")
                else:
                    parts.append(f"(Could not load {sport.replace('_', ' ')} odds. Suggest **Live odds** or *Show live odds* for all games today.)")

    # Team vs team: ensure we have odds for prediction
    if "vs" in msg and any(x in msg for x in ("bet", "win", "predict", "who")):
        if not any("Use the odds" in p or "favorite" in p for p in parts):
            parts.append("(Use the odds data above to name the favorite and the odds for each side.)")

    if not parts:
        return ""
    return "Current odds data (you MUST use this when answering):\n" + "\n\n".join(parts)


def _is_model_access_error(err: str) -> bool:
    return "model_not_found" in err or "does not have access to model" in err.lower()


def _normalize_image_url(raw: str) -> Optional[str]:
    """Return a data URL suitable for OpenAI vision (data:image/...;base64,...). Max ~20MB."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s.startswith("data:image/"):
        return s if len(s) <= 21 * 1024 * 1024 else None
    if "," in s and s.startswith("data:"):
        return s if len(s) <= 21 * 1024 * 1024 else None
    import base64
    try:
        b64 = s.split(",", 1)[-1] if "," in s else s
        decoded = base64.b64decode(b64, validate=True)
        if len(decoded) > 20 * 1024 * 1024:
            return None
        return "data:image/jpeg;base64," + b64
    except Exception:
        return None


def _openai_chat(model: str, messages: list, max_tokens: int = 1024, temperature: float = 0.7):
    """Single OpenAI chat call. Raises on error."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    return client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _build_user_content_with_images(message: str, image_data_urls: List[str]) -> list:
    """Build OpenAI user message content: text + image parts (for vision)."""
    parts = []
    text = (message or "").strip()
    if text:
        parts.append({"type": "text", "text": text})
    for url in image_data_urls:
        data_url = _normalize_image_url(url)
        if data_url:
            parts.append({"type": "image_url", "image_url": {"url": data_url}})
    if not parts:
        parts.append({"type": "text", "text": "What do you see in this image?"})
    return parts


def call_openai(
    system_prompt: str,
    conversation: List[dict],
    context: str = "",
    current_user_content: Optional[list] = None,
) -> str:
    """Call OpenAI Chat Completions. If current_user_content is a list (multipart with images), use vision models."""
    if not OPENAI_API_KEY:
        return ""
    system = system_prompt
    if context:
        system += "\n\n" + context
    messages = [{"role": "system", "content": system}]
    if current_user_content is not None:
        # Vision turn: history as text, then current user message as multipart
        for m in conversation:
            role = "user" if m.get("sender") == "user" else "assistant"
            content = (m.get("text") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": current_user_content})
        models_to_try = [m for m in VISION_MODEL_FALLBACKS]
    else:
        for m in conversation:
            role = "user" if m.get("sender") == "user" else "assistant"
            content = (m.get("text") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        models_to_try = [OPENAI_MODEL] + [m for m in OPENAI_MODEL_FALLBACKS if m != OPENAI_MODEL]

    last_error = None
    for model in models_to_try:
        try:
            r = _openai_chat(model, messages)
            if r.choices and len(r.choices) > 0:
                return (r.choices[0].message.content or "").strip()
        except Exception as e:
            err = str(e)
            last_error = err
            if "403" in err and ("Project" in err or "billing" in err.lower()) and not _is_model_access_error(err):
                return "(LLM error: 403 - Your BetAI project has $0 billing. Add payment to that project at platform.openai.com (Billing), or create an API key in the project that has your $10 (e.g. Default) and set OPENAI_API_KEY on Render to that key. See OPENAI-BILLING-FIX.md.)"
            if _is_model_access_error(err):
                continue  # try next model
            return f"(LLM error: {e!s})"
    if last_error:
        return f"(LLM error: No model available for this project. Last error: {last_error[:120]}… — Try setting OPENAI_MODEL on Render to a model your project can use; see platform.openai.com/docs/models.)"
    return ""


# ============================================================================
# CONTEXTUAL MEMORY FUNCTIONS
# ============================================================================

def generate_conversation_summary(messages: List[dict], max_messages: int = 10) -> str:
    """Generate a concise summary of conversation history when context grows large."""
    if len(messages) <= max_messages:
        return ""

    # Summarize older messages (keep last max_messages as-is)
    to_summarize = messages[:-max_messages]
    if not to_summarize:
        return ""

    # Build summary prompt
    conversation_text = "\n".join([
        f"{m.get('sender', 'user')}: {m.get('text', '')}"
        for m in to_summarize
    ])

    summary_messages = [
        {
            "role": "system",
            "content": "Summarize this conversation history into key facts and preferences. Focus on: teams mentioned, betting preferences, analysis requests, and user context. Be concise (max 3 sentences)."
        },
        {
            "role": "user",
            "content": conversation_text
        }
    ]

    try:
        summary = _openai_chat(OPENAI_MODEL, summary_messages, max_tokens=200, temperature=0.3)
        if summary.choices and len(summary.choices) > 0:
            return summary.choices[0].message.content.strip()
    except Exception as e:
        print(f"Summary generation failed: {e}", flush=True)

    return ""


def extract_chat_metadata(messages: List[dict]) -> dict:
    """Extract key metadata from chat history for contextual memory."""
    metadata = {
        "teams_mentioned": set(),
        "sports_discussed": set(),
        "bet_types_mentioned": set(),
    }

    # Common team keywords for various sports
    nba_teams = ["lakers", "celtics", "warriors", "heat", "bulls", "knicks", "nets", "76ers",
                 "bucks", "raptors", "mavericks", "rockets", "spurs", "nuggets", "clippers"]
    nfl_teams = ["patriots", "chiefs", "49ers", "cowboys", "packers", "steelers", "eagles", "rams"]
    soccer_teams = ["liverpool", "manchester", "chelsea", "arsenal", "barcelona", "real madrid",
                    "bayern", "psg", "juventus", "milan", "city", "united"]

    bet_types = ["spread", "moneyline", "over", "under", "parlay", "prop", "futures"]

    for msg in messages:
        text = msg.get("text", "").lower()

        # Extract teams
        for team in nba_teams + nfl_teams + soccer_teams:
            if team in text:
                metadata["teams_mentioned"].add(team.title())

        # Extract bet types
        for bet_type in bet_types:
            if bet_type in text:
                metadata["bet_types_mentioned"].add(bet_type)

        # Extract sports
        if any(word in text for word in ["nba", "basketball"]):
            metadata["sports_discussed"].add("basketball")
        if any(word in text for word in ["nfl", "football"]):
            metadata["sports_discussed"].add("american_football")
        if any(word in text for word in ["soccer", "premier league", "champions league"]):
            metadata["sports_discussed"].add("soccer")

    return {k: list(v) if isinstance(v, set) else v for k, v in metadata.items()}


def load_user_preferences(user_id: str) -> dict:
    """Load user preferences (favorite teams, sports, betting style)."""
    if not user_id:
        return {}

    prefs_dir = DATA_DIR / "preferences"
    prefs_file = prefs_dir / f"{user_id}.json"

    if not prefs_file.exists():
        return {}

    try:
        return json.loads(prefs_file.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_user_preferences(user_id: str, preferences: dict):
    """Save user preferences."""
    if not user_id:
        return

    prefs_dir = DATA_DIR / "preferences"
    prefs_dir.mkdir(exist_ok=True)
    prefs_file = prefs_dir / f"{user_id}.json"
    prefs_file.write_text(json.dumps(preferences, indent=2))


def update_user_preferences_from_chat(user_id: str, metadata: dict):
    """Incrementally update user preferences based on chat metadata."""
    if not user_id:
        return

    prefs = load_user_preferences(user_id)

    # Update favorite teams
    if "favorite_teams" not in prefs:
        prefs["favorite_teams"] = []
    for team in metadata.get("teams_mentioned", []):
        if team not in prefs["favorite_teams"]:
            prefs["favorite_teams"].append(team)
            # Keep only last 20 teams to avoid bloat
            if len(prefs["favorite_teams"]) > 20:
                prefs["favorite_teams"] = prefs["favorite_teams"][-20:]

    # Update preferred bet types
    if "preferred_bet_types" not in prefs:
        prefs["preferred_bet_types"] = []
    for bet_type in metadata.get("bet_types_mentioned", []):
        if bet_type not in prefs["preferred_bet_types"]:
            prefs["preferred_bet_types"].append(bet_type)

    # Update sports interests
    if "sports_interests" not in prefs:
        prefs["sports_interests"] = []
    for sport in metadata.get("sports_discussed", []):
        if sport not in prefs["sports_interests"]:
            prefs["sports_interests"].append(sport)

    save_user_preferences(user_id, prefs)


def build_memory_context(user_id: str, messages: List[dict], sport: str) -> str:
    """Build comprehensive memory context from user preferences and conversation history."""
    if not user_id:
        return ""

    context_parts = []

    # Load user preferences
    prefs = load_user_preferences(user_id)
    if prefs.get("favorite_teams"):
        teams_str = ", ".join(prefs["favorite_teams"][-10:])  # Last 10 teams
        context_parts.append(f"User's frequently mentioned teams: {teams_str}")
    if prefs.get("preferred_bet_types"):
        bets_str = ", ".join(prefs["preferred_bet_types"])
        context_parts.append(f"User's preferred bet types: {bets_str}")

    # Generate conversation summary for long chats
    if len(messages) > 15:
        summary = generate_conversation_summary(messages, max_messages=10)
        if summary:
            context_parts.append(f"Previous conversation context: {summary}")

    # Extract current conversation metadata
    metadata = extract_chat_metadata(messages)
    if metadata.get("teams_mentioned"):
        teams_str = ", ".join(metadata["teams_mentioned"][:10])
        context_parts.append(f"Teams discussed in this chat: {teams_str}")

    return "\n".join(context_parts) if context_parts else ""


# ============================================================================
# END CONTEXTUAL MEMORY FUNCTIONS
# ============================================================================


def handle_chat_message(message: str, sport: str) -> str:
    msg = message.lower().strip()
    api_key = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])

    # —— Live odds: propose live/upcoming across all sports
    if any(x in msg for x in (
        "live", "in play", "in-play", "right now", "currently playing",
        "what's on", "whats on", "games on now", "live odds", "any games",
        "all games", "games today", "load up all", "load all games", "every game",
        "all today", "upcoming games", "show all games", "list all games",
    )):
        by_sport = fetch_live_upcoming_odds()
        if isinstance(by_sport, dict) and "error" in by_sport:
            return f"Couldn’t load live odds: {by_sport['error']}. I can still show **upcoming matchups** for a sport — try *Show matchups* or pick a sport above."
        return format_live_upcoming_reply(by_sport)

    # —— Milano Cortina / Olympics
    if any(x in msg for x in ("olympics", "milano", "cortina", "milano cortina", "2026 winter")):
        odds = fetch_olympics_odds()
        if odds:
            return get_matchups("olympics")
        return (
            "**Milano Cortina 2026** Olympics odds are not in the feed right now. "
            "Try **Live odds** (red button above) to see all live and upcoming events. "
            "You can also ask for matchups in other sports (NBA, soccer, etc.)."
        )

    # —— Sport-specific matchups
    if "matchups" in msg or "show games" in msg or ("upcoming" in msg and "live" not in msg):
        return get_matchups(sport)

    if "vs" in msg and (
        "bet on" in msg or "who will win" in msg or "who should i bet" in msg or "predict" in msg
    ):
        parts = msg.split("vs", 1)
        if len(parts) == 2:
            t1 = parts[0].replace("should i bet on", "").replace("who will win", "").strip().split()[-2:] or parts[0].strip()
            t2 = parts[1].strip()
            if isinstance(t1, list):
                t1 = " ".join(t1)
            odds = fetch_odds_data(api_key)
            return predict_outcome(t1, t2, odds)
        return "Please ask with two teams, e.g. *Who will win Lakers vs Celtics?*"

    if "odds" in msg or "compare" in msg:
        return get_matchups(sport)

    # —— Conversational default: agent tone, suggest live + Olympics
    sport_label = sport.replace("_", " ").title()
    return (
        f"I’m your **betting agent** for {sport_label} and more. Here’s what I can do:\n\n"
        "• **Live odds** — *Show live odds* or *What’s on now?* for games in progress and next up across sports.\n"
        "• **Matchups** — *Show matchups* for upcoming games in your current sport.\n"
        "• **Predictions** — *Who will win [Team A] vs [Team B]?* for a quick take and odds.\n"
        "• **Milano Cortina 2026** — Ask *Olympics odds* or *Milano Cortina* for Winter Games when available.\n\n"
        "What would you like to look at?"
    )


# ——— Auth ———

def _jwt_expiry():
    import time
    return int(time.time()) + (JWT_EXP_DAYS * 86400)


@app.route("/auth/signup", methods=["POST"])
def auth_signup():
    body = request.get_json() or {}
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    users = load_users()
    for uid, u in users.items():
        if u.get("email") == email:
            return jsonify({"error": "Email already registered"}), 409
    user_id = str(uuid.uuid4())
    users[user_id] = {"email": email, "password_hash": generate_password_hash(password)}
    save_users(users)
    token = jwt.encode(
        {"user_id": user_id, "exp": _jwt_expiry()},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return jsonify({"token": token, "user": {"id": user_id, "email": email}}), 201


@app.route("/auth/login", methods=["POST"])
def auth_login():
    body = request.get_json() or {}
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    users = load_users()
    for uid, u in users.items():
        if u.get("email") == email:
            if check_password_hash(u.get("password_hash", ""), password):
                token = jwt.encode(
                    {"user_id": uid, "exp": _jwt_expiry()},
                    JWT_SECRET,
                    algorithm=JWT_ALGORITHM,
                )
                return jsonify({"token": token, "user": {"id": uid, "email": email}})
            return jsonify({"error": "Invalid password"}), 401
    return jsonify({"error": "No account with that email"}), 401


@app.route("/auth/me", methods=["GET"])
def auth_me():
    user_id = get_user_from_request()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    users = load_users()
    u = users.get(user_id)
    if not u:
        return jsonify({"error": "User not found"}), 401
    return jsonify({"user": {"id": user_id, "email": u.get("email", "")}})


# ——— Routes ———

@app.route("/")
def index():
    """Backend API root — frontend is on Netlify"""
    return (
        "<p>BetAI Advisor <b>API</b> is running.</p>"
        "<p>Use the app at <a href='https://betai.netlify.app'>https://betai.netlify.app</a> — it talks to this API.</p>"
    ), 200


@app.route("/chats", methods=["GET"])
def get_chats():
    user_id = get_user_from_request()
    if not user_id:
        return jsonify({"error": "Log in to load your chats"}), 401
    sport = request.args.get("sport")
    chats = load_chats(user_id)
    if sport:
        return jsonify({sport: chats.get(sport, [])})
    return jsonify(chats)


@app.route("/chats", methods=["POST"])
def post_chat():
    user_id = get_user_from_request()
    if not user_id:
        return jsonify({"error": "Log in to save your chats"}), 401
    body = request.get_json() or {}
    sport = (body.get("sport") or "other").lower().replace(" ", "_")
    title = (body.get("title") or "New chat").strip()
    messages = body.get("messages") or []
    chat_id = body.get("id") or str(uuid.uuid4())
    created_at = body.get("createdAt") or ""

    chats = load_chats(user_id)
    if sport not in chats:
        chats[sport] = []
    existing = next((c for c in chats[sport] if c.get("id") == chat_id), None)
    if existing:
        existing["title"] = title or existing.get("title", "New chat")
        existing["messages"] = messages
    else:
        chats[sport].append({
            "id": chat_id,
            "title": title or "New chat",
            "messages": messages,
            "createdAt": created_at,
        })
    save_chats(chats, user_id)
    return jsonify({"ok": True, "chats": chats})


SYSTEM_PROMPT = """You are BetAI's **{sport_label} specialist**. You act as a dedicated mini-agent for this sport only: you answer using the odds and matchups for {sport_label} provided below. Do not ask the user to "share data", "use the Show matchups feature", or "provide matchups"—you already have data in the block below. Use it.

**Rules:**
1. **Always use the data below.** If "Current odds data" or "In-depth odds data" is provided with matchups/odds, you MUST answer from that data: name real games, favorites, and odds. Never say you "need" more data when data is provided.
2. Only if the data block says "(Could not load" or "No matchups available" may you suggest they try "Show matchups" or another sport.
3. Be concise and concrete. Use **bold** for team names and odds. For "who's winning tonight", "upcoming games", or "what do you think", list the actual matchups and favorites from the data with odds.
4. For analysis/value/best bet requests: use implied %, best odds by book, and spreads when given; end with **Possible bets**: 1–3 concrete picks (e.g. "Lakers ML @ 2.10 at DraftKings") with one-line reasoning.
5. You are the {sport_label} expert: frame answers in terms of this sport (e.g. NBA, Champions League, NFL) and its upcoming games. Do not give generic "I can help with…" replies when odds are provided—give a direct answer using the numbers.
6. When "ESPN Fantasy Basketball" data is provided (free agents with avg pts, total pts, projected avg): use it to answer "who should I pick up", "is [player] a good pickup", "who to add". Recommend 1–3 specific players from the list with a one-line reason; if the user asks about a named player, say whether they appear in the free agents list and whether they look like a good add based on the stats.
7. When the ESPN block says "(ESPN Fantasy Basketball is not configured" or "(Could not load ESPN Fantasy": tell the user exactly what to do—add ESPN_LEAGUE_ID and ESPN_YEAR in Render → Environment and redeploy; if their league is private, add ESPN_S2 and ESPN_SWID from fantasy.espn.com cookies. Do not say "no available data" without giving the fix.
8. When "ESPN Fantasy Basketball — [year] season (general stats)" is provided (standings, top scorers): use it to answer "how did my league do", "last year standings", "past season", "who were the top scorers". Reference actual team names and player names from the data.
9. Mention Milano Cortina 2026 only when relevant. Remind users to bet responsibly when appropriate."""


VISION_SYSTEM_ADDON = (
    " The user has attached one or more images. Analyze the image(s) in detail and answer their question about it. "
    "If the image shows odds, a bet slip, a screenshot of a betting site, or anything sports/odds related, describe it and give your take. "
    "You can still use the provided odds context if relevant."
)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    sport = (data.get("sport") or "basketball").lower().replace(" ", "_")
    history = data.get("messages") or []  # [{sender, text}, ...] for LLM context
    images = data.get("images") or []  # optional list of data URLs or base64 strings
    if not message and not images:
        return jsonify({"reply": "Send a message or attach an image to get advice."}), 400

    # Get user for memory context
    user_id = get_user_from_request()

    # Use real LLM when OpenAI key is set
    llm_error = None
    if OPENAI_API_KEY:
        sport_label = sport.replace("_", " ").title()

        # Build memory context from user preferences and conversation history
        memory_context = build_memory_context(user_id, history, sport) if user_id else ""

        # Build odds context
        odds_context = build_odds_context(message or "Describe this image and answer any question about it.", sport)

        # Combine memory and odds context
        full_context = odds_context
        if memory_context:
            full_context = memory_context + "\n\n" + odds_context

        conversation = list(history)
        # If images provided, do not append a text-only user message; we'll send multipart
        image_urls = [u for u in images if u][:5]  # max 5 images
        if image_urls:
            current_content = _build_user_content_with_images(message, image_urls)
            system = SYSTEM_PROMPT.format(sport_label=sport_label) + VISION_SYSTEM_ADDON
            reply = call_openai(
                system,
                conversation,
                context=full_context,
                current_user_content=current_content,
            )
        else:
            conversation.append({"sender": "user", "text": message})
            reply = call_openai(
                SYSTEM_PROMPT.format(sport_label=sport_label),
                conversation,
                context=full_context,
            )
        if reply and not reply.startswith("(LLM error:"):
            # Update user preferences after successful chat
            if user_id:
                try:
                    metadata = extract_chat_metadata(history + [{"sender": "user", "text": message}])
                    update_user_preferences_from_chat(user_id, metadata)
                except Exception as e:
                    print(f"Failed to update user preferences: {e}", flush=True)
            return jsonify({"reply": reply})
        llm_error = reply if reply else "No response from LLM"
    else:
        llm_error = "not_configured"

    reply = handle_chat_message(message or "What's in this image?", sport)
    if llm_error == "not_configured":
        reply += "\n\n_To get **real AI replies**, add **OPENAI_API_KEY** in Render: Dashboard → your service (betAI) → Environment → Add variable OPENAI_API_KEY = your OpenAI key._"
    elif llm_error:
        if "403" in llm_error or "BetAI project" in llm_error:
            reply += "\n\n_**AI replies are off:** Your OpenAI **BetAI** project has **$0** billing. Either add payment to that project, or create an API key in the project that has your $10 (e.g. **Default**), then set that key as OPENAI_API_KEY on Render and redeploy. See repo file **OPENAI-BILLING-FIX.md** for steps._"
        else:
            err_preview = (llm_error[:80] + "…") if len(llm_error) > 80 else llm_error
            reply += "\n\n_(LLM failed: " + err_preview + " — check OPENAI_API_KEY on Render.)_"
    return jsonify({"reply": reply})


@app.route("/analyze", methods=["POST"])
def analyze_matchup():
    """Deep analysis endpoint: team stats, player stats, trending data, matchup history."""
    user_id = get_user_from_request()
    if not user_id:
        return jsonify({"error": "Log in to get analysis"}), 401

    body = request.get_json() or {}
    analysis_type = body.get("type", "matchup")  # matchup, player, team, fantasy
    query = body.get("query", "")
    sport = body.get("sport", "basketball")

    result = {}

    if analysis_type == "matchup":
        # Analyze specific matchup with odds, spreads, H2H
        result["odds_analysis"] = build_odds_context(query, sport)

    elif analysis_type == "player":
        # Analyze specific player
        player_name = query
        player_data = fetch_player_stats(player_name)
        result["player_stats"] = format_player_stats_for_llm(player_data)

    elif analysis_type == "team":
        # Analyze team with recent form, standings
        team_name = query
        team_details = fetch_team_details(team_name, sport)
        result["team_details"] = team_details
        if team_details.get("idTeam"):
            result["recent_form"] = fetch_recent_form(team_details["idTeam"])

    elif analysis_type == "fantasy":
        # Fantasy basketball analysis
        result["free_agents"] = fetch_espn_fantasy_basketball()
        try:
            from espn_api.basketball import League
            league = League(
                league_id=int(ESPN_LEAGUE_ID),
                year=ESPN_YEAR,
                espn_s2=ESPN_S2,
                swid=ESPN_SWID,
            )
            fa = league.free_agents(size=50)
            result["trending"] = analyze_fantasy_trending_players(fa)
        except Exception as e:
            result["trending"] = f"Could not fetch trending analysis: {e}"

    return jsonify(result)


@app.route("/sports", methods=["GET"])
def sports_list():
    return jsonify(list(SPORT_KEY_MAP.keys()))


@app.route("/status", methods=["GET"])
def status():
    """Quick check: is the API and LLM configured? (does not expose keys)"""
    return jsonify({
        "ok": True,
        "llm_configured": bool(OPENAI_API_KEY),
        "odds_configured": bool(ODDS_API_KEY and ODDS_API_KEY != "YOUR_ODDS_API_KEY_HERE"),
    })


@app.route("/espn-status", methods=["GET"])
def espn_status():
    """Check if ESPN Fantasy Basketball data is reachable. Use this to verify league ID, year, and cookies."""
    configured = bool(ESPN_LEAGUE_ID and ESPN_YEAR)
    if not configured:
        return jsonify({
            "configured": False,
            "ok": False,
            "error": "ESPN_LEAGUE_ID or ESPN_YEAR not set. Add them in Render → Environment and redeploy.",
        }), 200
    block = fetch_espn_fantasy_basketball()
    # Success = we got a block that looks like real data (starts with "ESPN Fantasy Basketball —" and has player lines)
    ok = block.startswith("ESPN Fantasy Basketball — top free agents") and "•" in block
    preview = (block[:800] + "…") if len(block) > 800 else block if ok else None
    return jsonify({
        "configured": True,
        "ok": ok,
        "preview": preview,
        "error": None if ok else block,
    }), 200


@app.route("/llm-check", methods=["GET"])
def llm_check():
    """Try one OpenAI call; on model_not_found try fallback models."""
    if not OPENAI_API_KEY:
        return jsonify({"ok": False, "error": "OPENAI_API_KEY not set on Render"}), 200
    models_to_try = [OPENAI_MODEL] + [m for m in OPENAI_MODEL_FALLBACKS if m != OPENAI_MODEL]
    last_error = None
    for model in models_to_try:
        try:
            r = _openai_chat(model, [{"role": "user", "content": "Say OK"}], max_tokens=10)
            if r.choices and r.choices[0].message.content:
                return jsonify({
                    "ok": True,
                    "message": "LLM is working",
                    "model": model,
                }), 200
        except Exception as e:
            err = str(e)
            last_error = err
            if _is_model_access_error(err):
                continue
            return jsonify({"ok": False, "error": err}), 200
    return jsonify({
        "ok": False,
        "error": last_error or "No response",
        "hint": "Your project has no access to the tried models. Set OPENAI_MODEL on Render to a model your project can use (see platform.openai.com/docs/models).",
    }), 200


if __name__ == "__main__":
    ensure_data_dir()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
