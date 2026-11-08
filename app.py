import os
import re
import datetime as dt
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Gnani Prisma API Configuration
API_URL = "https://api.vachana.ai/stt/v3"
API_KEY = os.getenv("GNANI_API_KEY", "")
DATA_FILE = "expenses.csv"

# Narrow Audience Persona Focus for Contest:
# "For college students & young hustlers who split chai, canteen, auto & bills in Hinglish / Telugu"
LANGUAGES = {
    "Hinglish / Hindi (hi-IN)": "hi-IN",
    "Telugu (te-IN)": "te-IN",
    "English - Indian (en-IN)": "en-IN",
    "Tamil (ta-IN)": "ta-IN",
    "Kannada (kn-IN)": "kn-IN",
}

# Rich category taxonomy with Hinglish, Telugu, Hindi keywords
CATEGORIES = {
    "Food & Chai": [
        "chai", "tea", "coffee", "lunch", "dinner", "breakfast", "tiffin", "biryani",
        "samosa", "snack", "khana", "canteen", "juice", "pani", "water", "food", "maggi",
        "roll", "dosa", "idli", "shawarma", "burger", "pizza", "momos", "sweets",
        "టీ", "భోజనం", "టిఫిన్", "చాయ్", "అన్నం", "బిర్యానీ", "దోశ", "ఇడ్లీ", "స్నాక్స్",
        "चाय", "खाना", "नाश्ता", "समोसा", "बिरयानी"
    ],
    "Travel & Commute": [
        "auto", "bus", "metro", "cab", "ola", "uber", "petrol", "diesel", "fuel",
        "ticket", "train", "bike", "rapido", "rickshaw", "toll", "parking",
        "ఆటో", "బస్సు", "పెట్రోల్", "రైలు", "టికెట్", "ర్యాపిడో",
        "ऑटो", "बस", "पेट्रोल", "किराया", "ट्रेन", "रैपिडो"
    ],
    "Groceries & Kirana": [
        "sabzi", "vegetables", "milk", "doodh", "rice", "atta", "dal", "oil", "grocery",
        "kirana", "fruits", "bread", "eggs", "curd", "dahi", "chips", "biscuit",
        "పాలు", "కూరగాయలు", "సరుకులు", "బియ్యం", "నూనె", "గుడ్లు",
        "सब्ज़ी", "दूध", "राशन", "फल", "किराना", "अंडे"
    ],
    "Recharge & Bills": [
        "recharge", "bill", "electricity", "current", "wifi", "rent", "gas", "cylinder",
        "hotstar", "netflix", "prime", "subscription",
        "రీఛార్జ్", "బిల్లు", "అద్దె", "కరెంట్", "వైఫై",
        "रिचार्ज", "बिल", "किराया", "बिजली", "सिलेंडर"
    ],
    "Health & Meds": [
        "medicine", "tablet", "doctor", "hospital", "dawai", "pharmacy", "clinic",
        "bandage", "syrup",
        "మందులు", "డాక్టర్", "ఆసుపత్రి", "దవాఖాన",
        "दवाई", "डॉक्टर", "अस्पताल", "गोली"
    ],
    "Shopping & Lifestyle": [
        "clothes", "shirt", "shoes", "dress", "kapde", "mobile", "jeans", "earphones",
        "amazon", "flipkart", "myntra", "tshirt",
        "బట్టలు", "చెప్పులు", "షర్టు", "షాపింగ్",
        "कपड़े", "जूते", "शॉपिंग", "शर्ट"
    ],
    "Fun & Entertainment": [
        "movie", "cinema", "game", "party", "outing", "treat", "theatre", "popcorn",
        "సినిమా", "పార్టీ", "ట్రీట్", "ఆటలు",
        "फिल्म", "सिनेमा", "पार्टी", "घूमना"
    ],
}

CATEGORY_ICONS = {
    "Food & Chai": "☕",
    "Travel & Commute": "🛺",
    "Groceries & Kirana": "🛒",
    "Recharge & Bills": "📱",
    "Health & Meds": "💊",
    "Shopping & Lifestyle": "🛍️",
    "Fun & Entertainment": "🎉",
    "Other": "📝"
}

