"""
BetAI Advisor API — Chat by sport category + odds & predictions.
Uses OpenAI for real LLM conversation when OPENAI_API_KEY is set; falls back to rule-based replies otherwise.
"""
import json
import os
import uuid
from pathlib import Path
from typing import List

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip() or "gpt-3.5-turbo"
# Try these in order when the project doesn't have access to the default model
OPENAI_MODEL_FALLBACKS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHATS_FILE = DATA_DIR / "chats.json"

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "YOUR_ODDS_API_KEY_HERE")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
SPORTS_API_URL = "https://api.the-odds-api.com/v4/sports/"

# Frontend sport key -> Odds API key (multiple keys tried for Olympics)
SPORT_KEY_MAP = {
    "basketball": "basketball_nba",
    "soccer": "soccer_uefa_champs_league",
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
    if not CHATS_FILE.exists():
        CHATS_FILE.write_text("{}")


def load_chats():
    ensure_data_dir()
    try:
        return json.loads(CHATS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_chats(chats):
    ensure_data_dir()
    CHATS_FILE.write_text(json.dumps(chats, indent=2))


def fetch_odds_data(sport_key="basketball_nba", live_only=False):
    """Fetch odds for a sport. Use sport_key='upcoming' for live + next 8 across all sports."""
    url = ODDS_API_URL.format(sport_key=sport_key)
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        return {"error": str(e)}
    return {"error": f"API Error: {r.status_code}"}


def fetch_live_upcoming_odds():
    """
    Fetch live and upcoming games across all sports (Odds API sport_key='upcoming').
    Returns games grouped by sport for conversational display.
    """
    data = fetch_odds_data("upcoming")
    if isinstance(data, dict) and "error" in data:
        return data
    by_sport = {}
    for event in data or []:
        sk = event.get("sport_key", "other")
        title = SPORT_TITLES.get(sk, sk.replace("_", " ").title())
        if title not in by_sport:
            by_sport[title] = []
        home = event.get("home_team", "?")
        away = event.get("away_team", "?")
        commence = event.get("commence_time", "")[:16].replace("T", " ")
        for b in event.get("bookmakers", [])[:1]:
            for m in b.get("markets", []):
                if m.get("key") != "h2h":
                    continue
                odds_str = ", ".join(f"{o['name']}: {o['price']}" for o in m.get("outcomes", []))
                by_sport[title].append({
                    "match": f"{home} vs {away}",
                    "odds": odds_str,
                    "commence": commence,
                })
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
    lines = ["Here’s what’s **live or coming up** across sports:\n"]
    for sport_name, games in by_sport.items():
        lines.append(f"**{sport_name}**")
        for g in games[:5]:
            lines.append(f"• {g['match']} — {g['odds']}")
        if len(games) > 5:
            lines.append(f"  _…and {len(games) - 5} more_")
        lines.append("")
    lines.append("_Want odds for one sport only? Pick it from the selector or ask e.g. *Show NBA matchups*. "
                 "You can also ask for **Milano Cortina 2026** Olympics._")
    return "\n".join(lines).strip()


def get_matchups(sport_key=None):
    api_key = SPORT_KEY_MAP.get(sport_key, "basketball_nba") if sport_key else None
    if not api_key and sport_key:
        api_key = sport_key
    odds = fetch_odds_data(api_key or "basketball_nba")
    if isinstance(odds, dict) and "error" in odds:
        return f"Could not load odds: {odds['error']}"
    lines = []
    for game in odds or []:
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
    return "\n".join(lines) if lines else "No matchups available for this sport right now."


def build_odds_context(message: str, sport: str) -> str:
    """Fetch relevant odds/live data based on user message and current sport. Returns a string for LLM context."""
    msg = message.lower().strip()
    parts = []

    # Live / upcoming across sports
    if any(x in msg for x in ("live", "in play", "what's on", "whats on", "games on now", "live odds", "any games")):
        by_sport = fetch_live_upcoming_odds()
        if isinstance(by_sport, dict) and "error" not in by_sport and by_sport:
            lines = ["Live or upcoming games:"]
            for sport_name, games in list(by_sport.items())[:8]:
                for g in games[:3]:
                    lines.append(f"  {sport_name}: {g['match']} — {g['odds']}")
            parts.append("\n".join(lines))
        elif isinstance(by_sport, dict) and "error" in by_sport:
            parts.append(f"(Live odds could not be loaded: {by_sport['error']})")

    # Olympics / Milano Cortina
    if any(x in msg for x in ("olympics", "milano", "cortina", "2026 winter")):
        odds = fetch_odds_data(SPORT_KEY_MAP.get("olympics", "olympics_winter_2026"))
        if isinstance(odds, dict) and "error" not in odds and odds:
            parts.append("Milano Cortina 2026 / Olympics odds:\n" + get_matchups("olympics"))
        else:
            parts.append("(Milano Cortina 2026 odds are not in the feed yet.)")

    # Sport-specific matchups
    if any(x in msg for x in ("matchups", "match ups", "show games", "upcoming", "odds", "compare")) or not parts:
        api_key = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])
        odds = fetch_odds_data(api_key)
        if isinstance(odds, dict) and "error" not in odds and odds:
            parts.append(f"Upcoming {sport.replace('_', ' ')} matchups:\n" + get_matchups(sport))

    # Team vs team: try to get prediction data
    if "vs" in msg and any(x in msg for x in ("bet", "win", "predict", "who")):
        api_key = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])
        odds = fetch_odds_data(api_key)
        if isinstance(odds, dict) and "error" not in odds:
            parts.append("(Use the odds data above to say who is the favorite and at what odds.)")

    if not parts:
        return ""
    return "Current odds data (use this when answering):\n" + "\n\n".join(parts)


