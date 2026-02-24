# Connect APIs on Render (LLM + Odds)

The backend on Render **cannot** use your encrypted key file — it only reads **Environment Variables**. Do this once so the agent uses ChatGPT and can fetch live odds.

---

## Steps on Render

1. **Open your service**  
   Go to [dashboard.render.com](https://dashboard.render.com) → **betAI** (your web service).

2. **Open Environment**  
   In the left sidebar, click **Environment**.

3. **Add the two keys**

   | Key | Value | What it does |
   |-----|--------|----------------|
   | **OPENAI_API_KEY** | Your OpenAI key (starts with `sk-...`) | Connects the agent to ChatGPT so it talks with the user using the LLM. |
   | **ODDS_API_KEY** | Your Odds API key from [the-odds-api.com](https://the-odds-api.com) | Lets the agent fetch live odds and matchups; the LLM uses this data to answer. |

   - Click **Add Environment Variable**.
   - For each row: type the **Key** exactly as above, paste the **Value**, then save.
   - Get OpenAI key: [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
   - Get Odds API key (free tier): [the-odds-api.com](https://the-odds-api.com).

   **Optional:** The app defaults to `gpt-5.2`. If your project uses different models (e.g. only GPT-4o or GPT-3.5), set **OPENAI_MODEL** on Render to a model you have access to (e.g. `gpt-4o`, `gpt-3.5-turbo`).

   **REQUIRED for production:** Set **JWT_SECRET** to a long random string (32+ characters) so login tokens are secure and cannot be forged. Generate one with:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   ⚠️ **Security Warning**: If JWT_SECRET is not set, the app falls back to an insecure default that attackers can use to forge authentication tokens. This is ONLY acceptable for local testing.

4. **Redeploy**  
   After saving, Render will redeploy. Wait for the deploy to finish (1–2 min).

5. **Check**  
   Open **https://betai-u72d.onrender.com/status** in your browser. You should see:
   - `"llm_configured": true`
   - `"odds_configured": true`

   If the app still shows "LLM failed" (403), open **https://betai-u72d.onrender.com/llm-check**. That page will show the exact error from OpenAI (no key is shown). Use it to confirm the key is loaded and which project/billing message OpenAI returns.

6. **If 403 persists (e.g. "Project … billing")**  
   Billing is **per project**. If your **BetAI** project shows **$0** monthly spend, the key from that project will always 403. See **OPENAI-BILLING-FIX.md** in this repo: either add billing to BetAI, or create the API key in the project that has your $10 (e.g. **Default**) and set that key on Render, then **Clear build cache & deploy**.

---

## How it works

- **User** types in the app at **betai.netlify.app**.
- **Frontend** sends the message to your **Render backend**.
- **Backend** uses **OPENAI_API_KEY** to call **ChatGPT** and **ODDS_API_KEY** to fetch live odds when needed.
- The **LLM** gets the odds as context and answers in natural language.
- The reply is sent back to the user.

Your encrypted key on your computer is only for **local** runs. On Render you **must** set **OPENAI_API_KEY** (and **ODDS_API_KEY** for odds) in Environment — that’s how the agent is connected to the LLM and the APIs.
