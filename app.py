import os
import re
import datetime as dt
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Gnani API Configuration
API_URL = "https://api.vachana.ai/stt/v3"
API_KEY = os.getenv("GNANI_API_KEY", "")
DATA_FILE = "expenses.csv"
UDHAR_FILE = "udhar_khata.csv"

# ---------------- MULTILINGUAL LOCALIZATION STRINGS ----------------
UI = {
    "hi-IN": {
        "title": "आवाज़ खर्चा",
        "subtitle": "जो खर्च किया, बस बोलिए। हम लिख लेंगे।",
        "speak": "बोलिए (Tap & Speak)",
        "heard": "मैंने यह सुना (Edit if needed)",
        "save": "खर्चा सेव करें",
        "today": "आज का खर्च",
        "month": "इस महीने का खर्च",
        "budget": "महीने का बजट",
        "example": 'जैसे: "आज चाय 20, ऑटो 80, लंच डेढ़ सौ, रवि को 500 उधार दिया"',
        "privacy": "🔒 आपकी आवाज़ सिर्फ खर्च लिखने के लिए इस्तेमाल होती है।",
        "empty_msg": "अभी कोई खर्च दर्ज नहीं है। ऊपर माइक दबाकर बोलिए।",
        "items_header": "पहचाने गए खर्चे:",
        "success_toast": "खर्च सफलतापूर्वक सेव हो गया! 👍",
        "undo": "↩ पिछला खर्च वापस लें (Undo)",
        "download": "खर्चा डाउनलोड करें (CSV)",
        "clear_all": "🗑️ सब साफ़ करें",
        "udhar_header": "📒 आवाज़ उधार / खाता (Voice Ledger)",
        "ask_header": "🗣️ आवाज़ से पूछिए (Ask by Voice)",
        "ask_example": 'जैसे: "इस महीने कितना खर्च हुआ?", "चाय पर कितना गया?"'
    },
    "te-IN": {
        "title": "ఆవాజ్ ఖర్చు",
        "subtitle": "మీరు ఖర్చు పెట్టింది మాట్లాడండి. మేము రాస్తాము.",
        "speak": "మాట్లాడండి (Tap & Speak)",
        "heard": "నేను విన్నది (సరిచూసుకోండి)",
        "save": "ఖర్చులను సేవ్ చేయండి",
        "today": "ఈ రోజు ఖర్చు",
        "month": "ఈ నెల మొత్తం ఖర్చు",
        "budget": "నెల బడ్జెట్",
        "example": 'ఉదా: "ఈరోజు టీ 20, ఆటో 80, భోజనం 150, రవికి 500 అప్పు ఇచ్చాను"',
        "privacy": "🔒 మీ స్వరం ఖర్చులను లెక్కించడానికి మాత్రమే ఉపయోగించబడుతుంది.",
        "empty_msg": "ఇంకా ఏమీ నమోదు కాలేదు. పైన మైక్ నొక్కి మాట్లాడండి.",
        "items_header": "గుర్తించిన ఖర్చులు:",
        "success_toast": "ఖర్చులు విజయవంతంగా సేవ్ అయ్యాయి! 👍",
        "undo": "↩ చివరి రికార్డును రద్దు చేయండి (Undo)",
        "download": "ఖర్చులను డౌన్‌లోడ్ చేయండి (CSV)",
        "clear_all": "🗑️ డేటా క్లియర్ చేయండి",
        "udhar_header": "📒 వాయిస్ ఉధార్ / ఖాతా (Voice Ledger)",
        "ask_header": "🗣️ స్వరం ద్వారా అడగండి (Ask by Voice)",
        "ask_example": 'ఉదా: "ఈ నెల ఎంత ఖర్చు అయింది?", "టీ కి ఎంత పోయింది?"'
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
        "example": 'Try: "today tea 20, auto 80, lunch 150, lent 500 to Ravi"',
        "privacy": "🔒 Your voice is only used on this device to log your expenses.",
        "empty_msg": "Nothing yet. Tap the mic above to log your first expense.",
        "items_header": "Detected Expenses:",
        "success_toast": "Expenses saved successfully! 👍",
        "undo": "↩ Undo Last Save",
        "download": "Download CSV",
        "clear_all": "🗑️ Clear All",
        "udhar_header": "📒 Udhar / Khata Voice Ledger",
        "ask_header": "🗣️ Ask by Voice",
        "ask_example": 'Try: "how much did I spend this month?", "how much on chai?"'
    }
}

