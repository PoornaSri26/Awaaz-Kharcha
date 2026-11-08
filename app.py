import os
import re
import datetime as dt
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables (contains GNANI_API_KEY)
load_dotenv()

API_URL = "https://api.vachana.ai/stt/v3"
API_KEY = os.getenv("GNANI_API_KEY", "")
DATA_FILE = "expenses.csv"

# ---------------- MULTILINGUAL LOCALIZATION & UI STRINGS ----------------
UI = {
    "hi-IN": {
        "title": "आवाज़ खर्चा",
        "subtitle": "जो खर्च किया, बस बोलिए। हम लिख लेंगे।",
        "speak": "बोलिए (Tap & Speak)",
        "heard": "मैंने यह सुना (Edit if needed)",
        "save": "खर्चा सेव करें",
        "today": "आज का खर्च",
        "month": "इस महीने",
        "budget": "महीने का बजट",
        "example": 'जैसे: "आज चाय 20, ऑटो 80, खाना 150, दवाई 200"',
        "privacy": "🔒 आपकी आवाज़ सिर्फ खर्च लिखने के लिए इस्तेमाल होती है।",
        "empty_msg": "अभी कोई खर्च दर्ज नहीं है। ऊपर माइक दबाकर बोलिए।",
        "items_header": "पहचाने गए खर्चे:",
        "success_toast": "खर्च सफलतापूर्वक सेव हो गया! 👍",
        "undo": "↩ पिछला खर्च वापस लें (Undo)",
        "download": "खर्चा डाउनलोड करें (CSV)",
        "clear_all": "🗑️ सब साफ़ करें"
    },
    "te-IN": {
        "title": "ఆవాజ్ ఖర్చు",
        "subtitle": "మీరు ఖర్చు పెట్టింది మాట్లాడండి. మేము రాస్తాము.",
        "speak": "మాట్లాడండి (Tap & Speak)",
        "heard": "నేను విన్నది (సరిచూసుకోండి)",
        "save": "ఖర్చులను సేవ్ చేయండి",
        "today": "ఈ రోజు ఖర్చు",
        "month": "ఈ నెల మొత్తం",
        "budget": "నెల బడ్జెట్",
        "example": 'ఉదా: "ఈరోజు టీ 20, ఆటో 80, భోజనం 150, మందులు 200"',
        "privacy": "🔒 మీ స్వరం ఖర్చులను లెక్కించడానికి మాత్రమే ఉపయోగించబడుతుంది.",
        "empty_msg": "ఇంకా ఏమీ నమోదు కాలేదు. పైన మైక్ నొక్కి మాట్లాడండి.",
        "items_header": "గుర్తించిన ఖర్చులు:",
        "success_toast": "ఖర్చులు విజయవంతంగా సేవ్ అయ్యాయి! 👍",
        "undo": "↩ చివరి రికార్డును రద్దు చేయండి (Undo)",
        "download": "ఖర్చులను డౌన్‌లోడ్ చేయండి (CSV)",
        "clear_all": "🗑️ డేటా క్లియర్ చేయండి"
    },
    "en-IN": {
        "title": "Awaaz Kharcha",
        "subtitle": "Say what you spent. We write it down.",
        "speak": "Tap & Speak",
        "heard": "What I heard (Edit if needed)",
        "save": "Save Expenses",
        "today": "Today's Spent",
        "month": "This Month",
        "budget": "Monthly Budget",
        "example": 'Try: "today tea 20, auto 80, lunch 150, medicine 200"',
        "privacy": "🔒 Your voice is only used on this device to log your expenses.",
        "empty_msg": "Nothing yet. Tap the mic above to log your first expense.",
        "items_header": "Detected Expenses:",
        "success_toast": "Expenses saved successfully! 👍",
        "undo": "↩ Undo Last Save",
        "download": "Download CSV",
        "clear_all": "🗑️ Clear All"
    }
}

LANG_MAP = {
    "Hinglish": "hi-IN",
    "తెలుగు": "te-IN",
    "English": "en-IN"
}

# Rich category dictionary with emojis
CAT_EMOJI = {
    "Food": "🍵",
    "Travel": "🛺",
    "Groceries": "🥬",
    "Bills": "💡",
    "Health": "💊",
    "Shopping": "🛍️",
    "Fun": "🎬",
    "Other": "📦"
}

