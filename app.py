"""Awaaz Kharcha — voice-first multilingual expense tracker.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import calendar
import datetime as dt
import hashlib

import pandas as pd
import streamlit as st

from awaaz import config, insights
from awaaz.parser import CAT_EMOJI, EXPENSE_CATEGORIES, parse_expenses
from awaaz.store import Store
from awaaz.stt import SttError, transcribe

DATA_FILE = "data/awaaz.db"  # shown in the sidebar for transparency

# ---------------- LOCALIZATION ----------------
UI = {
    "hi-IN": {
        "title": "आवाज़ खर्चा",
        "subtitle": "जो खर्च किया, बस बोलिए। हम लिख लेंगे।",
        "speak": "बोलिए या WhatsApp वॉइस नोट अपलोड करें",
        "heard": "मैंने यह सुना",
        "save": "खर्चा सेव करें",
        "today": "आज का खर्च",
        "month": "इस महीने",
        "week": "इस हफ्ते",
        "avg_day": "रोज़ का औसत",
        "budget_left": "बजट शेष",
        "safe_today": "आज सुरक्षित खर्च",
        "budget_target": "महीने का बजट (₹)",
        "example": 'जैसे: "kal chai 20, auto 80, lunch dedh sau, Ravi ko 500 udhar diya"',
        "privacy": "🔒 आपकी आवाज़ सिर्फ खर्च लिखने के लिए इस्तेमाल होती है।",
        "empty_msg": "अभी कोई खर्च दर्ज नहीं है। माइक दबाकर बोलिए या नीचे टाइप कीजिए।",
        "success_toast": "खर्च सफलतापूर्वक सेव हो गया!",
        "undo": "↩ पिछला सेव वापस लें",
        "download": "CSV डाउनलोड करें",
        "clear_all": "सारा डेटा साफ़ करें",
        "udhar_header": "आवाज़ उधार / खाता",
        "ask_header": "आवाज़ से पूछिए",
        "ask_example": 'जैसे: "इस महीने कितना खर्च हुआ?", "चाय पर कितना गया?", "बजट कितना बचा?"',
        "type_header": "टाइप करके खर्च जोड़ें",
        "type_placeholder": 'जैसे: "kal chai 20, auto 80, lunch dedh sau"',
        "one_tap": "एक टैप में जोड़ें",
        "history_header": "खर्च इतिहास",
        "insight_header": "साप्ताहिक जानकारी",
        "settle": "भुगतान हो गया",
        "pending": "बाकी",
        "settled": "चुका हुआ",
        "no_voice": "आवाज़ के लिए GNANI_API_KEY चाहिए। तब तक टाइप करके या एक टैप में खर्च जोड़िए।",
        "tabs": ["🎙️ बोलिए", "⌨️ लिखें", "📒 खाता", "📊 विश्लेषण", "📜 इतिहास", "🗣️ पूछें"],
    },
    "te-IN": {
        "title": "ఆవాజ్ ఖర్చు",
        "subtitle": "మీరు ఖర్చు పెట్టింది మాట్లాడండి. మేము రాస్తాము.",
        "speak": "మాట్లాడండి లేదా వాట్సాప్ వాయిస్ నోట్ అప్‌లోడ్ చేయండి",
        "heard": "నేను విన్నది",
        "save": "ఖర్చులను సేవ్ చేయండి",
        "today": "ఈ రోజు ఖర్చు",
        "month": "ఈ నెల",
        "week": "ఈ వారం",
        "avg_day": "రోజుకు సగటు",
        "budget_left": "బడ్జెట్ మిగిలింది",
        "safe_today": "ఈ రోజు సురక్షిత ఖర్చు",
        "budget_target": "నెల బడ్జెట్ (₹)",
        "example": 'ఉదా: "ninna tea 20, auto 80, lunch 150, Ravi ki 500 appu ichanu"',
        "privacy": "🔒 మీ స్వరం ఖర్చులను లెక్కించడానికి మాత్రమే ఉపయోగించబడుతుంది.",
        "empty_msg": "ఇంకా ఏమీ నమోదు కాలేదు. మైక్ నొక్కి మాట్లాడండి లేదా కింద టైప్ చేయండి.",
        "success_toast": "ఖర్చులు విజయవంతంగా సేవ్ అయ్యాయి!",
        "undo": "↩ చివరి సేవ్ రద్దు చేయండి",
        "download": "CSV డౌన్‌లోడ్",
        "clear_all": "డేటా క్లియర్ చేయండి",
        "udhar_header": "వాయిస్ ఉధార్ / ఖాతా",
        "ask_header": "స్వరం ద్వారా అడగండి",
        "ask_example": 'ఉదా: "ఈ నెల ఎంత ఖర్చు అయింది?", "టీ కి ఎంత పోయింది?", "బడ్జెట్ ఎంత మిగిలింది?"',
        "type_header": "టైప్ చేసి ఖర్చు జోడించండి",
        "type_placeholder": 'ఉదా: "ninna tea 20, auto 80, lunch 150"',
        "one_tap": "ఒక్క ట్యాప్‌తో జోడించండి",
        "history_header": "ఖర్చుల చరిత్ర",
        "insight_header": "వారపు విశ్లేషణ",
        "settle": "చెల్లించారు",
        "pending": "పెండింగ్",
        "settled": "పూర్తయింది",
        "no_voice": "వాయిస్ కోసం GNANI_API_KEY కావాలి. అంతవరకు టైప్ చేసి ఖర్చు జోడించవచ్చు.",
        "tabs": ["🎙️ మాట్లాడండి", "⌨️ టైప్", "📒 ఖాతా", "📊 విశ్లేషణ", "📜 చరిత్ర", "🗣️ అడగండి"],
    },
    "en-IN": {
        "title": "Awaaz Kharcha",
        "subtitle": "Say what you spent. We write it down.",
        "speak": "Tap & speak, or drop a WhatsApp voice note",
        "heard": "What I heard",
        "save": "Save expenses",
        "today": "Today's spend",
        "month": "This month",
        "week": "Last 7 days",
        "avg_day": "Avg / day",
        "budget_left": "Budget left",
        "safe_today": "Safe to spend today",
        "budget_target": "Monthly budget (₹)",
        "example": 'Try: "kal chai 20, auto 80, lunch dedh sau, lent 500 to Ravi"',
        "privacy": "🔒 Your voice is only used to log expenses.",
        "empty_msg": "Nothing yet. Tap the mic, type below, or use a one-tap chip.",
        "success_toast": "Expenses saved!",
        "undo": "↩ Undo last save",
        "download": "Download CSV",
        "clear_all": "Clear all data",
        "udhar_header": "Udhar / Khata ledger",
        "ask_header": "Ask by voice or text",
        "ask_example": 'Try: "how much did I spend this month?", "how much on chai?", "how much budget left?"',
        "type_header": "Type an expense",
        "type_placeholder": 'Try: "kal chai 20, auto 80, lunch dedh sau"',
        "one_tap": "One-tap logging",
        "history_header": "Expense history",
        "insight_header": "Weekly insight",
        "settle": "Mark settled",
        "pending": "Pending",
        "settled": "Settled",
        "no_voice": "Add GNANI_API_KEY to .env for voice input. Typing and one-tap logging work now.",
        "tabs": ["🎙️ Speak", "⌨️ Type", "📒 Khata", "📊 Insights", "📜 History", "🗣️ Ask"],
    },
}

CATEGORY_CHOICES = EXPENSE_CATEGORIES

#: Chrome that used to be English-only, now translated for every language.
EXTRA = {
    "hi-IN": {
        "settings": "सेटिंग्स", "export": "एक्सपोर्ट", "expenses_csv": "खर्च CSV",
        "backup_json": "पूरा बैकअप (JSON)", "restore_header": "बैकअप वापस लाएँ",
        "restore_hint": "पहले JSON बैकअप चुनिए, फिर तय कीजिए।",
        "restore_preview": "इस बैकअप में हैं", "restore_replaces": "वापस लाने पर इस डिवाइस का मौजूदा डेटा बदल जाएगा।",
        "restore_confirm": "मेरा डेटा इस बैकअप से बदल दो", "restore_now": "वापस लाएँ",
        "restore_done": "बैकअप वापस आ गया", "danger": "खतरनाक ज़ोन",
        "danger_hint": "इस डिवाइस के सारे खर्च और खाता एंट्री हट जाएँगे।",
        "danger_confirm": "समझ गया, सब हटा दो", "cleared": "सारा डेटा हट गया",
        "manual_header": "एक एंट�्री हाथ से जोड़ें (सही रकम, कोई भी तारीख)",
        "what": "क्या खरीदा?", "amount": "रकम (₹)", "category": "श्रेणी",
        "date": "तारीख", "add_expense": "खर्च जोड़ें",
        "need_desc": "नाम और शून्य से ज़्यादा रकम भरिए।",
        "owe_me": "मुझे मिलने हैं", "i_owe": "मुझे देने हैं", "people_pending": "लोग बाकी",
        "all_entries": "सारी एंट्री", "add_khata": "खाता एंट्री जोड़ें", "person": "किसका नाम",
        "type": "तरह", "add_entry": "एंट्री जोड़ें", "need_khata": "नाम और रकम भरिए।",
        "paid": "चुका दिया", "remaining": "बाकी", "record_payment": "भुगतान दर्ज करें",
        "payment_amount": "भुगतान (₹)", "need_payment": "पहले भुगतान की रकम भरिए।",
        "pick_one": "भुगतान के लिए एक ही एंट्री चुनिए।", "edit_entry": "एंट्री सुधारें",
        "save_edits": "बदलाव सेव करें", "updated": "बदलाव सेव हो गए", "delete": "हटाएँ",
        "deleted": "हटा दिया", "settled_toast": "भुगतान हो गया", "reopen_toast": "फिर बाकी में डाल दिया",
        "view_month": "कौन सा महीना", "this_month": "यह महीना", "last_14": "पिछले 14 दिन",
        "by_category": "श्रेणी के हिसाब से खर्च", "top_items": "सबसे बड़े खर्च",
        "patterns": "पैटर्न", "streak": "लगातार दिन", "no_items": "इस महीने अभी कुछ नहीं।",
        "month_filter": "महीना", "search_item": "नाम खोजें", "all_option": "सब",
        "delete_selected": "चुनी हुई हटाएँ", "entries": "एंट्री",
        "no_match": "इन फ़िल्टर से कुछ नहीं मिला।", "you_asked": "आपने पूछा",
        "ask_placeholder": "इस महीने कितना खर्च हुआ?",
    },
    "te-IN": {
        "settings": "సెట్టింగ్‌లు", "export": "ఎక్స్‌పోర్ట్", "expenses_csv": "ఖర్చుల CSV",
        "backup_json": "పూర్తి బ్యాకప్ (JSON)", "restore_header": "బ్యాకప్ తిరిగి తీసుకోండి",
        "restore_hint": "మొదట JSON బ్యాకప్ ఎంచుకోండి, తరువాత నిర్ణయించండి.",
        "restore_preview": "ఈ బ్యాకప్‌లో ఉన్నవి", "restore_replaces": "తిరిగి తీసుకుంటే ఈ పరికరంలోని డేటా మారిపోతుంది.",
        "restore_confirm": "నా డేటాను ఈ బ్యాకప్‌తో మార్చండి", "restore_now": "తిరిగి తీసుకోండి",
        "restore_done": "బ్యాకప్ తిరిగి వచ్చింది", "danger": "ప్రమాద ప్రాంతం",
        "danger_hint": "ఈ పరికరంలోని అన్ని ఖర్చులు, ఖాతా ఎంట్రీలు తొలగిపోతాయి.",
        "danger_confirm": "అర్థమైంది, అన్నీ తొలగించండి", "cleared": "డేటా తొలగించబడింది",
        "manual_header": "ఒక ఎంట్రీని చేతితో జోడించండి (ఖచ్చితమైన మొత్తం, ఏ తారీఖు అయినా)",
        "what": "ఏమి కొన్నారు?", "amount": "మొత్తం (₹)", "category": "వర్గం",
        "date": "తారీఖు", "add_expense": "ఖర్చు జోడించండి",
        "need_desc": "పేరు మరియు సున్నా కంటే ఎక్కువ మొత్తం ఇవ్వండి.",
        "owe_me": "నాకు రావాల్సినవి", "i_owe": "నేను ఇవ్వాల్సినవి", "people_pending": "మంది పెండింగ్",
        "all_entries": "అన్ని ఎంట్రీలు", "add_khata": "ఖాతా ఎంట్రీ జోడించండి", "person": "ఎవరు",
        "type": "రకం", "add_entry": "ఎంట్రీ జోడించండి", "need_khata": "పేరు మరియు మొత్తం ఇవ్వండి.",
        "paid": "చెల్లించినది", "remaining": "మిగిలినది", "record_payment": "చెల్లింపు నమోదు చేయండి",
        "payment_amount": "చెల్లింపు (₹)", "need_payment": "మొదట చెల్లింపు మొత్తం ఇవ్వండి.",
        "pick_one": "చెల్లింపు కోసం ఒక ఎంట్రీ మాత్రమే ఎంచుకోండి.", "edit_entry": "ఎంట్రీ సవరించండి",
        "save_edits": "మార్పులు సేవ్ చేయండి", "updated": "మార్పులు సేవ్ అయ్యాయి", "delete": "తొలగించండి",
        "deleted": "తొలగించబడింది", "settled_toast": "చెల్లించినట్టు గుర్తించారు", "reopen_toast": "మళ్ళీ పెండింగ్‌లో ఉంది",
        "view_month": "ఏ నెల", "this_month": "ఈ నెల", "last_14": "గత 14 రోజులు",
        "by_category": "వర్గం ప్రకారం ఖర్చు", "top_items": "ఎక్కువ ఖర్చైనవి",
        "patterns": "నమూనాలు", "streak": "వరుస రోజులు", "no_items": "ఈ నెలలో ఇంకా ఏమీ లేదు.",
        "month_filter": "నెల", "search_item": "పేరు వెతకండి", "all_option": "అన్నీ",
        "delete_selected": "ఎంచుకున్నవి తొలగించండి", "entries": "ఎంట్రీలు",
        "no_match": "ఈ ఫిల్టర్లకు ఏమీ దొరకలేదు.", "you_asked": "మీరు అడిగింది",
        "ask_placeholder": "ఈ నెల ఎంత ఖర్చు అయింది?",
    },
    "en-IN": {
        "settings": "Settings", "export": "Export", "expenses_csv": "Expenses CSV",
        "backup_json": "Full backup (JSON)", "restore_header": "Restore a backup",
        "restore_hint": "Pick a JSON backup first, then confirm.",
        "restore_preview": "This backup holds", "restore_replaces": "Restoring replaces the data already on this device.",
        "restore_confirm": "Replace my data with this backup", "restore_now": "Restore now",
        "restore_done": "Backup restored", "danger": "Danger zone",
        "danger_hint": "Deletes every expense and khata entry on this device.",
        "danger_confirm": "I understand, clear everything", "cleared": "All data cleared",
        "manual_header": "Add one entry manually (exact amount, any date)",
        "what": "What was it?", "amount": "Amount (₹)", "category": "Category",
        "date": "Date", "add_expense": "Add expense",
        "need_desc": "Add a description and an amount above zero.",
        "owe_me": "They owe me", "i_owe": "I owe them", "people_pending": "People pending",
        "all_entries": "All entries", "add_khata": "Add khata entry", "person": "Person",
        "type": "Type", "add_entry": "Add entry", "need_khata": "Add a name and an amount.",
        "paid": "Paid", "remaining": "Remaining", "record_payment": "Record payment",
        "payment_amount": "Payment (₹)", "need_payment": "Enter a payment amount first.",
        "pick_one": "Pick a single entry to record a payment against.", "edit_entry": "Edit an entry",
        "save_edits": "Save edits", "updated": "Edits saved", "delete": "Delete",
        "deleted": "Deleted", "settled_toast": "Marked as settled", "reopen_toast": "Back to pending",
        "view_month": "Month", "this_month": "This month", "last_14": "Last 14 days",
        "by_category": "Spending by category", "top_items": "Top items",
        "patterns": "Patterns", "streak": "Logging streak", "no_items": "No items yet this month.",
        "month_filter": "Month", "search_item": "Search item", "all_option": "All",
        "delete_selected": "Delete selected", "entries": "entries",
        "no_match": "No entries match these filters.", "you_asked": "You asked",
        "ask_placeholder": "is mahine kitna kharch hua?",
    },
}

QUICK_CHIPS = [
    ("🍵 Chai", 20.0, "Food"),
    ("🛺 Auto", 80.0, "Travel"),
    ("🍱 Lunch", 150.0, "Food"),
    ("💡 Recharge", 299.0, "Bills"),
    ("📚 Xerox", 30.0, "Education"),
    ("🥬 Sabzi", 60.0, "Groceries"),
]

st.set_page_config(page_title="Awaaz Kharcha", page_icon="🎙️", layout="centered")

st.markdown(
    """
