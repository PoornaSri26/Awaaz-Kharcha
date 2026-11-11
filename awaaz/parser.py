"""Turn code-mixed Indian speech (Hinglish / Telugu / English) into rows.

The parser is deliberately rule based: it runs offline, is deterministic, and
can be tested without an API key. It handles

* number words ("dedh sau", "paanch hazar", "रెండు వందలు", "पाँच सौ"),
* comma / "aur" / "మరియు" separated lists in one breath,
* relative dates ("kal", "aaj", "parso"),
* udhar / khata entries ("Ravi ko 500 udhar diya").
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Iterable

# ---------------- CATEGORY TAXONOMY ----------------

CAT_EMOJI = {
    "Food": "🍵",
    "Travel": "🛺",
    "Groceries": "🥬",
    "Bills": "💡",
    "Health": "💊",
    "Shopping": "🛍️",
    "Fun": "🎬",
    "Education": "📚",
    "Udhar/Khata": "🤝",
    "Other": "📦",
}

CATEGORIES = {
    "Food": [
        "chai", "tea", "coffee", "lunch", "dinner", "breakfast", "tiffin", "biryani",
        "samosa", "snack", "snacks", "khana", "canteen", "juice", "pani", "water",
        "food", "dosa", "idli", "vada", "poha", "maggi", "roti", "thali", "ice cream",
        "swiggy", "zomato", "dominos", "domino's", "kfc", "starbucks",
        "టీ", "భోజనం", "టిఫిన్", "చాయ్", "అన్నం", "బిర్యానీ", "కాఫీ", "డోసా",
        "चाय", "खाना", "नाश्ता", "कॉफी", "भोजन", "लंच", "डिनर", "स्नैक", "स्नैक्स",
    ],
    "Travel": [
        "auto", "bus", "metro", "cab", "ola", "uber", "petrol", "diesel", "fuel",
        "ticket", "train", "bike", "rapido", "rickshaw", "parking", "toll",
        "ఆటో", "బస్సు", "పెట్రోల్", "రైలు", "టికెట్", "మెట్రో",
        "ऑटो", "बस", "पेट्रोल", "ट्रेन", "टिकट", "मेट्रो",
    ],
    "Groceries": [
        "sabzi", "sabji", "vegetables", "milk", "doodh", "rice", "atta", "dal", "oil",
        "grocery", "groceries", "kirana", "fruits", "eggs", "bread", "sugar",
        "dmart", "bigbasket", "blinkit", "zepto", "instamart",
        "పాలు", "కూరగాయలు", "సరుకులు", "బియ్యం", "నూనె", "గుడ్లు",
        "सब्ज़ी", "दूध", "राशन", "आटा", "दाल", "तेल", "अंडे",
    ],
    "Bills": [
        "recharge", "bill", "electricity", "current", "wifi", "rent", "gas", "cylinder",
        "postpaid", "prepaid", "dth", "water bill", "hostel fee", "fee",
        "రీఛార్జ్", "బిల్లు", "అద్దె", "విద్యుత్", "గ్యాస్",
        "रिचार्ज", "बिल", "किराया", "बिजली", "गैस",
    ],
    "Health": [
        "medicine", "medicines", "tablet", "doctor", "hospital", "dawai", "pharmacy",
        "checkup", "dental", "gym",
        "మందులు", "డాక్టర్", "దవాఖాన", "ఫార్మసీ",
        "दवाई", "दवा", "डॉक्टर", "अस्पताल",
    ],
    "Shopping": [
        "clothes", "shirt", "tshirt", "shoes", "dress", "kapde", "mobile", "earphones",
        "headphones", "charger", "gift", "amazon", "flipkart", "myntra",
        "బట్టలు", "షాపింగ్", "చెప్పులు", "బట్ట",
        "कपड़े", "जूते", "शॉपिंग", "गिफ्ट",
    ],
    "Fun": [
        "movie", "cinema", "game", "party", "outing", "trip", "concert", "netflix",
        "spotify", "subscription",
        "సినిమా", "పార్టీ", "ట్రిప్",
        "फिल्म", "पार्टी", "घूमना",
    ],
    "Education": [
        "book", "books", "notebook", "stationary", "stationery", "pen", "xerox",
        "print", "course", "udemy", "exam fee", "college fee", "lab",
        "పుస్తకం", "పుస్తకాలు", "కాలేజీ", "ఫీజు",
        "किताब", "किताबें", "कॉलेज", "फीस", "स्टेशनरी",
    ],
    "Udhar/Khata": [
        "udhar", "khata", "lent", "borrow", "borrowed", "owe", "owes",
        "उधार", "खाता", "అప్పు", "ఖాతా",
    ],
}

#: Categories a normal expense can have (udhar has its own table).
EXPENSE_CATEGORIES = [
    "Food", "Travel", "Groceries", "Bills", "Health", "Shopping", "Fun",
    "Education", "Other",
]

#: Old v1 category names -> current taxonomy.
LEGACY_CATEGORY_MAP = {
    "food & chai": "Food",
    "food and chai": "Food",
    "travel & commute": "Travel",
    "travel and commute": "Travel",
    "recharge & bills": "Bills",
    "recharge and bills": "Bills",
    "bills & recharge": "Bills",
}

# ---------------- NUMBER WORDS ----------------

#: Multi-word phrases are replaced first (longest phrase wins).
NUMBER_WORDS = {
    # Hinglish
    "dedh sau": "150", "deedh sau": "150",
    "dhai sau": "250", "dhaai sau": "250", "adhai sau": "250",
    "ek sau": "100", "do sau": "200", "teen sau": "300", "char sau": "400",
    "chaar sau": "400", "paanch sau": "500", "panch sau": "500",
    "chhe sau": "600", "che sau": "600", "saat sau": "700", "aath sau": "800",
    "nau sau": "900",
    "dedh hazar": "1500", "dhai hazar": "2500", "dhaai hazar": "2500",
    "ek hazar": "1000", "do hazar": "2000", "teen hazar": "3000",
    "char hazar": "4000", "paanch hazar": "5000", "panch hazar": "5000",
    "das hazar": "10000", "dus hazar": "10000",
    # bare Hinglish numerals
    "bees": "20", "tees": "30", "chalis": "40", "pachas": "50", "pachaas": "50",
    "saath": "60", "sattar": "70", "assi": "80", "nabbe": "90",
    "ek": "1", "do": "2", "teen": "3", "char": "4", "paanch": "5", "chhe": "6",
    "saat": "7", "aath": "8", "nau": "9", "das": "10",
    "hazar": "1000", "hazaar": "1000", "sau": "100",
    # Telugu
    "రెండు వందలు": "200", "మూడు వందలు": "300", "ఐదు వందలు": "500",
    "రెండు వేలు": "2000", "ఐదు వేలు": "5000", "పది వేలు": "10000",
    "వంద": "100", "వందలు": "100", "వెయ్యి": "1000", "వేలు": "1000",
    "పది": "10", "ఇరవై": "20", "ముప్పై": "30", "నలభై": "40", "యాభై": "50",
    # Hindi / Devanagari
    "डेढ़ सौ": "150", "ढेढ़ सौ": "150", "देढ़ सौ": "150", "ढेढ सौ": "150",
    "ढाई सौ": "250", "अढ़ाई सौ": "250",
    "डेढ़ हज़ार": "1500", "ढेढ़ हज़ार": "1500", "ढाई हज़ार": "2500",
    "दो सौ": "200", "तीन सौ": "300",
    "पाँच सौ": "500", "पांच सौ": "500", "दस सौ": "1000",
    "दो हज़ार": "2000", "पाँच हज़ार": "5000", "दस हज़ार": "10000",
    "सौ": "100", "हज़ार": "1000", "हजार": "1000",
    "दस": "10", "बीस": "20", "तीस": "30", "चालीस": "40", "पचास": "50",
}

#: Relative date words -> day offset from today (script and romanised forms).
DATE_WORDS = {
    "aaj": 0, "today": 0, "आज": 0, "ఈ రోజు": 0, "నేడు": 0, "eeroju": 0, "ee roju": 0,
    "kal": -1, "yesterday": -1, "कल": -1, "నిన్న": -1, "ninna": -1,
    "parso": -2, "parson": -2, "परसों": -2, "మొన్న": -2, "monna": -2,
}

UDHAR_WORDS = (
    "udhar", "khata", "baki", "baaki", "lent", "borrow", "borrowed",
    "owe", "owes", "lend", "diya", "diye", "wapas", "wapis", "liya", "liye",
    "dena", "lena", "उधार", "खाता", "అప్పు", "ఖాతా", "ఇచ్చాను",
    "తీసుకున్నా", "दिया", "दिए", "लिया", "लिए",
)

LENT_HINTS = (
    "diya", "diye", "lent", "lend", "gave", "dena", "దియ్యా", "ఇచ్చాను",
    "दिया", "दिए", "उधार दिया",
)

FILLER = (
    r"\b(rupees?|rupaye|rupaiye|rupay|rs|inr|ka|ke|ki|ko|se|ne|me|mein|pe|par|liye|"
    r"at|from|by|using|via|upi|gpay|phonepe|paytm|cash|card|netbanking|credit|debit|"
    r"received|receive|credited|earned|bought|buy|purchased|got|"
    r"for|on|spent|spend|paid|pay|gaye|gaya|hua|huya|tha|thi|the|and|aur|phir|then|"
    r"aaj|today|kal|yesterday|parso|kharcha|kharch|karchu|karchif|pettanu|ayindi|"
    r"udhar|diya|diye|liya|liye|lent|borrow|borrowed|gave|give|to|from|please)\b|"
    r"₹|రూపాయలు|రూపాయి|ఖర్చు|అయింది|రూపాయల|"
    r"रुपये|रुपए|खर्च|रुपया|का|के|की|को|में|पर|के लिए"
    r"|(?<!\w)(?:आज|कल|परसों|ఈ రోజు|నేడు|నిన్న|మొన్న|aaj|today|kal|yesterday|"
    r"parso|parson|eeroju|ee roju|ninna|monna)(?!\w)"
)

SPLITTERS = (
    r",|\band\b|\baur\b|\bphir\b|\bthen\b|\binka\b|और|మరియు|ఇంకా|"
    r"\.(?!\d)|।|\n|;|\+"
)

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_ASCII_WORD_RE = re.compile(r"^[a-z0-9 ]+$")


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    if _ASCII_WORD_RE.match(phrase):
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return re.compile(escaped)


# Pre-compile once, longest phrase first so "dedh sau" beats "sau".
_NUMBER_PATTERNS = [
    (_phrase_pattern(phrase), value)
    for phrase, value in sorted(
        NUMBER_WORDS.items(), key=lambda kv: (-len(kv[0].split()), -len(kv[0]))
    )
]


def normalize_hinglish_numbers(text: str) -> str:
    """Replace Indian number words with digits, e.g. "dedh sau" -> "150"."""
    cleaned = text or ""
    # Gnani writes "₹20" as one token; split the symbol off so amounts stay numbers.
    cleaned = cleaned.replace("₹", " ")
    # "1,500" and "1,00,000" are single amounts, not two comma-separated items.
    for _ in range(3):
        before = cleaned
        # Lakh grouping (1,00,000) first, then the familiar 3-digit form (1,500).
        cleaned = re.sub(r"(?<=\d),(?=\d{2}(?!\d))", "", cleaned)
        cleaned = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", cleaned)
        if cleaned == before:
            break
    for pattern, value in _NUMBER_PATTERNS:
        cleaned = pattern.sub(value, cleaned)
    # "1k" / "2.5k" style shortcuts
    cleaned = re.sub(r"(\d+(?:\.\d+)?)\s*k\b", lambda m: str(int(float(m.group(1)) * 1000)), cleaned, flags=re.I)
    return cleaned


def _word_in(text: str, word: str) -> bool:
    """Word-boundary match for Latin keywords, substring match otherwise."""
    if _ASCII_WORD_RE.match(word.lower()):
        return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None
    return word in text


#: Public alias used by the insights module.
word_in = _word_in


def categorize(text: str) -> str:
    """Best-effort category for an expense description."""
    t = (text or "").lower()
    for cat, words in CATEGORIES.items():
        if cat == "Udhar/Khata":
            continue
        if any(_word_in(t, w) for w in words):
            return cat
    return "Other"


def normalize_category(name: str) -> str:
    """Map any category label (including v1 names) onto the current taxonomy."""
    if not name:
        return "Other"
    cleaned = str(name).strip()
    for cat in EXPENSE_CATEGORIES + ["Udhar/Khata"]:
        if cleaned.lower() == cat.lower():
            return cat
    if cleaned.lower() in LEGACY_CATEGORY_MAP:
        return LEGACY_CATEGORY_MAP[cleaned.lower()]
    guessed = categorize(cleaned)
    return guessed if guessed != "Other" else "Other"


#: How the money moved. Longest phrase first so "credit card" beats "card".
PAYMENT_MODES = {
    "google pay": "UPI",
    "credit card": "Card",
    "debit card": "Card",
    "net banking": "Netbanking",
    "bank transfer": "Netbanking",
    "phonepe": "UPI",
    "netbanking": "Netbanking",
    "gpay": "UPI",
    "paytm": "UPI",
    "upi": "UPI",
    "cash": "Cash",
    "card": "Card",
    "कैश": "Cash",
    "యూపీఐ": "UPI",
    "క్యాష్": "Cash",
}

#: Words that turn a spend into money coming in.
INCOME_WORDS = (
    "received", "receive", "salary", "income", "credited", "refund", "earned", "got paid",
    "मिला", "मिले", "जीत", "వచ్చింది", "జీతం", "ఆదాయం",
)

_MERCHANT_RE = re.compile(
    r"\b(?:at|from|se|से|నుండి)\s+([A-Za-z][A-Za-z&.'-]*(?:\s+[A-Za-z][A-Za-z&.'-]*){0,2})",
    re.IGNORECASE,
)
_MERCHANT_STOP = {
    "by", "using", "via", "for", "on", "with", "and", "aur", "rs", "inr", "rupees",
    "today", "aaj", "kal", "parso", "upi", "cash", "card", "gpay", "paytm", "phonepe",
}


def detect_payment_mode(text: str) -> str | None:
    """Which rail the money used, if the sentence says so."""
    lowered = (text or "").lower()
    for phrase in sorted(PAYMENT_MODES, key=len, reverse=True):
        if _word_in(lowered, phrase):
            return PAYMENT_MODES[phrase]
    return None


def detect_kind(text: str) -> str:
    """Income when the sentence talks about money arriving."""
    lowered = (text or "").lower()
    return "Income" if any(_word_in(lowered, w) for w in INCOME_WORDS) else "Expense"


def detect_merchant(text: str) -> str | None:
    """Shop or person from "at Paradise" / "from Amazon"."""
    match = _MERCHANT_RE.search(text or "")
    if not match:
        return None
    words = [word for word in match.group(1).split() if word.lower() not in _MERCHANT_STOP]
    if not words or words[0].isdigit():
        return None
    return _title(" ".join(words[:3]))


_SMS_AMOUNT_RE = re.compile(
    r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE
)


def parse_bank_sms(text: str, today: dt.date | None = None) -> dict | None:
    """Turn a bank/UPI SMS into one expense row, or None if it has no amount.

    "Rs 450 debited at Swiggy" -> 450, Swiggy, Food, Expense. A credit becomes
    income so it never inflates the spending totals.
    """
    today = today or dt.date.today()
    cleaned = (text or "").strip()
    match = _SMS_AMOUNT_RE.search(cleaned)
    if not match:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    if amount <= 0:
        return None

    lowered = cleaned.lower()
    merchant = detect_merchant(cleaned)
    kind = "Income" if any(_word_in(lowered, w) for w in INCOME_WORDS) else "Expense"
    item = merchant or ("Bank credit" if kind == "Income" else "Bank payment")
    return {
        "date": detect_date(cleaned, today).isoformat(),
        "item": item,
        "amount": round(amount, 2),
        "category": categorize(merchant or cleaned),
        "merchant": merchant,
        "payment_mode": detect_payment_mode(cleaned) or ("Netbanking" if kind == "Income" else None),
        "kind": kind,
    }


def _date_offset(text: str) -> int | None:
    """First relative-date offset mentioned in the text, if any."""
    lowered = (text or "").lower()
    for phrase, offset in sorted(DATE_WORDS.items(), key=lambda kv: -len(kv[0])):
        if _word_in(lowered, phrase):
            return offset
    return None


def detect_date(text: str, today: dt.date | None = None) -> dt.date:
    """Resolve "aaj"/"kal"/"parso" to a concrete date."""
    today = today or dt.date.today()
    offset = _date_offset(text)
    return today + dt.timedelta(days=offset) if offset is not None else today


def _pick_amount(chunk: str) -> float | None:
    """Pick the money amount out of a chunk like "2 chai 20"."""
    numbers = [float(n) for n in _NUM_RE.findall(chunk)]
    if not numbers:
        return None
    # Ignore quantities ("2 chai"), prefer the first plausible money amount.
    money = [n for n in numbers if n >= 10]
    amount = money[0] if money else max(numbers)
    return amount if amount > 0 else None


def _clean_item(chunk: str, extra_filler: Iterable[str] = ()) -> str:
    item = _NUM_RE.sub(" ", chunk)
    item = re.sub(FILLER, " ", item, flags=re.IGNORECASE)
    for word in extra_filler:
        item = re.sub(rf"\b{re.escape(word)}\b", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"[^\w\s\u0900-\u097F\u0C00-\u0C7F]", " ", item)
    item = re.sub(r"\s+", " ", item).strip(" .-")
    return item


def _title(text: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in text.split()) if text else text


def is_udhar_chunk(chunk: str) -> bool:
    lowered = (chunk or "").lower()
    return any(_word_in(lowered, w) for w in UDHAR_WORDS)


def _item_segments(chunk: str) -> list[str]:
    """Split a comma-less breath into one segment per money amount.

    Gnani Prisma returns "चाय ₹20 ऑटो ₹80 लंच ₹150" with no separators, so every
    amount anchors its own item. A small number directly before an amount
    ("2 chai 20") is a quantity, not a separate expense.
    """
    tokens = chunk.split()
    anchors: list[list[int]] = []
    for index, token in enumerate(tokens):
        if not _NUM_RE.fullmatch(token):
            continue
        if anchors and anchors[-1][-1] == index - 1:
            anchors[-1].append(index)  # "1 500" / "1,500" is a single amount
            continue
        later_money = any(
            _NUM_RE.fullmatch(rest) and float(rest) >= 10 for rest in tokens[index + 1 :]
        )
        if float(token) < 10 and later_money:
            continue  # quantity like the "2" in "2 chai 20"
        anchors.append([index])

    if not anchors:
        return [chunk]

    segments: list[str] = []
    start = 0
    for position, group in enumerate(anchors):
        words = tokens[start : group[0]] + [tokens[i] for i in group]
        if position + 1 == len(anchors):
            words += tokens[group[-1] + 1 :]  # trailing context belongs to the last item
        segment = " ".join(words).strip()
        if segment:
            segments.append(segment)
        start = group[-1] + 1
    return segments


def parse_expenses(
    text: str, today: dt.date | None = None
) -> tuple[list[dict], list[dict]]:
    """Parse free-form speech/text into (expense rows, udhar rows).

    Each expense row: ``{date, item, amount, category}``.
    Each udhar row: ``{date, person, amount, type, status}``.
    """
    today = today or dt.date.today()
    normalized = normalize_hinglish_numbers(text or "")
    expenses: list[dict] = []
    udhar: list[dict] = []
    if not normalized.strip():
        return expenses, udhar

    base_date = detect_date(normalized, today)
    # A mode said once at the end ("... by UPI") applies to every item.
    sentence_mode = detect_payment_mode(normalized)

    for chunk in re.split(SPLITTERS, normalized, flags=re.IGNORECASE):
        for part in _item_segments(chunk.strip()):
            amount = _pick_amount(part)
            if amount is None:
                continue
            # A date word in the segment wins; otherwise inherit the sentence date.
            offset = _date_offset(part)
            row_date = today + dt.timedelta(days=offset) if offset is not None else base_date

            if is_udhar_chunk(part):
                person = _title(_clean_item(part, extra_filler=UDHAR_WORDS)) or "Someone"
                action = (
                    "Lent (Diya)"
                    if any(_word_in(part.lower(), w) for w in LENT_HINTS)
                    else "Borrowed (Liya)"
                )
                udhar.append(
                    {
                        "date": row_date.isoformat(),
                        "person": person,
                        "amount": round(amount, 2),
                        "type": action,
                        "status": "Pending",
                    }
                )
            else:
                merchant = detect_merchant(part)
                item_text = _clean_item(part)
                if merchant:  # the shop is its own field, not part of the item
                    item_text = re.sub(
                        re.escape(merchant), " ", item_text, flags=re.IGNORECASE
                    ).strip()
                expenses.append(
                    {
                        "date": row_date.isoformat(),
                        "item": _title(item_text) or "General",
                        "amount": round(amount, 2),
                        "category": categorize(part),
                        "merchant": merchant,
                        "payment_mode": detect_payment_mode(part) or sentence_mode,
                        "kind": detect_kind(part),
                    }
                )

    return expenses, udhar
