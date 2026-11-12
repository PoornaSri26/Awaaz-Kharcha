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
from awaaz.parser import CAT_EMOJI, EXPENSE_CATEGORIES, parse_bank_sms, parse_expenses
from awaaz.store import Store
from awaaz.stt import SttError, transcribe_detailed

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
    "bn-IN": {
        "title": "আওয়াজ খরচা",
        "subtitle": "যা খরচ করলেন, শুধু বলুন। আমরা লিখে নেব।",
        "speak": "বলুন বা হোয়াটসঅ্যাপ ভয়েস নোট আপলোড করুন",
        "heard": "আমি যা শুনলাম",
        "save": "খরচ সেভ করুন",
        "today": "আজকের খরচ",
        "month": "এই মাসে",
        "week": "এই সপ্তাহে",
        "avg_day": "দৈনিক গড়",
        "budget_left": "বাজেট বাকি",
        "safe_today": "আজ নিরাপদ খরচ",
        "budget_target": "মাসিক বাজেট (₹)",
        "example": 'যেমন: "আজ চা ২০, অটো ৮০, দুপুরের খাবার দেড়শো, রবিকে ৫০০ ধার"',
        "privacy": "🔒 আপনার ভয়েস শুধু খরচ লেখার জন্য ব্যবহার হয়।",
        "empty_msg": "এখনও কিছু নেই। মাইক চেপে বলুন বা নিচে টাইপ করুন।",
        "success_toast": "খরচ সেভ হয়েছে!",
        "undo": "↩ শেষ সেভ ফিরিয়ে নিন",
        "download": "CSV ডাউনলোড",
        "clear_all": "সব ডেটা মুছুন",
        "udhar_header": "ধার / খাতা",
        "ask_header": "ভয়েসে জিজ্ঞাসা করুন",
        "ask_example": 'যেমন: "এই মাসে কত খরচ হল?", "চায়ে কত গেল?", "বাজেট কত বাকি?"',
        "type_header": "টাইপ করে খরচ যোগ করুন",
        "type_placeholder": 'যেমন: "আজ চা ২০, অটো ৮০"',
        "one_tap": "এক ট্যাপে যোগ করুন",
        "history_header": "খরচের ইতিহাস",
        "insight_header": "সাপ্তাহিক বিশ্লেষণ",
        "settle": "পরিশোধ হয়েছে",
        "pending": "বাকি",
        "settled": "পরিশোধিত",
        "no_voice": "ভয়েসের জন্য GNANI_API_KEY দরকার। ততক্ষণ টাইপ বা এক ট্যাপে যোগ করুন।",
        "tabs": ["🎙️ বলুন", "⌨️ লিখুন", "📒 খাতা", "📊 বিশ্লেষণ", "📜 ইতিহাস", "🗣️ জিজ্ঞাসা"],
    },
    "ta-IN": {
        "title": "ஆவாஸ் கர்ச்சா",
        "subtitle": "என்ன செலவு செய்தீர்கள், சொல்லுங்கள். நாங்கள் எழுதுகிறோம்.",
        "speak": "பேசுங்கள் அல்லது வாட்ஸ்அப் குரல் குறிப்பை பதிவேற்றுங்கள்",
        "heard": "நான் கேட்டது",
        "save": "செலவுகளை சேமி",
        "today": "இன்றைய செலவு",
        "month": "இந்த மாதம்",
        "week": "இந்த வாரம்",
        "avg_day": "நாள் சராசரி",
        "budget_left": "பட்ஜெட் மீதம்",
        "safe_today": "இன்று பாதுகாப்பான செலவு",
        "budget_target": "மாத பட்ஜெட் (₹)",
        "example": 'உதா: "இன்று டீ 20, ஆட்டோ 80, மதிய உணவு 150"',
        "privacy": "🔒 உங்கள் குரல் செலவு எழுத மட்டுமே பயன்படும்.",
        "empty_msg": "இன்னும் ஒன்றும் இல்லை. மைக்கை அழுத்தி பேசுங்கள் அல்லது கீழே தட்டச்சு செய்யுங்கள்.",
        "success_toast": "செலவுகள் சேமிக்கப்பட்டன!",
        "undo": "↩ கடைசி சேமிப்பை ரத்து செய்",
        "download": "CSV பதிவிறக்கம்",
        "clear_all": "எல்லா தரவையும் அழி",
        "udhar_header": "கடன் / கணக்கு",
        "ask_header": "குரல் மூலம் கேளுங்கள்",
        "ask_example": 'உதா: "இந்த மாதம் எவ்வளவு செலவு?", "டீக்கு எவ்வளவு போனது?", "பட்ஜெட் எவ்வளவு மீதம்?"',
        "type_header": "தட்டச்சு செய்து செலவு சேர்",
        "type_placeholder": 'உதா: "இன்று டீ 20, ஆட்டோ 80"',
        "one_tap": "ஒரு தட்டில் சேர்",
        "history_header": "செலவு வரலாறு",
        "insight_header": "வாராந்திர பகுப்பாய்வு",
        "settle": "தீர்ந்தது",
        "pending": "நிலுவை",
        "settled": "செலுத்தப்பட்டது",
        "no_voice": "குரலுக்கு GNANI_API_KEY தேவை. அதுவரை தட்டச்சு அல்லது ஒரு தட்டு பயன்படுத்துங்கள்.",
        "tabs": ["🎙️ பேசு", "⌨️ தட்டச்சு", "📒 கணக்கு", "📊 பகுப்பாய்வு", "📜 வரலாறு", "🗣️ கேள்"],
    },
    "kn-IN": {
        "title": "ಆವಾಜ್ ಖರ್ಚ",
        "subtitle": "ಏನು ಖರ್ಚು ಮಾಡಿದಿರಿ ಹೇಳಿ. ನಾವು ಬರೆದುಕೊಳ್ಳುತ್ತೇವೆ.",
        "speak": "ಮಾತನಾಡಿ ಅಥವಾ ವಾಟ್ಸಪ್ ಧ್ವನಿ ಟಿಪ್ಪಣಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "heard": "ನಾನು ಕೇಳಿದ್ದು",
        "save": "ಖರ್ಚುಗಳನ್ನು ಉಳಿಸಿ",
        "today": "ಇಂದಿನ ಖರ್ಚು",
        "month": "ಈ ತಿಂಗಳು",
        "week": "ಈ ವಾರ",
        "avg_day": "ದಿನದ ಸರಾಸರಿ",
        "budget_left": "ಬಡ್ಜೆಟ್ ಬಾಕಿ",
        "safe_today": "ಇಂದು ಸುರಕ್ಷಿತ ಖರ್ಚು",
        "budget_target": "ಮಾಸಿಕ ಬಡ್ಜೆಟ್ (₹)",
        "example": 'ಉದಾ: "ಇಂದು ಟೀ 20, ಆಟೋ 80, ಊಟ 150"',
        "privacy": "🔒 ನಿಮ್ಮ ಧ್ವನಿ ಖರ್ಚು ಬರೆಯಲು ಮಾತ್ರ ಬಳಸಲಾಗುತ್ತದೆ.",
        "empty_msg": "ಇನ್ನೂ ಏನೂ ಇಲ್ಲ. ಮೈಕ್ ಒತ್ತಿ ಮಾತನಾಡಿ ಅಥವಾ ಕೆಳಗೆ ಟೈಪ್ ಮಾಡಿ.",
        "success_toast": "ಖರ್ಚುಗಳು ಉಳಿಸಲಾಗಿವೆ!",
        "undo": "↩ ಕೊನೆಯ ಉಳಿಸುವಿಕೆ ರದ್ದುಮಾಡಿ",
        "download": "CSV ಡೌನ್‌ಲೋಡ್",
        "clear_all": "ಎಲ್ಲಾ ಡೇಟಾ ಅಳಿಸಿ",
        "udhar_header": "ಸಾಲ / ಖಾತೆ",
        "ask_header": "ಧ್ವನಿಯಿಂದ ಕೇಳಿ",
        "ask_example": 'ಉದಾ: "ಈ ತಿಂಗಳು ಎಷ್ಟು ಖರ್ಚು?", "ಟೀಗೆ ಎಷ್ಟು ಹೋಯಿತು?", "ಬಡ್ಜೆಟ್ ಎಷ್ಟು ಉಳಿದಿದೆ?"',
        "type_header": "ಟೈಪ್ ಮಾಡಿ ಖರ್ಚು ಸೇರಿಸಿ",
        "type_placeholder": 'ಉದಾ: "ಇಂದು ಟೀ 20, ಆಟೋ 80"',
        "one_tap": "ಒಂದೇ ಟ್ಯಾಪ್‌ನಲ್ಲಿ ಸೇರಿಸಿ",
        "history_header": "ಖರ್ಚಿನ ಇತಿಹಾಸ",
        "insight_header": "ವಾರದ ವಿಶ್ಲೇಷಣೆ",
        "settle": "ಪಾವತಿಯಾಗಿದೆ",
        "pending": "ಬಾಕಿ",
        "settled": "ಪೂರ್ಣವಾಗಿದೆ",
        "no_voice": "ಧ್ವನಿಗೆ GNANI_API_KEY ಬೇಕು. ಅಲ್ಲಿಯವರೆಗೆ ಟೈಪ್ ಅಥವಾ ಒಂದೇ ಟ್ಯಾಪ್ ಬಳಸಿ.",
        "tabs": ["🎙️ ಮಾತನಾಡಿ", "⌨️ ಟೈಪ್", "📒 ಖಾತೆ", "📊 ವಿಶ್ಲೇಷಣೆ", "📜 ಇತಿಹಾಸ", "🗣️ ಕೇಳಿ"],
    },
}

CATEGORY_CHOICES = EXPENSE_CATEGORIES