<style>
.block-container { max-width: 780px; padding-top: 1.1rem; padding-bottom: 3rem; }
html, body, [class*="css"] { font-size: 17px; }
.stButton > button, .stDownloadButton > button {
    min-height: 50px; font-size: 1.02rem; font-weight: 600; border-radius: 14px;
}
.st-key-mic, .st-key-ask_mic {
    background: #FFFFFF; border: 2px dashed #0F766E; border-radius: 18px;
    padding: 14px; margin: 8px 0 6px 0; box-shadow: 0 4px 12px rgba(15, 118, 110, 0.08);
}
[data-testid="stMetricValue"] { font-size: 1.75rem; font-weight: 800; color: #0F766E; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.hero {
    background: linear-gradient(135deg, #0F766E 0%, #115E59 100%);
    color: #FFFFFF; border-radius: 20px; padding: 22px 26px; margin: 6px 0 14px 0;
    box-shadow: 0 8px 24px rgba(15, 118, 110, 0.25);
}
.hero-label { font-size: 0.95rem; opacity: 0.9; font-weight: 600; letter-spacing: 0.02em; }
.hero-value { font-size: 2.9rem; font-weight: 800; line-height: 1.05; margin: 2px 0 6px 0; }
.hero-sub { font-size: 1rem; opacity: 0.95; font-weight: 500; }
.hero-sub b { font-weight: 800; }
.insight-card {
    background: #F1EADF; border-left: 4px solid #0F766E; padding: 12px 16px;
    border-radius: 10px; margin: 10px 0; font-size: 0.97rem; color: #1F2937;
}
.budget-badge {
    background: #FEF3C7; border: 1px solid #F59E0B; padding: 10px 14px;
    border-radius: 10px; margin: 10px 0; font-size: 0.92rem; color: #92400E;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_store() -> Store:
    return Store(config.db_path())


store = get_store()

# ---------------- HEADER ----------------
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(
        "<h2 style='margin:0; font-weight:800; color:#0F766E;'>🎙️ Awaaz Kharcha</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Say what you spent. We write it down. Powered by Gnani Prisma.")
with col_h2:
    with st.popover("ℹ️ Help"):
        st.markdown(
            """
            **What you can say**
            - `aaj chai 20, auto 80, lunch dedh sau` — one breath, many expenses
            - `kal metro 40` — backdate with *kal* / *parso* / *yesterday*
            - `Ravi ko 500 udhar diya` — khata entry, settle it later
            - `is mahine kitna kharch hua?` — ask by voice
            - `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) all work

            **Tips**
            - Edit the transcript before saving if Prisma mishears a number.
            - Everything is stored locally in SQLite; export any time from the sidebar.
            """
        )

lang_choice = st.segmented_control(
    "Language",
    options=list(config.LANGUAGES.keys()),
    default=config.DEFAULT_LANGUAGE,
    label_visibility="collapsed",
) or config.DEFAULT_LANGUAGE
lang_code = config.LANGUAGES.get(lang_choice, "hi-IN")
T = {**UI[lang_code], **EXTRA.get(lang_code, {})}
voice_ready = config.api_key_configured()

expenses_df = store.expenses()
udhar_df = store.udhar()

# ---------------- SIDEBAR: SETTINGS, DATA ----------------
with st.sidebar:
    st.markdown(f"### ⚙️ {T['settings']}")
    budget_value = store.get_budget()
    new_budget = st.number_input(
        T["budget_target"],
        min_value=0,
        max_value=1_000_000,
        value=int(budget_value),
        step=500,
        key="budget_input",
    )
    if int(new_budget) != int(budget_value):
        store.set_budget(new_budget)
        budget_value = float(new_budget)

    stats = insights.summary(expenses_df)
    if stats["count"]:
        st.caption(f"📦 {stats['count']} expenses · 📒 {len(udhar_df)} khata entries")

    st.divider()
    st.markdown(f"### 📤 {T['export']}")
    st.download_button(
        f"⬇️ {T['expenses_csv']}",
        data=store.export_csv(),
        file_name=f"awaaz_kharcha_{dt.date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=expenses_df.empty,
    )
    st.download_button(
        f"⬇️ {T['backup_json']}",
        data=store.export_json(),
        file_name=f"awaaz_kharcha_backup_{dt.date.today().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
        disabled=expenses_df.empty and udhar_df.empty,
    )

    with st.expander(f"♻️ {T['restore_header']}"):
        st.caption(T["restore_hint"])
        backup_file = st.file_uploader(
            T["backup_json"], type=["json"], key="restore_file", label_visibility="collapsed"
        )
        if backup_file is not None:
            raw = backup_file.getvalue().decode("utf-8", errors="replace")
            try:
                preview = store.backup_preview(raw)
            except ValueError as exc:
                st.error(str(exc))
            else:
                span = f"{preview['first']} → {preview['last']}" if preview["first"] else "—"
                st.caption(
                    f"{T['restore_preview']} {preview['expenses']} {T['entries']} ({span}), "
                    f"{preview['udhar']} khata · {insights.inr(preview['budget'])}"
                )
                st.warning(T["restore_replaces"])
                if st.checkbox(T["restore_confirm"], key="confirm_restore"):
                    if st.button(T["restore_now"], type="primary", use_container_width=True):
                        restored = store.restore_json(raw)
                        st.toast(f"{T['restore_done']}: {restored[0]} + {restored[1]}", icon="♻️")
                        st.rerun()

    st.divider()
    with st.expander(f"🗑️ {T['danger']}"):
        st.caption(T["danger_hint"])
        confirm = st.checkbox(T["danger_confirm"], key="confirm_clear")
        if st.button(T["clear_all"], disabled=not confirm, use_container_width=True):
            store.clear_all()
            st.session_state.pop("last_saved_ids", None)
            st.session_state.pop("last_saved_udhar_ids", None)
            st.toast(T["cleared"], icon="🗑️")
            st.rerun()

    st.caption(f"DB: {DATA_FILE}")

# ---------------- DASHBOARD HEADER NUMBERS ----------------
today = dt.date.today()
stats = insights.summary(expenses_df, today)
budget = store.get_budget()
budget_info = insights.budget_status(stats["month"], budget, today)

hero_sub = f"{T['month']}: <b>{insights.inr(stats['month'])}</b>"
if budget > 0:
    hero_sub += f" &nbsp;·&nbsp; {T['budget_left']}: <b>{insights.inr(max(budget_info['remaining'], 0))}</b>"
st.markdown(
    f"""
    <div class="hero">
      <div class="hero-label">{T['today']}</div>
      <div class="hero-value">{insights.inr(stats['today'])}</div>
      <div class="hero-sub">{hero_sub}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if stats["count"] == 0 and udhar_df.empty:
    st.info(T["empty_msg"])

m1, m2, m3 = st.columns(3)
m1.metric(T["week"], insights.inr(stats["week"]))
m2.metric(
    T["avg_day"],
    insights.inr(stats["avg_per_day"]),
    help="Average spend per elapsed day this month",
)
if budget > 0:
    m3.metric(T["safe_today"], insights.inr(budget_info["per_day"]))
else:
    m3.metric(T["month"], insights.inr(stats["month"]))

if not voice_ready:
    st.info(T["no_voice"])


def save_rows(rows: list[dict], udhar_rows: list[dict], source: str) -> None:
    """Persist parsed rows and remember the ids so the user can undo."""
    expense_ids = store.add_expenses(rows, source=source) if rows else []
    udhar_ids = store.add_udhar(udhar_rows) if udhar_rows else []
    st.session_state["last_saved_ids"] = expense_ids
    st.session_state["last_saved_udhar_ids"] = udhar_ids
    # Widget keys cannot be cleared after they are created, so flag it for the
    # next run, where the reset happens before any widget is instantiated.
    st.session_state["clear_entry"] = True
    st.toast(T["success_toast"], icon="👍")
    st.rerun()


def render_parsed(rows: list[dict], udhar_rows: list[dict]) -> None:
    if rows:
        st.markdown("##### 🛒 Personal expenses")
        preview = pd.DataFrame(rows)
        preview["amount"] = preview["amount"].map(insights.inr)
        preview["category"] = preview["category"].map(lambda c: f"{CAT_EMOJI.get(c, '📦')} {c}")
        st.dataframe(
            preview.rename(columns={"date": "date", "item": "item", "amount": "amount"}),
            use_container_width=True,
            hide_index=True,
        )
    if udhar_rows:
        st.markdown("##### 🤝 Khata entries")
        preview = pd.DataFrame(udhar_rows)
        preview["amount"] = preview["amount"].map(insights.inr)
        st.dataframe(preview, use_container_width=True, hide_index=True)


def review_block(widget_key: str, source: str) -> None:
    """Editable transcript review + save, shared by the voice flows."""
    if not st.session_state.get(widget_key, "").strip():
        return
    st.markdown(f"#### 📝 {T['heard']}")
    edited = st.text_area("Transcript", height=90, key=widget_key, label_visibility="collapsed")
    rows, udhar_rows = parse_expenses(edited, today)

    if not rows and not udhar_rows:
        st.warning("I could not catch an amount. Try 'chai 20' or 'dedh sau (150)'.")
        return

    render_parsed(rows, udhar_rows)
    col_save, col_redo = st.columns([3, 1])
    if col_save.button(
        f"✅ {T['save']} ({len(rows) + len(udhar_rows)})",
        type="primary",
        key=f"{widget_key}_save",
        use_container_width=True,
    ):
        save_rows(rows, udhar_rows, source)
    if col_redo.button("↩ Redo", key=f"{widget_key}_redo", use_container_width=True):
        st.session_state["clear_entry"] = True
        st.rerun()


# Apply a pending reset before any of the affected widgets are created.
if st.session_state.pop("clear_entry", False):
    for _key in ("transcript", "voice_text", "typed_text", "last_audio"):
        st.session_state.pop(_key, None)

tabs = st.tabs(T["tabs"])

# ---------------- TAB 1: VOICE ----------------
with tabs[0]:
    st.markdown(f"#### 🎙️ {T['speak']}")
    audio = st.audio_input("Record your expenses", key="mic", label_visibility="collapsed")
    with st.expander("📲 Or forward a WhatsApp voice note (OGG, M4A, MP3, WAV)"):
        upload = st.file_uploader(
            "Upload audio",
            type=["ogg", "opus", "oga", "m4a", "mp3", "wav", "aac", "flac"],
            label_visibility="collapsed",
        )

    active_audio = audio or upload
    if active_audio is not None and voice_ready:
        payload = active_audio.getvalue()
        digest = hashlib.md5(payload).hexdigest()
        if st.session_state.get("last_audio") != digest:
            try:
                with st.spinner("Understanding your voice with Gnani Prisma..."):
                    label = getattr(active_audio, "name", "") or getattr(active_audio, "type", "")
                    heard = transcribe(payload, label, lang_code)
                st.session_state["voice_text"] = heard
                st.session_state["last_audio"] = digest
            except SttError as exc:
                st.session_state["last_audio"] = digest
                st.session_state["voice_text"] = ""
                st.warning("I could not hear that clearly. Please try again a little closer to the mic.")
                with st.expander("Technical details"):
                    st.code(str(exc))

    if st.session_state.get("voice_text"):
        review_block("voice_text", "voice")
    else:
        st.caption(f"💡 {T['example']}")
    st.caption(T["privacy"])

# ---------------- TAB 2: TYPE / QUICK ADD ----------------
with tabs[1]:
    st.markdown(f"#### ⌨️ {T['type_header']}")
    typed = st.text_area(
        "Type expenses",
        placeholder=T["type_placeholder"],
        height=100,
        key="typed_text",
        label_visibility="collapsed",
    )
    if typed.strip():
        rows, udhar_rows = parse_expenses(typed, today)
        if rows or udhar_rows:
            render_parsed(rows, udhar_rows)
            if st.button(
                f"✅ {T['save']} ({len(rows) + len(udhar_rows)})",
                type="primary",
                key="typed_save",
                use_container_width=True,
            ):
                save_rows(rows, udhar_rows, "typed")
        else:
            st.warning("I could not catch an amount. Try 'chai 20' or 'dedh sau (150)'.")

    st.divider()
    st.markdown(f"##### ⚡ {T['one_tap']}")
    chip_cols = st.columns(3)
    for index, (label, amount, category) in enumerate(QUICK_CHIPS):
        if chip_cols[index % 3].button(
            f"{label} · {insights.inr(amount)}", key=f"chip_{index}", use_container_width=True
        ):
            ids = store.add_expenses(
                [
                    {
                        "date": today.isoformat(),
                        "item": label.split(" ", 1)[1],
                        "amount": amount,
                        "category": category,
                    }
                ],
                source="quick",
            )
            st.session_state["last_saved_ids"] = ids
            st.toast(f"{label} added", icon="⚡")
            st.rerun()

    st.divider()
    with st.expander(f"➕ {T['manual_header']}"):
        with st.form("manual_entry", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            item = c1.text_input(T["what"], placeholder="Chai, auto, medicine...")
            amount = c2.number_input(T["amount"], min_value=0.0, step=10.0, format="%.2f")
            c3, c4 = st.columns([1, 1])
            category = c3.selectbox(
                T["category"], CATEGORY_CHOICES, index=CATEGORY_CHOICES.index("Other")
            )
            entry_date = c4.date_input(T["date"], value=today)
            submitted = st.form_submit_button(
                T["add_expense"], type="primary", use_container_width=True
            )
            if submitted:
                if item.strip() and amount > 0:
                    ids = store.add_expenses(
                        [
                            {
                                "date": entry_date.isoformat(),
                                "item": item.strip(),
                                "amount": amount,
                                "category": category,
                            }
                        ],
                        source="manual",
                    )
                    st.session_state["last_saved_ids"] = ids
                    st.toast(T["add_expense"], icon="✅")
                    st.rerun()
                else:
                    st.warning(T["need_desc"])

# ---------------- TAB 3: KHATA ----------------
with tabs[2]:
    st.markdown(f"#### 📒 {T['udhar_header']}")
    current_udhar = store.udhar()
    pending = current_udhar[current_udhar["status"] == "Pending"] if not current_udhar.empty else current_udhar

    if not pending.empty:
        lent = pending.loc[pending["type"].astype(str).str.contains("Lent", na=False), "amount"].sum()
        taken = pending["amount"].sum() - lent
        k1, k2, k3 = st.columns(3)
        k1.metric("They owe me", insights.inr(lent))
        k2.metric("I owe them", insights.inr(taken))
        k3.metric("People pending", int(pending["person"].nunique()))
        st.dataframe(
            pending.assign(amount=pending["amount"].map(insights.inr))[
                ["date", "person", "amount", "type", "status"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No pending khata entries. Say 'Ravi ko 500 udhar diya' or add one below.")

    with st.expander("➕ Add khata entry"):
        with st.form("khata_form", clear_on_submit=True):
            p1, p2 = st.columns([2, 1])
            person = p1.text_input("Person", placeholder="Ravi")
            khata_amount = p2.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%.0f")
            p3, p4 = st.columns([1, 1])
            entry_type = p3.selectbox("Type", ["Lent (Diya)", "Borrowed (Liya)"])
            khata_date = p4.date_input("Date", value=today, key="khata_date")
            add_khata = st.form_submit_button("Add entry", type="primary", use_container_width=True)
            if add_khata:
                if person.strip() and khata_amount > 0:
                    ids = store.add_udhar(
                        [
                            {
                                "date": khata_date.isoformat(),
                                "person": person.strip(),
                                "amount": khata_amount,
                                "type": entry_type,
                                "status": "Pending",
                            }
                        ]
                    )
                    st.session_state["last_saved_udhar_ids"] = ids
                    st.toast("Khata entry added", icon="✅")
                    st.rerun()
                else:
                    st.warning("Add a name and an amount above zero.")

    if not current_udhar.empty:
        st.markdown("##### All entries")
        ledger = current_udhar.copy()
        ledger.insert(0, "select", False)
        edited_ledger = st.data_editor(
            ledger[["select", "id", "date", "person", "amount", "type", "status"]],
            hide_index=True,
            use_container_width=True,
            disabled=["id", "date", "person", "amount", "type", "status"],
            column_config={
                "select": st.column_config.CheckboxColumn("✓", width="small"),
                "id": st.column_config.NumberColumn("ID", width="small"),
                "amount": st.column_config.NumberColumn("Amount", format="₹%.0f"),
            },
            key="ledger_editor",
        )
        selected = [int(i) for i in edited_ledger.loc[edited_ledger["select"] == True, "id"]]
        b1, b2, b3 = st.columns(3)
        if b1.button(f"✅ {T['settle']}", disabled=not selected, use_container_width=True):
            store.set_udhar_status(selected, "Settled")
            st.toast("Marked as settled", icon="✅")
            st.rerun()
        if b2.button("↩ " + T["pending"], disabled=not selected, use_container_width=True):
            store.set_udhar_status(selected, "Pending")
            st.toast("Back to pending", icon="↩")
            st.rerun()
        if b3.button("🗑️ Delete", disabled=not selected, use_container_width=True):
            store.delete_udhar(selected)
            st.toast("Deleted", icon="🗑️")
            st.rerun()

# ---------------- TAB 4: INSIGHTS ----------------
with tabs[3]:
    st.markdown(f"#### 📊 {T['insight_header']}")
    if expenses_df.empty:
        st.info(T["empty_msg"])
    else:
        st.markdown(
            f'<div class="insight-card">{insights.weekly_insight(expenses_df, today)}</div>',
            unsafe_allow_html=True,
        )

        if budget > 0:
            st.progress(min(1.0, max(0.0, budget_info["pct"] / 100)))
            st.caption(
                f"{insights.inr(stats['month'])} of {insights.inr(budget)} used "
                f"({budget_info['pct']:.0f}%) · {budget_info['days_left']} days left · "
                f"{insights.inr(budget_info['per_day'])}/day keeps you inside the budget"
            )
            if budget_info["level"] == "over":
                st.markdown(
                    f'<div class="budget-badge" style="background:#FEE2E2; border-color:#EF4444; '
                    f'color:#B91C1C;">⚠️ Over budget by '
                    f"{insights.inr(abs(budget_info['remaining']))}. Time to slow down.</div>",
                    unsafe_allow_html=True,
                )
            elif budget_info["level"] in ("alert", "nudge"):
                icon = "⚠️" if budget_info["level"] == "alert" else "🔔"
                st.markdown(
                    f'<div class="budget-badge">{icon} You have used '
                    f"{budget_info['pct']:.0f}% of your monthly budget with "
                    f"{budget_info['days_left']} days still to go.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption(f"💚 You are on track — {insights.inr(budget_info['remaining'])} spare this month.")

        delta = stats["delta_pct"]
        if stats["prev_month"] > 0:
            arrow = "📈" if delta > 0 else "📉"
            st.caption(
                f"{arrow} {abs(delta):.0f}% {'more' if delta > 0 else 'less'} than last month "
                f"({insights.inr(stats['prev_month'])} then vs {insights.inr(stats['month'])} now)."
            )

        st.markdown("##### 📈 Last 14 days")
        st.line_chart(insights.daily_totals(expenses_df, 14, today), color="#0F766E", height=200)

        cat_totals = insights.category_totals(expenses_df, today)
        if not cat_totals.empty:
            st.markdown("##### 🏷️ Spending by category (this month)")
            st.bar_chart(cat_totals, color="#0F766E", height=220)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("##### 💸 Top items this month")
            best = insights.top_items(expenses_df, 5, today)
            if best.empty:
                st.caption("No items yet this month.")
            else:
                st.dataframe(
                    best.assign(amount=best["amount"].map(insights.inr)).rename(
                        columns={"item": "Item", "amount": "Total", "count": "Times"}
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
        with col_b:
            st.markdown("##### 🗓️ Patterns")
            pattern = insights.weekday_insight(expenses_df, today)
            st.write(pattern or "Log a few more days to reveal your weekly pattern.")
            streak = insights.logging_streak(expenses_df, today)
            st.metric("Logging streak", f"{streak} day{'s' if streak != 1 else ''}")

# ---------------- TAB 5: HISTORY ----------------
with tabs[4]:
    st.markdown(f"#### 📜 {T['history_header']}")
    all_expenses = store.expenses()
    if all_expenses.empty:
        st.info(T["empty_msg"])
    else:
        working = all_expenses.copy()
        working["date"] = pd.to_datetime(working["date"])
        months = sorted(working["date"].dt.strftime("%Y-%m"), reverse=True)
        f1, f2, f3 = st.columns([1, 1, 1])
        month_pick = f1.selectbox("Month", ["All"] + months)
        category_pick = f2.multiselect("Category", CATEGORY_CHOICES)
        search = f3.text_input("Search item", placeholder="chai")

        view = working
        if month_pick != "All":
            view = view[view["date"].dt.strftime("%Y-%m") == month_pick]
        if category_pick:
            view = view[view["category"].isin(category_pick)]
        if search.strip():
            view = view[view["item"].str.contains(search.strip(), case=False, regex=False)]

        st.caption(f"{len(view)} entries · {insights.inr(view['amount'].sum())}")

        if view.empty:
            st.info("No entries match these filters.")
        else:
            editable = view[["id", "date", "item", "amount", "category", "source"]].copy()
            editable["date"] = editable["date"].dt.date
            editable.insert(0, "select", False)
            original = editable.set_index("id")

            edited = st.data_editor(
                editable,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "select": st.column_config.CheckboxColumn("✓", width="small"),
                    "id": st.column_config.NumberColumn("ID", width="small", disabled=True),
                    "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                    "amount": st.column_config.NumberColumn("Amount", format="₹%.0f", min_value=0.0),
                    "category": st.column_config.SelectboxColumn("Category", options=CATEGORY_CHOICES),
                    "source": st.column_config.TextColumn("Via", disabled=True, width="small"),
                },
                key="history_editor",
            )

            selected_rows = [int(i) for i in edited.loc[edited["select"] == True, "id"]]
            c1, c2 = st.columns(2)
            if c1.button("💾 Save edits", type="primary", use_container_width=True):
                changed = 0
                for row in edited.to_dict("records"):
                    before = original.loc[row["id"]]
                    updates = {}
                    if str(row["date"]) != str(before["date"]):
                        updates["date"] = str(row["date"])
                    if str(row["item"]) != str(before["item"]):
                        updates["item"] = str(row["item"])
                    if round(float(row["amount"]), 2) != round(float(before["amount"]), 2):
                        updates["amount"] = float(row["amount"])
                    if row["category"] != before["category"]:
                        updates["category"] = row["category"]
                    if updates:
                        store.update_expense(int(row["id"]), **updates)
                        changed += 1
                st.toast(f"Updated {changed} entr{'y' if changed == 1 else 'ies'}", icon="💾")
                st.rerun()
            if c2.button("🗑️ Delete selected", disabled=not selected_rows, use_container_width=True):
                removed = store.delete_expenses(selected_rows)
                st.toast(f"Deleted {removed} entr{'y' if removed == 1 else 'ies'}", icon="🗑️")
                st.rerun()

# ---------------- TAB 6: ASK ----------------
with tabs[5]:
    st.markdown(f"#### {T['ask_header']}")
    st.caption(T["ask_example"])

    if "ask_pending" in st.session_state:
        st.session_state["ask_question"] = st.session_state.pop("ask_pending")

    ask_audio = st.audio_input("Ask a question", key="ask_mic", label_visibility="collapsed")
    if ask_audio is not None and voice_ready:
        payload = ask_audio.getvalue()
        digest = hashlib.md5(payload).hexdigest()
        if st.session_state.get("last_ask_audio") != digest:
            st.session_state["last_ask_audio"] = digest
            try:
                with st.spinner("Prisma is interpreting your question..."):
                    st.session_state["ask_question"] = transcribe(payload, "query.wav", lang_code)
            except SttError as exc:
                st.warning("Could not interpret that question. Try typing it below.")
                with st.expander("Technical details"):
                    st.code(str(exc))

    question = st.text_input(
        "Ask about your money",
        key="ask_question",
        placeholder="is mahine kitna kharch hua?",
        label_visibility="collapsed",
    )

    samples = [
        "is mahine kitna kharch hua?",
        "chai pe kitna gaya?",
        "budget kitna bacha?",
        "sabse mehnga kharch?",
    ]
    sample_cols = st.columns(2)
    for index, sample in enumerate(samples):
        if sample_cols[index % 2].button(sample, key=f"sample_q_{index}", use_container_width=True):
            st.session_state["ask_pending"] = sample
            st.rerun()

    if question.strip():
        st.markdown(f"**You asked:** *\"{question.strip()}\"*")
        answer = insights.answer_query(question, expenses_df, udhar_df, budget=budget, today=today)
        st.success(f"🤖 {answer}")

# ---------------- UNDO ----------------
last_ids = st.session_state.get("last_saved_ids") or []
last_udhar_ids = st.session_state.get("last_saved_udhar_ids") or []
if last_ids or last_udhar_ids:
    st.divider()
    if st.button(f"{T['undo']} ({len(last_ids) + len(last_udhar_ids)})", use_container_width=True):
        if last_ids:
            store.delete_expenses(last_ids)
        if last_udhar_ids:
            store.delete_udhar(last_udhar_ids)
        st.session_state["last_saved_ids"] = []
        st.session_state["last_saved_udhar_ids"] = []
        st.toast("Undone", icon="↩")
        st.rerun()
