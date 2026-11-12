"""Spending analytics and the multilingual voice Q&A engine."""

from __future__ import annotations

import calendar
import datetime as dt

import pandas as pd

from . import config
from .parser import CATEGORIES, word_in

MONTH_WORDS = ("is mahine", "is mahina", "this month", "इस महीने", "ఈ నెల", "e nel", "current month")
LAST_MONTH_WORDS = ("pichle mahine", "last month", "previous month", "पिछले महीने", "గత నెల")
TODAY_WORDS = ("aaj", "today", "आज", "ఈ రోజు", "eeroju", "నేడు")
WEEK_WORDS = ("is hafte", "this week", "hafte", "hafta", "week", "इस हफ्ते", "ఈ వారం")
BUDGET_WORDS = ("budget", "bacha", "bachega", "bachcha", "left", "remaining", "kitna bacha", "बजट", "బడ్జెట్")
UDHAR_WORDS = ("udhar", "khata", "baki", "baaki", "lent", "owe", "owes", "उधार", "అప్పు", "ఖాతా")
TOP_WORDS = ("top", "most", "sabse zyada", "sabse jyada", "highest", "बड़ा", "ఎక్కువ")
AVERAGE_WORDS = ("average", "per day", "roz", "daily", "औसत", "సగటు")
BIGGEST_WORDS = ("biggest", "largest", "sabse bada", "sabse mehnga", "highest single")
COUNT_WORDS = ("how many", "kitni", "kitne", "count", "number of")
PREV_WORDS = ("pichle hafte", "last week", "previous week")
FORECAST_WORDS = (
    "forecast", "projection", "projected", "end of month", "month end", "kitna hoga",
    "mahine ke end", "महीने के अंत", "నెల చివర",
)

WEEKDAY_NAMES = {
    "en-IN": {
        "Monday": "Monday", "Tuesday": "Tuesday", "Wednesday": "Wednesday",
        "Thursday": "Thursday", "Friday": "Friday", "Saturday": "Saturday", "Sunday": "Sunday",
    },
    "hi-IN": {
        "Monday": "सोमवार", "Tuesday": "मंगलवार", "Wednesday": "बुधवार",
        "Thursday": "गुरुवार", "Friday": "शुक्रवार", "Saturday": "शनिवार", "Sunday": "रविवार",
    },
    "te-IN": {
        "Monday": "సోమవారం", "Tuesday": "మంగళవారం", "Wednesday": "బుధవారం",
        "Thursday": "గురువారం", "Friday": "శుక్రవారం", "Saturday": "శనివారం", "Sunday": "ఆదివారం",
    },
    "bn-IN": {
        "Monday": "সোমবার", "Tuesday": "মঙ্গলবার", "Wednesday": "বুধবার",
        "Thursday": "বৃহস্পতিবার", "Friday": "শুক্রবার", "Saturday": "শনিবার", "Sunday": "রবিবার",
    },
    "ta-IN": {
        "Monday": "திங்கள்", "Tuesday": "செவ்வாய்", "Wednesday": "புதன்",
        "Thursday": "வியாழன்", "Friday": "வெள்ளி", "Saturday": "சனி", "Sunday": "ஞாயிறு",
    },
    "kn-IN": {
        "Monday": "ಸೋಮವಾರ", "Tuesday": "ಮಂಗಳವಾರ", "Wednesday": "ಬುಧವಾರ",
        "Thursday": "ಗುರುವಾರ", "Friday": "ಶುಕ್ರವಾರ", "Saturday": "ಶನಿವಾರ", "Sunday": "ಭಾನುವಾರ",
    },
    "ml-IN": {
        "Monday": "തിങ്കളാഴ്ച", "Tuesday": "ചൊവ്വാഴ്ച", "Wednesday": "ബുധനാഴ്ച",
        "Thursday": "വ്യാഴാഴ്ച", "Friday": "വെള്ളിയാഴ്ച", "Saturday": "ശനിയാഴ്ച", "Sunday": "ഞായറാഴ്ച",
    },
}

