# Set up the Odds API (live odds & matchups)

Follow these steps to get an Odds API key and add it so your BetAI agent can show live odds and matchups.

---

## 1. Get your Odds API key

1. Go to **https://the-odds-api.com**
2. Click **"Get API Key"** or **"Sign up"** (they have a **free tier** with a limited number of requests per month).
3. Sign up with your email (or log in if you already have an account).
4. After signup you’ll see your **API key** (a long string). Copy it and keep it somewhere safe.

---

## 2. Add the key on Render

1. Open **https://dashboard.render.com**
2. Click your **betAI** web service.
3. In the left sidebar, click **Environment**.
4. Click **"Add Environment Variable"**.
5. Set:
   - **Key:** `ODDS_API_KEY`
   - **Value:** paste the API key you copied from The Odds API
6. Click **Save**.

Render will redeploy automatically. Wait 1–2 minutes for the deploy to finish.

---

## 3. Check that it’s working

1. Open **https://betai-u72d.onrender.com/status** in your browser.
2. You should see `"odds_configured": true`.
3. In your app at **https://betai.netlify.app**, try **"Show live odds"** or **"What’s on now?"** — you should get real odds instead of an error.

---

## Free tier limits (The Odds API)

- Free tier gives a limited number of requests per month (see their site for current limits).
- If you hit the limit, you’ll get errors until the next month or until you upgrade.
- For light use (a few live odds / matchups per day), the free tier is usually enough.

That’s it. Once **ODDS_API_KEY** is set on Render, the agent can fetch live odds and the LLM can use that data in its answers.
