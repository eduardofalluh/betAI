# ESPN Fantasy Basketball — Who to pick up

BetAI can use your **ESPN Fantasy Basketball** league so users can ask things like:
- *Who should I pick up?*
- *Is [player name] a good pickup?*
- *Best free agents right now?*

The app uses the **espn-api** Python package and your league’s **free agents** list (with fantasy points and projections) so the AI can recommend pickups and comment on specific players.

---

## 1. Get your League ID and year

1. Go to **https://fantasy.espn.com/basketball** and open your league.
2. The URL looks like:  
   `https://fantasy.espn.com/basketball/team?leagueId=**469892829**&seasonId=**2026**`
3. **League ID** = `leagueId` (e.g. `469892829`).  
   **Year** = `seasonId` (e.g. `2026`).

---

## 2. Set env vars (Render or local)

**If you use the app at betai.netlify.app**, the backend runs on **Render**. You must add these variables there or the AI will say it doesn’t have access to player data.

1. Open **Render** → your **BetAI Web Service** (backend) → **Environment**.
2. Add **ESPN_LEAGUE_ID** and **ESPN_YEAR** (values below). Save — Render will redeploy.
3. Wait 1–2 minutes, then try again in the app (Basketball → *Who should I pick up?*).

Add to your backend environment (e.g. Render → Service → Environment):

| Variable        | Example  | Required |
|----------------|----------|----------|
| **ESPN_LEAGUE_ID** | `469892829` | Yes      |
| **ESPN_YEAR**      | `2026`     | Yes      |
| **ESPN_PAST_YEARS** | `2024,2023` | Optional (standings + top scorers; default: previous year) |
| **ESPN_S2**        | *(long string)* | Only for **private** leagues |
| **ESPN_SWID**      | `{...}`  | Only for **private** leagues |

- **Public leagues:** `ESPN_LEAGUE_ID` + `ESPN_YEAR` are enough.
- **Private leagues:** you must also set **ESPN_S2** and **ESPN_SWID** from your browser cookies (see below).
- **Past seasons (optional):** set **ESPN_PAST_YEARS** to a comma-separated list (e.g. `2024,2023`) to include standings and top scorers from those years. If unset, the previous year (`ESPN_YEAR - 1`) is used. The AI can then answer “how did my league do last year?”, “past season standings”, “who were the top scorers?”.

---

## 3. Private leagues: get ESPN_S2 and SWID

1. Log in at **https://fantasy.espn.com**.
2. Open DevTools (F12 or right‑click → Inspect).
3. Go to **Application** (Chrome) or **Storage** (Firefox) → **Cookies** → `https://fantasy.espn.com`.
4. Find and copy:
   - **ESPN_S2** — long string (often 200+ characters).
   - **SWID** — usually like `{12345678-1234-1234-1234-123456789012}`.

Set them as **ESPN_S2** and **ESPN_SWID** in your backend env. They expire; if “Could not load ESPN Fantasy” appears, refresh the cookies and update the env vars.

---

## 4. Deploy and test

After saving env vars and redeploying, in the app (with **Basketball** selected) try:
- *Who should I pick up?*
- *Is Tyrese Haliburton a good pickup?*
- *How did my league do last year?* / *Past season standings* (uses ESPN past-season data if configured)

If ESPN isn’t configured, the AI will say to set **ESPN_LEAGUE_ID** and **ESPN_YEAR** (and cookies for private leagues).
