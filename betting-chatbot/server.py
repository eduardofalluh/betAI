from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import joblib

app = Flask(__name__)
CORS(app)

# Load AI model (optional, placeholder for now)
# model = joblib.load("betting_model.pkl")

@app.route("/", methods=["GET"])
def home():
    return "Betting Chatbot Backend is Running!"

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"].lower()

    if "nba" in user_message:
        response = "Here are today's NBA betting odds! (API integration coming soon)"
    elif "bet" in user_message:
        response = "Our AI suggests betting on Team X! (AI model coming soon)"
    else:
        response = "Ask me about NBA games or betting recommendations!"

    return jsonify({"reply": response})

if __name__ == "__main__":
    app.run(port=5000, debug=True)