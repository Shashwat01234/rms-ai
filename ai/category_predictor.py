# ai/category_predictor.py
# NOTE: This module is kept for reference but is NOT loaded at import time.
# The active NLP pipeline is in ai/nlp_engine.py (keyword + ML hybrid).
# SentenceTransformer is not used in production to avoid startup crashes.

# If you want to enable semantic similarity in future, install:
#   pip install sentence-transformers
# and import this module explicitly (not at startup).

CATEGORIES = {
    "Electricity": [
        "fan not working", "switch broken", "light fused", "ac not cooling",
        "socket issue", "electrical wiring problem", "geyser not working",
    ],
    "Plumbing": [
        "water leakage", "pipe broken", "flush not working", "tap issue",
        "drain blockage", "no water supply",
    ],
    "Carpentry": [
        "door repair", "bed broken", "window jammed", "furniture issue",
        "cupboard damaged", "hinge broken",
    ],
    "Housekeeping": [
        "room cleaning", "washroom dirty", "floor not cleaned", "dusting",
        "pest control", "cockroach in room",
    ],
    "WiFi/IT": [
        "wifi not working", "internet down", "slow network", "lan issue",
        "ums portal down",
    ],
    "Mess/Food": [
        "bad food", "poor quality", "cold food", "mess complaint",
        "stale food", "unhygienic mess",
    ],
    "Security": [
        "suspicious activity", "security issue", "lost id", "theft",
        "stolen belongings",
    ],
    "Laundry": [
        "clothes missing", "late laundry", "laundry complaint",
        "clothes damaged",
    ],
    "Admin": [
        "fee issue", "room change", "documentation", "certificate request",
        "gate pass",
    ],
}


def predict_category(query: str) -> dict:
    """
    Lightweight keyword-based category predictor (no ML model required).
    Returns category, confidence, and best matching phrase.
    """
    q = query.lower()
    best_cat, best_score, best_phrase = "Admin", 0, ""

    for cat, samples in CATEGORIES.items():
        for phrase in samples:
            # Count matching words
            phrase_words = set(phrase.split())
            query_words  = set(q.split())
            overlap = len(phrase_words & query_words)
            score = overlap / max(len(phrase_words), 1)
            if score > best_score:
                best_score = score
                best_cat   = cat
                best_phrase = phrase

    return {
        "category":   best_cat,
        "confidence": round(float(best_score), 3),
        "top_match":  best_phrase,
    }
