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
| **ML categorisation** | Char n-gram TF-IDF + logistic-regression classifier (`awaaz/nlp.py`) upgrades items the lexicon can't place; trained on lexicon templates + your own corrected rows via `train_model.py` |
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

## 🎧 Audio pipeline (`awaaz/audio.py`, `awaaz/stt_local.py`, `awaaz/eval.py`)

Local CPU-only DSP front-end: `preprocess()` decodes to 16 kHz mono, `highpass()` removes rumble, `denoise()` does spectral-subtraction noise reduction, `voice_activity()` segments speech, `mfcc_delta()`/`logmel_spectrogram()`/`pitch_f0()` extract acoustic features, and `diarize()` wraps pyannote when `HF_TOKEN` is set. `stt_local.py` adds optional faster-whisper transcription + language ID; `eval.py` has SNR-benchmark, WER (jiwer) and DER (pyannote.metrics) helpers plus per-stage latency timing. `api.py` exposes the whole thing as a FastAPI service (`uvicorn api:app`).

## 🎧 Audio preprocessing (`awaaz/audio.py`)

Local CPU-only DSP front-end that sits before STT: `preprocess()` decodes any voice note to 16 kHz mono, `denoise()` does spectral-subtraction noise reduction, `voice_activity()` segments speech for endpointing, `mfcc()` extracts cepstral features, and `diarize()` wraps pyannote when `HF_TOKEN` is set. No downloads, no GPU — degrades gracefully without optional deps.

## 📊 Evaluation (`eval/`)

```bash
python eval/make_clips.py --out eval/clips --n 10   # synthetic speech-like clips at 0/5/10/20 dB SNR
python -c "from awaaz.eval import snr_benchmark; from pathlib import Path;   import collections; rows=snr_benchmark(sorted(map(str,Path('eval/clips').glob('*_snr*.wav'))));   agg=collections.defaultdict(list); [agg[r['target_snr_db']].append(r['delta_db']) for r in rows];   [print(k, round(sum(v)/len(v),1),'dB') for k,v in sorted(agg.items())]"
```

Measured on the synthetic clip set (harmonic speech-like bursts + white noise):

| Target SNR | Mean SNR gain after denoise |
|---|---|
| 0 dB | **+9.9 dB** |
| 5 dB | **+11.2 dB** |
| 10 dB | **+11.7 dB** |
| 20 dB | **+12.1 dB** |

These are DSP-level numbers on synthetic signals — they prove the denoiser lowers the noise floor, not WER. For real WER/DER numbers, record ~20 clips per language and run `awaaz.eval.word_error_rate` / `diarization_error_rate` (jiwer / pyannote.metrics) — see `docs/MODEL_CARD.md`-style honesty note: cite only what you measured.

## 🧠 ML layer (category classifier)

`awaaz/nlp.py` ships a trainable semantic classifier that sits *behind* the rule parser: when the lexicon cannot place an item (`Other`), the model — char n-gram TF-IDF + logistic regression, which handles code-mixed Telugu/Tamil/Hinglish without language-specific tokenisation — suggests a category if its confidence clears the threshold. No model file → identical behaviour to before.

```bash
python train_model.py          # lexicon templates + user-corrected rows in data/awaaz.db
```

Training blends two label sources: generated sentences from the category lexicon, and **your own edits** in the History tab (the highest-quality labels). Held-out accuracy on the lexicon set is ~95%; retrain any time the app accumulates corrections. Export a Spark-ready JSONL dataset with:

```python
from awaaz.pipeline import export_training_jsonl
export_training_jsonl()   # -> data/training_data.jsonl  {"text","label","source","ts"}
```

See `docs/MODEL_CARD.md` for model details and limits.

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
awaaz/nlp.py        ML category classifier (TF-IDF + logistic regression)
awaaz/pipeline.py   labelled-data export (JSONL, Spark-ready)
awaaz/audio.py      denoise, VAD, MFCC/mel/pitch features, SNR eval utils
awaaz/stt_local.py  optional faster-whisper ASR + language ID
awaaz/eval.py       WER/DER/SNR metrics + latency timer
api.py              optional FastAPI voice-expense service
train_model.py      classifier training entry point
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