#: Display names for categories; the canonical English key is what gets stored.
CAT_LABELS = {
    "en-IN": {
        "Food": "Food", "Travel": "Travel", "Groceries": "Groceries", "Bills": "Bills",
        "Health": "Health", "Shopping": "Shopping", "Fun": "Fun",
        "Education": "Education", "Other": "Other",
    },
    "hi-IN": {
        "Food": "भोजन", "Travel": "सफ़र", "Groceries": "राशन", "Bills": "बिल",
        "Health": "सेहत", "Shopping": "खरीदारी", "Fun": "मज़ा",
        "Education": "पढ़ाई", "Other": "अन्य",
    },
    "te-IN": {
        "Food": "ఆహారం", "Travel": "ప్రయాణం", "Groceries": "సరుకులు", "Bills": "బిల్లులు",
        "Health": "ఆరోగ్యం", "Shopping": "షాపింగ్", "Fun": "వినోదం",
        "Education": "చదువు", "Other": "ఇతర",
    },
    "bn-IN": {
        "Food": "খাবার", "Travel": "যাতায়াত", "Groceries": "বাজার", "Bills": "বিল",
        "Health": "স্বাস্থ্য", "Shopping": "কেনাকাটা", "Fun": "বিনোদন",
        "Education": "পড়াশোনা", "Other": "অন্যান্য",
    },
    "ta-IN": {
        "Food": "உணவு", "Travel": "பயணம்", "Groceries": "மளிகை", "Bills": "பில்",
        "Health": "உடல்நலம்", "Shopping": "ஷாப்பிங்", "Fun": "பொழுதுபோக்கு",
        "Education": "கல்வி", "Other": "மற்றவை",
    },
    "kn-IN": {
        "Food": "ಆಹಾರ", "Travel": "ಪ್ರಯಾಣ", "Groceries": "ಸರಕು", "Bills": "ಬಿಲ್",
        "Health": "ಆರೋಗ್ಯ", "Shopping": "ಶಾಪಿಂಗ್", "Fun": "ಮನರಂಜನೆ",
        "Education": "ಶಿಕ್ಷಣ", "Other": "ಇತರೆ",
    },
}

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
        "dup_warn": "यह एंट्री अभी-अभी सेव हुई लगती है", "dup_confirm": "फिर भी सेव करें",
        "kind_label": "किस्म", "merchant_label": "दुकान/जगह", "mode_label": "भुगतान",
        "income_label": "आमदनी", "paid_by": "तरीका",
        "pace_note": "🔮 इस रफ़्तार से इस महीने {amount} तक पहुँच सकते हैं।",
        "cross_note": " बजट {date} के आसपास पार हो जाएगा।",
        "anomaly_header": "असामान्य खर्च",
        "anomaly_hint": "हर एंट्री अपनी श्रेणी के सामान्य खर्च से कम से कम 3 गुना है।",
        "sms_header": "बैंक SMS पेस्ट करें",
        "sms_hint": "जैसे: \"Rs 450 debited at Swiggy\" — यह एंट्री बन जाएगी।",
        "no_amount": "रकम नहीं मिली। 'chai 20' या 'dedh sau (150)' आज़माइए।",
        "personal_expenses": "मेरे खर्च", "khata_entries": "खाता एंट्री",
        "whatsapp_hint": "📲 या WhatsApp वॉइस नोट भेजिए (OGG, M4A, MP3, WAV)",
        "listening": "Gnani Prisma आपकी आवाज़ समझ रहा है...",
        "stt_failed": "ठीक से सुनाई नहीं दिया। माइक के थोड़ा पास बोलिए।",
        "technical": "तकनीकी जानकारी",
        "no_pending": "कोई बाकी खाता एंट्री नहीं। 'Ravi ko 500 udhar diya' कहिए या नीचे जोड़िए।",
        "khata_added": "खाता एंट्री जुड़ गई",
        "interpreting": "Prisma आपका सवाल समझ रहा है...",
        "ask_failed": "सवाल समझ नहीं आया। नीचे टाइप कीजिए।",
        "undone": "वापस लिया", "redo": "↩ फिर से",
        "budget_used": "{spent} / {budget} इस्तेमाल ({pct}%) · {days} दिन बाकी · रोज़ {per_day} में बजट के अंदर रहेंगे",
        "over_budget": "⚠️ बजट से {amount} ज़्यादा। अब थोड़ा रुकिए।",
        "nudge_note": "{pct}% बजट इस्तेमाल हो गया, अभी {days} दिन बाकी हैं।",
        "on_track": "💚 आप ट्रैक पर हैं — इस महीने {amount} बचेंगे।",
        "tagline": "जो खर्च किया, बस बोलिए। Gnani Prisma से लिखा जाता है।",
        "help": "मदद",
        "help_body": """**आप क्या बोल सकते हैं**
- `aaj chai 20, auto 80, lunch dedh sau` — एक सांस में कई खर्च
- `kal metro 40` — *kal* / *parso* / *yesterday* से पिछली तारीख
- `Ravi ko 500 udhar diya` — खाता एंट्री, बाद में सेटल कीजिए
- `is mahine kitna kharch hua?` — आवाज़ से पूछिए
- `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) सब चलते हैं

**सुझाव**
- Prisma गलत सुने तो सेव करने से पहले ट्रांसक्रिप्ट सुधार लीजिए।
- सारा डेटा इस डिवाइस के SQLite में रहता है; साइडबार से कभी भी एक्सपोर्ट कीजिए।""",
        "db_counts": "📦 {expenses} खर्च · 📒 {khata} खाता एंट्री",
        "avg_help": "इस महीने बीते हर दिन का औसत खर्च",
        "chips": ["🍵 चाय", "🛺 ऑटो", "🍱 लंच", "💡 रिचार्ज", "📚 ज़ेरॉक्स", "🥬 सब्ज़ी"],
        "added": "{item} जोड़ा गया",
        "item_placeholder": "चाय, ऑटो, दवाई...",
        "lent_option": "उधार दिया", "borrowed_option": "उधार लिया",
        "status_label": "स्थिति",
        "col_item": "चीज़", "col_total": "कुल", "col_times": "बार", "col_usual": "सामान्य",
        "streak_day": "{days} दिन", "streak_days": "{days} दिन",
        "delta_more": "📈 पिछले महीने से {pct}% ज़्यादा (तब {then}, अब {now})।",
        "delta_less": "📉 पिछले महीने से {pct}% कम (तब {then}, अब {now})।",
        "pattern_empty": "कुछ और दिन दर्ज कीजिए, फिर साप्ताहिक पैटर्न दिखेगा।",
        "updated_entries": "{n} एंट्री अपडेट हुईं", "deleted_entries": "{n} एंट्री हटाई गईं",
        "ask_samples": [
            "इस महीने कितना खर्च हुआ?", "चाय पर कितना गया?",
            "बजट कितना बचा?", "सबसे महंगा खर्च?",
        ],
        "lbl_transcript": "ट्रांसक्रिप्ट", "lbl_upload": "ऑडियो अपलोड",
        "lbl_type": "खर्च टाइप करें", "lbl_sms": "बैंक SMS",
        "lbl_record": "अपने खर्च बोलिए", "lbl_ask_mic": "सवाल पूछिए",
        "lbl_ask": "अपने पैसों के बारे में पूछिए", "chart_amount": "रकम (₹)",
        "auto_detect": "🎧 बोली हुई भाषा अपने आप पहचानें",
        "auto_detect_hint": "Prisma खुद समझ लेगा कि आपने हिंदी, तेलुगु या अंग्रेज़ी बोली — चुनने की ज़रूरत नहीं।",
        "heard_lang": "🗣️ सुनी गई भाषा: {lang}",
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
        "dup_warn": "ఈ ఎంట్రీ ఇప్పుడే సేవ్ అయినట్టుంది", "dup_confirm": "అయినా సేవ్ చేయండి",
        "kind_label": "రకం", "merchant_label": "దుకాణం", "mode_label": "చెల్లింపు",
        "income_label": "ఆదాయం", "paid_by": "విధానం",
        "pace_note": "🔮 ఈ వేగంతో ఈ నెల {amount} వరకు చేరవచ్చు.",
        "cross_note": " బడ్జెట్ {date} సుమారుగా దాటిపోతుంది.",
        "anomaly_header": "అసాధారణ ఖర్చులు",
        "anomaly_hint": "ప్రతిదీ దాని వర్గంలో సాధారణ ఖర్చు కంటే కనీసం 3 రెట్లు ఉంది.",
        "sms_header": "బ్యాంక్ SMS పేస్ట్ చేయండి",
        "sms_hint": "ఉదా: \"Rs 450 debited at Swiggy\" — ఇది ఎంట్రీగా మారుతుంది.",
        "no_amount": "మొత్తం దొరకలేదు. 'chai 20' లేదా 'dedh sau (150)' ప్రయత్నించండి.",
        "personal_expenses": "నా ఖర్చులు", "khata_entries": "ఖాతా ఎంట్రీలు",
        "whatsapp_hint": "📲 లేదా వాట్సాప్ వాయిస్ నోట్ పంపండి (OGG, M4A, MP3, WAV)",
        "listening": "Gnani Prisma మీ స్వరం అర్థం చేసుకుంటోంది...",
        "stt_failed": "స్పష్టంగా వినిపించలేదు. మైక్ దగ్గరగా మాట్లాడండి.",
        "technical": "సాంకేతిక వివరాలు",
        "no_pending": "పెండింగ్ ఖాతా ఎంట్రీలు లేవు. 'Ravi ko 500 udhar diya' అనండి లేదా కింద జోడించండి.",
        "khata_added": "ఖాతా ఎంట్రీ జోడించబడింది",
        "interpreting": "Prisma మీ ప్రశ్నను అర్థం చేసుకుంటోంది...",
        "ask_failed": "ప్రశ్న అర్థం కాలేదు. కింద టైప్ చేయండి.",
        "undone": "రద్దు చేయబడింది", "redo": "↩ మళ్ళీ",
        "budget_used": "{spent} / {budget} వాడారు ({pct}%) · {days} రోజులు మిగిలాయి · రోజుకు {per_day}లో బడ్జెట్ లోపల ఉంటారు",
        "over_budget": "⚠️ బడ్జెట్ కంటే {amount} ఎక్కువ. కొంచెం ఆగండి.",
        "nudge_note": "బడ్జెట్‌లో {pct}% వాడారు, ఇంకా {days} రోజులు ఉన్నాయి.",
        "on_track": "💚 మీరు సరైన దారిలో ఉన్నారు — ఈ నెల {amount} మిగులుతుంది.",
        "tagline": "ఖర్చు ఏమిటో చెప్పండి. మేము రాస్తాము. Gnani Prisma తో.",
        "help": "సహాయం",
        "help_body": """**మీరు ఏమి చెప్పవచ్చు**
- `aaj chai 20, auto 80, lunch dedh sau` — ఒకే ఊపిరిలో చాలా ఖర్చులు
- `kal metro 40` — *kal* / *parso* / *yesterday* తో గత తారీఖు
- `Ravi ko 500 udhar diya` — ఖాతా ఎంట్రీ, తరువాత సెటిల్ చేయండి
- `is mahine kitna kharch hua?` — స్వరంతో అడగండి
- `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) అన్నీ పని చేస్తాయి

**చిట్కాలు**
- Prisma తప్పుగా విన్నట్టయితే సేవ్ చేయడానికి ముందు ట్రాన్స్‌క్రిప్ట్ సవరించండి.
- డేటా మొత్తం ఈ పరికరంలోని SQLiteలో ఉంటుంది; సైడ్‌బార్ నుండి ఎప్పుడైనా ఎక్స్‌పోర్ట్ చేయండి.""",
        "db_counts": "📦 {expenses} ఖర్చులు · 📒 {khata} ఖాతా ఎంట్రీలు",
        "avg_help": "ఈ నెల గడిచిన రోజుల సగటు ఖర్చు",
        "chips": ["🍵 టీ", "🛺 ఆటో", "🍱 లంచ్", "💡 రీఛార్జ్", "📚 జెరాక్స్", "🥬 కూరగాయలు"],
        "added": "{item} జోడించబడింది",
        "item_placeholder": "టీ, ఆటో, మందులు...",
        "lent_option": "అప్పు ఇచ్చాను", "borrowed_option": "అప్పు తీసుకున్నాను",
        "status_label": "స్థితి",
        "col_item": "వస్తువు", "col_total": "మొత్తం", "col_times": "సార్లు", "col_usual": "సాధారణం",
        "streak_day": "{days} రోజు", "streak_days": "{days} రోజులు",
        "delta_more": "📈 గత నెల కంటే {pct}% ఎక్కువ (అప్పుడు {then}, ఇప్పుడు {now}).",
        "delta_less": "📉 గత నెల కంటే {pct}% తక్కువ (అప్పుడు {then}, ఇప్పుడు {now}).",
        "pattern_empty": "ఇంకా కొన్ని రోజులు నమోదు చేయండి, వారపు నమూనా కనిపిస్తుంది.",
        "updated_entries": "{n} ఎంట్రీలు అప్‌డేట్ అయ్యాయి", "deleted_entries": "{n} ఎంట్రీలు తొలగించబడ్డాయి",
        "ask_samples": [
            "ఈ నెల ఎంత ఖర్చు అయింది?", "టీ కి ఎంత పోయింది?",
            "బడ్జెట్ ఎంత మిగిలింది?", "అత్యధిక ఖర్చు ఏమిటి?",
        ],
        "lbl_transcript": "ట్రాన్స్‌క్రిప్ట్", "lbl_upload": "ఆడియో అప్‌లోడ్",
        "lbl_type": "ఖర్చు టైప్ చేయండి", "lbl_sms": "బ్యాంక్ SMS",
        "lbl_record": "మీ ఖర్చులు చెప్పండి", "lbl_ask_mic": "ప్రశ్న అడగండి",
        "lbl_ask": "మీ డబ్బు గురించి అడగండి", "chart_amount": "మొత్తం (₹)",
        "auto_detect": "🎧 మాట్లాడిన భాషను ఆటోమేటిక్‌గా గుర్తించండి",
        "auto_detect_hint": "మీరు హిందీ, తెలుగు లేదా ఇంగ్లీష్ మాట్లాడారో Prisma తనే గుర్తిస్తుంది — ఎంచుకోవాల్సిన అవసరం లేదు.",
        "heard_lang": "🗣️ విన్న భాష: {lang}",
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
        "dup_warn": "This looks like a duplicate of an entry saved minutes ago",
        "dup_confirm": "Save anyway", "kind_label": "Kind", "merchant_label": "Merchant",
        "mode_label": "Payment", "income_label": "Income", "paid_by": "Via",
        "pace_note": "🔮 At this pace you will spend {amount} this month.",
        "cross_note": " That crosses your budget around {date}.",
        "anomaly_header": "Unusual expenses",
        "anomaly_hint": "Each of these is at least 3x your usual spend in its category.",
        "sms_header": "Paste a bank SMS",
        "sms_hint": "e.g. \"Rs 450 debited at Swiggy\" — it becomes an entry you can save.",
        "no_amount": "I could not catch an amount. Try 'chai 20' or 'dedh sau (150)'.",
        "personal_expenses": "Personal expenses", "khata_entries": "Khata entries",
        "whatsapp_hint": "📲 Or forward a WhatsApp voice note (OGG, M4A, MP3, WAV)",
        "listening": "Understanding your voice with Gnani Prisma...",
        "stt_failed": "I could not hear that clearly. Please try again a little closer to the mic.",
        "technical": "Technical details",
        "no_pending": "No pending khata entries. Say 'Ravi ko 500 udhar diya' or add one below.",
        "khata_added": "Khata entry added",
        "interpreting": "Prisma is interpreting your question...",
        "ask_failed": "Could not interpret that question. Try typing it below.",
        "undone": "Undone", "redo": "↩ Redo",
        "budget_used": "{spent} of {budget} used ({pct}%) · {days} days left · {per_day}/day keeps you inside the budget",
        "over_budget": "⚠️ Over budget by {amount}. Time to slow down.",
        "nudge_note": "You have used {pct}% of your monthly budget with {days} days still to go.",
        "on_track": "💚 You are on track — {amount} spare this month.",
        "tagline": "Say what you spent. We write it down. Powered by Gnani Prisma.",
        "help": "Help",
        "help_body": """**What you can say**
- `aaj chai 20, auto 80, lunch dedh sau` — one breath, many expenses
- `kal metro 40` — backdate with *kal* / *parso* / *yesterday*
- `Ravi ko 500 udhar diya` — khata entry, settle it later
- `is mahine kitna kharch hua?` — ask by voice
- `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) all work

**Tips**
- Edit the transcript before saving if Prisma mishears a number.
- Everything is stored locally in SQLite; export any time from the sidebar.""",
        "db_counts": "📦 {expenses} expenses · 📒 {khata} khata entries",
        "avg_help": "Average spend per elapsed day this month",
        "chips": ["🍵 Chai", "🛺 Auto", "🍱 Lunch", "💡 Recharge", "📚 Xerox", "🥬 Sabzi"],
        "added": "{item} added",
        "item_placeholder": "Chai, auto, medicine...",
        "lent_option": "Lent (gave)", "borrowed_option": "Borrowed (took)",
        "status_label": "Status",
        "col_item": "Item", "col_total": "Total", "col_times": "Times", "col_usual": "Usual",
        "streak_day": "{days} day", "streak_days": "{days} days",
        "delta_more": "📈 {pct}% more than last month ({then} then vs {now} now).",
        "delta_less": "📉 {pct}% less than last month ({then} then vs {now} now).",
        "pattern_empty": "Log a few more days to reveal your weekly pattern.",
        "updated_entries": "Updated {n} entries", "deleted_entries": "Deleted {n} entries",
        "ask_samples": [
            "is mahine kitna kharch hua?", "chai pe kitna gaya?",
            "budget kitna bacha?", "sabse mehnga kharch?",
        ],
        "lbl_transcript": "Transcript", "lbl_upload": "Upload audio",
        "lbl_type": "Type expenses", "lbl_sms": "Bank SMS",
        "lbl_record": "Record your expenses", "lbl_ask_mic": "Ask a question",
        "lbl_ask": "Ask about your money", "chart_amount": "Amount (₹)",
        "auto_detect": "🎧 Auto-detect the spoken language",
        "auto_detect_hint": "Prisma works out whether you spoke Hindi, Telugu or English — no need to pick one.",
        "heard_lang": "🗣️ Heard {lang}",
    },
    "bn-IN": {
        "settings": "সেটিংস", "export": "এক্সপোর্ট", "expenses_csv": "খরচের CSV",
        "backup_json": "সম্পূর্ণ ব্যাকঅাপ (JSON)", "restore_header": "ব্যাকঅাপ ফিরিয়ে আনুন",
        "restore_hint": "আগে JSON ব্যাকঅাপ বেছে নিন, তারপর নিশ্চিত করুন।",
        "restore_preview": "এই ব্যাকঅাপে আছে", "restore_replaces": "ফিরিয়ে আনলে এই ডিভাইসের বর্তমান ডেটা বদলে যাবে।",
        "restore_confirm": "আমার ডেটা এই ব্যাকঅাপ দিয়ে বদলে দাও", "restore_now": "ফিরিয়ে আনুন",
        "restore_done": "ব্যাকঅাপ ফিরে এসেছে", "danger": "বিপদ অঞ্চল",
        "danger_hint": "এই ডিভাইসের সব খরচ ও খাতা এন্ট্রি মুছে যাবে।",
        "danger_confirm": "বুঝেছি, সব মুছে দাও", "cleared": "সব ডেটা মুছে গেছে",
        "manual_header": "একটি এন্ট্রি হাতে যোগ করুন (সঠিক টাকা, যেকোনো তারিখ)",
        "what": "কী কিনেছেন?", "amount": "টাকা (₹)", "category": "শ্রেণি",
        "date": "তারিখ", "add_expense": "খরচ যোগ করুন",
        "need_desc": "নাম আর শূন্যের বেশি টাকা দিন।",
        "owe_me": "আমাকে পাওনা", "i_owe": "আমাকে দিতে হবে", "people_pending": "লোক বাকি",
        "all_entries": "সব এন্ট্রি", "add_khata": "খাতা এন্ট্রি যোগ করুন", "person": "কার নাম",
        "type": "ধরন", "add_entry": "এন্ট্রি যোগ করুন", "need_khata": "নাম আর টাকা দিন।",
        "paid": "দেওয়া হয়েছে", "remaining": "বাকি", "record_payment": "পেমেন্ট লিখুন",
        "payment_amount": "পেমেন্ট (₹)", "need_payment": "আগে পেমেন্টের টাকা দিন।",
        "pick_one": "পেমেন্টের জন্য একটি এন্ট্রি বেছে নিন।", "edit_entry": "এন্ট্রি সংশোধন করুন",
        "save_edits": "পরিবর্তন সেভ করুন", "updated": "পরিবর্তন সেভ হয়েছে", "delete": "মুছুন",
        "deleted": "মুছে ফেলা হয়েছে", "settled_toast": "পরিশোধ হিসেবে চিহ্নিত", "reopen_toast": "আবার বাকিতে",
        "view_month": "কোন মাস", "this_month": "এই মাস", "last_14": "গত ১৪ দিন",
        "by_category": "শ্রেণি অনুযায়ী খরচ", "top_items": "সবচেয়ে বড় খরচ",
        "patterns": "ধরন", "streak": "টানা দিন", "no_items": "এই মাসে এখনও কিছু নেই।",
        "month_filter": "মাস", "search_item": "নাম খুঁজুন", "all_option": "সব",
        "delete_selected": "নির্বাচিত মুছুন", "entries": "এন্ট্রি",
        "no_match": "এই ফিল্টারে কিছু মেলেনি।", "you_asked": "আপনি জিজ্ঞাসা করেছেন",
        "ask_placeholder": "এই মাসে কত খরচ হল?",
        "dup_warn": "এই এন্ট্রি এইমাত্র সেভ হয়েছে বলে মনে হচ্ছে", "dup_confirm": "তবুও সেভ করুন",
        "kind_label": "ধরন", "merchant_label": "দোকান", "mode_label": "পেমেন্ট",
        "income_label": "আয়", "paid_by": "মাধ্যন",
        "pace_note": "🔮 এই গতিতে এই মাসে {amount} পর্যন্ত পৌঁছাতে পারেন।",
        "cross_note": " বাজেট {date}-এর আশেপাশে পেরিয়ে যাবে।",
        "anomaly_header": "অস্বাভাবিক খরচ",
        "anomaly_hint": "প্রতিটি এন্ট্রি তার শ্রেণির সাধারণ খরচের অন্তত ৩ গুণ।",
        "sms_header": "ব্যাংক SMS পেস্ট করুন",
        "sms_hint": "যেমন: \"Rs 450 debited at Swiggy\" — এটি এন্ট্রি হয়ে যাবে।",
        "no_amount": "টাকা পাওয়া যায়নি। 'chai 20' বা 'dedh sau (150)' চেষ্টা করুন।",
        "personal_expenses": "আমার খরচ", "khata_entries": "খাতা এন্ট্রি",
        "whatsapp_hint": "📲 বা WhatsApp ভয়েস নোট পাঠান (OGG, M4A, MP3, WAV)",
        "listening": "Gnani Prisma আপনার কথা বুঝছে...",
        "stt_failed": "ঠিকভাবে শোনা যায়নি। মাইকের কাছে গিয়ে বলুন।",
        "technical": "কারিগরি তথ্য",
        "no_pending": "কোনো বাকি খাতা এন্ট্রি নেই। 'Ravi ko 500 udhar diya' বলুন বা নিচে যোগ করুন।",
        "khata_added": "খাতা এন্ট্রি যোগ হয়েছে",
        "interpreting": "Prisma আপনার প্রশ্ন বুঝছে...",
        "ask_failed": "প্রশ্নটা বোঝা যায়নি। নিচে টাইপ করুন।",
        "undone": "ফিরিয়ে নেওয়া হয়েছে", "redo": "↩ আবার",
        "budget_used": "{spent} / {budget} ব্যবহার ({pct}%) · {days} দিন বাকি · দিনে {per_day} হলে বাজেটের মধ্যে থাকবেন",
        "over_budget": "⚠️ বাজেটের চেয়ে {amount} বেশি। একটু থামুন।",
        "nudge_note": "বাজেটের {pct}% ব্যবহার হয়ে গেছে, এখনও {days} দিন বাকি।",
        "on_track": "💚 আপনি ঠিক পথে আছেন — এই মাসে {amount} বাঁচবে।",
        "tagline": "যা খরচ করলেন, শুধু বলুন। Gnani Prisma দিয়ে লেখা হয়।",
        "help": "সাহায্য",
        "help_body": """**আপনি কী বলতে পারেন**
- `aaj chai 20, auto 80, lunch dedh sau` — এক শ্বাসে অনেক খরচ
- `kal metro 40` — *kal* / *parso* / *yesterday* দিয়ে আগের তারিখ
- `Ravi ko 500 udhar diya` — খাতা এন্ট্রি, পরে পরিশোধ করুন
- `is mahine kitna kharch hua?` — ভয়েসে জিজ্ঞাসা করুন
- `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) সবই চলে

**পরামর্শ**
- Prisma ভুল শুনলে সেভ করার আগে ট্রান্সক্রিপ্ট ঠিক করে নিন।
- সব ডেটা এই ডিভাইসের SQLite-এ থাকে; সাইডবার থেকে যেকোনো সময় এক্সপোর্ট করুন।""",
        "db_counts": "📦 {expenses} খরচ · 📒 {khata} খাতা এন্ট্রি",
        "avg_help": "এই মাসে বেড়ে যাওয়া প্রতিদিনের গড় খরচ",
        "chips": ["🍵 চা", "🛺 অটো", "🍱 লাঞ্চ", "💡 রিচার্জ", "📚 জেরক্স", "🥬 সবজি"],
        "added": "{item} যোগ হয়েছে",
        "item_placeholder": "চা, অটো, ওষুধ...",
        "lent_option": "ধার দিয়েছি", "borrowed_option": "ধার নিয়েছি",
        "status_label": "অবস্থা",
        "col_item": "জিনিস", "col_total": "মোট", "col_times": "বার", "col_usual": "সাধারণ",
        "streak_day": "{days} দিন", "streak_days": "{days} দিন",
        "delta_more": "📈 গত মাসের চেয়ে {pct}% বেশি (তখন {then}, এখন {now})।",
        "delta_less": "📉 গত মাসের চেয়ে {pct}% কম (তখন {then}, এখন {now})।",
        "pattern_empty": "আরও কয়েক দিন লিখুন, সাপ্তাহিক ধরন দেখা যাবে।",
        "updated_entries": "{n} এন্ট্রি আপডেট হয়েছে", "deleted_entries": "{n} এন্ট্রি মোছা হয়েছে",
        "ask_samples": [
            "এই মাসে কত খরচ হল?", "চায়ে কত গেল?",
            "বাজেট কত বাকি?", "সবচেয়ে বড় খরচ?",
        ],
        "lbl_transcript": "ট্রান্সক্রিপ্ট", "lbl_upload": "অডিও আপলোড",
        "lbl_type": "খরচ টাইপ করুন", "lbl_sms": "ব্যাংক SMS",
        "lbl_record": "আপনার খরচ বলুন", "lbl_ask_mic": "প্রশ্ন করুন",
        "lbl_ask": "আপনার টাকা নিয়ে জিজ্ঞাসা করুন", "chart_amount": "টাকা (₹)",
        "auto_detect": "🎧 বলা ভাষা নিজে বুঝে নিন",
        "auto_detect_hint": "Prisma নিজেই বুঝবে আপনি হিন্দি, তেলুগু বা ইংরেজি বলেছেন — বেছে নিতে হবে না।",
        "heard_lang": "🗣️ শোনা ভাষা: {lang}",
    },
    "ta-IN": {
        "settings": "அமைப்புகள்", "export": "ஏற்றுமதி", "expenses_csv": "செலவு CSV",
        "backup_json": "முழு காப்பு (JSON)", "restore_header": "காப்பை மீட்டெடு",
        "restore_hint": "முதலில் JSON காப்பை தேர்ந்தெடுத்து, பின்னர் உறுதி செய்யுங்கள்.",
        "restore_preview": "இந்தக் காப்பில் உள்ளது", "restore_replaces": "மீட்டெடுத்தால் இந்த சாதனத்தின் தற்போதைய தரவு மாறும்.",
        "restore_confirm": "என் தரவை இந்தக் காப்பால் மாற்று", "restore_now": "மீட்டெடு",
        "restore_done": "காப்பு மீட்டெடுக்கப்பட்டது", "danger": "ஆபத்து பகுதி",
        "danger_hint": "இந்த சாதனத்தின் அனைத்து செலவுகளும் கணக்கு பதிவுகளும் அழியும்.",
        "danger_confirm": "புரிந்தது, எல்லாவற்றையும் அழி", "cleared": "எல்லா தரவும் அழிக்கப்பட்டது",
        "manual_header": "ஒரு பதிவை கையால் சேர் (சரியான தொகை, எந்த தேதியும்)",
        "what": "என்ன வாங்கினீர்கள்?", "amount": "தொகை (₹)", "category": "வகை",
        "date": "தேதி", "add_expense": "செலவு சேர்",
        "need_desc": "பெயரும் பூஜ்ஜியத்திற்கு மேல் தொகையும் கொடுங்கள்.",
        "owe_me": "எனக்கு வரவேண்டியது", "i_owe": "நான் தரவேண்டியது", "people_pending": "நிலுவை நபர்கள்",
        "all_entries": "அனைத்து பதிவுகள்", "add_khata": "கணக்கு பதிவு சேர்", "person": "யாருடைய பெயர்",
        "type": "வகை", "add_entry": "பதிவு சேர்", "need_khata": "பெயரும் தொகையும் கொடுங்கள்.",
        "paid": "செலுத்தியது", "remaining": "மீதம்", "record_payment": "பணம் பதிவு செய்",
        "payment_amount": "பணம் (₹)", "need_payment": "முதலில் பணத் தொகையை கொடுங்கள்.",
        "pick_one": "பணம் பதிவு செய்ய ஒரு பதிவை மட்டும் தேர்ந்தெடுங்கள்.", "edit_entry": "பதிவை திருத்து",
        "save_edits": "மாற்றங்களை சேமி", "updated": "மாற்றங்கள் சேமிக்கப்பட்டன", "delete": "அழி",
        "deleted": "அழிக்கப்பட்டது", "settled_toast": "செலுத்தியதாக குறிக்கப்பட்டது", "reopen_toast": "மீண்டும் நிலுவையில்",
        "view_month": "எந்த மாதம்", "this_month": "இந்த மாதம்", "last_14": "கடந்த 14 நாட்கள்",
        "by_category": "வகை வாரியாக செலவு", "top_items": "அதிக செலவுகள்",
        "patterns": "வடிவங்கள்", "streak": "தொடர் நாட்கள்", "no_items": "இந்த மாதம் இன்னும் ஒன்றும் இல்லை.",
        "month_filter": "மாதம்", "search_item": "பெயர் தேடு", "all_option": "அனைத்தும்",
        "delete_selected": "தேர்ந்தவற்றை அழி", "entries": "பதிவுகள்",
        "no_match": "இந்த வடிகட்டிகளுக்கு எதுவும் இல்லை.", "you_asked": "நீங்கள் கேட்டது",
        "ask_placeholder": "இந்த மாதம் எவ்வளவு செலவு?",
        "dup_warn": "இந்தப் பதிவு இப்போதுதான் சேமிக்கப்பட்டது போல உள்ளது", "dup_confirm": "இருந்தாலும் சேமி",
        "kind_label": "வகை", "merchant_label": "கடை", "mode_label": "பணம்",
        "income_label": "வருமானம்", "paid_by": "முறை",
        "pace_note": "🔮 இந்த வேகத்தில் இந்த மாதம் {amount} வரை செல்லலாம்.",
        "cross_note": " பட்ஜெட் {date} அளவில் தாண்டும்.",
        "anomaly_header": "அசாதாரண செலவுகள்",
        "anomaly_hint": "ஒவ்வொன்றும் அதன் வகையின் சராசரி செலவை விட குறைந்தது 3 மடங்கு.",
        "sms_header": "வங்கி SMS ஒட்டுங்கள்",
        "sms_hint": "உதா: \"Rs 450 debited at Swiggy\" — இது பதிவாகும்.",
        "no_amount": "தொகை கிடைக்கவில்லை. 'chai 20' அல்லது 'dedh sau (150)' முயற்சிக்கவும்.",
        "personal_expenses": "என் செலவுகள்", "khata_entries": "கணக்கு பதிவுகள்",
        "whatsapp_hint": "📲 அல்லது வாட்ஸ்அப் குரல் குறிப்பை அனுப்புங்கள் (OGG, M4A, MP3, WAV)",
        "listening": "Gnani Prisma உங்கள் குரலை புரிந்துகொள்கிறது...",
        "stt_failed": "தெளிவாக கேட்கவில்லை. மைக்கிற்கு அருகில் பேசுங்கள்.",
        "technical": "தொழில்நுட்ப விவரங்கள்",
        "no_pending": "நிலுவை கணக்கு பதிவுகள் இல்லை. 'Ravi ko 500 udhar diya' சொல்லுங்கள் அல்லது கீழே சேர்க்கவும்.",
        "khata_added": "கணக்கு பதிவு சேர்க்கப்பட்டது",
        "interpreting": "Prisma உங்கள் கேள்வியை புரிந்துகொள்கிறது...",
        "ask_failed": "கேள்வி புரியவில்லை. கீழே தட்டச்சு செய்யுங்கள்.",
        "undone": "ரத்து செய்யப்பட்டது", "redo": "↩ மீண்டும்",
        "budget_used": "{spent} / {budget} பயன்படுத்தப்பட்டது ({pct}%) · {days} நாட்கள் மீதம் · நாளுக்கு {per_day} என்றால் பட்ஜெட்டுக்குள் இருப்பீர்கள்",
        "over_budget": "⚠️ பட்ஜெட்டை விட {amount} அதிகம். சற்று நிறுத்துங்கள்.",
        "nudge_note": "பட்ஜெட்டில் {pct}% பயன்படுத்திவிட்டீர்கள், இன்னும் {days} நாட்கள் உள்ளன.",
        "on_track": "💚 சரியான பாதையில் உள்ளீர்கள் — இந்த மாதம் {amount} மிச்சமாகும்.",
        "tagline": "என்ன செலவு செய்தீர்கள், சொல்லுங்கள். Gnani Prisma மூலம் எழுதப்படுகிறது.",
        "help": "உதவி",
        "help_body": """**நீங்கள் என்ன சொல்லலாம்**
- `aaj chai 20, auto 80, lunch dedh sau` — ஒரே மூச்சில் பல செலவுகள்
- `kal metro 40` — *kal* / *parso* / *yesterday* மூலம் முந்தைய தேதி
- `Ravi ko 500 udhar diya` — கணக்கு பதிவு, பின்னர் தீர்க்கலாம்
- `is mahine kitna kharch hua?` — குரல் மூலம் கேளுங்கள்
- `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) எல்லாம் வேலை செய்யும்

**குறிப்புகள்**
- Prisma தவறாகக் கேட்டால் சேமிக்கும் முன் டிரான்ஸ்கிரிப்டை திருத்துங்கள்.
- தரவு முழுவதும் இந்த சாதனத்தின் SQLite-ல் உள்ளது; பக்கப் பலகையிலிருந்து எப்போதும் ஏற்றுமதி செய்யலாம்.""",
        "db_counts": "📦 {expenses} செலவுகள் · 📒 {khata} கணக்கு பதிவுகள்",
        "avg_help": "இந்த மாதம் கடந்த நாட்களின் சராசரி செலவு",
        "chips": ["🍵 டீ", "🛺 ஆட்டோ", "🍱 மதிய உணவு", "💡 ரீசார்ஜ்", "📚 ஜெராக்ஸ்", "🥬 காய்கறி"],
        "added": "{item} சேர்க்கப்பட்டது",
        "item_placeholder": "டீ, ஆட்டோ, மருந்து...",
        "lent_option": "கடன் கொடுத்தேன்", "borrowed_option": "கடன் வாங்கினேன்",
        "status_label": "நிலை",
        "col_item": "பொருள்", "col_total": "மொத்தம்", "col_times": "முறை", "col_usual": "வழக்கமான",
        "streak_day": "{days} நாள்", "streak_days": "{days} நாட்கள்",
        "delta_more": "📈 கடந்த மாதத்தை விட {pct}% அதிகம் (அப்போது {then}, இப்போது {now}).",
        "delta_less": "📉 கடந்த மாதத்தை விட {pct}% குறைவு (அப்போது {then}, இப்போது {now}).",
        "pattern_empty": "இன்னும் சில நாட்கள் பதிவு செய்யுங்கள், வார வடிவம் தெரியும்.",
        "updated_entries": "{n} பதிவுகள் புதுப்பிக்கப்பட்டன", "deleted_entries": "{n} பதிவுகள் அழிக்கப்பட்டன",
        "ask_samples": [
            "இந்த மாதம் எவ்வளவு செலவு?", "டீக்கு எவ்வளவு போனது?",
            "பட்ஜெட் எவ்வளவு மீதம்?", "அதிக செலவு என்ன?",
        ],
        "lbl_transcript": "டிரான்ஸ்கிரிப்ட்", "lbl_upload": "ஆடியோ பதிவேற்றம்",
        "lbl_type": "செலவை தட்டச்சு செய்யுங்கள்", "lbl_sms": "வங்கி SMS",
        "lbl_record": "உங்கள் செலவுகளைச் சொல்லுங்கள்", "lbl_ask_mic": "கேள்வி கேளுங்கள்",
        "lbl_ask": "உங்கள் பணம் பற்றி கேளுங்கள்", "chart_amount": "தொகை (₹)",
        "auto_detect": "🎧 பேசிய மொழியை தானாக கண்டறி",
        "auto_detect_hint": "நீங்கள் இந்தி, தெலுங்கு அல்லது ஆங்கிலம் பேசினீர்களா என்பதை Prisma தானே கண்டறியும் — தேர்ந்தெடுக்க வேண்டாம்.",
        "heard_lang": "🗣️ கேட்ட மொழி: {lang}",
    },
    "kn-IN": {
        "settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು", "export": "ಎಕ್ಸ್‌ಪೋರ್ಟ್", "expenses_csv": "ಖರ್ಚಿನ CSV",
        "backup_json": "ಪೂರ್ಣ ಬ್ಯಾಕಪ್ (JSON)", "restore_header": "ಬ್ಯಾಕಪ್ ಮರುಸ್ಥಾಪಿಸಿ",
        "restore_hint": "ಮೊದಲು JSON ಬ್ಯಾಕಪ್ ಆಯ್ಕೆಮಾಡಿ, ನಂತರ ದೃಢೀಕರಿಸಿ.",
        "restore_preview": "ಈ ಬ್ಯಾಕಪ್‌ನಲ್ಲಿದೆ", "restore_replaces": "ಮರುಸ್ಥಾಪಿಸಿದರೆ ಈ ಸಾಧನದ ಪ್ರಸ್ತುತ ಡೇಟಾ ಬದಲಾಗುತ್ತದೆ.",
        "restore_confirm": "ನನ್ನ ಡೇಟಾವನ್ನು ಈ ಬ್ಯಾಕಪ್‌ನಿಂದ ಬದಲಿಸು", "restore_now": "ಮರುಸ್ಥಾಪಿಸು",
        "restore_done": "ಬ್ಯಾಕಪ್ ಮರಳಿ ಬಂದಿದೆ", "danger": "ಅಪಾಯ ವಲಯ",
        "danger_hint": "ಈ ಸಾಧನದ ಎಲ್ಲಾ ಖರ್ಚು ಮತ್ತು ಖಾತೆ ನಮೂದುಗಳು ಅಳಿಸಿಹೋಗುತ್ತವೆ.",
        "danger_confirm": "ಅರ್ಥವಾಯಿತು, ಎಲ್ಲವನ್ನೂ ಅಳಿಸು", "cleared": "ಎಲ್ಲಾ ಡೇಟಾ ಅಳಿಸಲಾಗಿದೆ",
        "manual_header": "ಒಂದು ನಮೂದನ್ನು ಕೈಯಿಂದ ಸೇರಿಸಿ (ನಿಖರ ಮೊತ್ತ, ಯಾವುದೇ ದಿನಾಂಕ)",
        "what": "ಏನು ಖರೀದಿಸಿದಿರಿ?", "amount": "ಮೊತ್ತ (₹)", "category": "ವರ್ಗ",
        "date": "ದಿನಾಂಕ", "add_expense": "ಖರ್ಚು ಸೇರಿಸಿ",
        "need_desc": "ಹೆಸರು ಮತ್ತು ಸೊನ್ನೆಗಿಂತ ಹೆಚ್ಚಿನ ಮೊತ್ತ ನೀಡಿ.",
        "owe_me": "ನನಗೆ ಬರಬೇಕಾದದ್ದು", "i_owe": "ನಾನು ಕೊಡಬೇಕಾದದ್ದು", "people_pending": "ಬಾಕಿ ಜನರು",
        "all_entries": "ಎಲ್ಲಾ ನಮೂದುಗಳು", "add_khata": "ಖಾತೆ ನಮೂದು ಸೇರಿಸಿ", "person": "ಯಾರ ಹೆಸರು",
        "type": "ರೀತಿ", "add_entry": "ನಮೂದು ಸೇರಿಸಿ", "need_khata": "ಹೆಸರು ಮತ್ತು ಮೊತ್ತ ನೀಡಿ.",
        "paid": "ಪಾವತಿಸಲಾಗಿದೆ", "remaining": "ಬಾಕಿ", "record_payment": "ಪಾವತಿ ದಾಖಲಿಸಿ",
        "payment_amount": "ಪಾವತಿ (₹)", "need_payment": "ಮೊದಲು ಪಾವತಿ ಮೊತ್ತ ನೀಡಿ.",
        "pick_one": "ಪಾವತಿಗೆ ಒಂದೇ ನಮೂದು ಆಯ್ಕೆಮಾಡಿ.", "edit_entry": "ನಮೂದು ಸರಿಪಡಿಸಿ",
        "save_edits": "ಬದಲಾವಣೆ ಉಳಿಸಿ", "updated": "ಬದಲಾವಣೆ ಉಳಿಸಲಾಗಿದೆ", "delete": "ಅಳಿಸಿ",
        "deleted": "ಅಳಿಸಲಾಗಿದೆ", "settled_toast": "ಪಾವತಿಯಾಗಿದೆ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ", "reopen_toast": "ಮತ್ತೆ ಬಾಕಿಗೆ",
        "view_month": "ಯಾವ ತಿಂಗಳು", "this_month": "ಈ ತಿಂಗಳು", "last_14": "ಕಳೆದ 14 ದಿನಗಳು",
        "by_category": "ವರ್ಗದ ಪ್ರಕಾರ ಖರ್ಚು", "top_items": "ಹೆಚ್ಚಿನ ಖರ್ಚುಗಳು",
        "patterns": "ಮಾದರಿಗಳು", "streak": "ಸತತ ದಿನಗಳು", "no_items": "ಈ ತಿಂಗಳು ಇನ್ನೂ ಏನೂ ಇಲ್ಲ.",
        "month_filter": "ತಿಂಗಳು", "search_item": "ಹೆಸರು ಹುಡುಕಿ", "all_option": "ಎಲ್ಲಾ",
        "delete_selected": "ಆಯ್ಕೆಮಾಡಿದವನ್ನು ಅಳಿಸಿ", "entries": "ನಮೂದುಗಳು",
        "no_match": "ಈ ಫಿಲ್ಟರ್‌ಗಳಿಗೆ ಏನೂ ಸಿಗಲಿಲ್ಲ.", "you_asked": "ನೀವು ಕೇಳಿದ್ದು",
        "ask_placeholder": "ಈ ತಿಂಗಳು ಎಷ್ಟು ಖರ್ಚು?",
        "dup_warn": "ಈ ನಮೂದು ಈಗಷ್ಟೇ ಉಳಿಸಲಾಗಿದೆ ಎನಿಸುತ್ತದೆ", "dup_confirm": "ಹಾಗಿದ್ದರೂ ಉಳಿಸಿ",
        "kind_label": "ರೀತಿ", "merchant_label": "ಅಂಗಡಿ", "mode_label": "ಪಾವತಿ",
        "income_label": "ಆದಾಯ", "paid_by": "ಮಾರ್ಗ",
        "pace_note": "🔮 ಈ ವೇಗದಲ್ಲಿ ಈ ತಿಂಗಳು {amount} ವರೆಗೆ ತಲುಪಬಹುದು.",
        "cross_note": " ಬಡ್ಜೆಟ್ {date} ಸುಮಾರಿಗೆ ದಾಟುತ್ತದೆ.",
        "anomaly_header": "ಅಸಾಮಾನ್ಯ ಖರ್ಚುಗಳು",
        "anomaly_hint": "ಪ್ರತಿಯೊಂದೂ ತನ್ನ ವರ್ಗದ ಸಾಮಾನ್ಯ ಖರ್ಚಿಗಿಂತ ಕನಿಷ್ಠ 3 ಪಟ್ಟು.",
        "sms_header": "ಬ್ಯಾಂಕ್ SMS ಅಂಟಿಸಿ",
        "sms_hint": "ಉದಾ: \"Rs 450 debited at Swiggy\" — ಇದು ನಮೂದಾಗುತ್ತದೆ.",
        "no_amount": "ಮೊತ್ತ ಸಿಗಲಿಲ್ಲ. 'chai 20' ಅಥವಾ 'dedh sau (150)' ಪ್ರಯತ್ನಿಸಿ.",
        "personal_expenses": "ನನ್ನ ಖರ್ಚುಗಳು", "khata_entries": "ಖಾತೆ ನಮೂದುಗಳು",
        "whatsapp_hint": "📲 ಅಥವಾ ವಾಟ್ಸಪ್ ಧ್ವನಿ ಟಿಪ್ಪಣಿ ಕಳುಹಿಸಿ (OGG, M4A, MP3, WAV)",
        "listening": "Gnani Prisma ನಿಮ್ಮ ಧ್ವನಿ ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳುತ್ತಿದೆ...",
        "stt_failed": "ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ಮೈಕ್ ಹತ್ತಿರ ಮಾತನಾಡಿ.",
        "technical": "ತಾಂತ್ರಿಕ ವಿವರಗಳು",
        "no_pending": "ಬಾಕಿ ಖಾತೆ ನಮೂದುಗಳಿಲ್ಲ. 'Ravi ko 500 udhar diya' ಹೇಳಿ ಅಥವಾ ಕೆಳಗೆ ಸೇರಿಸಿ.",
        "khata_added": "ಖಾತೆ ನಮೂದು ಸೇರಿಸಲಾಗಿದೆ",
        "interpreting": "Prisma ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳುತ್ತಿದೆ...",
        "ask_failed": "ಪ್ರಶ್ನೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಕೆಳಗೆ ಟೈಪ್ ಮಾಡಿ.",
        "undone": "ರದ್ದುಮಾಡಲಾಗಿದೆ", "redo": "↩ ಮತ್ತೆ",
        "budget_used": "{spent} / {budget} ಬಳಸಲಾಗಿದೆ ({pct}%) · {days} ದಿನ ಬಾಕಿ · ದಿನಕ್ಕೆ {per_day} ಆದರೆ ಬಡ್ಜೆಟ್ ಒಳಗೆ ಇರುತ್ತೀರಿ",
        "over_budget": "⚠️ ಬಡ್ಜೆಟ್‌ಗಿಂತ {amount} ಹೆಚ್ಚು. ಸ್ವಲ್ಪ ನಿಲ್ಲಿಸಿ.",
        "nudge_note": "ಬಡ್ಜೆಟ್‌ನ {pct}% ಬಳಸಿದ್ದೀರಿ, ಇನ್ನೂ {days} ದಿನ ಉಳಿದಿದೆ.",
        "on_track": "💚 ಸರಿಯಾದ ದಾರಿಯಲ್ಲಿದ್ದೀರಿ — ಈ ತಿಂಗಳು {amount} ಉಳಿಯುತ್ತದೆ.",
        "tagline": "ಏನು ಖರ್ಚು ಮಾಡಿದಿರಿ ಹೇಳಿ. Gnani Prisma ನಿಂದ ಬರೆಯಲಾಗುತ್ತದೆ.",
        "help": "ಸಹಾಯ",
        "help_body": """**ನೀವು ಏನು ಹೇಳಬಹುದು**
- `aaj chai 20, auto 80, lunch dedh sau` — ಒಂದೇ ಉಸಿರಿನಲ್ಲಿ ಹಲವು ಖರ್ಚು
- `kal metro 40` — *kal* / *parso* / *yesterday* ಮೂಲಕ ಹಿಂದಿನ ದಿನಾಂಕ
- `Ravi ko 500 udhar diya` — ಖಾತೆ ನಮೂದು, ನಂತರ ಇತ್ಯರ್ಥ ಮಾಡಿ
- `is mahine kitna kharch hua?` — ಧ್ವನಿಯಿಂದ ಕೇಳಿ
- `dedh sau` (150), `dhai hazar` (2500), `paanch sau` (500) ಎಲ್ಲವೂ ಕೆಲಸ ಮಾಡುತ್ತವೆ

**ಸಲಹೆಗಳು**
- Prisma ತಪ್ಪಾಗಿ ಕೇಳಿಸಿಕೊಂಡರೆ ಉಳಿಸುವ ಮೊದಲು ಟ್ರಾನ್ಸ್‌ಕ್ರಿಪ್ಟ್ ಸರಿಪಡಿಸಿ.
- ಡೇಟಾ ಎಲ್ಲಾ ಈ ಸಾಧನದ SQLiteನಲ್ಲಿದೆ; ಸೈಡ್‌ಬಾರ್‌ನಿಂದ ಯಾವಾಗ ಬೇಕಾದರೂ ಎಕ್ಸ್‌ಪೋರ್ಟ್ ಮಾಡಿ.""",
        "db_counts": "📦 {expenses} ಖರ್ಚುಗಳು · 📒 {khata} ಖಾತೆ ನಮೂದುಗಳು",
        "avg_help": "ಈ ತಿಂಗಳು ಕಳೆದ ದಿನಗಳ ಸರಾಸರಿ ಖರ್ಚು",
        "chips": ["🍵 ಟೀ", "🛺 ಆಟೋ", "🍱 ಊಟ", "💡 ರೀಚಾರ್ಜ್", "📚 ಜೆರಾಕ್ಸ್", "🥬 ತರಕಾರಿ"],
        "added": "{item} ಸೇರಿಸಲಾಗಿದೆ",
        "item_placeholder": "ಟೀ, ಆಟೋ, ಔಷಧ...",
        "lent_option": "ಸಾಲ ಕೊಟ್ಟೆ", "borrowed_option": "ಸಾಲ ತಗೊಂಡೆ",
        "status_label": "ಸ್ಥಿತಿ",
        "col_item": "ವಸ್ತು", "col_total": "ಒಟ್ಟು", "col_times": "ಸಲ", "col_usual": "ಸಾಮಾನ್ಯ",
        "streak_day": "{days} ದಿನ", "streak_days": "{days} ದಿನಗಳು",
        "delta_more": "📈 ಕಳೆದ ತಿಂಗಳಿಗಿಂತ {pct}% ಹೆಚ್ಚು (ಆಗ {then}, ಈಗ {now}).",
        "delta_less": "📉 ಕಳೆದ ತಿಂಗಳಿಗಿಂತ {pct}% ಕಡಿಮೆ (ಆಗ {then}, ಈಗ {now}).",
        "pattern_empty": "ಇನ್ನೂ ಕೆಲವು ದಿನ ದಾಖಲಿಸಿ, ವಾರದ ಮಾದರಿ ಕಾಣುತ್ತದೆ.",
        "updated_entries": "{n} ನಮೂದುಗಳು ನವೀಕರಿಸಲಾಗಿದೆ", "deleted_entries": "{n} ನಮೂದುಗಳು ಅಳಿಸಲಾಗಿದೆ",
        "ask_samples": [
            "ಈ ತಿಂಗಳು ಎಷ್ಟು ಖರ್ಚು?", "ಟೀಗೆ ಎಷ್ಟು ಹೋಯಿತು?",
            "ಬಡ್ಜೆಟ್ ಎಷ್ಟು ಉಳಿದಿದೆ?", "ಅತಿ ಹೆಚ್ಚು ಖರ್ಚು ಯಾವುದು?",
        ],
        "lbl_transcript": "ಟ್ರಾನ್ಸ್‌ಕ್ರಿಪ್ಟ್", "lbl_upload": "ಆಡಿಯೊ ಅಪ್‌ಲೋಡ್",
        "lbl_type": "ಖರ್ಚು ಟೈಪ್ ಮಾಡಿ", "lbl_sms": "ಬ್ಯಾಂಕ್ SMS",
        "lbl_record": "ನಿಮ್ಮ ಖರ್ಚು ಹೇಳಿ", "lbl_ask_mic": "ಪ್ರಶ್ನೆ ಕೇಳಿ",
        "lbl_ask": "ನಿಮ್ಮ ಹಣದ ಬಗ್ಗೆ ಕೇಳಿ", "chart_amount": "ಮೊತ್ತ (₹)",
        "auto_detect": "🎧 ಮಾತನಾಡಿದ ಭಾಷೆಯನ್ನು ತಾನೇ ಗುರುತಿಸಿ",
        "auto_detect_hint": "ನೀವು ಹಿಂದಿ, ತೆಲುಗು ಅಥವಾ ಇಂಗ್ಲಿಷ್ ಮಾತನಾಡಿದಿರಾ ಎಂದು Prisma ತಾನೇ ಗುರುತಿಸುತ್ತದೆ — ಆಯ್ಕೆ ಮಾಡಬೇಕಿಲ್ಲ.",
        "heard_lang": "🗣️ ಕೇಳಿದ ಭಾಷೆ: {lang}",
    },
}

