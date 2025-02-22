from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import joblib
import numpy as np
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# The Odds API key (replace with your own free key from https://the-odds-api.com/)
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "YOUR_ODDS_API_KEY_HERE")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
SPORTS_API_URL = "https://api.the-odds-api.com/v4/sports/"

# Load or mock betting model
try:
    model = joblib.load("betting_model.pkl")
    print("Model loaded successfully!")
except Exception as e:
    print(f"⚠️ Model not found or error: {e}")
    model = None

# Fetch all sports available in The Odds API
def fetch_all_sports():
    params = {"apiKey": ODDS_API_KEY}
    response = requests.get(SPORTS_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    return {"error": f"API Error: {response.status_code}"}

# Fetch odds data for a specific sport
def fetch_odds_data(sport_key="basketball_nba"):
    url = ODDS_API_URL.format(sport_key=sport_key)
    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h", "oddsFormat": "decimal"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"API Response for {sport_key}: {data}")  # Debug: Print full API response
        return data
    return {"error": f"API Error: {response.status_code}"}

# Predict outcome based on odds or model
def predict_outcome(team1, team2, odds_data):
    team1 = team1.lower().strip()
    team2 = team2.lower().strip()
    print(f"Searching for odds: {team1} vs {team2}")  # Debug

    if "error" in odds_data:
        return f"⚠️ Error fetching odds: {odds_data['error']}"

    found_match = False
    for game in odds_data:
        home_team = game["home_team"].lower().strip()
        away_team = game["away_team"].lower().strip()
        print(f"Checking game: {home_team} vs {away_team}")  # Debug
        # Flexible matching: check if team names are in each other, exact matches, or common abbreviations
        if ((team1 in home_team or home_team == team1 or 
             (team1 == "utah" and "jazz" in home_team) or (team1 == "okc" and "thunder" in home_team)) and 
            (team2 in away_team or away_team == team2 or 
             (team2 == "utah" and "jazz" in away_team) or (team2 == "okc" and "thunder" in away_team))) or \
           ((team2 in home_team or home_team == team2 or 
             (team2 == "utah" and "jazz" in home_team) or (team2 == "okc" and "thunder" in home_team)) and 
            (team1 in away_team or away_team == team1 or 
             (team1 == "utah" and "jazz" in away_team) or (team1 == "okc" and "thunder" in away_team))):
            found_match = True
            home_odds = None
            away_odds = None
            # Extract odds from the first bookmaker with h2h market
            for bookmaker in game["bookmakers"]:
                print(f"Bookmaker: {bookmaker['key']}")  # Debug
                for market in bookmaker["markets"]:
                    if market["key"] == "h2h":
                        print(f"Market: {market}")  # Debug
                        for outcome in market["outcomes"]:
                            outcome_name = outcome["name"].lower().strip()
                            if outcome_name == home_team:
                                home_odds = outcome["price"]
                            elif outcome_name == away_team:
                                away_odds = outcome["price"]
            if home_odds and away_odds:
                print(f"Found odds: {home_team} vs {away_team} - Home: {home_odds}, Away: {away_odds}")  # Debug
                if model:
                    # Example: Use model with dummy stats (replace with real stats if available)
                    features = np.array([[100, 90, 95, 85]])  # [team1_off, team1_def, team2_off, team2_def]
                    prediction = model.predict(features)[0]
                    winner = game["home_team"] if prediction == 1 else game["away_team"]
                else:
                    # Dummy logic: Lower odds = favorite
                    winner = game["home_team"] if home_odds < away_odds else game["away_team"]
                return f"🏆 {winner} is predicted to win. Odds: {game['home_team']}: {home_odds}, {game['away_team']}: {away_odds}"
    if not found_match:
        print(f"No matching games found for {team1} vs {team2}")  # Debug
        return f"⚠️ No odds found for {team1} vs {team2}. Check if these teams have an upcoming game or use exact team names from The Odds API, like 'Utah Jazz' vs 'Oklahoma City Thunder'."

# Get matchups and odds for a specific sport or all sports
def get_matchups(sport_key=None):
    if sport_key:
        # Map user-friendly sport names to API keys
        sport_mapping = {
            "nba": "basketball_nba",
            "soccer": "soccer_uefa_champs_league",  # Default to UEFA Champions League, can expand
            "mls": "soccer_usa_mls",
            "ncaa football": "americanfootball_ncaaf",
            "nfl": "americanfootball_nfl",
            "nhl": "icehockey_nhl",
            "afl": "australianfootball_afl",
            "mlb": "baseball_mlb",
            "ncaa baseball": "baseball_ncaab",
            "boxing": "boxing",
            "mma": "mma_mixed_martial_arts",
            "nrl": "rugby_league_nrl",
            "six nations": "rugby_union_six_nations",
            "tennis": "tennis_atp"
        }
        api_key = sport_mapping.get(sport_key.lower(), sport_key.lower())
        odds_data = fetch_odds_data(api_key)
        if "error" in odds_data:
            return f"Error for {sport_key}: {odds_data['error']}"
        
        matchups = []
        for game in odds_data:
            home_team = game["home_team"]
            away_team = game["away_team"]
            home_odds = None
            away_odds = None
            for bookmaker in game["bookmakers"]:
                for market in bookmaker["markets"]:
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home_team:
                                home_odds = outcome["price"]
                            elif outcome["name"] == away_team:
                                away_odds = outcome["price"]
            if home_odds and away_odds:
                matchups.append(f"{sport_key.upper()}: {home_team} vs {away_team} - Odds: {home_team}: {home_odds}, {away_team}: {away_odds}")
        return "\n".join(matchups) if matchups else f"No matchups available for {sport_key} at this time."
    else:
        # Get all matchups across all sports
        sports = fetch_all_sports()
        if "error" in sports:
            return f"Error fetching sports: {sports['error']}"
        
        all_matchups = []
        for sport in sports:
            sport_key = sport["key"]
            sport_title = sport["title"]
            odds_data = fetch_odds_data(sport_key)
            if "error" in odds_data:
                all_matchups.append(f"Error for {sport_title}: {odds_data['error']}")
                continue
            for game in odds_data:
                home_team = game["home_team"]
                away_team = game["away_team"]
                home_odds = None
                away_odds = None
                for bookmaker in game["bookmakers"]:
                    for market in bookmaker["markets"]:
                        if market["key"] == "h2h":
                            for outcome in market["outcomes"]:
                                if outcome["name"] == home_team:
                                    home_odds = outcome["price"]
                                elif outcome["name"] == away_team:
                                    away_odds = outcome["price"]
                if home_odds and away_odds:
                    all_matchups.append(f"{sport_title}: {home_team} vs {away_team} - Odds: {home_team}: {home_odds}, {away_team}: {away_odds}")
        return "\n".join(all_matchups) if all_matchups else "No matchups available at this time."

# Chatbot route for betting and matchups
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"].lower()

    if "should i bet on" in user_message or "who will win" in user_message or "who should i bet on" in user_message:
        # Extract teams from message (e.g., "Should I bet on Utah Jazz vs Oklahoma City Thunder?" or "Who will win Utah vs OKC?")
        if "vs" in user_message:
            teams = user_message.split("vs")
            if len(teams) == 2:
                team1, team2 = (teams[0].strip().split("on")[-1].strip() if "should i bet on" in user_message else teams[0].strip()), teams[1].strip()
                # Handle abbreviations and full team names
                team_mapping = {
                    "utah": "Utah Jazz",
                    "okc": "Oklahoma City Thunder",
                    "lakers": "Los Angeles Lakers",
                    "celtics": "Boston Celtics",
                    "warriors": "Golden State Warriors",
                    "heat": "Miami Heat",
                    "jazz": "Utah Jazz",
                    "thunder": "Oklahoma City Thunder"
                }
                team1 = team_mapping.get(team1, team1)
                team2 = team_mapping.get(team2, team2)
                odds_data = fetch_odds_data("basketball_nba")  # Default to NBA, can extend to other sports later
                if "error" in odds_data:
                    return jsonify({"reply": f"Error fetching odds: {odds_data['error']}"})
                advice = predict_outcome(team1, team2, odds_data)
                return jsonify({"reply": advice})
            return jsonify({"reply": "Please specify two teams like 'Team A vs Team B'."})
        else:
            # Handle queries like "Who should I bet on?" or "Who will win Utah?"
            teams = user_message.split()
            if len(teams) >= 3 and ("should" in teams or "will" in teams):
                # Extract potential team names (simplified, may need refinement)
                team1 = teams[-2] if teams[-2] in team_mapping else teams[-1]
                team2 = teams[-1] if teams[-2] in team_mapping else None
                if team2:
                    team1 = team_mapping.get(team1, team1)
                    team2 = team_mapping.get(team2, team2)
                    odds_data = fetch_odds_data("basketball_nba")
                    if "error" in odds_data:
                        return jsonify({"reply": f"Error fetching odds: {odds_data['error']}"})
                    advice = predict_outcome(team1, team2, odds_data)
                    return jsonify({"reply": advice})
                return jsonify({"reply": "Please specify two teams like 'Team A vs Team B' or 'Who will win Team A vs Team B'."})
            return jsonify({"reply": "Please specify two teams like 'Team A vs Team B' or 'Who will win Team A vs Team B'."})

    elif "show matchups" in user_message:
        # Extract sport from message (e.g., "Show matchups NBA", "Show matchups Soccer")
        sport = user_message.replace("show matchups", "").strip()
        if sport:
            matchups = get_matchups(sport)
        else:
            matchups = get_matchups()  # Show all matchups if no sport specified
        return jsonify({"reply": matchups})

    else:
        return jsonify({
            "reply": "I’m your betting expert! Ask something like 'Should I bet on Utah Jazz vs Oklahoma City Thunder?' or 'Show matchups NBA' to see NBA matchups and odds."
        })

if __name__ == "__main__":
    app.run(port=5000, debug=True)