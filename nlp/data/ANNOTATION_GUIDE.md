# Annotation guide — expense utterances

Each line of `annotated/*.jsonl`:

```json
{"text": "auto ke liye 150 diye", "lang": "hinglish", "category": "Travel",
 "entities": [{"start": 0, "end": 4, "label": "ITEM", "text": "auto"},
              {"start": 15, "end": 18, "label": "AMOUNT", "text": "150"}]}
```

Rules:
- `lang`: en / hi / te / ta / hinglish (romanised code-mix counts as hinglish)
- `category`: one of the app's 9 expense categories
- entities (char spans, half-open): AMOUNT (money), ITEM (thing bought/service), PAYEE (person/shop), DATE (day reference)
- number words count as AMOUNT ("dedh sau" -> one span)
- mark `source: "human"`; synthetic/LLM rows must say so
- split rule: keep whole templates out of test (train/val/test by template family)
