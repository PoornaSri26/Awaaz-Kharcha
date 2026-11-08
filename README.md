# 🎙️ Awaaz Kharcha (आवाज़ खर्चा / ఆవాజ్ ఖర్చు)
### Voice-First Multilingual Expense Tracker for Indian College Students & Daily Commuters

[![Gnani Prisma](https://img.shields.io/badge/Powered%20By-Gnani%20Prisma%20STT-FF6B00.svg)](https://gnani.ai)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io)
[![Event](https://img.shields.io/badge/Great%20Indian%20AI%20Internship%20Challenge-Nov%208--10%2C%202026-green.svg)](https://gnani.ai)

> **"Just say what you spent, in your own language. Awaaz Kharcha writes it down, sorts it into categories, and shows where your money went."**

---

## 🎯 Target Persona: Narrow Audience Focus
> **"For college students & daily commuters who split canteen chai, samosa, rapido bikes, autos and hostel bills in Hinglish and Telugu."**
- **The Problem (Razorpay Fix My Itch #90.5):** People stop tracking expenses because typing out every ₹20 chai or ₹60 auto ride is tedious.
- **The Solution:** Open the mic, speak naturally (*"aaj chai 20, auto 80, lunch biryani 150"*), let **Gnani Prisma** inverse-text-normalize the numerals, auto-categorize, and graph monthly burn.

---

## 🏗️ Architecture & Data Flow

```text
       🎤 User Voice Input (Hinglish / Telugu / Indian English)
                               |
                               v
            Gnani Prisma STT API (api.vachana.ai/stt/v3)
              Inverse Text Normalization (digits: 0-9)
                               |
                               v
               Live Editable Transcript Review Box
              (Instant error correction before saving)
                               |
                               v
               Multilingual Regex Expense Parser
            (Splits items, amounts, categories & icons)
                               |
                               v
                    expenses.csv (Local Storage)
                               |
                               v
           Visual FinTech Analytics Dashboard & Alerts
          (Today's sum, month's total, category bar chart, 
           budget utilization gauge, and CSV export)
```

---

## 🚀 Quick Setup & Run

### 1. Prerequisites
- Python 3.10+
- Valid Gnani AI API Key (configured in `.env`)

### 2. Installation
```bash
# Clone or navigate to the folder
cd C:\Users\npoor\.gemini\antigravity\scratch\awaaz-kharcha

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application
```bash
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

---

## 💡 Real Voice Demo Scripts to Try

| Language | Spoken Audio Input | Detected Result |
|---|---|---|
| **Hinglish** | `"aaj canteen chai 20, auto ka 80, lunch biryani 160, recharge 299"` | 4 items: Food & Chai, Travel, Food, Bills |
| **Telugu** | `"eeroju tiffin dosa 60, rapido bike 75, medicines 180, evening snacks 45"` | 4 items: Food & Chai, Travel, Health, Food |
| **English (IN)** | `"metro ticket 40, coffee 60, stationary 120, groceries 350"` | 4 items: Travel, Food, Other, Groceries |



---

## 🏷️ Social Sharing Template (LinkedIn & X)

> I kept forgetting where my money went every month, so I built a voice-first expense tracker. 🎙️💸
>
> Just say: *"aaj chai 20, auto 80, lunch 150, recharge 299"* — it transcribes, auto-sorts, and graphs your spending in seconds!
>
> Built in 2 days using **@Gnani.ai's Prisma** speech-to-text model, which handles code-mixed Hinglish and Telugu with remarkable numeral accuracy.
>
> Inspired by Razorpay's Fix My Itch: *"Why do people struggle to track where their money goes each month?"*
>
> 🎯 Narrow focus: For college students and daily commuters splitting chai, canteen, and autos.
>
> Would you use this over traditional expense apps? What language should we support next? 👇
>
> **#GnaniAI #GreatIndianAIInternshipChallenge**