#: Canonical item behind each one-tap chip; the visible label is translated.
CHIP_ITEMS = [
    (20.0, "Food", "Chai"),
    (80.0, "Travel", "Auto"),
    (150.0, "Food", "Lunch"),
    (299.0, "Bills", "Recharge"),
    (30.0, "Education", "Xerox"),
    (60.0, "Groceries", "Sabzi"),
]

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

# ---------------- LANGUAGE + HEADER ----------------
lang_choice = st.segmented_control(
    "Language / भाषा / భాష",
    options=list(config.LANGUAGES.keys()),
    default=config.DEFAULT_LANGUAGE,
    label_visibility="collapsed",
) or config.DEFAULT_LANGUAGE
lang_code = config.LANGUAGES.get(lang_choice, "hi-IN")
T = {**UI[lang_code], **EXTRA.get(lang_code, {})}
CAT = CAT_LABELS.get(lang_code, CAT_LABELS["en-IN"])
voice_ready = config.api_key_configured()

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(
        f"<h2 style='margin:0; font-weight:800; color:#0F766E;'>🎙️ {T['title']}</h2>",
        unsafe_allow_html=True,
    )
    st.caption(T["tagline"])
with col_h2:
    with st.popover(f"ℹ️ {T['help']}"):
        st.markdown(T["help_body"])


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
        st.caption(T["db_counts"].format(expenses=stats["count"], khata=len(udhar_df)))

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
    help=T["avg_help"],
)
if budget > 0:
    m3.metric(T["safe_today"], insights.inr(budget_info["per_day"]))
