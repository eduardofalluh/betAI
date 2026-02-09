# Deploy BetAI Advisor to the cloud

Deploy the **backend** to Render (free tier) and the **frontend** to Vercel (free tier). Then you open one URL and everything works — no local backend.

---

## 1. Deploy backend (Render)

1. Go to **[render.com](https://render.com)** and sign in (or create an account).
2. **New → Web Service**.
3. Connect your GitHub repo **eduardofalluh/betAI**.
4. Set:
   - **Root Directory:** `betai-advisor/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 1 -b 0.0.0.0:$PORT server:app`
   - **Instance Type:** Free
5. **Environment** (in the dashboard):
   - `OPENAI_API_KEY` = your OpenAI API key (required for LLM)
   - `ODDS_API_KEY` = your Odds API key (optional, for live odds)
6. Click **Create Web Service**. Wait for the first deploy to finish.
7. Copy your service URL, e.g. **`https://betai-advisor-api.onrender.com`** (no trailing slash).

---

## 2. Deploy frontend (Vercel)

1. Go to **[vercel.com](https://vercel.com)** and sign in with GitHub.
2. **Add New → Project**, import **eduardofalluh/betAI**.
3. Set:
   - **Root Directory:** `betai-advisor` (or leave default and set it to the folder that has `package.json` for the frontend)
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. **Environment Variables** (add before deploying):
   - **Name:** `VITE_API_URL`  
   - **Value:** your Render backend URL, e.g. `https://betai-advisor-api.onrender.com`  
   - (No trailing slash.)
5. If the repo root is the whole project, set **Root Directory** to **`betai-advisor`** so Vercel uses the frontend folder.
6. Click **Deploy**. When it’s done, you get a URL like **`https://betai-advisor-xxx.vercel.app`**.

---

## 3. Use the app

Open the **Vercel URL** in your browser. The app will call the **Render backend** automatically. No local backend or port 5000 needed.

---

## Optional: Netlify instead of Vercel

- **Build command:** `npm run build`
- **Publish directory:** `dist`
- **Environment variable:** `VITE_API_URL` = your Render backend URL (e.g. `https://betai-advisor-api.onrender.com`)

Set **Base directory** to `betai-advisor` if the repo root is the whole repo.