LANG_MAP = {
    "Hinglish": "hi-IN",
    "తెలుగు": "te-IN",
    "English": "en-IN"
}

# Category Icons & taxonomy
CAT_EMOJI = {
    "Food": "🍵",
    "Travel": "🛺",
    "Groceries": "🥬",
    "Bills": "💡",
    "Health": "💊",
    "Shopping": "🛍️",
    "Fun": "🎬",
    "Udhar/Khata": "🤝",
    "Other": "📦"
}

CATEGORIES = {
    "Food": ["chai", "tea", "coffee", "lunch", "dinner", "breakfast", "tiffin", "biryani",
             "samosa", "snack", "khana", "canteen", "juice", "pani", "water", "food",
             "టీ", "భోజనం", "టిఫిన్", "చాయ్", "అన్నం", "బిర్యానీ", "चाय", "खाना", "नाश्ता"],
    "Travel": ["auto", "bus", "metro", "cab", "ola", "uber", "petrol", "diesel", "fuel",
               "ticket", "train", "bike", "rapido", "ఆటో", "బస్సు", "పెట్రోల్", "రైలు", "ऑटो", "बस", "पेट्रोल"],
    "Groceries": ["sabzi", "vegetables", "milk", "doodh", "rice", "atta", "dal", "oil", "grocery",
                  "kirana", "fruits", "పాలు", "కూరగాయలు", "సరుకులు", "सब्ज़ी", "दूध", "राशन"],
    "Bills": ["recharge", "bill", "electricity", "current", "wifi", "rent", "gas", "cylinder",
              "రీఛార్జ్", "బిల్లు", "అద్దె", "రిచార్జ్", "रिचार्ज", "बिल", "किराया"],
    "Health": ["medicine", "tablet", "doctor", "hospital", "dawai", "మందులు", "డాక్టర్", "దవాఖాన", "दवाई", "दवा"],
    "Shopping": ["clothes", "shirt", "shoes", "dress", "kapde", "mobile", "బట్టలు", "షాపింగ్", "कपड़े", "जूते"],
    "Fun": ["movie", "cinema", "game", "party", "outing", "సినిమా", "పార్టీ", "फिल्म", "पार्टी"],
    "Udhar/Khata": ["udhar", "diya", "diye", "wapas", "liya", "liye", "khatam", "baki", "lena", "dena", "అప్పు", "ఇచ్చాను", "తీసుకున్నా"]
}

# ---------------- FEATURE 1: HINGLISH & INDIAN NUMBER WORDS TO DIGITS ----------------
NUMBER_WORDS = {
    "dedh sau": "150", "dhai sau": "250", "ek sau": "100", "do sau": "200", "teen sau": "300",
    "char sau": "400", "paanch sau": "500", "chhe sau": "600", "saat sau": "700", "aath sau": "800",
    "nau sau": "900", "dedh hazar": "1500", "dhai hazar": "2500", "ek hazar": "1000", "do hazar": "2000",
    "paanch hazar": "5000", "dus hazar": "10000", "dedh": "1.5", "dhai": "2.5", "hazar": "1000", "sau": "100",
    "వంద": "100", "రెండు వందలు": "200", "ఐదు వందలు": "500", "వెయ్యి": "1000", "రెండు వేలు": "2000", "ఐదు వేలు": "5000",
    "सौ": "100", "हज़ार": "1000", "डेढ़ सौ": "150", "ढाई सौ": "250"
}

def normalize_hinglish_numbers(text: str) -> str:
    """Replaces spoken colloquial expressions like 'dedh sau', 'dhai sau' into clean numbers."""
    cleaned = text
    for phrase, num in NUMBER_WORDS.items():
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        cleaned = pattern.sub(num, cleaned)
    return cleaned

