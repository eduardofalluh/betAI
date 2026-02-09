# Fix OpenAI 403 — BetAI project has $0 billing

The **403** error happens because **billing is per project**. Your **BetAI** project shows **$0** monthly spend, so the API key from that project cannot call the API even if your account has $10 credit in another project.

You have **two options**. Do one of them.

---

## Option A: Add billing to the BetAI project (keep using your current key)

1. Go to **[platform.openai.com](https://platform.openai.com)**.
2. In the **top-left**, click the project/organization name and switch to **BetAI** (the project where you created the key).
3. Open **Settings** → **Billing** (or go to [platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing)).
4. Add a **payment method** or **purchase credits** for this organization/project so BetAI has a non‑zero balance.
5. Wait a minute, then try the app again. No need to change the key on Render.

---

## Option B: Use a key from the project that already has the $10 (easiest)

1. Go to **[platform.openai.com](https://platform.openai.com)**.
2. In the **top-left**, switch to the **Default** project (or whichever project shows **non‑$0** monthly spend and has your $10 credit).
3. Go to **Settings** → **API keys** (or [platform.openai.com/api-keys](https://platform.openai.com/api-keys)).
4. Click **Create new secret key**. Name it e.g. `BetAI-Render`. Copy the key (starts with `sk-...`).
5. In **Render** → your betAI service → **Environment**, set **OPENAI_API_KEY** to this new key (replace the old one). Save.
6. **Manual Deploy** → **Clear build cache & deploy**.
7. When deploy finishes, open **https://betai-u72d.onrender.com/llm-check** — you should see `"ok": true`.

---

After either option, the app at **https://betai.netlify.app** should get real AI replies without 403.