_I18N = {
    "en-IN": {
        "no_history": "Log your first expense to unlock weekly insights.",
        "weekday_heavy": "{day}s are your heaviest days, averaging {amount}.",
        "weekly": (
            "You spent {total} in the last 7 days; {top} was your biggest bucket "
            "at {amount}{item}.{streak}"
        ),
        "weekly_item": " (mostly {item})",
        "weekly_streak": " {days}-day logging streak — keep it going!",
        "scope_overall": "overall",
        "scope_month": "this month",
        "scope_today": "today",
        "scope_week": "in the last 7 days",
        "scope_prev_week": "last week",
        "scope_in": "in {label}",
        "ask_empty": "Ask me something like 'is mahine kitna kharch hua?' or 'chai pe kitna gaya?'.",
        "ask_nothing": "You have not recorded anything yet. Log an expense and ask me again.",
        "budget_unset": "Set a monthly budget in the sidebar and I will track what is left.",
        "budget_over": "You are over budget by {over}. {spent} spent of {budget} this month.",
        "budget_left": "{left} left of your {budget} budget, about {per_day} a day for the remaining {days} days.",
        "forecast_none": "Nothing is logged this month yet, so there is no pace to project.",
        "forecast_base": "At {pace} a day you are heading for {projected} this month",
        "forecast_cross": ", crossing your {budget} budget around {date}.",
        "forecast_inside": ", which stays inside your {budget} budget.",
        "forecast_end": ".",
        "khata_none_person": "Nothing pending with {person}. {amount} is already settled.",
        "khata_parts": "{person} {parts}.",
        "khata_owes": "owes you {amount}",
        "khata_you_owe": "you owe {amount}",
        "khata_settled": "Every khata entry is settled. Nothing pending.",
        "khata_summary": (
            "{owed} is pending to come back to you from {people} people, and you owe {taken}."
        ),
        "no_expenses": "No expenses {label}.",
        "average": "Your average is {avg} per day {label} ({total} over {days} days).",
        "biggest": "Your biggest expense {label} was {item} at {amount} on {date}.",
        "count": "You logged {count} expenses {label}, totalling {total}.",
        "topic_none": "Nothing recorded in {topic} {label}.",
        "topic": "{topic} cost you {amount} {label} across {count} entries ({share}% of your spending).",
        "top_overall": "Your top categories overall are {cats}.",
        "items": "You spent {amount} on {names} {label} across {count} entries.",
        "period": "You spent {total} {label} across {count} expenses. {top} topped the list at {amount}.",
    },
    "hi-IN": {
        "no_history": "साप्ताहिक जानकारी के लिए अपना पहला खर्च जोड़ें।",
        "weekday_heavy": "{day} को सबसे ज़्यादा खर्च होता है, औसतन {amount}।",
        "weekly": "पिछले 7 दिनों में आपने {total} खर्च किए; {top} सबसे ऊपर रहा — {amount}{item}।{streak}",
        "weekly_item": " (ज़्यादातर {item})",
        "weekly_streak": " {days} दिन का स्ट्रीक — ऐसे ही जारी रखें!",
        "scope_overall": "कुल मिलाकर",
        "scope_month": "इस महीने",
        "scope_today": "आज",
        "scope_week": "पिछले 7 दिनों में",
        "scope_prev_week": "पिछले हफ्ते",
        "scope_in": "{label} में",
        "ask_empty": "मुझसे पूछिए जैसे 'is mahine kitna kharch hua?' या 'chai pe kitna gaya?'।",
        "ask_nothing": "अभी कुछ दर्ज नहीं है। पहले कोई खर्च जोड़ें, फिर पूछिए।",
        "budget_unset": "साइडबार में मासिक बजट सेट करें, मैं बाकी रकम बताऊँगा।",
        "budget_over": "आप बजट से {over} आगे हैं। इस महीने {budget} में से {spent} खर्च हो चुका है।",
        "budget_left": "आपके {budget} बजट में {left} बचे हैं, बाकी {days} दिनों के लिए रोज़ करीब {per_day}।",
        "forecast_none": "इस महीने अभी कुछ दर्ज नहीं है, इसलिए अनुमान नहीं लगाया जा सकता।",
        "forecast_base": "रोज़ {pace} की रफ्तार से महीने के अंत तक करीब {projected} खर्च होगा",
        "forecast_cross": ", और आपका {budget} का बजट लगभग {date} तक पार हो सकता है।",
        "forecast_inside": ", जो आपके {budget} के बजट के अंदर रहेगा।",
        "forecast_end": "।",
        "khata_none_person": "{person} के साथ कुछ बकाया नहीं। {amount} पहले ही सेटल हो चुका है।",
        "khata_parts": "{person} {parts}।",
        "khata_owes": "को आपको {amount} देना है",
        "khata_you_owe": "को आपको {amount} देना है (आपका उधार)",
        "khata_settled": "हर खाता एंट्री सेटल है। कुछ भी बकाया नहीं।",
        "khata_summary": "{people} लोगों से आपको {owed} वापस मिलने बाकी हैं, और आपको {taken} देना है।",
        "no_expenses": "{label} कोई खर्च नहीं।",
        "average": "{label} आपका औसत रोज़ {avg} है ({days} दिनों में {total})।",
        "biggest": "{label} सबसे बड़ा खर्च {item} था — {amount}, {date} को।",
        "count": "{label} आपने {count} खर्च दर्ज किए, कुल {total}।",
        "topic_none": "{label} {topic} में कुछ दर्ज नहीं।",
        "topic": "{label} {topic} पर {amount} खर्च हुए, {count} एंट्री ({share}%)।",
        "top_overall": "कुल मिलाकर आपकी सबसे बड़ी श्रेणियाँ: {cats}।",
        "items": "{label} {names} पर {amount} खर्च हुए, {count} एंट्री में।",
        "period": "{label} आपने {count} खर्चों में {total} खर्च किए। {top} सबसे ऊपर रहा — {amount}।",
    },
    "te-IN": {
        "no_history": "వారపు అంతర్దృష్టుల కోసం మీ మొదటి ఖర్చును నమోదు చేయండి.",
        "weekday_heavy": "{day} రోజుల్లో ఎక్కువ ఖర్చు అవుతుంది, సగటు {amount}.",
        "weekly": "గత 7 రోజుల్లో మీరు {total} ఖర్చు చేశారు; {top} ఎక్కువ — {amount}{item}.{streak}",
        "weekly_item": " (చాలావరకు {item})",
        "weekly_streak": " {days} రోజుల స్ట్రీక్ — కొనసాగించండి!",
        "scope_overall": "మొత్తంగా",
        "scope_month": "ఈ నెల",
        "scope_today": "ఈ రోజు",
        "scope_week": "గత 7 రోజుల్లో",
        "scope_prev_week": "గత వారం",
        "scope_in": "{label}లో",
        "ask_empty": "నన్ను 'is mahine kitna kharch hua?' లేదా 'chai pe kitna gaya?' లాగా అడగండి.",
        "ask_nothing": "ఇంకా ఏమీ నమోదు కాలేదు. ముందుగా ఖర్చును జోడించి మళ్లీ అడగండి.",
        "budget_unset": "సైడ్‌బార్‌లో నెల బడ్జెట్ సెట్ చేయండి, మిగిలినది నేను చెబుతాను.",
        "budget_over": "మీరు బడ్జెట్ కంటే {over} ఎక్కువగా ఉన్నారు. ఈ నెల {budget}లో {spent} ఖర్చు చేశారు.",
        "budget_left": "మీ {budget} బడ్జెట్‌లో {left} మిగిలింది, మిగతా {days} రోజులకు రోజుకు సుమారు {per_day}.",
        "forecast_none": "ఈ నెల ఇంకా ఏమీ నమోదు కాలేదు, కాబట్టి అంచనా వేయలేము.",
        "forecast_base": "రోజుకు {pace} చొప్పున నెల చివరికి సుమారు {projected} అవుతుంది",
        "forecast_cross": ", మీ {budget} బడ్జెట్ సుమారు {date} నాటికి దాటవచ్చు.",
        "forecast_inside": ", ఇది మీ {budget} బడ్జెట్ లోపలే ఉంటుంది.",
        "forecast_end": ".",
        "khata_none_person": "{person}తో పెండింగ్ ఏమీ లేదు. {amount} ఇప్పటికే సెటిల్ అయింది.",
        "khata_parts": "{person} {parts}.",
        "khata_owes": "మీకు {amount} ఇవ్వాలి",
        "khata_you_owe": "మీరు {amount} ఇవ్వాలి",
        "khata_settled": "అన్ని ఖాతా ఎంట్రీలు సెటిల్ అయ్యాయి. పెండింగ్ ఏమీ లేదు.",
        "khata_summary": "{people} మంది మీకు {owed} ఇవ్వాల్సి ఉంది, మరియు మీరు {taken} ఇవ్వాలి.",
        "no_expenses": "{label} ఖర్చులు లేవు.",
        "average": "{label} మీ సగటు రోజుకు {avg} ({days} రోజుల్లో {total}).",
        "biggest": "{label} అతిపెద్ద ఖర్చు {item} — {amount}, {date}న.",
        "count": "{label} మీరు {count} ఖర్చులు నమోదు చేశారు, మొత్తం {total}.",
        "topic_none": "{label} {topic}లో ఏమీ నమోదు కాలేదు.",
        "topic": "{label} {topic}పై {amount} ఖర్చు చేశారు, {count} ఎంట్రీలు ({share}%).",
        "top_overall": "మొత్తంగా మీ అగ్ర వర్గాలు: {cats}.",
        "items": "{label} {names}పై {amount} ఖర్చు చేశారు, {count} ఎంట్రీలు.",
        "period": "{label} మీరు {count} ఖర్చుల్లో {total} ఖర్చు చేశారు. {top} అగ్రస్థానంలో — {amount}.",
    },
    "bn-IN": {
        "no_history": "সাপ্তাহিক বিশ্লেষণের জন্য প্রথম খরচ যোগ করুন।",
        "weekday_heavy": "{day} সবচেয়ে বেশি খরচ হয়, গড়ে {amount}।",
        "weekly": "গত ৭ দিনে আপনি {total} খরচ করেছেন; {top} সবচেয়ে বেশি — {amount}{item}।{streak}",
        "weekly_item": " (বেশিরভাগ {item})",
        "weekly_streak": " {days} দিনের স্ট্রিক — চালিয়ে যান!",
        "scope_overall": "সব মিলিয়ে",
        "scope_month": "এই মাসে",
        "scope_today": "আজ",
        "scope_week": "গত ৭ দিনে",
        "scope_prev_week": "গত সপ্তাহে",
        "scope_in": "{label}",
        "ask_empty": "আমাকে জিজ্ঞাসা করুন, যেমন 'is mahine kitna kharch hua?' বা 'chai pe kitna gaya?'।",
        "ask_nothing": "এখনও কিছু জমা নেই। আগে খরচ যোগ করে আবার জিজ্ঞাসা করুন।",
        "budget_unset": "সাইডবাবে মাসিক বাজেট দিন, বাকি টাকা আমি দেখাব।",
        "budget_over": "আপনি বাজেটের চেয়ে {over} বেশি। এই মাসে {budget}-এর মধ্যে {spent} খরচ হয়েছে।",
        "budget_left": "আপনার {budget} বাজেটে {left} বাকি, বাকি {days} দিনে দিনে প্রায় {per_day}।",
        "forecast_none": "এই মাসে এখনও কিছু নেই, তাই অনুমান করা যাচ্ছে না।",
        "forecast_base": "দিনে {pace} হারে মাসের শেষে প্রায় {projected} হবে",
        "forecast_cross": ", আর আপনার {budget} বাজেট প্রায় {date} নাগাদ পার হতে পারে।",
        "forecast_inside": ", যা আপনার {budget} বাজেটের মধ্যেই থাকবে।",
        "forecast_end": "।",
        "khata_none_person": "{person}-এর সাথে কিছু বাকি নেই। {amount} আগেই পরিশোধিত।",
        "khata_parts": "{person} {parts}।",
        "khata_owes": "আপনাকে {amount} দিতে হবে",
        "khata_you_owe": "আপনাকে {amount} দিতে হবে (আপনার ধার)",
        "khata_settled": "সব খাতা এন্ট্রি পরিশোধিত। কিছু বাকি নেই।",
        "khata_summary": "{people} জনের কাছে আপনার {owed} পাওনা, আর আপনাকে {taken} দিতে হবে।",
        "no_expenses": "{label} কোনো খরচ নেই।",
        "average": "{label} আপনার গড় প্রতিদিন {avg} ({days} দিনে {total})।",
        "biggest": "{label} সবচেয়ে বড় খরচ {item} — {amount}, {date}-এ।",
        "count": "{label} আপনি {count} খরচ লিখেছেন, মোট {total}।",
        "topic_none": "{label} {topic}-এ কিছু নেই।",
        "topic": "{label} {topic}-এ {amount} খরচ হয়েছে, {count} এন্ট্রি ({share}%)।",
        "top_overall": "সব মিলিয়ে আপনার শীর্ষ শ্রেণি: {cats}।",
        "items": "{label} {names}-এ {amount} খরচ হয়েছে, {count} এন্ট্রিতে।",
        "period": "{label} আপনি {count} খরচে {total} খরচ করেছেন। {top} শীর্ষে — {amount}।",
    },
    "ta-IN": {
        "no_history": "வாராந்திர பகுப்பாய்வுக்கு முதல் செலவைப் பதிவு செய்யுங்கள்.",
        "weekday_heavy": "{day} அன்று அதிகம் செலவாகிறது, சராசரி {amount}.",
        "weekly": "கடந்த 7 நாட்களில் {total} செலவு செய்தீர்கள்; {top} முதலிடம் — {amount}{item}.{streak}",
        "weekly_item": " (பெரும்பாலும் {item})",
        "weekly_streak": " {days} நாள் தொடர் — தொடருங்கள்!",
        "scope_overall": "மொத்தமாக",
        "scope_month": "இந்த மாதம்",
        "scope_today": "இன்று",
        "scope_week": "கடந்த 7 நாட்களில்",
        "scope_prev_week": "கடந்த வாரம்",
        "scope_in": "{label}",
        "ask_empty": "'is mahine kitna kharch hua?' அல்லது 'chai pe kitna gaya?' போல கேளுங்கள்.",
        "ask_nothing": "இன்னும் எதுவும் பதிவாகவில்லை. முதலில் செலவைச் சேர்த்து மீண்டும் கேளுங்கள்.",
        "budget_unset": "பக்கப் பலகையில் மாத பட்ஜெட்டை அமைக்கவும், மீதியை நான் சொல்கிறேன்.",
        "budget_over": "நீங்கள் பட்ஜெட்டை விட {over} அதிகம். இந்த மாதம் {budget} இல் {spent} செலவானது.",
        "budget_left": "உங்கள் {budget} பட்ஜெட்டில் {left} மீதம், மீதமுள்ள {days} நாட்களுக்கு நாளுக்கு சுமார் {per_day}.",
        "forecast_none": "இந்த மாதம் இன்னும் எதுவும் இல்லை, எனவே கணிக்க முடியாது.",
        "forecast_base": "நாளுக்கு {pace} வீதம் மாத இறுதியில் சுமார் {projected} ஆகும்",
        "forecast_cross": ", உங்கள் {budget} பட்ஜெட் {date} அளவில் தாண்டும்.",
        "forecast_inside": ", இது உங்கள் {budget} பட்ஜெட்டுக்குள் இருக்கும்.",
        "forecast_end": ".",
        "khata_none_person": "{person} உடன் நிலுவை இல்லை. {amount} ஏற்கனவே தீர்நது.",
        "khata_parts": "{person} {parts}.",
        "khata_owes": "உங்களுக்கு {amount} தர வேண்டும்",
        "khata_you_owe": "நீங்கள் {amount} தர வேண்டும்",
        "khata_settled": "அனைத்து கணக்கு பதிவுகளும் தீர்நது. நிலுவை இல்லை.",
        "khata_summary": "{people} பேரிடம் {owed} வரவேண்டியுள்ளது, நீங்கள் {taken} தர வேண்டும்.",
        "no_expenses": "{label} செலவுகள் இல்லை.",
        "average": "{label} உங்கள் சராசரி நாளுக்கு {avg} ({days} நாட்களில் {total}).",
        "biggest": "{label} மிகப்பெரிய செலவு {item} — {amount}, {date} அன்று.",
        "count": "{label} நீங்கள் {count} செலவுகளைப் பதிவு செய்தீர்கள், மொத்தம் {total}.",
        "topic_none": "{label} {topic} இல் எதுவும் இல்லை.",
        "topic": "{label} {topic} க்கு {amount} செலவானது, {count} பதிவுகள் ({share}%).",
        "top_overall": "மொத்தமாக உங்கள் முதன்மை வகைகள்: {cats}.",
        "items": "{label} {names} க்கு {amount} செலவானது, {count} பதிவுகளில்.",
        "period": "{label} நீங்கள் {count} செலவுகளில் {total} செலவு செய்தீர்கள். {top} முதலிடம் — {amount}.",
    },
    "kn-IN": {
        "no_history": "ವಾರದ ವಿಶ್ಲೇಷಣೆಗಾಗಿ ನಿಮ್ಮ ಮೊದಲ ಖರ್ಚು ಸೇರಿಸಿ.",
        "weekday_heavy": "{day} ಹೆಚ್ಚು ಖರ್ಚಾಗುತ್ತದೆ, ಸರಾಸರಿ {amount}.",
        "weekly": "ಕಳೆದ 7 ದಿನಗಳಲ್ಲಿ ನೀವು {total} ಖರ್ಚು ಮಾಡಿದ್ದೀರಿ; {top} ಮುಂಚೂಣಿಯಲ್ಲಿ — {amount}{item}.{streak}",
        "weekly_item": " (ಹೆಚ್ಚಾಗಿ {item})",
        "weekly_streak": " {days} ದಿನಗಳ ಸ್ಟ್ರೀಕ್ — ಮುಂದುವರಿಸಿ!",
        "scope_overall": "ಒಟ್ಟಾರೆ",
        "scope_month": "ಈ ತಿಂಗಳು",
        "scope_today": "ಇಂದು",
        "scope_week": "ಕಳೆದ 7 ದಿನಗಳಲ್ಲಿ",
        "scope_prev_week": "ಕಳೆದ ವಾರ",
        "scope_in": "{label}",
        "ask_empty": "'is mahine kitna kharch hua?' ಅಥವಾ 'chai pe kitna gaya?' ಎಂದು ಕೇಳಿ.",
        "ask_nothing": "ಇನ್ನೂ ಏನೂ ದಾಖಲಾಗಿಲ್ಲ. ಮೊದಲು ಖರ್ಚು ಸೇರಿಸಿ ಮತ್ತೆ ಕೇಳಿ.",
        "budget_unset": "ಸೈಡ್‌ಬಾರ್‌ನಲ್ಲಿ ಮಾಸಿಕ ಬಡ್ಜೆಟ್ ಹಾಕಿ, ಉಳಿದದ್ದನ್ನು ನಾನು ಹೇಳುತ್ತೇನೆ.",
        "budget_over": "ನೀವು ಬಡ್ಜೆಟ್‌ಗಿಂತ {over} ಹೆಚ್ಚಿದ್ದೀರಿ. ಈ ತಿಂಗಳು {budget} ರಲ್ಲಿ {spent} ಖರ್ಚಾಗಿದೆ.",
        "budget_left": "ನಿಮ್ಮ {budget} ಬಡ್ಜೆಟ್‌ನಲ್ಲಿ {left} ಉಳಿದಿದೆ, ಉಳಿದ {days} ದಿನಗಳಿಗೆ ದಿನಕ್ಕೆ ಸುಮಾರು {per_day}.",
        "forecast_none": "ಈ ತಿಂಗಳು ಇನ್ನೂ ಏನೂ ಇಲ್ಲ, ಹಾಗಾಗಿ ಅಂದಾಜು ಸಾಧ್ಯವಿಲ್ಲ.",
        "forecast_base": "ದಿನಕ್ಕೆ {pace} ದರದಲ್ಲಿ ತಿಂಗಳ ಕೊನೆಗೆ ಸುಮಾರು {projected} ಆಗುತ್ತದೆ",
        "forecast_cross": ", ಮತ್ತು ನಿಮ್ಮ {budget} ಬಡ್ಜೆಟ್ ಸುಮಾರು {date} ಗೆ ದಾಟಬಹುದು.",
        "forecast_inside": ", ಇದು ನಿಮ್ಮ {budget} ಬಡ್ಜೆಟ್ ಒಳಗೇ ಇರುತ್ತದೆ.",
        "forecast_end": ".",
        "khata_none_person": "{person} ಜೊತೆ ಬಾಕಿ ಇಲ್ಲ. {amount} ಈಗಾಗಲೇ ಇತ್ಯರ್ಥವಾಗಿದೆ.",
        "khata_parts": "{person} {parts}.",
        "khata_owes": "ನಿಮಗೆ {amount} ಕೊಡಬೇಕು",
        "khata_you_owe": "ನೀವು {amount} ಕೊಡಬೇಕು",
        "khata_settled": "ಎಲ್ಲಾ ಖಾತೆ ನಮೂದುಗಳು ಇತ್ಯರ್ಥವಾಗಿವೆ. ಬಾಕಿ ಇಲ್ಲ.",
        "khata_summary": "{people} ಜನರಿಂದ ನಿಮಗೆ {owed} ಬರಬೇಕು, ಮತ್ತು ನೀವು {taken} ಕೊಡಬೇಕು.",
        "no_expenses": "{label} ಖರ್ಚುಗಳಿಲ್ಲ.",
        "average": "{label} ನಿಮ್ಮ ಸರಾಸರಿ ದಿನಕ್ಕೆ {avg} ({days} ದಿನಗಳಲ್ಲಿ {total}).",
        "biggest": "{label} ದೊಡ್ಡ ಖರ್ಚು {item} — {amount}, {date} ರಂದು.",
        "count": "{label} ನೀವು {count} ಖರ್ಚು ದಾಖಲಿಸಿದ್ದೀರಿ, ಒಟ್ಟು {total}.",
        "topic_none": "{label} {topic} ನಲ್ಲಿ ಏನೂ ಇಲ್ಲ.",
        "topic": "{label} {topic} ಗೆ {amount} ಖರ್ಚಾಗಿದೆ, {count} ನಮೂದುಗಳು ({share}%).",
        "top_overall": "ಒಟ್ಟಾರೆ ನಿಮ್ಮ ಪ್ರಮುಖ ವರ್ಗಗಳು: {cats}.",
        "items": "{label} {names} ಗೆ {amount} ಖರ್ಚಾಗಿದೆ, {count} ನಮೂದುಗಳಲ್ಲಿ.",
        "period": "{label} ನೀವು {count} ಖರ್ಚುಗಳಲ್ಲಿ {total} ಖರ್ಚು ಮಾಡಿದ್ದೀರಿ. {top} ಮುಂಚೂಣಿಯಲ್ಲಿ — {amount}.",
    },
    "ml-IN": {
        "no_history": "ആഴ്ച വിശകലനത്തിന് ആദ്യ ചെലവ് ചേർക്കൂ.",
        "weekday_heavy": "{day} ഏറ്റവും കൂടുതൽ ചെലവ് വരുന്നു, ശരാശരി {amount}.",
        "weekly": "കഴിഞ്ഞ 7 ദിവസത്തിൽ {total} ചെലവിട്ടു; {top} മുന്നിൽ — {amount}{item}.{streak}",
        "weekly_item": " (കൂടുതലും {item})",
        "weekly_streak": " {days} ദിവസത്തെ തുടർച്ച — തുടരൂ!",
        "scope_overall": "ആകെ",
        "scope_month": "ഈ മാസം",
        "scope_today": "ഇന്ന്",
        "scope_week": "കഴിഞ്ഞ 7 ദിവസത്തിൽ",
        "scope_prev_week": "കഴിഞ്ഞ ആഴ്ച",
        "scope_in": "{label}",
        "ask_empty": "'is mahine kitna kharch hua?' അല്ലെങ്കിൽ 'chai pe kitna gaya?' എന്നു ചോദിക്കൂ.",
        "ask_nothing": "ഇതുവരെ ഒന്നും രേഖപ്പെടുത്തിയിട്ടില്ല. ആദ്യം ചെലവ് ചേർത്ത് വീണ്ടും ചോദിക്കൂ.",
        "budget_unset": "സൈഡ്ബാറിൽ മാസ ബജറ്റ് ഇടൂ, ബാക്കി ഞാൻ പറയാം.",
        "budget_over": "നിങ്ങൾ ബജറ്റിനേക്കാൾ {over} മുന്നിലാണ്. ഈ മാസം {budget} ൽ {spent} ചെലവായി.",
        "budget_left": "നിങ്ങളുടെ {budget} ബജറ്റിൽ {left} ബാക്കി, ബാക്കി {days} ദിവസത്തിന് ദിവസം ഏതാണ്ട് {per_day}.",
        "forecast_none": "ഈ മാസം ഇതുവരെ ഒന്നുമില്ല, അതിനാൽ അനുമാനിക്കാനാകില്ല.",
        "forecast_base": "ദിവസം {pace} എന്ന നിരക്കിൽ മാസാവസാനം ഏതാണ്ട് {projected} ആകും",
        "forecast_cross": ", നിങ്ങളുടെ {budget} ബജറ്റ് {date}-ഓടെ കവിയാം.",
        "forecast_inside": ", ഇത് നിങ്ങളുടെ {budget} ബജറ്റിനുള്ളിൽ നിൽക്കും.",
        "forecast_end": ".",
        "khata_none_person": "{person}-മായി ബാക്കിയില്ല. {amount} നേരത്തെ തീർത്തു.",
        "khata_parts": "{person} {parts}.",
        "khata_owes": "നിങ്ങൾക്ക് {amount} തരണം",
        "khata_you_owe": "നിങ്ങൾ {amount} കൊടുക്കണം",
        "khata_settled": "എല്ലാ കണക്ക് എൻട്രികളും തീർത്തു. ബാക്കിയില്ല.",
        "khata_summary": "{people} പേരിൽ നിന്ന് {owed} കിട്ടാനുണ്ട്, നിങ്ങൾ {taken} കൊടുക്കണം.",
        "no_expenses": "{label} ചെലവുകളില്ല.",
        "average": "{label} നിങ്ങളുടെ ശരാശരി ദിവസം {avg} ({days} ദിവസത്തിൽ {total}).",
        "biggest": "{label} ഏറ്റവും വലിയ ചെലവ് {item} — {amount}, {date}-ന്.",
        "count": "{label} നിങ്ങൾ {count} ചെലവുകൾ രേഖപ്പെടുത്തി, ആകെ {total}.",
        "topic_none": "{label} {topic}-ൽ ഒന്നുമില്ല.",
        "topic": "{label} {topic}-ന് {amount} ചെലവായി, {count} എൻട്രികൾ ({share}%).",
        "top_overall": "ആകെ നിങ്ങളുടെ പ്രധാന വിഭാഗങ്ങൾ: {cats}.",
        "items": "{label} {names}-ന് {amount} ചെലവായി, {count} എൻട്രികളിൽ.",
        "period": "{label} നിങ്ങൾ {count} ചെലവുകളിൽ {total} ചെലവിട്ടു. {top} മുന്നിൽ — {amount}.",
    },
}


