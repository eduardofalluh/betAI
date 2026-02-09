# BetAI Advisor

AI betting advisor with **chats documented per sport** (Basketball, Soccer, American Football, Baseball, Hockey, Tennis, MMA, Other). Sleek web UI with animations and sport-categorized history.

## Structure

- **`betai-advisor/`** — App (Vite + React frontend, Flask backend)

**Deploy to the cloud (no local backend):** see **[betai-advisor/DEPLOY.md](betai-advisor/DEPLOY.md)** — backend on Render, frontend on Vercel.

## BetAI Advisor – Quick start

### 1. Backend (Python)

```bash
cd betai-advisor/backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Runs at **http://localhost:5000**. Chats are stored in `backend/data/chats.json` by sport.

### 2. Frontend (Node)

```bash
cd betai-advisor
npm install
npm run dev
```

Runs at **http://localhost:3000** and proxies `/api` to the backend.

### 3. APIs (recommended)

Copy `betai-advisor/backend/.env.example` to `betai-advisor/backend/.env` and set:

- **OPENAI_API_KEY** — For real AI replies (conversational LLM). Get a key at [OpenAI](https://platform.openai.com/api-keys). Without it, the app uses rule-based replies.
- **ODDS_API_KEY** — For live odds, matchups, and predictions. Get a key at [The Odds API](https://the-odds-api.com/).

## Features

- **Real LLM agent** — Uses OpenAI (e.g. gpt-4o-mini) when `OPENAI_API_KEY` is set; understands natural language and uses live odds/matchups as context. Without the key, falls back to rule-based replies.
- **Conversational betting agent** — Chat naturally: live odds, matchups, predictions, Olympics.
- **Live odds** — "Show live odds" or **Live odds** chip: games in progress and next upcoming across all sports.
- **Milano Cortina 2026** — Sport option and prompts for Winter Olympics odds (when available from the API).
- **Sport categories** — Chats organized by sport, including Milano Cortina 2026.
- **Sidebar** — Browse and open past chats per sport; start new chat per category
- **Save chat** — Persist current conversation to the backend (documented per sport)
- **Quick prompts** — "Show live odds", "What's on now?", "Milano Cortina 2026 odds".
- **Sport selector** — Change sport in the header; agent uses it for matchups and predictions.
- **Responsive layout** — Works on desktop and mobile

## Tech

- **Frontend:** React 18, Vite, Framer Motion
- **Backend:** Flask, CORS, JSON file storage, OpenAI API (optional)
- **Fonts:** Outfit (UI), JetBrains Mono (messages)
