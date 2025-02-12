import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib

app = Flask(__name__)
CORS(app)

# 🔑 API KEYS
SPORTS_API_KEY = "b45f2ebd-29bb-4392-92d4-eedda38815cd"
BET_ODDS_API_KEY = "591d7763735e987dc3561843dc50c03b"
SOCCER_API_KEY = "51596ada19624648af56cc929dc110f7"
DEEPSEEK_API_KEY = "sk-fa680cac8d674db9bf01ab0ac7468653"  # DeepSeek AI Key

# 📌 API ENDPOINTS
NBA_API_URL = f"https://api.the-odds-api.com/v4/sports/basketball_nba/scores/?apiKey={SPORTS_API_KEY}"
EPL_API_URL = f"https://api.the-odds-api.com/v4/sports/soccer_epl/scores/?apiKey={SPORTS_API_KEY}"
NFL_API_URL = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores/?apiKey={SPORTS_API_KEY}"
MLB_API_URL = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/scores/?apiKey={SPORTS_API_KEY}"
SOCCER_API_URL = "https://api.football-data.org/v4/matches"
NHL_API_URL = "https://statsapi.web.nhl.com/api/v1/schedule"

# API HEADERS
HEADERS = {"x-api-key": SPORTS_API_KEY}
HEADERS_SOCCER = {"X-Auth-Token": SOCCER_API_KEY}

# 🎰 Load AI Betting Model
try:
    model = joblib.load("betting_model.pkl")
except Exception as e:
    print(f"⚠️ Error loading model: {e}")
    model = None

# 🔥 **Helper function to fetch API data**
def fetch_data(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        print(f"Fetching data from {url} - Status: {response.status_code}")  # Debugging log
        if response.status_code == 200:
            return response.json()
        return f"Failed to fetch data: {response.text}"
    except Exception as e:
        return f"API error: {e}"

# 🏀 **Get NBA Scores**
def get_nba_scores():
    data = fetch_data(NBA_API_URL)
    if isinstance(data, dict) and "data" in data:
        return [{"home": g["home_team"], "away": g["away_team"], "score": g.get("scores", "N/A")} for g in data["data"]]
    return "Failed to fetch NBA data."

# ⚽ **Get EPL Scores**
def get_epl_scores():
    data = fetch_data(EPL_API_URL)
    if isinstance(data, dict) and "data" in data:
        return [{"home": g["home_team"], "away": g["away_team"], "score": g.get("scores", "N/A")} for g in data["data"]]
    return "Failed to fetch EPL data."

# 🌍 **Get Soccer Scores**
def get_soccer_scores():
    data = fetch_data(SOCCER_API_URL, HEADERS_SOCCER)
    if isinstance(data, dict) and "matches" in data:
        return [{"home": m["homeTeam"]["name"], "away": m["awayTeam"]["name"], "status": m["status"]} for m in data["matches"]]
    return "Failed to fetch Soccer data."

# 🏒 **Get NHL Games**
def get_nhl_scores():
    data = fetch_data(NHL_API_URL)
    if isinstance(data, dict) and "dates" in data:
        games = []
        for date in data["dates"]:
            for game in date["games"]:
                games.append({"home": game["teams"]["home"]["team"]["name"], "away": game["teams"]["away"]["team"]["name"], "status": game["status"]["abstractGameState"]})
        return games
    return "Failed to fetch NHL data."

# 🎰 **Betting Prediction**
@app.route("/predict", methods=["POST"])
def predict_bet():
    if model is None:
        return jsonify({"bet_advice": "❌ Betting model not loaded!"})
    
    data = request.json
    features = [[data.get("team_off", 0), data.get("team_def", 0), data.get("opp_off", 0), data.get("opp_def", 0)]]
    prediction = model.predict(features)[0]
    return jsonify({"bet_advice": "🏆 Bet WIN" if prediction == 1 else "❌ Bet LOSE"})

# 📊 **Get Sports Scores API**
@app.route("/scores", methods=["GET"])
def get_scores():
    sport = request.args.get("sport")

    if sport == "nba":
        return jsonify(get_nba_scores())
    elif sport == "epl":
        return jsonify(get_epl_scores())
    elif sport == "soccer":
        return jsonify(get_soccer_scores())
    elif sport == "nhl":
        return jsonify(get_nhl_scores())

    return jsonify({"error": "Sport not supported"})

# 🤖 **Get DeepSeek AI Response**
def get_deepseek_response(user_message):
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": user_message}]}
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"Error: {response.text}"
    except Exception as e:
        return f"Error fetching AI response: {e}"

# 📢 **Chatbot AI Route**
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"].lower()

    if "nba" in user_message:
        response = get_nba_scores()
    elif "epl" in user_message:
        response = get_epl_scores()
    elif "soccer" in user_message:
        response = get_soccer_scores()
    elif "nhl" in user_message:
        response = get_nhl_scores()
    elif "bet" in user_message:
        response = predict_bet()
    else:
        response = get_deepseek_response(user_message)

    return jsonify({"reply": response})

# 🔥 **Run Flask Server**
if __name__ == "__main__":
    app.run(port=5000, debug=True)