else:
    m3.metric(T["month"], insights.inr(stats["month"]))

if not voice_ready:
    st.info(T["no_voice"])

auto_speech = st.checkbox(
    T["auto_detect"], value=True, key="auto_speech",
    help=T["auto_detect_hint"],
)


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
        st.markdown(f"##### 🛒 {T['personal_expenses']}")
        preview = pd.DataFrame(rows)
        preview["amount"] = preview["amount"].map(insights.inr)
        preview["category"] = preview["category"].map(lambda c: f"{CAT_EMOJI.get(c, '📦')} {CAT.get(c, c)}")
        st.dataframe(
            preview[
                ["date", "item", "amount", "category", "merchant", "payment_mode", "kind"]
            ].rename(
                columns={
                    "date": T["date"],
                    "item": T["col_item"],
                    "amount": T["amount"],
                    "category": T["category"],
                    "merchant": T["merchant_label"],
                    "payment_mode": T["mode_label"],
                    "kind": T["kind_label"],
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    if udhar_rows:
        st.markdown(f"##### 🤝 {T['khata_entries']}")
        preview = pd.DataFrame(udhar_rows)
        preview["amount"] = preview["amount"].map(insights.inr)
        preview = preview.rename(
            columns={
                "date": T["date"], "person": T["person"], "amount": T["amount"],
                "type": T["type"], "status": T["status_label"],
            }
        )
        st.dataframe(preview, use_container_width=True, hide_index=True)


def duplicate_guard(rows: list[dict], key: str) -> bool:
    """Warn about a repeat entry and require an explicit confirmation."""
    dupes = store.recent_duplicates(rows)
    if not dupes:
        return True
    names = ", ".join(f"#{d['id']} {d['item']} {insights.inr(d['amount'])}" for d in dupes)
    st.warning(f"{T['dup_warn']}: {names}")
    return st.checkbox(T["dup_confirm"], key=f"{key}_dup")


def review_block(widget_key: str, source: str) -> None:
    """Editable transcript review + save, shared by the voice flows."""
    if not st.session_state.get(widget_key, "").strip():
        return
    st.markdown(f"#### 📝 {T['heard']}")
    edited = st.text_area(T["lbl_transcript"], height=90, key=widget_key, label_visibility="collapsed")
    rows, udhar_rows = parse_expenses(edited, today)

    if not rows and not udhar_rows:
        st.warning(T["no_amount"])
        return

    render_parsed(rows, udhar_rows)
    can_save = duplicate_guard(rows, widget_key)
    col_save, col_redo = st.columns([3, 1])
    if col_save.button(
        f"✅ {T['save']} ({len(rows) + len(udhar_rows)})",
        type="primary",
        key=f"{widget_key}_save",
        use_container_width=True,
        disabled=not can_save,
    ):
        save_rows(rows, udhar_rows, source)
    if col_redo.button(T["redo"], key=f"{widget_key}_redo", use_container_width=True):
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
    audio = st.audio_input(T["lbl_record"], key="mic", label_visibility="collapsed")
    with st.expander(T["whatsapp_hint"]):
        upload = st.file_uploader(
            T["lbl_upload"],
            type=["ogg", "opus", "oga", "m4a", "mp3", "wav", "aac", "flac"],
            label_visibility="collapsed",
        )

    active_audio = audio or upload
    if active_audio is not None and voice_ready:
        payload = active_audio.getvalue()
        digest = hashlib.md5(payload).hexdigest()
        if st.session_state.get("last_audio") != digest:
            try:
                with st.spinner(T["listening"]):
                    label = getattr(active_audio, "name", "") or getattr(active_audio, "type", "")
                    result = transcribe_detailed(
                        payload, label, "" if auto_speech else lang_code
                    )
                st.session_state["voice_text"] = result.text
                st.session_state["voice_lang"] = result.language
                st.session_state["last_audio"] = digest
            except SttError as exc:
                st.session_state["last_audio"] = digest
                st.session_state["voice_text"] = ""
                st.warning(T["stt_failed"])
                with st.expander(T["technical"]):
                    st.code(str(exc))

    if st.session_state.get("voice_text"):
        heard_lang = st.session_state.get("voice_lang")
        if heard_lang:
            st.caption(
                T["heard_lang"].format(
                    lang=config.LANGUAGE_NAMES.get(heard_lang, heard_lang)
                )
            )
        review_block("voice_text", "voice")
    else:
        st.caption(f"💡 {T['example']}")
    st.caption(T["privacy"])

# ---------------- TAB 2: TYPE / QUICK ADD ----------------
with tabs[1]:
    st.markdown(f"#### ⌨️ {T['type_header']}")
    typed = st.text_area(
        T["lbl_type"],
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
                disabled=not duplicate_guard(rows, "typed"),
            ):
                save_rows(rows, udhar_rows, "typed")
        else:
            st.warning(T["no_amount"])

    st.divider()
    st.markdown(f"##### ⚡ {T['one_tap']}")
    chip_cols = st.columns(3)
    for index, (amount, category, item) in enumerate(CHIP_ITEMS):
        label = T["chips"][index % len(T["chips"])]
        if chip_cols[index % 3].button(
            f"{label} · {insights.inr(amount)}", key=f"chip_{index}", use_container_width=True
        ):
            ids = store.add_expenses(
                [
                    {
                        "date": today.isoformat(),
                        "item": item,
                        "amount": amount,
                        "category": category,
                    }
                ],
                source="quick",
            )
            st.session_state["last_saved_ids"] = ids
            st.toast(T["added"].format(item=label), icon="⚡")
            st.rerun()

    st.divider()
    with st.expander(f"➕ {T['manual_header']}"):
        with st.form("manual_entry", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            item = c1.text_input(T["what"], placeholder=T["item_placeholder"])
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

    with st.expander(f"📩 {T['sms_header']}"):
        st.caption(T["sms_hint"])
        sms_text = st.text_area(
            T["lbl_sms"], key="sms_text", height=90, label_visibility="collapsed"
        )
        if sms_text.strip():
            sms_row = parse_bank_sms(sms_text, today)
            if sms_row is None:
                st.warning(T["no_amount"])
            else:
                render_parsed([sms_row], [])
                if st.button(
                    f"✅ {T['save']}",
                    key="sms_save",
                    type="primary",
                    use_container_width=True,
                ):
                    save_rows([sms_row], [], "sms")

# ---------------- TAB 3: KHATA ----------------
with tabs[2]:
    st.markdown(f"#### 📒 {T['udhar_header']}")
    current_udhar = store.udhar()
    pending = current_udhar[current_udhar["status"] == "Pending"] if not current_udhar.empty else current_udhar

    if not pending.empty:
        lent = pending.loc[pending["type"].astype(str).str.contains("Lent", na=False), "amount"].sum()
        taken = pending["amount"].sum() - lent
        k1, k2, k3 = st.columns(3)
        k1.metric(T["owe_me"], insights.inr(lent))
        k2.metric(T["i_owe"], insights.inr(taken))
        k3.metric(T["people_pending"], int(pending["person"].nunique()))
        shown = pending.assign(amount=pending["amount"].map(insights.inr))
        shown["type"] = shown["type"].map(
            lambda v: T["lent_option"] if str(v).startswith("Lent") else T["borrowed_option"]
        )
        shown["status"] = shown["status"].map(
            lambda v: T["settled"] if str(v) == "Settled" else T["pending"]
        )
        columns = ["date", "person", "amount", "type", "status"]
        labels = {
            "date": T["date"], "person": T["person"], "amount": T["amount"],
            "type": T["type"], "status": T["status_label"],
        }
        if "remaining" in pending.columns:
            shown["remaining"] = pending["remaining"].map(insights.inr)
            columns = ["date", "person", "amount", "remaining", "type", "status"]
            labels["remaining"] = T["remaining"]
        st.dataframe(shown[columns].rename(columns=labels), use_container_width=True, hide_index=True)
    else:
        st.info(T["no_pending"])

    with st.expander(f"➕ {T['add_khata']}"):
        with st.form("khata_form", clear_on_submit=True):
            p1, p2 = st.columns([2, 1])
            person = p1.text_input(T["person"], placeholder="Ravi")
            khata_amount = p2.number_input(
                T["amount"], min_value=0.0, step=50.0, format="%.2f"
            )
            p3, p4 = st.columns([1, 1])
            entry_type = p3.selectbox(
                T["type"],
                ["Lent (Diya)", "Borrowed (Liya)"],
                format_func=lambda value: (
                    T["lent_option"] if str(value).startswith("Lent") else T["borrowed_option"]
                ),
            )
            khata_date = p4.date_input(T["date"], value=today, key="khata_date")
            add_khata = st.form_submit_button(
                T["add_entry"], type="primary", use_container_width=True
            )
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
                    st.toast(T["khata_added"], icon="✅")
                    st.rerun()
                else:
                    st.warning(T["need_khata"])

    if not current_udhar.empty:
        st.markdown(f"##### {T['all_entries']}")
        ledger = current_udhar.copy()
        ledger["type"] = ledger["type"].map(
            lambda v: T["lent_option"] if str(v).startswith("Lent") else T["borrowed_option"]
        )
        ledger["status"] = ledger["status"].map(
            lambda v: T["settled"] if str(v) == "Settled" else T["pending"]
        )
        ledger.insert(0, "select", False)
        edited_ledger = st.data_editor(
            ledger[["select", "id", "date", "person", "amount", "type", "status"]],
            hide_index=True,
            use_container_width=True,
            disabled=["id", "date", "person", "amount", "type", "status"],
            column_config={
                "select": st.column_config.CheckboxColumn("✓", width="small"),
                "id": st.column_config.NumberColumn("ID", width="small"),
                "date": st.column_config.TextColumn(T["date"]),
                "person": st.column_config.TextColumn(T["person"]),
                "amount": st.column_config.NumberColumn(T["amount"], format="₹%.2f"),
                "type": st.column_config.TextColumn(T["type"]),
                "status": st.column_config.TextColumn(T["status_label"]),
            },
            key="ledger_editor",
        )
        selected = [int(i) for i in edited_ledger.loc[edited_ledger["select"] == True, "id"]]
        b1, b2, b3 = st.columns(3)
        if b1.button(f"✅ {T['settle']}", disabled=not selected, use_container_width=True):
            store.set_udhar_status(selected, "Settled")
            st.toast(T["settled_toast"], icon="✅")
            st.rerun()
        if b2.button("↩ " + T["pending"], disabled=not selected, use_container_width=True):
            store.set_udhar_status(selected, "Pending")
            st.toast(T["reopen_toast"], icon="↩")
            st.rerun()
        if b3.button(f"🗑️ {T['delete']}", disabled=not selected, use_container_width=True):
            store.delete_udhar(selected)
            st.toast(T["deleted"], icon="🗑️")
            st.rerun()

# ---------------- TAB 4: INSIGHTS ----------------
with tabs[3]:
    st.markdown(f"#### 📊 {T['insight_header']}")
    if expenses_df.empty:
        st.info(T["empty_msg"])
    else:
        st.markdown(
            f'<div class="insight-card">'
            f'{insights.weekly_insight(expenses_df, today, lang_code, CAT)}</div>',
            unsafe_allow_html=True,
        )

        if budget > 0:
            st.progress(min(1.0, max(0.0, budget_info["pct"] / 100)))
            st.caption(
                T["budget_used"].format(
                    spent=insights.inr(stats["month"]),
                    budget=insights.inr(budget),
                    pct=f"{budget_info['pct']:.0f}",
                    days=budget_info["days_left"],
                    per_day=insights.inr(budget_info["per_day"]),
                )
            )
            if budget_info["level"] == "over":
                over_text = T["over_budget"].format(
                    amount=insights.inr(abs(budget_info["remaining"]))
                )
                st.markdown(
                    f'<div class="budget-badge" style="background:#FEE2E2; '
                    f'border-color:#EF4444; color:#B91C1C;">{over_text}</div>',
                    unsafe_allow_html=True,
                )
            elif budget_info["level"] in ("alert", "nudge"):
                icon = "⚠️" if budget_info["level"] == "alert" else "🔔"
                nudge_text = T["nudge_note"].format(
                    pct=f"{budget_info['pct']:.0f}", days=budget_info["days_left"]
                )
                st.markdown(
                    f'<div class="budget-badge">{icon} {nudge_text}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption(
                    T["on_track"].format(amount=insights.inr(budget_info["remaining"]))
                )

        pace = insights.forecast(expenses_df, budget, today)
        if pace["spent"] > 0:
            note = T["pace_note"].format(amount=insights.inr(pace["projected"]))
            if pace["cross_on"] is not None:
                note += T["cross_note"].format(date=pace["cross_on"].strftime("%d %b"))
            st.caption(note)

        flagged = insights.anomalies(expenses_df, today)
        if not flagged.empty:
            with st.expander(f"⚠️ {T['anomaly_header']} ({len(flagged)})"):
                st.caption(T["anomaly_hint"])
                st.dataframe(
                    flagged.assign(
                        amount=flagged["amount"].map(insights.inr),
                        usual=flagged["usual"].map(insights.inr),
                    )
                    .assign(category=flagged["category"].map(lambda c: CAT.get(c, c)))
                    .rename(
                        columns={
                            "date": T["date"], "item": T["col_item"],
                            "amount": T["amount"], "category": T["category"],
                            "usual": T["col_usual"], "times": T["col_times"],
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

        delta = stats["delta_pct"]
        if stats["prev_month"] > 0:
            key = "delta_more" if delta > 0 else "delta_less"
            st.caption(
                T[key].format(
                    pct=f"{abs(delta):.0f}",
                    then=insights.inr(stats["prev_month"]),
                    now=insights.inr(stats["month"]),
                )
            )

        st.markdown(f"##### 📈 {T['last_14']}")
        daily = insights.daily_totals(expenses_df, 14, today).rename(
            columns={"amount": T["chart_amount"]}
        )
        st.line_chart(daily, color="#0F766E", height=200)

        cat_totals = insights.category_totals(expenses_df, today)
        if not cat_totals.empty:
            st.markdown(f"##### 🏷️ {T['by_category']}")
            # Horizontal bars keep long Telugu/Hindi category names readable.
            st.bar_chart(
                cat_totals.rename(index=lambda c: CAT.get(c, c)),
                color="#0F766E",
                height=240,
                horizontal=True,
            )

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"##### 💸 {T['top_items']}")
            best = insights.top_items(expenses_df, 5, today)
            if best.empty:
                st.caption(T["no_items"])
            else:
                st.dataframe(
                    best.assign(amount=best["amount"].map(insights.inr)).rename(
                        columns={
                            "item": T["col_item"],
                            "amount": T["col_total"],
                            "count": T["col_times"],
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
        with col_b:
            st.markdown(f"##### 🗓️ {T['patterns']}")
            pattern = insights.weekday_insight(expenses_df, today, lang_code)
            st.write(pattern or T["pattern_empty"])
            streak = insights.logging_streak(expenses_df, today)
            streak_key = "streak_day" if streak == 1 else "streak_days"
            st.metric(T["streak"], T[streak_key].format(days=streak))

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
        month_pick = f1.selectbox(T["month_filter"], [T["all_option"]] + months)
        category_pick = f2.multiselect(
            T["category"], CATEGORY_CHOICES, format_func=lambda c: CAT.get(c, c)
        )
        search = f3.text_input(T["search_item"], placeholder="chai")

        view = working
        if month_pick != T["all_option"]:
            view = view[view["date"].dt.strftime("%Y-%m") == month_pick]
        if category_pick:
            view = view[view["category"].isin(category_pick)]
        if search.strip():
            view = view[view["item"].str.contains(search.strip(), case=False, regex=False)]

        st.caption(f"{len(view)} {T['entries']} · {insights.inr(view['amount'].sum())}")

        if view.empty:
            st.info(T["no_match"])
        else:
            editable = view[
                ["id", "date", "item", "amount", "category", "merchant", "payment_mode", "source"]
            ].copy()
            editable["date"] = editable["date"].dt.date
            # Show category names in the chosen language, store the canonical key.
            cat_reverse = {label: key for key, label in CAT.items()}
            editable["category"] = editable["category"].map(lambda c: CAT.get(c, c))
            editable.insert(0, "select", False)
            original = editable.set_index("id")

            edited = st.data_editor(
                editable,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "select": st.column_config.CheckboxColumn("✓", width="small"),
                    "id": st.column_config.NumberColumn("ID", width="small", disabled=True),
                    "date": st.column_config.DateColumn(T["date"], format="DD-MM-YYYY"),
                    "amount": st.column_config.NumberColumn(
                        T["amount"], format="₹%.2f", min_value=0.0
                    ),
                    "category": st.column_config.SelectboxColumn(
                        T["category"], options=[CAT[c] for c in CATEGORY_CHOICES]
                    ),
                    "merchant": st.column_config.TextColumn(
                        T["merchant_label"], disabled=True, width="small"
                    ),
                    "payment_mode": st.column_config.TextColumn(
                        T["paid_by"], disabled=True, width="small"
                    ),
                    "source": st.column_config.TextColumn(
                        T["paid_by"], disabled=True, width="small"
                    ),
                },
                key="history_editor",
            )

            selected_rows = [int(i) for i in edited.loc[edited["select"] == True, "id"]]
            c1, c2 = st.columns(2)
            if c1.button(f"💾 {T['save_edits']}", type="primary", use_container_width=True):
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
                        updates["category"] = cat_reverse.get(row["category"], row["category"])
                    if updates:
                        store.update_expense(int(row["id"]), **updates)
                        changed += 1
                st.toast(T["updated_entries"].format(n=changed), icon="💾")
                st.rerun()
            if c2.button(
                f"🗑️ {T['delete_selected']}",
                disabled=not selected_rows,
                use_container_width=True,
            ):
                removed = store.delete_expenses(selected_rows)
                st.toast(T["deleted_entries"].format(n=removed), icon="🗑️")
                st.rerun()

# ---------------- TAB 6: ASK ----------------
with tabs[5]:
    st.markdown(f"#### {T['ask_header']}")
    st.caption(T["ask_example"])

    if "ask_pending" in st.session_state:
        st.session_state["ask_question"] = st.session_state.pop("ask_pending")

    ask_audio = st.audio_input(T["lbl_ask_mic"], key="ask_mic", label_visibility="collapsed")
    if ask_audio is not None and voice_ready:
        payload = ask_audio.getvalue()
        digest = hashlib.md5(payload).hexdigest()
        if st.session_state.get("last_ask_audio") != digest:
            st.session_state["last_ask_audio"] = digest
            try:
                with st.spinner(T["interpreting"]):
                    result = transcribe_detailed(
                        payload, "query.wav", "" if auto_speech else lang_code
                    )
                    st.session_state["ask_question"] = result.text
                st.session_state["ask_lang"] = result.language
            except SttError as exc:
                st.warning(T["ask_failed"])
                with st.expander(T["technical"]):
                    st.code(str(exc))

    question = st.text_input(
        T["lbl_ask"],
        key="ask_question",
        placeholder=T["ask_placeholder"],
        label_visibility="collapsed",
    )

    samples = T["ask_samples"]
    sample_cols = st.columns(2)
    for index, sample in enumerate(samples):
        if sample_cols[index % 2].button(sample, key=f"sample_q_{index}", use_container_width=True):
            st.session_state["ask_pending"] = sample
            st.rerun()

    if question.strip():
        st.markdown(f"**{T['you_asked']}:** *\"{question.strip()}\"*")
        answer = insights.answer_query(
            question, expenses_df, udhar_df, budget=budget,
            today=today, lang=lang_code, cat_labels=CAT,
        )
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
        st.toast(T["undone"], icon="↩")
        st.rerun()