def _tr(lang: str) -> dict:
    return _I18N.get(lang) or _I18N["en-IN"]


def _indian_group(value: float, decimals: int) -> str:
    """Group digits the Indian way: 1,00,000 rather than 100,000."""
    whole, _, fraction = f"{value:.{decimals}f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{whole}.{fraction}" if fraction else whole


def inr(amount: float) -> str:
    """Format a rupee amount in Indian grouping, with paise only when present."""
    raw = float(amount or 0)
    sign = "-" if raw < 0 else ""
    value = abs(raw)
    if abs(value - round(value)) < 0.005:
        return f"{sign}₹{_indian_group(value, 0)}"
    return f"{sign}₹{_indian_group(value, 2)}"


def _prep(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return a copy with parsed dates and numeric amounts."""
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=["id", "date", "item", "amount", "category"])
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"])
    if "amount" in out.columns:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)
    else:
        out["amount"] = 0.0
    if "category" not in out.columns:
        out["category"] = "Other"
    if "item" not in out.columns:
        out["item"] = "General"
    # Money coming in is not spending: keep it out of totals, charts and answers.
    if "kind" in out.columns:
        out = out[out["kind"].astype(str).str.lower() != "income"]
    return out


def month_frame(frame: pd.DataFrame, ref: dt.date) -> pd.DataFrame:
    if frame.empty:
        return frame
    return frame[(frame["date"].dt.month == ref.month) & (frame["date"].dt.year == ref.year)]


def shift_month(ref: dt.date, months: int = -1) -> dt.date:
    year = ref.year
    month = ref.month + months
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    day = min(ref.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def summary(expenses: pd.DataFrame, today: dt.date | None = None) -> dict:
    """Headline numbers used by the dashboard."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    stamp = pd.Timestamp(today)
    empty = {
        "today": 0.0, "month": 0.0, "week": 0.0, "prev_month": 0.0,
        "delta_pct": 0.0, "count": 0, "avg_per_day": 0.0, "top_category": None,
    }
    if frame.empty:
        return empty

    month = month_frame(frame, today)
    prev = month_frame(frame, shift_month(today))
    week = frame[frame["date"] >= stamp - dt.timedelta(days=6)]
    day_total = float(frame.loc[frame["date"] == stamp, "amount"].sum())
    month_total = float(month["amount"].sum())
    prev_total = float(prev["amount"].sum())

    top_category = month.groupby("category")["amount"].sum().idxmax() if not month.empty else None
    delta_pct = ((month_total - prev_total) / prev_total * 100) if prev_total > 0 else 0.0

    return {
        "today": day_total,
        "month": month_total,
        "week": float(week["amount"].sum()),
        "prev_month": prev_total,
        "delta_pct": delta_pct,
        "count": int(len(frame)),
        "avg_per_day": month_total / max(today.day, 1),
        "top_category": top_category,
    }


def budget_status(month_total: float, budget: float, today: dt.date | None = None) -> dict:
    """How much of the monthly budget is left, and how loud the nudge is."""
    today = today or dt.date.today()
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    if budget <= 0:
        return {"pct": 0.0, "remaining": 0.0, "days_left": days_left, "per_day": 0.0, "level": "off"}
    pct = month_total / budget * 100
    remaining = budget - month_total
    if remaining < 0:
        level = "over"
    elif pct >= config.ALERT_PCT:
        level = "alert"
    elif pct >= config.NUDGE_PCT:
        level = "nudge"
    else:
        level = "ok"
    return {
        "pct": pct, "remaining": remaining, "days_left": days_left,
        "per_day": max(remaining, 0.0) / days_left, "level": level,
    }


def forecast(expenses: pd.DataFrame, budget: float = 0.0, today: dt.date | None = None) -> dict:
    """Where this month lands if the current pace continues."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    month = month_frame(frame, today)
    spent = float(month["amount"].sum())
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    pace = spent / max(today.day, 1)
    projected = pace * days_in_month
    result = {
        "spent": spent, "pace": pace, "projected": projected,
        "days_in_month": days_in_month, "cross_on": None,
        "over_by": max(projected - budget, 0.0) if budget > 0 else 0.0,
    }
    if budget > 0 and pace > 0 and projected > budget:
        cross_day = int(budget // pace)
        if cross_day < days_in_month:
            cross_day = max(cross_day, today.day)
            result["cross_on"] = dt.date(today.year, today.month, cross_day)
    return result


def anomalies(
    expenses: pd.DataFrame, today: dt.date | None = None,
    factor: float = 3.0, minimum: int = 3,
) -> pd.DataFrame:
    """Expenses far above the usual size for their category this month."""
    today = today or dt.date.today()
    columns = ["date", "item", "amount", "category", "usual", "times"]
    month = month_frame(_prep(expenses), today)
    if month.empty:
        return pd.DataFrame(columns=columns)

    medians = month.groupby("category")["amount"].median()
    counts = month.groupby("category")["amount"].size()
    flagged = []
    for _, row in month.iterrows():
        category = row["category"]
        usual = float(medians.get(category, 0.0))
        if counts.get(category, 0) < minimum or usual <= 0:
            continue
        if row["amount"] >= usual * factor and row["amount"] > usual:
            flagged.append(
                {
                    "date": row["date"].date().isoformat(),
                    "item": row["item"], "amount": float(row["amount"]),
                    "category": category, "usual": round(usual, 2),
                    "times": round(float(row["amount"]) / usual, 1),
                }
            )
    return pd.DataFrame(flagged, columns=columns).sort_values("amount", ascending=False)


def category_totals(expenses: pd.DataFrame, today: dt.date | None = None) -> pd.Series:
    today = today or dt.date.today()
    month = month_frame(_prep(expenses), today)
    if month.empty:
        return pd.Series(dtype="float64")
    return month.groupby("category")["amount"].sum().sort_values(ascending=False)


def daily_totals(expenses: pd.DataFrame, days: int = 14, today: dt.date | None = None) -> pd.DataFrame:
    """One row per day (zero-filled) for the trend chart."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    start = pd.Timestamp(today) - dt.timedelta(days=days - 1)
    index = pd.date_range(start=start, end=pd.Timestamp(today), freq="D")
    index.name = "date"
    if frame.empty:
        return pd.DataFrame({"amount": 0.0}, index=index)
    window = frame[frame["date"] >= start]
    series = window.groupby(window["date"].dt.normalize())["amount"].sum()
    series = series.reindex(index, fill_value=0.0)
    return pd.DataFrame({"amount": series.astype(float)}, index=index)


def top_items(expenses: pd.DataFrame, n: int = 5, today: dt.date | None = None) -> pd.DataFrame:
    today = today or dt.date.today()
    month = month_frame(_prep(expenses), today)
    if month.empty:
        return pd.DataFrame(columns=["item", "amount", "count"])
    grouped = (
        month.groupby("item")
        .agg(amount=("amount", "sum"), count=("amount", "size"))
        .sort_values("amount", ascending=False)
        .head(n)
        .reset_index()
    )
    return grouped


def weekday_insight(
    expenses: pd.DataFrame, today: dt.date | None = None, lang: str = "en-IN"
) -> str | None:
    """Spot the weekly pattern, e.g. "Saturdays are your heaviest days"."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    start = pd.Timestamp(today) - dt.timedelta(days=27)
    recent = frame[frame["date"] >= start]
    if len(recent) < 6:
        return None
    totals = recent.groupby(recent["date"].dt.day_name())["amount"].mean().sort_values(ascending=False)
    if len(totals) < 3 or totals.iloc[0] <= 0:
        return None
    top_day = totals.index[0]
    day_name = (WEEKDAY_NAMES.get(lang) or WEEKDAY_NAMES["en-IN"]).get(top_day, top_day)
    return _tr(lang)["weekday_heavy"].format(day=day_name, amount=inr(totals.iloc[0]))


def weekly_insight(
    expenses: pd.DataFrame,
    today: dt.date | None = None,
    lang: str = "en-IN",
    cat_labels: dict[str, str] | None = None,
) -> str:
    """A single human sentence about the last seven days."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    tr = _tr(lang)
    if frame.empty:
        return tr["no_history"]

    start = pd.Timestamp(today) - dt.timedelta(days=6)
    week = frame[frame["date"] >= start]
    if week.empty:
        week = frame  # fall back to whatever history exists

    total = float(week["amount"].sum())
    by_category = week.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_category = by_category.index[0]
    top_amount = float(by_category.iloc[0])
    top_item_frame = week[week["category"] == top_category]
    item_note = ""
    if not top_item_frame.empty:
        item = top_item_frame.groupby("item")["amount"].sum().idxmax()
        if item and item != "General":
            item_note = tr["weekly_item"].format(item=item)

    streak = _logging_streak(frame, today)
    streak_note = tr["weekly_streak"].format(days=streak) if streak >= 2 else ""
    top_label = (cat_labels or {}).get(top_category, top_category)
    return tr["weekly"].format(
        total=inr(total), top=top_label, amount=inr(top_amount),
        item=item_note, streak=streak_note,
    )


def logging_streak(expenses: pd.DataFrame, today: dt.date | None = None) -> int:
    """Consecutive days (ending today) with at least one logged expense."""
    today = today or dt.date.today()
    return _logging_streak(_prep(expenses), today)


def _logging_streak(frame: pd.DataFrame, today: dt.date) -> int:
    if frame.empty:
        return 0
    days = set(frame["date"].dt.date)
    streak = 0
    cursor = today
    while cursor in days:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


# ---------------- VOICE Q&A ----------------


def _has(query: str, words: tuple[str, ...]) -> bool:
    return any(word_in(query, w) for w in words)


def _scope(expenses: pd.DataFrame, query: str, today: dt.date, lang: str = "en-IN"):
    """Narrow the data to the period the question talks about; returns (frame, label)."""
    tr = _tr(lang)
    if not expenses.empty:
        if _has(query, LAST_MONTH_WORDS):
            prev = shift_month(today)
            label = prev.strftime("%B %Y") if lang == "en-IN" else prev.strftime("%m/%Y")
            return month_frame(expenses, prev), tr["scope_in"].format(label=label)
        if _has(query, MONTH_WORDS):
            return month_frame(expenses, today), tr["scope_month"]
        if _has(query, TODAY_WORDS):
            return expenses[expenses["date"] == pd.Timestamp(today)], tr["scope_today"]
        if _has(query, PREV_WORDS):
            start = pd.Timestamp(today) - dt.timedelta(days=13)
            end = pd.Timestamp(today) - dt.timedelta(days=7)
            return expenses[(expenses["date"] >= start) & (expenses["date"] <= end)], tr["scope_prev_week"]
        if _has(query, WEEK_WORDS):
            start = pd.Timestamp(today) - dt.timedelta(days=6)
            return expenses[expenses["date"] >= start], tr["scope_week"]
    return expenses, tr["scope_overall"]


def _topic(query: str) -> str | None:
    for category, words in CATEGORIES.items():
        if category == "Udhar/Khata":
            continue
        if any(word_in(query, word) for word in words):
            return category
    return None


def _person_from_query(query: str, udhar: pd.DataFrame) -> str | None:
    if udhar.empty or "person" not in udhar.columns:
        return None
    for person in udhar["person"].dropna().unique():
        first = str(person).split()[0].lower()
        if len(first) >= 3 and word_in(query, first):
            return str(person)
    return None


def _item_match(scope: pd.DataFrame, query: str) -> pd.DataFrame:
    """Free-text item lookup: "chai pe kitna gaya" -> rows mentioning chai."""
    if scope.empty:
        return scope
    stop = {
        "how", "much", "did", "the", "and", "for", "kitna", "kitne", "kitni", "gaya",
        "gayi", "hua", "hui", "spent", "spend", "pe", "par", "ka", "ke", "ki", "ko",
        "is", "this", "month", "mahine", "today", "aaj", "week", "hafte", "on", "my",
        "total", "show", "what", "which", "was", "were", "i", "didi", "batao",
    }
    tokens = [t for t in str(query).lower().replace("?", " ").split() if t not in stop and len(t) >= 3]
    if not tokens:
        return scope.iloc[0:0]
    mask = scope["item"].astype(str).str.lower()
    combined = pd.Series(False, index=scope.index)
    for token in tokens:
        combined = combined | mask.str.contains(token, regex=False)
    return scope[combined]


def answer_query(
    query: str,
    expenses: pd.DataFrame,
    udhar: pd.DataFrame | None = None,
    budget: float = 0.0,
    today: dt.date | None = None,
    lang: str = "en-IN",
    cat_labels: dict[str, str] | None = None,
) -> str:
    """Answer a spoken-style question about spending, offline, in the chosen language."""
    today = today or dt.date.today()
    q = (query or "").lower().strip()
    frame = _prep(expenses)
    khata = udhar if udhar is not None else pd.DataFrame()
    tr = _tr(lang)

    if not q:
        return tr["ask_empty"]
    if frame.empty and (khata is None or len(khata) == 0):
        return tr["ask_nothing"]

    # 1. Budget question
    if _has(q, BUDGET_WORDS):
        if budget <= 0:
            return tr["budget_unset"]
        month_total = float(month_frame(frame, today)["amount"].sum())
        status = budget_status(month_total, budget, today)
        if status["level"] == "over":
            return tr["budget_over"].format(
                over=inr(abs(status["remaining"])), spent=inr(month_total), budget=inr(budget),
            )
        return tr["budget_left"].format(
            left=inr(status["remaining"]), budget=inr(budget),
            per_day=inr(status["per_day"]), days=status["days_left"],
        )

    # 2. Forecast question
    if _has(q, FORECAST_WORDS):
        pace = forecast(frame, budget, today)
        if pace["spent"] <= 0:
            return tr["forecast_none"]
        answer = tr["forecast_base"].format(pace=inr(pace["pace"]), projected=inr(pace["projected"]))
        if pace["cross_on"] is not None:
            answer += tr["forecast_cross"].format(budget=inr(budget), date=pace["cross_on"].strftime("%d %b"))
        elif budget > 0:
            answer += tr["forecast_inside"].format(budget=inr(budget))
        else:
            answer += tr["forecast_end"]
        return answer

    # 3. Udhar / khata question
    if _has(q, UDHAR_WORDS) and khata is not None and len(khata) > 0:
        pending = khata[khata["status"] == "Pending"] if "status" in khata else khata
        money = "remaining" if "remaining" in pending.columns else "amount"
        person = _person_from_query(q, khata)
        if person:
            person_rows = pending[pending["person"] == person]
            if person_rows.empty:
                settled = khata[(khata["person"] == person) & (khata["status"] == "Settled")]
                amount = float(settled["amount"].sum()) if not settled.empty else 0.0
                return tr["khata_none_person"].format(person=person, amount=inr(amount))
            owed = float(person_rows.loc[person_rows["type"].str.contains("Lent", na=False), money].sum())
            taken = float(person_rows[money].sum()) - owed
            parts = []
            if owed:
                parts.append(tr["khata_owes"].format(amount=inr(owed)))
            if taken:
                parts.append(tr["khata_you_owe"].format(amount=inr(taken)))
            joined = " and ".join(parts) if lang == "en-IN" else ", ".join(parts)
            out = tr["khata_parts"].format(person=person, parts=joined)
            return out.capitalize() if lang == "en-IN" else out
        if pending.empty:
            return tr["khata_settled"]
        owed_total = float(pending.loc[pending["type"].astype(str).str.contains("Lent", na=False), money].sum())
        taken_total = float(pending[money].sum()) - owed_total
        return tr["khata_summary"].format(
            owed=inr(owed_total), people=pending["person"].nunique(), taken=inr(taken_total),
        )

    scope, label = _scope(frame, q, today, lang)
    scope_total = float(scope["amount"].sum())

    # 4. Averages / biggest / counts
    if _has(q, AVERAGE_WORDS):
        if scope.empty:
            return tr["no_expenses"].format(label=label)
        days = max((scope["date"].max() - scope["date"].min()).days + 1, 1)
        return tr["average"].format(avg=inr(scope_total / days), label=label, total=inr(scope_total), days=days)

    if _has(q, BIGGEST_WORDS):
        if scope.empty:
            return tr["no_expenses"].format(label=label)
        row = scope.loc[scope["amount"].idxmax()]
        return tr["biggest"].format(
            label=label, item=row["item"], amount=inr(row["amount"]), date=row["date"].date(),
        )

    if _has(q, COUNT_WORDS):
        return tr["count"].format(count=len(scope), label=label, total=inr(scope_total))

    # 5. Category or item question inside the period
    topic = _topic(q)
    labels = cat_labels or {}
    if topic:
        matched = scope[scope["category"] == topic]
        if matched.empty:
            return tr["topic_none"].format(topic=labels.get(topic, topic), label=label)
        share = matched["amount"].sum() / scope_total * 100 if scope_total else 0
        return tr["topic"].format(
            topic=labels.get(topic, topic), amount=inr(matched["amount"].sum()),
            label=label, count=len(matched), share=f"{share:.0f}",
        )

    if label == tr["scope_overall"] and _has(q, TOP_WORDS) and not frame.empty:
        by_category = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_three = ", ".join(
            f"{labels.get(cat, cat)} {inr(amt)}" for cat, amt in by_category.head(3).items()
        )
        return tr["top_overall"].format(cats=top_three)

    item_rows = _item_match(scope, q)
    if item_rows is not None and len(item_rows) > 0:
        names = ", ".join(item_rows["item"].astype(str).value_counts().head(3).index)
        return tr["items"].format(amount=inr(item_rows["amount"].sum()), names=names, label=label, count=len(item_rows))

    # 6. Period total, or a friendly overall summary
    by_category = scope.groupby("category")["amount"].sum().sort_values(ascending=False)
    if scope.empty:
        return tr["no_expenses"].format(label=label)
    top_category = by_category.index[0]
    return tr["period"].format(
        total=inr(scope_total), label=label, count=len(scope),
        top=labels.get(top_category, top_category), amount=inr(by_category.iloc[0]),
    )