CATEGORIES = {
    "Food": ["chai", "tea", "coffee", "lunch", "dinner", "breakfast", "tiffin", "biryani",
             "samosa", "snack", "khana", "canteen", "juice", "pani", "water", "food",
             "టీ", "భోజనం", "టిఫిన్", "చాయ్", "అన్నం", "బిర్యానీ", "చाय", "खाना", "नाश्ता"],
    "Travel": ["auto", "bus", "metro", "cab", "ola", "uber", "petrol", "diesel", "fuel",
               "ticket", "train", "bike", "rapido", "ఆటో", "బస్సు", "పెట్రోల్", "రైలు", "ऑटो", "बस", "पेट्रोल"],
    "Groceries": ["sabzi", "vegetables", "milk", "doodh", "rice", "atta", "dal", "oil", "grocery",
                  "kirana", "fruits", "పాలు", "కూరగాయలు", "సరుకులు", "सब्ज़ी", "दूध", "राशन"],
    "Bills": ["recharge", "bill", "electricity", "current", "wifi", "rent", "gas", "cylinder",
              "రీఛార్జ్", "బిల్లు", "అద్దె", "రిచార్జ్", "रिचार्ज", "बिल", "किराया"],
    "Health": ["medicine", "tablet", "doctor", "hospital", "dawai", "మందులు", "డాక్టర్", "దవాఖాన", "दवाई", "दवा"],
    "Shopping": ["clothes", "shirt", "shoes", "dress", "kapde", "mobile", "బట్టలు", "షాపింగ్", "कपड़े", "जूते"],
    "Fun": ["movie", "cinema", "game", "party", "outing", "సినిమా", "పార్టీ", "फिल्म", "पार्टी"],
}

FILLER = (
    r"\b(rupees?|rupaye|rupaiye|rupay|rs|ka|ke|ki|ko|me|mein|pe|liye|for|on|spent|"
    r"aaj|today|kharcha|kharch|paid|gaye|gaya|hua|diye|karchu|pettanu|ayindi)\b|"
    r"₹|రూపాయలు|రూపాయి|ఖర్చు|అయింది|रुपये|रुपए|खर्च"
)
SPLITTERS = r",|\band\b|\baur\b|\bphir\b|\bthen\b|\binka\b|और|మరియు|ఇంకా|\.(?!\d)|।|\n|;"