FILLER = (
    r"\b(rupees?|rupaye|rupaiye|rupay|rs|ka|ke|ki|ko|me|mein|pe|liye|for|on|spent|"
    r"aaj|today|kharcha|kharch|paid|gaye|gaya|hua|diye|karchu|pettanu|ayindi)\b|"
    r"₹|రూపాయలు|రూపాయి|ఖర్చు|అయింది|రెండు|रुपये|रुपए|खर्च"
)
SPLITTERS = r",|\band\b|\baur\b|\bphir\b|\bthen\b|\binka\b|और|మరియు|ఇంకా|\.(?!\d)|।|\n|;"


def transcribe(audio_bytes: bytes, filename: str, language_code: str) -> str:
    """Call Gnani Prisma STT v3."""
    if not API_KEY:
        raise RuntimeError("GNANI_API_KEY is not configured.")
    resp = requests.post(
        API_URL,
        headers={"X-API-Key-ID": API_KEY},
        files={"audio_file": (filename, audio_bytes)},
        data={
            "language_code": language_code,
            "format": "transcribe",
            "itn_native_numerals": "false"
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
    """Parses text into expense items while normalizing colloquial number words and detecting Udhar."""
    normalized_text = normalize_hinglish_numbers(text)
    rows = []
    udhar_rows = []
    
    if not normalized_text:
        return rows, udhar_rows

    chunks = re.split(SPLITTERS, normalized_text, flags=re.I)
    for chunk in chunks:
        chunk = chunk.strip()
        m = re.search(r"\d+(?:\.\d+)?", chunk)
        if not m:
            continue
        
        amount = float(m.group())
        chunk_lower = chunk.lower()

        # ---------------- FEATURE 6: UDHAR / KHATA DETECTION ----------------
        is_udhar = any(w in chunk_lower for w in ["udhar", "उधार", "అప్పు", "lent", "borrow", "diya", "diye", "wapas"])
        
        item = re.sub(r"\d+(?:\.\d+)?", " ", chunk)
        item = re.sub(FILLER, " ", item, flags=re.I)
        item = re.sub(r"\s+", " ", item).strip() or "General"

        if is_udhar:
            # Detect who gave/took
            action = "Lent (Diya)" if any(w in chunk_lower for w in ["diya", "diye", "lent", "ఇచ్చాను"]) else "Received/Borrowed (Liya)"
            udhar_rows.append({
                "date": dt.date.today().isoformat(),
                "person": item.capitalize(),
                "amount": amount,
                "type": action,
                "status": "Pending"
            })
        else:
            rows.append({
                "date": dt.date.today().isoformat(),
                "item": item.capitalize(),
                "amount": amount,
                "category": categorize(chunk),
            })
            
    return rows, udhar_rows


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


def load_udhar_data() -> pd.DataFrame:
    if os.path.exists(UDHAR_FILE):
        try:
            return pd.read_csv(UDHAR_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["date", "person", "amount", "type", "status"])


def save_udhar_rows(rows):
    df = pd.concat([load_udhar_data(), pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(UDHAR_FILE, index=False)


# ---------------- FEATURE 5: ASK BY VOICE ENGINE ----------------
def answer_voice_query(query: str, df: pd.DataFrame, udhar_df: pd.DataFrame) -> str:
    """Answers voice questions like 'is mahine kitna kharch hua?' or 'chai pe kitna gaya?'."""
    q = query.lower()
    
    if df.empty and udhar_df.empty:
        return "You have not recorded any expenses yet. Record an expense first!"
    
    # Check date scope
    df_scope = df.copy()
    if not df_scope.empty:
        df_scope["date"] = pd.to_datetime(df_scope["date"])
        today = pd.Timestamp.today().normalize()

    # Query: This month total
    if any(w in q for w in ["is mahine", "this month", "month", "ఈ నెల"]):
        m_df = df_scope[(df_scope["date"].dt.month == today.month) & (df_scope["date"].dt.year == today.year)]
        tot = m_df["amount"].sum()
        top_cat = m_df.groupby("category")["amount"].sum().idxmax() if not m_df.empty else "None"
        return f"This month you spent a total of ₹{tot:,.0f}. Your highest spending category is {top_cat}."
    
    # Query: Today's total
    if any(w in q for w in ["aaj", "today", "ఈ రోజు", "eeroju"]):
        t_df = df_scope[df_scope["date"] == today]
        tot = t_df["amount"].sum()
        cnt = len(t_df)
        return f"Today you have spent ₹{tot:,.0f} across {cnt} transactions."

    # Query: Specific Category (e.g. Chai / Auto / Petrol)
    for cat_name, words in CATEGORIES.items():
        if any(w in q for w in words):
            matched = df[df["category"] == cat_name]
            tot = matched["amount"].sum()
            return f"You have spent ₹{tot:,.0f} in the {cat_name} category ({len(matched)} items)."

    # Query: Udhar / Khata who owes me
    if any(w in q for w in ["udhar", "khata", "baki", "lent", "అప్పు"]):
        if not udhar_df.empty:
            pending = udhar_df[udhar_df["status"] == "Pending"]
            tot = pending["amount"].sum()
            return f"You currently have ₹{tot:,.0f} in pending Udhar ledger across {len(pending)} people."
        return "You have zero pending Udhar records."

    # Default fallback
    tot_lifetime = df["amount"].sum() if not df.empty else 0
    return f"Total tracked spending is ₹{tot_lifetime:,.0f}. Try asking: 'is mahine kitna kharch hua?' or 'chai pe kitna gaya?'."


# ---------------- STREAMLIT PAGE CONFIG ----------------
st.set_page_config(page_title="Awaaz Kharcha", page_icon="🎙️", layout="centered")

st.markdown("""
<style>
.block-container { 
    max-width: 720px; 
    padding-top: 1.2rem; 
    padding-bottom: 3rem;
}
html, body, [class*="css"] { font-size: 17px; }
.stButton > button, .stDownloadButton > button {
    min-height: 52px; font-size: 1.05rem; font-weight: 600; border-radius: 14px; width: 100%;
}
.st-key-mic {
    background: #FFFFFF; border: 2px dashed #0F766E; border-radius: 18px;
    padding: 14px; margin: 8px 0 6px 0; box-shadow: 0 4px 12px rgba(15, 118, 110, 0.08);
}
[data-testid="stMetricValue"] { font-size: 2.3rem; font-weight: 800; color: #0F766E; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.badge-feature {
    display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem;
    font-weight: bold; background: #0F766E22; color: #0F766E; margin-right: 6px;
}
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
        **New Features Added:**
        - **Hinglish Number Words:** Say *"dedh sau"* (150), *"dhai sau"* (250), *"paanch hazar"* (5000).
        - **Udhar / Khata Mode:** Say *"Ravi ko 500 udhar diya"* to auto-create ledger.
        - **Ask by Voice:** Ask *"is mahine kitna kharch hua?"* to hear answers!
        """)

# Language Selector
try:
    lang_choice = st.segmented_control(
        "Language", options=["Hinglish", "తెలుగు", "English"], default="Hinglish", label_visibility="collapsed"
    )
except AttributeError:
    lang_choice = st.radio(
        "Language", options=["Hinglish", "తెలుగు", "English"], horizontal=True, label_visibility="collapsed"
    )

selected_lang = lang_choice or "Hinglish"
lang_code = LANG_MAP.get(selected_lang, "hi-IN")
T = UI[lang_code]


# ---------------- MODES: TRACK EXPENSE vs ASK BY VOICE ----------------
mode = st.radio("Mode", ["📝 Log Expense / Udhar", "🗣️ Ask by Voice (Q&A)"], horizontal=True, label_visibility="collapsed")

if mode == "📝 Log Expense / Udhar":
    # Step indicator
    step = 1 if "transcript" not in st.session_state else 2
    labels = ["① Speak", "② Check", "③ Save"]
    html_stepper = " &nbsp;→&nbsp; ".join(
        f"<b style='color:#0F766E; font-size:1.05rem;'>{l}</b>" if i + 1 == step 
        else f"<span style='color:#6B7280;'>{l}</span>"
        for i, l in enumerate(labels)
    )
    st.markdown(f"<div style='margin: 8px 0;'>{html_stepper}</div>", unsafe_allow_html=True)

    # Mic widget
    st.markdown(f"#### 🎙️ {T['speak']}")
    audio = st.audio_input("Record your expenses", key="mic", label_visibility="collapsed")

    col_info1, col_info2 = st.columns([3, 2])
    with col_info1:
        st.caption(f"💡 {T['example']}")
    with col_info2:
        st.caption(T['privacy'])

    # Auto-transcribe upon receiving audio
    if audio is not None and st.session_state.get("last_processed_audio") != audio:
        try:
            with st.spinner("Understanding your voice with Gnani Prisma..."):
                transcribed_text = transcribe(audio.getvalue(), "voice.wav", lang_code)
                st.session_state["transcript"] = transcribed_text
                st.session_state["last_processed_audio"] = audio
        except Exception as e:
            st.warning("I couldn't hear that clearly. Please try once more, a bit closer to the mic.")
            st.session_state["transcript"] = ""

    # Check & Edit Step
    if st.session_state.get("transcript"):
        st.divider()
        st.markdown(f"#### 📝 {T['heard']}")
        
        current_val = st.session_state["transcript"]
        user_edited = st.text_area(label="Edit transcript", value=current_val, height=85, label_visibility="collapsed")
        if user_edited != current_val:
            st.session_state["transcript"] = user_edited

        parsed_rows, parsed_udhar = parse_expenses(st.session_state["transcript"])
        
        if parsed_rows or parsed_udhar:
            # 1. Normal Expenses
            if parsed_rows:
                st.markdown("##### 🛒 Personal / Daily Expenses:")
                df_prev = pd.DataFrame(parsed_rows)
                df_prev["category"] = df_prev["category"].map(lambda c: f"{CAT_EMOJI.get(c, '📦')} {c}")
                df_prev["amount_display"] = df_prev["amount"].map(lambda a: f"₹{a:,.0f}")
                st.dataframe(df_prev[["item", "amount_display", "category"]], use_container_width=True, hide_index=True)

            # 2. Udhar / Khata items
            if parsed_udhar:
                st.markdown("##### 🤝 Udhar / Khata Entries:")
                df_udh = pd.DataFrame(parsed_udhar)
                df_udh["amount_display"] = df_udh["amount"].map(lambda a: f"₹{a:,.0f}")
                st.dataframe(df_udh[["person", "amount_display", "type", "status"]], use_container_width=True, hide_index=True)

            col_save, col_redo = st.columns([3, 1])
            with col_save:
                tot_items = len(parsed_rows) + len(parsed_udhar)
                if st.button(f"✅ {T['save']} ({tot_items} items)", type="primary"):
                    if parsed_rows:
                        save_rows(parsed_rows)
                    if parsed_udhar:
                        save_udhar_rows(parsed_udhar)
                    st.session_state["last_saved_n"] = len(parsed_rows)
                    st.session_state["last_saved_udhar_n"] = len(parsed_udhar)
                    st.session_state.pop("transcript", None)
                    st.toast(T["success_toast"], icon="👍")
                    st.rerun()

            with col_redo:
                if st.button("↩ Redo"):
                    st.session_state.pop("transcript", None)
                    st.rerun()
        else:
            st.info("I couldn't catch an amount. Say e.g. 'chai 20' or 'dedh sau (150)'.")

else:
    # ---------------- MODE: ASK BY VOICE ----------------
    st.markdown(f"#### {T['ask_header']}")
    st.caption(T['ask_example'])
    
    ask_audio = st.audio_input("Ask a question about your spending", key="ask_mic", label_visibility="collapsed")
    
    if ask_audio is not None and st.session_state.get("last_ask_audio") != ask_audio:
        try:
            with st.spinner("Prisma is interpreting your query..."):
                query_text = transcribe(ask_audio.getvalue(), "query.wav", lang_code)
                st.session_state["ask_query"] = query_text
                st.session_state["last_ask_audio"] = ask_audio
        except Exception:
            st.warning("Could not interpret question. Please speak clearly.")

    if st.session_state.get("ask_query"):
        st.markdown(f"**You asked:** *\"{st.session_state['ask_query']}\"*")
        ans = answer_voice_query(st.session_state["ask_query"], load_data(), load_udhar_data())
        st.success(f"🤖 **Answer:** {ans}")


# ---------------- DASHBOARD & TOTALS ----------------
st.divider()
df = load_data()
udhar_df = load_udhar_data()

if df.empty and udhar_df.empty:
    st.info(T["empty_msg"])
else:
    today_total = 0
    month_total = 0
    
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        today = pd.Timestamp.today().normalize()
        month_df = df[(df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)]
        today_total = df[df["date"] == today]["amount"].sum()
        month_total = month_df["amount"].sum()

    # Hero Card
    st.markdown(f"""
    <div style="background:#0F766E; color:#FFFFFF; border-radius:18px; padding:20px 24px; margin:10px 0 16px 0; box-shadow:0 6px 20px rgba(15,118,110,0.25);">
      <div style="font-size:0.95rem; opacity:0.9; font-weight:600;">{T['today']}</div>
      <div style="font-size:2.8rem; font-weight:800; line-height:1.1; margin:4px 0;">₹{today_total:,.0f}</div>
      <div style="font-size:1.05rem; opacity:0.95; margin-top:6px; font-weight:500;">{T['month']}: ₹{month_total:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- UDHAR / KHATA LEDGER DISPLAY ----------------
    if not udhar_df.empty:
        st.markdown(f"#### {T['udhar_header']}")
        pending_udh = udhar_df[udhar_df["status"] == "Pending"]
        tot_pending = pending_udh["amount"].sum()
        
        c_udh1, c_udh2 = st.columns([1, 1])
        c_udh1.metric("Pending Udhar / Lent Out", f"₹{tot_pending:,.0f}", f"{len(pending_udh)} people")
        c_udh2.metric("Settled Entries", f"{len(udhar_df) - len(pending_udh)}", "Cleared")

        disp_udhar = udhar_df.copy()
        disp_udhar["amount"] = disp_udhar["amount"].map(lambda a: f"₹{a:,.0f}")
        st.dataframe(disp_udhar, use_container_width=True, hide_index=True)

    # Category Bar Chart
    if not df.empty:
        month_df = df[(df["date"].dt.month == pd.Timestamp.today().month)]
        if not month_df.empty:
            st.markdown("##### 📊 " + ("खर्च श्रेणियां" if lang_code == "hi-IN" else ("ఖర్చు వర్గాలు" if lang_code == "te-IN" else "Spending by Category")))
            st.bar_chart(month_df.groupby("category")["amount"].sum(), color="#0F766E", height=230)

    # Actions: Undo, Download, Clear
    col_act1, col_act2, col_act3 = st.columns([2, 2, 2])
    with col_act1:
        if st.session_state.get("last_saved_n") or st.session_state.get("last_saved_udhar_n"):
            if st.button(T["undo"]):
                if os.path.exists(DATA_FILE) and st.session_state.get("last_saved_n"):
                    d_curr = load_data()
                    d_curr.iloc[:-st.session_state["last_saved_n"]].to_csv(DATA_FILE, index=False)
                    st.session_state["last_saved_n"] = 0
                if os.path.exists(UDHAR_FILE) and st.session_state.get("last_saved_udhar_n"):
                    u_curr = load_udhar_data()
                    u_curr.iloc[:-st.session_state["last_saved_udhar_n"]].to_csv(UDHAR_FILE, index=False)
                    st.session_state["last_saved_udhar_n"] = 0
                st.toast("Undone!", icon="↩")
                st.rerun()

    with col_act2:
        if not df.empty:
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
            if os.path.exists(UDHAR_FILE):
                os.remove(UDHAR_FILE)
            st.rerun()
