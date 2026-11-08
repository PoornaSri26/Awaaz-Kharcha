# 🎙️ Awaaz Kharcha (आवाज़ खर्चा / ఆవాజ్ ఖర్చు)

### Voice-first multilingual expense tracker for Indian students and daily commuters

[![Gnani Prisma](https://img.shields.io/badge/Powered%20By-Gnani%20Prisma%20STT-FF6B00.svg)](https://gnani.ai)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)

> **"Just say what you spent, in your own language. Awaaz Kharcha writes it down, sorts it into categories, and shows where your money went."**

---

## 🎯 Who it is for

College students and daily commuters who split canteen chai, samosas, Rapido bikes, autos and hostel bills — in Hinglish, Telugu or Indian English.

- **The problem (Razorpay Fix My Itch #90.5):** people stop tracking expenses because typing every ₹20 chai or ₹60 auto ride is tedious.
- **The answer:** speak one sentence — *"aaj chai 20, auto 80, lunch dedh sau, Ravi ko 500 udhar diya"* — and it becomes categorised rows, a monthly burn chart, a khata ledger and a Q&A assistant.

---

## ✨ What's inside

| Area | Feature |
|---|---|
| **Voice** | Gnani Prisma STT with Inverse Text Normalization (numerals stay digits), live editable transcript before saving |
| **Voice notes** | Drop a forwarded WhatsApp `.ogg` / `.m4a` / `.mp3` / `.wav` / `.aac` clip instead of recording |
| **No-mic path** | Type the same natural sentence, or use one-tap chips (Chai ₹20, Auto ₹80, Lunch ₹150, Recharge ₹299…) |
| **Parsing** | Indian number words (`dedh sau`, `dhai hazar`, `paanch sau`, `रెండు వందలు`, `पाँच सौ`), comma / *aur* / *మరియు* lists, quantities ignored (`2 chai 20` → ₹20), relative dates (`aaj`, `kal`, `parso`, `eeroju`) |
| **Categories** | Food, Travel, Groceries, Bills, Health, Shopping, Fun, Education, Other |
| **Khata / Udhar** | Detect *"Ravi ko 500 udhar diya"*, per-person totals of who owes what, one-tap settle / reopen |
| **Budget** | Persisted monthly budget, progress bar, 80% nudge and 90% alert, "safe to spend today" and per-day allowance for the remaining days |
| **Insights** | 14-day trend, spending by category, top items, weekday pattern, month-over-month change, logging streak, one-line weekly insight |
| **Ask** | Voice or typed questions — *"is mahine kitna kharch hua?"*, *"chai pe kitna gaya?"*, *"budget kitna bacha?"*, *"ravi ko kitna udhar?"* — answered offline from local data |
| **History** | Filter by month, category or item; edit any row inline; delete selected rows |
| **Data** | SQLite storage with per-row ids, CSV + full JSON export, guarded "clear all" |

Three UI languages: **Hinglish**, **తెలుగు**, **English (IN)** — switchable in one tap.

---

## 🏗️ How it works

```text
  🎤 voice  ──┐
              ├──> Gnani Prisma STT (api.vachana.ai/stt/v3)
  📎 voice ───┘        │  transcript (digits preserved)
                       v
              Editable transcript review  ──┐
                                            │
  ⌨️ typed sentence ────────────────────────┤
                                            v
                               awaaz/parser.py
                     number words → digits, split, categorise,
                     relative dates, expense vs udhar rows
                                            │
                                            v
                       awaaz/store.py  (SQLite: expenses, udhar, settings)
                                            │
                    ┌───────────────────────┼────────────────────────┐
                    v                       v                        v
            awaaz/insights.py        Streamlit UI              CSV / JSON export
        totals, budget, trends,   hero card, tabs, charts,
        weekly insight, Q&A       khata ledger, history
```

Everything except speech-to-text runs locally. Nothing is uploaded except the audio clip you choose to transcribe.

---

## 🚀 Quick start

```bash
git clone https://github.com/PoornaSri26/Awaaz-Kharcha.git
cd Awaaz-Kharcha

python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Gnani Prisma key (only needed for voice input)
cp .env.example .env      # then edit .env and set GNANI_API_KEY=...

streamlit run app.py
```

Open **http://localhost:8501**. Without an API key the app still runs: typing, one-tap chips, khata, insights and Q&A all work; the voice tab explains what is missing.

Optional demo data:

```bash
python seed_data.py           # seeds only if the database is empty
python seed_data.py --force   # seed on top of existing rows
```

Optional key check:

```bash
python test_stt.py path/to/clip.wav   # or no argument for a silent test clip
```

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The suite covers the parser (number words, multi-item sentences, quantities, relative dates, Telugu/English, udhar direction), the SQLite store (CRUD, settlement, settings, export, one-time legacy CSV import) and insights/Q&A (totals, budget levels, zero-filled trends, every question intent, and empty-data safety).

---

## 📁 Project structure

```text
app.py               Streamlit UI (six tabs, sidebar settings/export)
awaaz/config.py      env, paths, language codes, thresholds
awaaz/parser.py      number words, categorisation, expense + udhar parsing
awaaz/store.py       SQLite persistence, settings, exports, v1 CSV migration
awaaz/insights.py    totals, budget status, trends, weekly insight, Q&A engine
awaaz/stt.py         Gnani Prisma client with typed errors
tests/               pytest suite
seed_data.py         demo data (relative dates, no absolute paths)
test_stt.py          API connectivity smoke check
```

Upgrading from v1? Your old `expenses.csv` and `udhar_khata.csv` are imported into SQLite on first run and renamed `*.csv.imported`, so nothing is lost and nothing is double-counted.

---

## 💡 Voice scripts to try

| Language | Spoken input | Parsed result |
|---|---|---|
| **Hinglish** | `aaj canteen chai 20, auto ka 80, lunch biryani 160, recharge 299` | 4 expenses: Food, Travel, Food, Bills |
| **Hinglish + khata** | `Ravi ko 500 udhar diya, kal metro 40` | 1 khata entry, 1 backdated travel expense |
| **Telugu** | `eeroju tiffin dosa 60, rapido bike 75, medicines 180` | 3 expenses: Food, Travel, Health |
| **English (IN)** | `metro ticket 40, coffee 60, stationary 120, groceries 350` | 4 expenses incl. Education, Groceries |
| **Question** | `is mahine kitna kharch hua?` / `budget kitna bacha?` | spoken answer from your own data |

---

## 🔒 Privacy & limits

- Audio is sent **only** to Gnani Prisma for transcription, and only when you record or upload.
- Expenses, khata and settings live in `data/awaaz.db` on your machine; `.env`, the database and audio files are git-ignored.
- **The API key never leaves `.env`.** `.env.example` documents variable *names* only, the app never renders the key, and API errors are surfaced without request headers. Keep keys in `.env` (or `st.secrets` when deployed), never in code, screenshots, issues or chat — if a key is ever pasted somewhere shared, rotate it in the Gnani console immediately.
- Single-user, single-device by design: there is no login or cloud sync yet.
- Parsing is rule based. It handles the phrasing in the scripts above very well; unusual constructions (*"do chai aur ek samosa, total pachas"*) may need an edit in the transcript box — which is exactly why the transcript is editable before saving.
- Amounts are rounded to rupees; mixed-currency input is not supported.

---

## 🗺️ Roadmap

- [ ] Weekly/monthly PDF or image share card for WhatsApp
- [ ] Recurring expenses (rent, recharge) auto-posted
- [ ] Optional cloud sync with a user account
- [ ] Per-category budgets
- [ ] More languages (Tamil, Bengali, Marathi) once validated with native speakers

---

## 🏷️ Built for

**Great Indian AI Internship Challenge** (Nov 8–10, 2026), inspired by Razorpay's *Fix My Itch* #90.5: *"Why do people struggle to track where their money goes each month?"*

Speech recognition by **[Gnani.ai Prisma](https://gnani.ai)**. Built with Streamlit, pandas and SQLite.