def _is_model_access_error(err: str) -> bool:
    return "model_not_found" in err or "does not have access to model" in err.lower()


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


def call_openai(system_prompt: str, conversation: List[dict], context: str = "") -> str:
    """Call OpenAI Chat Completions. Tries OPENAI_MODEL then fallbacks if project has no access."""
    if not OPENAI_API_KEY:
        return ""
    system = system_prompt
    if context:
        system += "\n\n" + context
    messages = [{"role": "system", "content": system}]
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


def handle_chat_message(message: str, sport: str) -> str:
    msg = message.lower().strip()
    api_key = SPORT_KEY_MAP.get(sport, SPORT_KEY_MAP["basketball"])

    # —— Live odds: propose live/upcoming across all sports
    if any(x in msg for x in ("live", "in play", "in-play", "right now", "currently playing",
                               "what's on", "whats on", "games on now", "live odds", "any games")):
        by_sport = fetch_live_upcoming_odds()
        if isinstance(by_sport, dict) and "error" in by_sport:
            return f"Couldn’t load live odds: {by_sport['error']}. I can still show **upcoming matchups** for a sport — try *Show matchups* or pick a sport above."
        return format_live_upcoming_reply(by_sport)

    # —— Milano Cortina / Olympics
    if any(x in msg for x in ("olympics", "milano", "cortina", "milano cortina", "2026 winter")):
        olympics_key = SPORT_KEY_MAP.get("olympics", "olympics_winter_2026")
        odds = fetch_odds_data(olympics_key)
        if isinstance(odds, dict) and "error" in odds:
            return (
                "**Milano Cortina 2026** Winter Olympics odds aren’t in the feed yet (or the API key doesn’t have access). "
                "As the Games get closer (Feb 6–22, 2026), bookmakers will list outrights and event odds — I’ll show them here when available. "
                "Meanwhile, ask for **live odds** or matchups for NBA, NFL, soccer, etc."
            )
        if odds:
            return get_matchups("olympics")
        return "No Milano Cortina 2026 odds available right now. Try *Live odds* or matchups for other sports."

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
    sport = request.args.get("sport")
    chats = load_chats()
    if sport:
        return jsonify({sport: chats.get(sport, [])})
    return jsonify(chats)


@app.route("/chats", methods=["POST"])
def post_chat():
    body = request.get_json() or {}
    sport = (body.get("sport") or "other").lower().replace(" ", "_")
    title = (body.get("title") or "New chat").strip()
    messages = body.get("messages") or []
    chat_id = body.get("id") or str(uuid.uuid4())
    created_at = body.get("createdAt") or ""

    chats = load_chats()
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
    save_chats(chats)
    return jsonify({"ok": True, "chats": chats})


SYSTEM_PROMPT = """You are BetAI, a friendly and knowledgeable betting advisor. You help users with sports betting: live odds, matchups, predictions, and responsible gambling tips.

Current sport context: {sport_label} (user can change sport in the app).

Guidelines:
- Use any "Current odds data" provided below when answering; cite real odds and matchups when you have them.
- Be concise but helpful. You can use light markdown (e.g. **bold** for team names or odds).
- If the user asks for live odds, matchups, or a prediction and data is provided, summarize it clearly.
- For "who will win" or "should I bet on" questions, name the favorite and the odds when you have the data.
- Mention Milano Cortina 2026 Olympics when relevant; if no Olympics data is provided, say it may not be in the feed yet.
- Gently remind users to bet responsibly when appropriate.
- If you don't have specific data, suggest they try "Show live odds" or "Show matchups" for their sport."""


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    sport = (data.get("sport") or "basketball").lower().replace(" ", "_")
    history = data.get("messages") or []  # [{sender, text}, ...] for LLM context
    if not message:
        return jsonify({"reply": "Send a message to get advice."}), 400

    # Use real LLM when OpenAI key is set
    llm_error = None
    if OPENAI_API_KEY:
        sport_label = sport.replace("_", " ").title()
        context = build_odds_context(message, sport)
        conversation = list(history)
        conversation.append({"sender": "user", "text": message})
        reply = call_openai(
            SYSTEM_PROMPT.format(sport_label=sport_label),
            conversation,
            context=context,
        )
        if reply and not reply.startswith("(LLM error:"):
            return jsonify({"reply": reply})
        llm_error = reply if reply else "No response from LLM"
    else:
        llm_error = "not_configured"

    reply = handle_chat_message(message, sport)
    if llm_error == "not_configured":
        reply += "\n\n_To get **real AI replies**, add **OPENAI_API_KEY** in Render: Dashboard → your service (betAI) → Environment → Add variable OPENAI_API_KEY = your OpenAI key._"
    elif llm_error:
        if "403" in llm_error or "BetAI project" in llm_error:
            reply += "\n\n_**AI replies are off:** Your OpenAI **BetAI** project has **$0** billing. Either add payment to that project, or create an API key in the project that has your $10 (e.g. **Default**), then set that key as OPENAI_API_KEY on Render and redeploy. See repo file **OPENAI-BILLING-FIX.md** for steps._"
        else:
            err_preview = (llm_error[:80] + "…") if len(llm_error) > 80 else llm_error
            reply += "\n\n_(LLM failed: " + err_preview + " — check OPENAI_API_KEY on Render.)_"
    return jsonify({"reply": reply})


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