def transcribe(audio_bytes: bytes, filename: str, language_code: str) -> str:
    """Call Gnani Prisma STT v3 with ITN numerals."""
    if not API_KEY:
        raise RuntimeError("GNANI_API_KEY is not configured.")
    resp = requests.post(
        API_URL,
        headers={"X-API-Key-ID": API_KEY},
        files={"audio_file": (filename, audio_bytes)},
        data={
            "language_code": language_code,
            "format": "transcribe",
            "itn_native_numerals": "false"  # digits as 0-9
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gnani Error {resp.status_code}: {resp.text}")
    return resp.json().get("transcript", "").strip()


def categorize(text: str) -> str:
    t = text.lower()
    for cat, words in CATEGORIES.items():
        if any(w in t for w in words):
            return cat
    return "Other"


def parse_expenses(text: str):
    rows = []
    if not text:
        return rows
    chunks = re.split(SPLITTERS, text, flags=re.I)
    for chunk in chunks:
        chunk = chunk.strip()
        m = re.search(r"\d+(?:\.\d+)?", chunk)
        if not m:
            continue
        amount = float(m.group())
        item = re.sub(r"\d+(?:\.\d+)?", " ", chunk)
        item = re.sub(FILLER, " ", item, flags=re.I)
        item = re.sub(r"\s+", " ", item).strip() or "General"
        rows.append({
            "date": dt.date.today().isoformat(),
            "item": item.capitalize(),
            "amount": amount,
            "category": categorize(chunk),
        })
    return rows


def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["date", "item", "amount", "category"])


def save_rows(rows):
    df = pd.concat([load_data(), pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)


# ---------------- PAGE SETUP & THEME ----------------
st.set_page_config(page_title="Awaaz Kharcha", page_icon="🎙️", layout="centered")

# Research-Backed CSS for Low-Friction 1-Page Layout
st.markdown("""
<style>
.block-container { 
    max-width: 720px; 
    padding-top: 1.2rem; 
    padding-bottom: 3rem;
}
html, body, [class*="css"] { 
    font-size: 17px; 
}

/* Big, thumb-friendly touch targets (min 52px) */
.stButton > button, .stDownloadButton > button {
    min-height: 52px; 
    font-size: 1.05rem; 
    font-weight: 600; 
    border-radius: 14px;
    width: 100%;
}

/* Central Prominent Mic Card styling */
.st-key-mic {
    background: #FFFFFF; 
    border: 2px dashed #0F766E; 
    border-radius: 18px;
    padding: 14px; 
    margin: 8px 0 6px 0;
    box-shadow: 0 4px 12px rgba(15, 118, 110, 0.08);
}

/* Metric card numbers */
[data-testid="stMetricValue"] { 
    font-size: 2.3rem; 
    font-weight: 800; 
    color: #0F766E;
}

/* Hide Streamlit default clutter for clean demo */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------- HEADER ----------------
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("<h2 style='margin:0; font-weight:800; color:#0F766E;'>🎙️ Awaaz Kharcha</h2>", unsafe_allow_html=True)
    st.caption("Say what you spent. We write it down. Powered by Gnani Prisma.")

with col_h2:
    with st.popover("ℹ️ Help"):
        st.markdown("""
        **How it works:**
        1. Select your spoken language.
        2. Tap the mic and say: *"chai 20, auto 80, lunch 150"*.
        3. Review what was heard, edit if needed, and tap Save!
        """)


# ---------------- STEP 1: ONE-TAP LANGUAGE SELECTOR ----------------
try:
    lang_choice = st.segmented_control(
        "Language",
        options=["Hinglish", "తెలుగు", "English"],
        default="Hinglish",
        label_visibility="collapsed"
    )
except AttributeError:
    lang_choice = st.radio(
        "Language",
        options=["Hinglish", "తెలుగు", "English"],
        horizontal=True,
        label_visibility="collapsed"
    )

selected_lang = lang_choice or "Hinglish"
lang_code = LANG_MAP.get(selected_lang, "hi-IN")
T = UI[lang_code]


# ---------------- PROGRESS HINT ----------------
step = 1 if "transcript" not in st.session_state else 2
labels = ["① Speak", "② Check", "③ Save"]
html_stepper = " &nbsp;→&nbsp; ".join(
    f"<b style='color:#0F766E; font-size:1.05rem;'>{l}</b>" if i + 1 == step 
    else f"<span style='color:#6B7280;'>{l}</span>"
    for i, l in enumerate(labels)
)
st.markdown(f"<div style='margin: 10px 0;'>{html_stepper}</div>", unsafe_allow_html=True)


# ---------------- STEP 2: THE GIANT MIC CARD ----------------
st.markdown(f"#### 🎙️ {T['speak']}")
audio = st.audio_input("Record your expenses", key="mic", label_visibility="collapsed")

col_info1, col_info2 = st.columns([3, 2])
with col_info1:
    st.caption(f"💡 {T['example']}")
with col_info2:
    st.caption(T['privacy'])


# Process audio automatically on capture
if audio is not None:
    # Trigger transcription if this is a newly recorded audio
    if st.session_state.get("last_processed_audio") != audio:
        try:
            with st.spinner("Understanding your voice with Gnani Prisma..."):
                transcribed_text = transcribe(audio.getvalue(), "voice.wav", lang_code)
                st.session_state["transcript"] = transcribed_text
                st.session_state["last_processed_audio"] = audio
        except Exception as e:
            st.warning("I couldn't hear that clearly. Please try once more, a bit closer to the mic.")
            st.session_state["transcript"] = ""


# ---------------- STEP 3: CHECK & CONFIRM (EDITABLE) ----------------
if st.session_state.get("transcript"):
    st.divider()
    st.markdown(f"#### 📝 {T['heard']}")
    
    # Editable transcript
    current_val = st.session_state["transcript"]
    user_edited = st.text_area(
        label="Edit transcript",
        value=current_val,
        height=85,
        label_visibility="collapsed"
    )
    if user_edited != current_val:
        st.session_state["transcript"] = user_edited

    # Parse rows
    parsed_rows = parse_expenses(st.session_state["transcript"])
    if parsed_rows:
        # Format table with friendly emojis
        df_preview = pd.DataFrame(parsed_rows)
        df_preview["category"] = df_preview["category"].map(lambda c: f"{CAT_EMOJI.get(c, '📦')} {c}")
        df_preview["amount_display"] = df_preview["amount"].map(lambda a: f"₹{a:,.0f}")
        
        st.dataframe(
            df_preview[["item", "amount_display", "category"]],
            column_config={
                "item": "Kharcha / Item",
                "amount_display": "Amount",
                "category": "Category"
            },
            use_container_width=True,
            hide_index=True
        )

        col_save, col_redo = st.columns([3, 1])
        with col_save:
            btn_save = st.button(f"✅ {T['save']} ({len(parsed_rows)} items)", type="primary")
            if btn_save:
                save_rows(parsed_rows)
                st.session_state["last_saved_n"] = len(parsed_rows)
                st.session_state.pop("transcript", None)
                st.toast(T["success_toast"], icon="👍")
                st.rerun()

        with col_redo:
            if st.button("↩ Redo"):
                st.session_state.pop("transcript", None)
                st.rerun()
    else:
        st.info("I couldn't catch an amount. Please try again with clear numbers, e.g. 'chai 20'.")


# ---------------- STEP 4: HERO SPENDING INTELLIGENCE ----------------
st.divider()
df = load_data()

if df.empty:
    st.info(T["empty_msg"])
else:
    df["date"] = pd.to_datetime(df["date"])
    today = pd.Timestamp.today().normalize()
    month_df = df[(df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)]
    
    today_total = df[df["date"] == today]["amount"].sum()
    month_total = month_df["amount"].sum()

    # Hero card with high-contrast palette
    st.markdown(f"""
    <div style="background:#0F766E; color:#FFFFFF; border-radius:18px; padding:20px 24px; margin:10px 0 16px 0; box-shadow:0 6px 20px rgba(15,118,110,0.25);">
      <div style="font-size:0.95rem; opacity:0.9; font-weight:600;">{T['today']}</div>
      <div style="font-size:2.8rem; font-weight:800; line-height:1.1; margin:4px 0;">₹{today_total:,.0f}</div>
      <div style="font-size:1.05rem; opacity:0.95; margin-top:6px; font-weight:500;">{T['month']}: ₹{month_total:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

    # Budget progress indicator
    DEFAULT_BUDGET = 12000
    budget_pct = (month_total / DEFAULT_BUDGET) * 100
    if budget_pct >= 90:
        st.warning(f"⚠️ Budget Alert: You have used {budget_pct:.0f}% of your monthly ₹{DEFAULT_BUDGET:,.0f} budget.")

    # Category Bar Chart
    if not month_df.empty:
        st.markdown("##### 📊 " + ("खर्च श्रेणियां" if lang_code == "hi-IN" else ("ఖర్చు వర్గాలు" if lang_code == "te-IN" else "Spending by Category")))
        cat_data = month_df.groupby("category")["amount"].sum()
        st.bar_chart(cat_data, color="#0F766E", height=230)

    # Undo Action & Table List
    col_act1, col_act2, col_act3 = st.columns([2, 2, 2])
    
    # Undo button
    if st.session_state.get("last_saved_n"):
        with col_act1:
            if st.button(T["undo"]):
                df_curr = load_data()
                n = st.session_state["last_saved_n"]
                df_curr.iloc[:-n].to_csv(DATA_FILE, index=False)
                st.session_state["last_saved_n"] = 0
                st.toast("Undone!", icon="↩")
                st.rerun()

    with col_act2:
        st.download_button(
            label=T["download"],
            data=df.to_csv(index=False),
            file_name=f"awaaz_kharcha_{dt.date.today().isoformat()}.csv",
            mime="text/csv"
        )

    with col_act3:
        if st.button(T["clear_all"]):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.rerun()

    # Quick collapsible transaction log
    with st.expander("📜 " + ("लेनदेन इतिहास" if lang_code == "hi-IN" else ("లావాదేవీల చరిత్ర" if lang_code == "te-IN" else "Transaction History"))):
        display_df = df.sort_values("date", ascending=False).copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df["category"] = display_df["category"].map(lambda c: f"{CAT_EMOJI.get(c, '📦')} {c}")
        display_df["amount"] = display_df["amount"].map(lambda a: f"₹{a:,.0f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