FILLER = (
    r"\b(rupees?|rupaye|rupaiye|rupay|rs|ka|ke|ki|ko|me|mein|pe|liye|for|on|spent|"
    r"aaj|today|kharcha|kharch|paid|gaye|gaya|hua|diya|diye|pettanu|ayindi|karchu)\b|"
    r"₹|రూపాయలు|రూపాయి|ఖర్చు|అయింది|రెండు|रुपये|रुपए|खर्च|दिया"
)

SPLITTERS = r",|\band\b|\baur\b|\bphir\b|\bthen\b|\binka\b|\bandaru\b|और|మరియు|ఇంకా|\.(?!\d)|।|\n|;"


def transcribe(audio_bytes: bytes, filename: str, language_code: str) -> str:
    """Send voice recording to Gnani Prisma STT v3."""
    if not API_KEY:
        raise RuntimeError("GNANI_API_KEY is not set. Please check your environment or .env file.")
    
    resp = requests.post(
        API_URL,
        headers={"X-API-Key-ID": API_KEY},
        files={"audio_file": (filename, audio_bytes)},
        data={
            "language_code": language_code,
            "format": "transcribe",
            "itn_native_numerals": "false"  # Keep 0-9 digits for clean regex parsing
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gnani API Error ({resp.status_code}): {resp.text}")
    
    data = resp.json()
    return data.get("transcript", "").strip()


def categorize(text: str) -> str:
    """Classify expense item by matching Hinglish / Telugu keywords."""
    t = text.lower()
    for cat, words in CATEGORIES.items():
        if any(w in t for w in words):
            return cat
    return "Other"


def parse_expenses(text: str):
    """
    Parses natural multilingual voice notes into structured expenses.
    e.g. 'aaj chai ke 20 rupaye, auto ka 80, lunch 150, medicine 200'
    """
    rows = []
    if not text:
        return rows

    chunks = re.split(SPLITTERS, text, flags=re.I)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        
        # Extract numerical amount (e.g. 20, 80.50)
        m = re.search(r"\d+(?:\.\d+)?", chunk)
        if not m:
            continue
        
        amount = float(m.group())
        # Clean item name by stripping numbers and conversational stop words
        item = re.sub(r"\d+(?:\.\d+)?", " ", chunk)
        item = re.sub(FILLER, " ", item, flags=re.I)
        item = re.sub(r"\s+", " ", item).strip().capitalize()
        
        if not item or len(item) < 2:
            item = "General Expense"
            
        rows.append({
            "date": dt.date.today().isoformat(),
            "item": item,
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
    existing = load_data()
    updated = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    updated.to_csv(DATA_FILE, index=False)


# ---------------- UI CONFIGURATION ----------------
st.set_page_config(
    page_title="Awaaz Kharcha - Voice Expense Tracker",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished FinTech look
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem !important;
        font-weight: 800;
        margin-bottom: 0px;
        background: -webkit-linear-gradient(45deg, #FF6B00, #FFAE00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        background: rgba(255, 107, 0, 0.15);
        color: #FF8800;
        border: 1px solid rgba(255, 107, 0, 0.3);
        margin-bottom: 12px;
    }
    .metric-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/microphone.png", width=64)
    st.markdown("### 🎙️ **Awaaz Kharcha**")
    st.caption("Voice-first expense tracking for India")
    
    st.markdown('<div class="badge-pill">⚡ Powered by Gnani Prisma STT</div>', unsafe_allow_html=True)
    
    st.markdown("**Persona Target:**")
    st.info("🎯 *For college students & daily commuters splitting chai, canteen, autos & bills in Hinglish/Telugu.*")

    st.divider()
    st.markdown("#### 🌐 Recognition Engine")
    lang_label = st.selectbox("Speech Language", list(LANGUAGES.keys()), index=0)
    lang_code = LANGUAGES[lang_label]

    st.markdown("#### 💡 Quick Voice Test Samples")
    st.markdown("""
    - *Hinglish:*  
      `"aaj chai 20, auto ka 80, lunch 150, recharge 299"`
    - *Telugu:*  
      `"eeroju tiffin 50, auto 60, biryani 220 karchu"`
    - *Daily Hustle:*  
      `"bus ticket 25, snacks 40, petrol 200, dawai 110"`
    """)

    st.divider()
    monthly_budget = st.number_input("Monthly Budget (₹)", min_value=500, max_value=200000, value=12000, step=500)
    
    st.caption("Great Indian AI Internship Challenge 2026")


# ---------------- MAIN CONTENT ----------------
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown('<h1 class="main-title">🎙️ Awaaz Kharcha</h1>', unsafe_allow_html=True)
    st.write("**Just say what you spent in your language.** We transcribe it, categorize it, and graph your money.")

with col_head2:
    st.write("")
    st.metric("Engine Status", "Gnani Prisma ⚡", "Active (hi/te/en)")

tab_record, tab_samples, tab_history = st.tabs(["🗣️ Voice Input & Splitter", "🧪 Quick Pre-recorded Samples", "📜 Full Expense Log"])

with tab_record:
    col_input1, col_input2 = st.columns([1, 1])
    
    with col_input1:
        st.subheader("1. Speak or Upload Voice Note")
        audio_rec = st.audio_input("Tap the mic icon and speak your expenses:")
        audio_file = st.file_uploader("...or drop a voice note (wav / mp3 / m4a):", type=["wav", "mp3", "m4a", "ogg"])
        
        active_audio = audio_rec or audio_file
        
        btn_transcribe = st.button("🚀 Transcribe with Gnani Prisma", type="primary", use_container_width=True)

    with col_input2:
        st.subheader("2. Speech to Text Result")
        
        if active_audio is not None and btn_transcribe:
            try:
                with st.spinner("Prisma Neural STT is listening and formatting digits..."):
                    audio_bytes = active_audio.getvalue()
                    fname = getattr(active_audio, "name", "recording.wav")
                    transcript_text = transcribe(audio_bytes, fname, lang_code)
                    st.session_state["transcript"] = transcript_text
                    st.toast("Transcribed with Gnani Prisma!", icon="✅")
            except Exception as e:
                st.error(f"Transcription failed: {e}")

        # Editable Transcript box
        current_transcript = st.session_state.get("transcript", "")
        edited_text = st.text_area(
            "What I heard (live editable before saving):",
            value=current_transcript,
            placeholder="e.g. aaj chai 20, auto 80, lunch 150",
            height=110
        )
        if edited_text != current_transcript:
            st.session_state["transcript"] = edited_text

    # Parsed Items Preview
    if st.session_state.get("transcript", "").strip():
        st.subheader("3. Detected Expense Breakdown")
        detected_rows = parse_expenses(st.session_state["transcript"])
        
        if detected_rows:
            parsed_df = pd.DataFrame(detected_rows)
            parsed_df["Icon"] = parsed_df["category"].map(lambda c: CATEGORY_ICONS.get(c, "📝"))
            
            c_disp1, c_disp2 = st.columns([2, 1])
            with c_disp1:
                st.dataframe(
                    parsed_df[["Icon", "item", "amount", "category"]],
                    column_config={
                        "Icon": st.column_config.TextColumn("", width="small"),
                        "item": st.column_config.TextColumn("Item / Kharcha"),
                        "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
                        "category": st.column_config.TextColumn("Category"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
            
            with c_disp2:
                total_detected = sum(r["amount"] for r in detected_rows)
                st.metric("Total in this Note", f"₹{total_detected:,.2f}", f"{len(detected_rows)} items")
                if st.button("💾 Confirm & Save to Dashboard", type="primary", use_container_width=True):
                    save_rows(detected_rows)
                    st.session_state.pop("transcript", None)
                    st.success(f"Saved {len(detected_rows)} expenses totaling ₹{total_detected:,.0f}!")
                    st.rerun()
        else:
            st.info("💡 No numerical amounts detected in this phrase. Try saying digits clearly (e.g. 'chai 20, auto 80').")

with tab_samples:
    st.subheader("Try Instant Demo Audio Samples (Pre-configured)")
    st.write("Click any sample to quickly populate the parser and test categories:")
    
    sample_col1, sample_col2, sample_col3 = st.columns(3)
    
    with sample_col1:
        st.markdown("**Sample 1: College Day (Hinglish)**")
        st.caption('"aaj canteen chai 20, auto ka 80, lunch biryani 160, metro card recharge 200"')
        if st.button("Load Sample 1"):
            st.session_state["transcript"] = "aaj canteen chai 20, auto ka 80, lunch biryani 160, metro card recharge 200"
            st.rerun()

    with sample_col2:
        st.markdown("**Sample 2: Telugu Daily Commute**")
        st.caption('"eeroju tiffin dosa 60, rapido bike 75, medicines 180, evening snacks 45"')
        if st.button("Load Sample 2"):
            st.session_state["transcript"] = "eeroju tiffin dosa 60, rapido bike 75, medicines 180, evening snacks 45"
            st.rerun()

    with sample_col3:
        st.markdown("**Sample 3: Weekend Outing & Groceries**")
        st.caption('"movie ticket 250, popcorn 120, sabzi and milk 140, cab 190"')
        if st.button("Load Sample 3"):
            st.session_state["transcript"] = "movie ticket 250, popcorn 120, sabzi and milk 140, cab 190"
            st.rerun()

# ---------------- SPENDING DASHBOARD ----------------
st.divider()
st.subheader("📊 Spending Intelligence & Budget Tracking")

df_expenses = load_data()

if df_expenses.empty:
    st.info("No recorded expenses yet. Speak into the microphone above to log your first kharcha!")
else:
    df_expenses["date"] = pd.to_datetime(df_expenses["date"])
    today = pd.Timestamp.today().normalize()
    
    today_mask = df_expenses["date"] == today
    month_mask = (df_expenses["date"].dt.month == today.month) & (df_expenses["date"].dt.year == today.year)
    
    today_sum = df_expenses[today_mask]["amount"].sum()
    month_sum = df_expenses[month_mask]["amount"].sum()
    total_count = len(df_expenses)
    
    # Budget Progress
    budget_pct = (month_sum / monthly_budget) * 100 if monthly_budget > 0 else 0

    # KPI Metrics Row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Today's Kharcha", f"₹{today_sum:,.0f}", f"{df_expenses[today_mask].shape[0]} items")
    kpi2.metric("This Month", f"₹{month_sum:,.0f}", f"{budget_pct:.1f}% of budget")
    kpi3.metric("Monthly Budget", f"₹{monthly_budget:,.0f}", f"₹{max(0, monthly_budget - month_sum):,.0f} left")
    kpi4.metric("Logged Entries", f"{total_count} transactions", "Lifetime")

    # Budget Warning Alert
    if budget_pct >= 90:
        st.error(f"⚠️ Budget Alert: You have utilized {budget_pct:.1f}% of your monthly ₹{monthly_budget:,.0f} budget!")
    elif budget_pct >= 75:
        st.warning(f"⚡ Caution: You have crossed {budget_pct:.1f}% of your monthly ₹{monthly_budget:,.0f} budget.")

    # Charts Row
    chart_col1, chart_col2 = st.columns([1, 1])
    
    month_df = df_expenses[month_mask]
    if not month_df.empty:
        cat_group = month_df.groupby("category")["amount"].sum().reset_index()
        
        with chart_col1:
            st.markdown("##### 📌 Spending by Category (This Month)")
            st.bar_chart(cat_group.set_index("category")["amount"], color="#FF6B00", height=280)
            
        with chart_col2:
            st.markdown("##### 📅 Daily Spending Trend")
            daily_group = month_df.groupby(month_df["date"].dt.strftime("%d %b"))["amount"].sum()
            st.line_chart(daily_group, height=280)

with tab_history:
    st.subheader("Transaction History")
    if not df_expenses.empty:
        hist_df = df_expenses.sort_values("date", ascending=False).copy()
        hist_df["date"] = hist_df["date"].dt.strftime("%Y-%m-%d")
        
        st.dataframe(
            hist_df,
            column_config={
                "date": "Date",
                "item": "Item",
                "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
                "category": "Category",
            },
            use_container_width=True,
            hide_index=True
        )
        
        c_down1, c_down2 = st.columns([1, 3])
        with c_down1:
            st.download_button(
                "📥 Download CSV Export",
                data=hist_df.to_csv(index=False),
                file_name=f"awaaz_kharcha_{dt.date.today().isoformat()}.csv",
                mime="text/csv"
            )
        with c_down2:
            if st.button("🗑️ Reset All Expenses (Clear Log)"):
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
                st.success("Expense log cleared.")
                st.rerun()
