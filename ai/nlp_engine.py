# ai/nlp_engine.py — Advanced NLP Pipeline for RMS-AI
# Multi-stage: preprocessing → intent detection → entity extraction → routing
import re
import os
from difflib import SequenceMatcher

# ═══════════════════════════════════════════════════════════════════
#  SPELL CORRECTION / NORMALIZATION
# ═══════════════════════════════════════════════════════════════════
SLANG_MAP = {
    # Typos & abbreviations
    "wokring": "working", "workin": "working", "wrkng": "working",
    "workng":  "working", "wrking": "working",
    "not wrking": "not working", "nt working": "not working",
    "nt wrking":  "not working", "ntwrking": "not working",
    "plz": "please", "pls": "please", "plez": "please",
    "urgnt": "urgent", "urgently": "urgent",
    "prob": "problem", "prb": "problem", "pbm": "problem",
    "iss": "issue", "isue": "issue",
    "rep": "repair", "repar": "repair",
    "brk": "broken", "brkn": "broken", "broekn": "broken",
    "leek": "leak", "liek": "leak", "lakage": "leakage",
    "watet": "water", "watr": "water",
    "elec": "electricity", "eletricity": "electricity",
    "eletrician": "electrician", "electrican": "electrician",
    "plmbr": "plumber", "plumbar": "plumber",
    "carpnter": "carpenter", "carpanter": "carpenter",
    # Hostel abbreviations
    "bathrom": "bathroom", "bathrom": "bathroom", "bthrm": "bathroom",
    "washrom": "washroom", "wshrm": "washroom",
    "hstl": "hostel", "hostl": "hostel",
    "rm":  "room", "r.m": "room",
    "clg": "college", "colg": "college",
    # Equipment
    "ac":  "air conditioner", "a.c": "air conditioner", "a/c": "air conditioner",
    "AC":  "air conditioner",
    "wifi": "wifi", "wi fi": "wifi", "wi-fi": "wifi",
    "inet": "internet", "net": "internet",
    "fan ": "fan ", # preserve spacing
    # Time shortcuts
    "tmrw": "tomorrow", "tmr": "tomorrow",
    "evng": "evening", "evn": "evening",
    "morn": "morning", "mrng": "morning",
    "aft": "afternoon", "aftrn": "afternoon",
}

def normalize_text(text: str) -> str:
    """Clean, lowercase, fix slang, collapse whitespace."""
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Replace slang (longest match first to avoid partial replacements)
    for wrong, right in sorted(SLANG_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(wrong.lower(), right)
    # Remove excessive punctuation but keep useful ones
    text = re.sub(r'[^\w\s\.\,\!\?\:\-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ═══════════════════════════════════════════════════════════════════
#  INTENT DETECTION
# ═══════════════════════════════════════════════════════════════════

# Strong signals of a MAINTENANCE complaint (physical issue)
MAINTENANCE_SIGNALS = {
    "high": [
        "not working", "broken", "damaged", "not cooling", "leaking", "leak",
        "blocked", "burst", "jammed", "not closing", "fused", "no power",
        "not heating", "no water", "not spinning", "falling", "collapsed",
        "flooding", "short circuit", "sparks", "smoke", "pest control",
        "cockroach", "rat", "mosquito", "ants", "infestation",
        "dirty", "not cleaned", "not mopped", "overflowing", "stale food",
        "missing clothes", "clothes not returned",
    ],
    "medium": [
        "repair", "fix", "replace", "clean", "inspect", "check", "issue",
        "problem", "complaint", "request", "need help with", "please fix",
        "slow", "noise", "blinking", "flickering", "dripping", "smell",
        "foul", "damp", "peeling", "crack", "wobbly", "loose",
    ],
}

# Strong signals of an ACADEMIC / INFORMATION query
INQUIRY_SIGNALS = {
    "high": [
        "how do i", "how to", "what is", "when is", "where is", "why is",
        "can i", "is there", "how can", "what are", "tell me", "explain",
        "guide me", "i want to know", "information about",
        "cgpa", "sgpa", "marks", "result", "grade", "exam", "backlog",
        "scholarship", "fee", "challan", "bonafide", "certificate", "noc",
        "attendance", "ums", "portal", "timetable", "syllabus",
        "placement", "internship", "re-evaluation", "recheck",
        "admission", "registration", "migration", "transfer certificate",
        "date sheet", "hall ticket",
    ],
    "medium": [
        "apply", "application", "process", "procedure", "steps",
        "deadline", "last date", "download", "upload", "check",
        "verify", "status",
    ],
}

# Keywords that — even in an inquiry — should force technician routing
OVERRIDE_TO_MAINTENANCE = [
    "fix my", "repair my", "replace my", "my fan", "my light", "my ac",
    "my tap", "my pipe", "my door", "my window", "my bed", "my cupboard",
    "my socket", "my switch", "my geyser", "my internet", "my wifi",
    "water leaking", "pipe burst", "drain blocked", "flush not", "ac not",
    "fan not", "light not", "switch not", "power not",
]


def detect_intent(text: str) -> dict:
    """
    Returns intent classification:
      - type: 'maintenance' | 'inquiry' | 'emergency' | 'mixed'
      - confidence: 0.0 – 1.0
      - is_urgent: bool
    """
    t = text.lower()

    # Emergency detection (highest priority)
    emergency_words = ["fire", "flood", "gas leak", "sparks", "electric shock",
                       "smoke", "collapsed", "emergency", "urgent help",
                       "someone hurt", "accident", "bleeding"]
    if any(w in t for w in emergency_words):
        return {"type": "emergency", "confidence": 0.95, "is_urgent": True}

    # Override check: if text contains strong maintenance phrases, don't send to academic AI
    has_override = any(phrase in t for phrase in OVERRIDE_TO_MAINTENANCE)

    # Score maintenance signals
    maint_score = 0
    for sig in MAINTENANCE_SIGNALS["high"]:
        if sig in t:
            maint_score += 2
    for sig in MAINTENANCE_SIGNALS["medium"]:
        if sig in t:
            maint_score += 1

    # Score inquiry signals
    inq_score = 0
    for sig in INQUIRY_SIGNALS["high"]:
        if sig in t:
            inq_score += 2
    for sig in INQUIRY_SIGNALS["medium"]:
        if sig in t:
            inq_score += 1

    total = maint_score + inq_score or 1
    maint_conf = maint_score / total
    inq_conf   = inq_score  / total

    is_urgent = any(w in t for w in ["urgent", "asap", "immediately", "right now",
                                      "not working since", "since morning", "since yesterday"])

    if has_override:
        return {"type": "maintenance", "confidence": min(maint_conf + 0.3, 1.0), "is_urgent": is_urgent}

    if maint_score == 0 and inq_score == 0:
        return {"type": "inquiry", "confidence": 0.5, "is_urgent": False}

    if maint_conf >= 0.65:
        return {"type": "maintenance", "confidence": maint_conf, "is_urgent": is_urgent}
    if inq_conf >= 0.65:
        return {"type": "inquiry",     "confidence": inq_conf,   "is_urgent": is_urgent}

    # Mixed: contains both signals (e.g. "how do I fix my fan?")
    # If it mentions a physical object, lean maintenance
    physical_objects = ["fan", "light", "switch", "ac", "tap", "pipe", "door",
                        "window", "bed", "cupboard", "wifi", "internet", "geyser",
                        "socket", "plug", "bulb", "tube", "flush", "drain"]
    if any(obj in t for obj in physical_objects) and maint_score > 0:
        return {"type": "maintenance", "confidence": 0.7, "is_urgent": is_urgent}

    return {"type": "inquiry", "confidence": inq_conf, "is_urgent": is_urgent}


# ═══════════════════════════════════════════════════════════════════
#  ENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════

def extract_entities(text: str) -> dict:
    """
    Extract structured data from the query text:
      - room_number: str | None
      - time_hour: int | None  (24h format)
      - urgency: 'low' | 'medium' | 'high' | 'emergency'
      - issue_objects: list[str]
      - floor: str | None
    """
    t = text.lower()

    # Room number extraction
    room = None
    room_patterns = [
        r'room\s*(?:no\.?|number|#)?\s*(\d{1,4}[a-z]?)',
        r'r(?:oom)?\s*-?\s*(\d{3,4})',
        r'(\d{3,4})\s*(?:room|r\.?m\.?)',
    ]
    for pat in room_patterns:
        m = re.search(pat, t)
        if m:
            room = m.group(1).upper()
            break

    # Floor extraction
    floor = None
    floor_m = re.search(r'(\d+)(?:st|nd|rd|th)?\s*floor', t)
    if floor_m:
        floor = floor_m.group(1)

    # Time extraction (robust)
    time_hour = _extract_time_robust(t)

    # Urgency scoring
    urgency_words = {
        "emergency": ["emergency", "fire", "flood", "shock", "gas leak"],
        "high":      ["urgent", "asap", "immediately", "since morning",
                      "since yesterday", "2 days", "3 days", "not working since",
                      "very urgent", "please help"],
        "medium":    ["please", "as soon as", "today", "right now", "broken"],
        "low":       ["when possible", "no rush", "whenever"],
    }
    urgency = "medium"
    for level, words in urgency_words.items():
        if any(w in t for w in words):
            urgency = level
            break

    # Extract issue objects mentioned
    physical_objects = {
        "fan": ["fan", "ceiling fan"],
        "light": ["light", "tube light", "bulb", "lamp"],
        "switch": ["switch", "button"],
        "socket": ["socket", "plug", "outlet", "charger point", "power point"],
        "air_conditioner": ["ac", "air conditioner", "airconditioner", "a.c"],
        "geyser": ["geyser", "water heater", "hot water"],
        "tap": ["tap", "faucet", "knob"],
        "pipe": ["pipe", "pipeline"],
        "flush": ["flush", "commode", "toilet"],
        "drain": ["drain", "drainage", "blockage"],
        "door": ["door"],
        "window": ["window"],
        "bed": ["bed", "mattress"],
        "cupboard": ["cupboard", "wardrobe", "almirah", "cabinet"],
        "chair": ["chair"],
        "table": ["table", "desk"],
        "wifi": ["wifi", "wi-fi", "internet", "network", "lan"],
        "pest": ["cockroach", "rat", "mosquito", "ants", "pest", "insects"],
    }
    found_objects = []
    for obj_key, aliases in physical_objects.items():
        if any(alias in t for alias in aliases):
            found_objects.append(obj_key)

    return {
        "room_number":   room,
        "floor":         floor,
        "time_hour":     time_hour,
        "urgency":       urgency,
        "issue_objects": found_objects,
    }


def _extract_time_robust(text: str) -> int | None:
    """
    Handles: '3pm', '3 pm', 'at 3', 'after 4', 'by 5', 'around 6',
             'morning', 'afternoon', 'evening', 'night', '15:00'
    Returns 24h integer hour or None.
    """
    t = text.lower()

    # HH:MM format
    m = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', t)
    if m:
        h = int(m.group(1))
        meridiem = m.group(3)
        if meridiem == "pm" and h != 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        return h

    # X am/pm format
    m = re.search(r'(\d{1,2})\s*(am|pm)', t)
    if m:
        h = int(m.group(1))
        if m.group(2) == "pm" and h != 12:
            h += 12
        elif m.group(2) == "am" and h == 12:
            h = 0
        return h

    # Preposition + number (at 5, after 4, by 6, around 3, before 7)
    prep_pattern = r'(?:at|after|by|around|before|from|past)\s+(\d{1,2})\b'
    m = re.search(prep_pattern, t)
    if m:
        h = int(m.group(1))
        # If number >= 1 and <= 6 with no context, assume PM for afternoon hours
        if 1 <= h <= 6:
            h += 12
        return h

    # Natural language time
    time_map = {
        "morning":   9,
        "afternoon": 14,
        "evening":   18,
        "night":     20,
        "midnight":  0,
        "noon":      12,
        "lunch":     13,
        "breakfast": 8,
        "dinner":    19,
    }
    for word, hour in time_map.items():
        if word in t:
            return hour

    return None


# ═══════════════════════════════════════════════════════════════════
#  TECHNICIAN ROLE MAPPING
# ═══════════════════════════════════════════════════════════════════

ROLE_RULES = {
    "electrician": {
        "objects":   ["fan", "light", "switch", "socket", "air_conditioner", "geyser"],
        "keywords":  ["fan", "light", "bulb", "tube", "switch", "socket", "plug", "ac",
                      "air conditioner", "geyser", "water heater", "wiring", "fuse",
                      "power cut", "no power", "electricity", "electric", "charger point",
                      "short circuit", "sparks", "tripped"],
    },
    "plumber": {
        "objects":   ["tap", "pipe", "flush", "drain", "geyser"],
        "keywords":  ["water", "leak", "tap", "pipe", "flush", "drain", "toilet", "washroom",
                      "bathroom", "blocked", "burst", "overflow", "sewage", "smell",
                      "no water", "water pressure", "dripping", "faucet"],
    },
    "carpenter": {
        "objects":   ["door", "window", "bed", "cupboard", "chair", "table"],
        "keywords":  ["door", "window", "bed", "cupboard", "almirah", "wardrobe",
                      "furniture", "hinge", "lock", "handle", "shelf", "broken chair",
                      "broken table", "broken bed", "jammed", "wood", "rack", "cabinet"],
    },
    "painter": {
        "objects":   [],
        "keywords":  ["paint", "peeling", "wall", "colour", "color", "damp", "moisture",
                      "seepage", "stain", "crack", "ceiling stain"],
    },
    "housekeeping": {
        "objects":   ["pest"],
        "keywords":  ["clean", "cleaning", "dirty", "dust", "mop", "sweep",
                      "garbage", "dustbin", "pest", "cockroach", "rat", "mosquito",
                      "ants", "insects", "washroom not clean", "floor dirty",
                      "corridor", "common area"],
    },
    "it_support": {
        "objects":   ["wifi"],
        "keywords":  ["wifi", "internet", "network", "lan", "slow internet",
                      "no internet", "wifi not working", "internet not working",
                      "internet down", "wifi down", "lan issue", "lan cable",
                      "ums portal down", "ums is down", "portal not loading",
                      "cannot access ums", "ums login not working"],
    },
    "mess_manager": {
        "objects":   [],
        "keywords":  ["mess", "food", "meal", "canteen", "quality", "stale",
                      "cold food", "hygiene", "quantity", "diet"],
    },
    "laundry": {
        "objects":   [],
        "keywords":  ["laundry", "clothes", "washing", "ironing", "missing clothes",
                      "clothes not returned", "laundry delay"],
    },
    "security": {
        "objects":   [],
        "keywords":  ["suspicious", "theft", "stolen", "security", "lost id",
                      "lost card", "lost belongings", "unauthorized"],
    },
}

# Map roles to DB role values (for technician lookup)
ROLE_TO_DB = {
    "electrician": "electrician",
    "plumber":     "plumber",
    "carpenter":   "carpenter",
    "painter":     "painter",
    "housekeeping": "housekeeping",
    "it_support":  "it_support",
    "mess_manager": "mess_manager",
    "laundry":     "laundry",
    "security":    "security",
}

# Category labels
ROLE_TO_CATEGORY = {
    "electrician":  "Electricity",
    "plumber":      "Plumbing",
    "carpenter":    "Carpentry",
    "painter":      "Painting",
    "housekeeping": "Housekeeping",
    "it_support":   "WiFi/IT",
    "mess_manager": "Mess/Food",
    "laundry":      "Laundry",
    "security":     "Security",
}


def detect_role(text: str, entities: dict) -> tuple[str | None, float]:
    """
    Returns (role_name, confidence) for the best matching technician role.
    Uses extracted entities + keyword scoring.
    """
    t = text.lower()
    scores = {}

    for role, rules in ROLE_RULES.items():
        score = 0
        # Object match (strong signal)
        for obj in entities.get("issue_objects", []):
            if obj in rules["objects"]:
                score += 3
        # Keyword match
        for kw in rules["keywords"]:
            if kw in t:
                score += 1
        if score > 0:
            scores[role] = score

    if not scores:
        return None, 0.0

    best_role = max(scores, key=scores.get)
    best_score = scores[best_role]
    total = sum(scores.values()) or 1
    confidence = round(best_score / total, 3)

    return best_role, confidence


# ═══════════════════════════════════════════════════════════════════
#  DUPLICATE DETECTION  (Jaccard similarity — fixed)
# ═══════════════════════════════════════════════════════════════════

def jaccard_similarity(s1: str, s2: str) -> float:
    """Compute word-level Jaccard similarity between two strings."""
    stop_words = {"i", "my", "the", "is", "in", "a", "an", "of", "to",
                  "and", "not", "it", "this", "that", "are", "was", "on"}
    w1 = set(s1.lower().split()) - stop_words
    w2 = set(s2.lower().split()) - stop_words
    if not w1 and not w2:
        return 1.0
    if not w1 or not w2:
        return 0.0
    intersection = len(w1 & w2)
    union = len(w1 | w2)
    return intersection / union


def sequence_similarity(s1: str, s2: str) -> float:
    """Character-level sequence similarity."""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def is_duplicate_query(new_query: str, existing_queries: list[dict],
                        student_id: str, threshold: float = 0.72) -> tuple[bool, str | None]:
    """
    Compare new_query against existing queries for the same student.
    Returns (is_duplicate, existing_request_id).
    Uses combined Jaccard + sequence similarity to avoid false positives.
    """
    new_norm = normalize_text(new_query)
    for row in existing_queries:
        if row.get("student_id") != student_id:
            continue
        if row.get("status") in ("resolved", "ai_resolved"):
            continue  # Don't flag against resolved requests
        old_norm = normalize_text(str(row.get("query", "")))
        j_sim = jaccard_similarity(new_norm, old_norm)
        s_sim = sequence_similarity(new_norm, old_norm)
        combined = (j_sim * 0.6) + (s_sim * 0.4)
        if combined >= threshold:
            return True, row["request_id"]
    return False, None


# ═══════════════════════════════════════════════════════════════════
#  HUMAN-LIKE RESPONSE BUILDER
# ═══════════════════════════════════════════════════════════════════

MAINTENANCE_RESPONSES = {
    "electrician": {
        "assigned": (
            "Your complaint has been noted and **{tech}** (Electrician) will visit "
            "your room to fix the {issue}. They are available {schedule}. "
            "Please ensure someone is present in the room at that time."
        ),
        "no_technician": (
            "We've received your complaint about the {issue}. Unfortunately, all "
            "electricians are currently busy. Your request has been logged and you'll "
            "be assigned the next available technician. Expected resolution: within 24 hours."
        ),
    },
    "plumber": {
        "assigned": (
            "Your plumbing complaint about {issue} has been registered. "
            "**{tech}** (Plumber) will attend to your room {schedule}. "
            "To minimize damage, please turn off the water tap near the affected area if possible."
        ),
        "no_technician": (
            "Your plumbing issue ({issue}) has been logged. All plumbers are "
            "currently occupied. Your request is in queue — expected response within 4-6 hours. "
            "If there's active flooding, please inform the hostel warden immediately."
        ),
    },
    "carpenter": {
        "assigned": (
            "Noted! **{tech}** (Carpenter) will visit to repair the {issue} in your room. "
            "They'll arrive {schedule}. Please keep the area accessible."
        ),
        "no_technician": (
            "Your carpentry complaint about {issue} has been registered. "
            "A carpenter will be assigned soon. Expected response: within 24 hours."
        ),
    },
    "painter": {
        "assigned": (
            "Your painting complaint has been registered. **{tech}** will assess the "
            "{issue} and schedule the repainting work. They'll visit {schedule}."
        ),
        "no_technician": (
            "Your complaint about {issue} has been logged. A painter will be assigned "
            "shortly. Painting work typically takes 1-2 business days to schedule."
        ),
    },
    "housekeeping": {
        "assigned": (
            "Housekeeping has been notified about the {issue}. **{tech}** will "
            "clean/address your concern {schedule}. Thank you for maintaining hostel cleanliness standards."
        ),
        "no_technician": (
            "Your housekeeping request for {issue} has been logged. The cleaning "
            "team will attend to your room during the next scheduled round."
        ),
    },
    "it_support": {
        "assigned": (
            "Your internet/IT complaint has been escalated to **{tech}** (IT Support). "
            "They will diagnose the {issue} {schedule}. You can also try restarting "
            "your device and reconnecting to the WiFi as a temporary fix."
        ),
        "no_technician": (
            "Your WiFi/IT complaint has been logged. As a temporary fix, try: "
            "1) Restart your device, 2) Forget and reconnect to the WiFi network, "
            "3) Move closer to the router. IT support will contact you within 2-4 hours."
        ),
    },
    "default": {
        "assigned": (
            "Your complaint has been received and **{tech}** will attend to the {issue} {schedule}."
        ),
        "no_technician": (
            "Your complaint about {issue} has been logged. A technician will be assigned shortly. "
            "Ticket ID saved for tracking."
        ),
    },
}

EMERGENCY_RESPONSE = (
    "🚨 **EMERGENCY DETECTED** — Please take immediate action:\n\n"
    "1. **Evacuate the area** if there is any immediate danger\n"
    "2. **Call Hostel Warden** immediately: Available at the hostel reception\n"
    "3. **Emergency Maintenance**: +91-1824-517000 (24/7)\n"
    "4. Your complaint has been flagged as URGENT in the system\n\n"
    "Do NOT wait — contact hostel staff right now!"
)


def build_human_response(intent: dict, role: str | None, tech: str | None,
                         s_time: str | None, e_time: str | None,
                         assigned_time, entities: dict, query: str) -> str:
    """
    Generate a warm, human-like response for a maintenance complaint.
    """
    if intent["type"] == "emergency":
        return EMERGENCY_RESPONSE

    # Build issue description from extracted entities
    objects = entities.get("issue_objects", [])
    if objects:
        issue = " and ".join(o.replace("_", " ") for o in objects[:2])
    else:
        issue = "the reported issue"

    # Build schedule string
    if assigned_time and s_time and e_time:
        schedule = f"at approximately {assigned_time}:00 hrs (available {s_time}–{e_time})"
    elif s_time and e_time:
        schedule = f"between {s_time} and {e_time}"
    else:
        schedule = "as soon as possible"

    # Add urgency acknowledgment
    urgency = entities.get("urgency", "medium")
    urgency_prefix = ""
    if urgency in ("high", "emergency"):
        urgency_prefix = "⚡ **Urgent request received.** "
    elif urgency == "medium":
        urgency_prefix = ""

    # Pick template
    role_key = role if role in MAINTENANCE_RESPONSES else "default"
    if tech:
        template = MAINTENANCE_RESPONSES[role_key]["assigned"]
        msg = template.format(tech=tech, issue=issue, schedule=schedule)
    else:
        template = MAINTENANCE_RESPONSES[role_key]["no_technician"]
        msg = template.format(issue=issue)

    # Add room context if detected
    room = entities.get("room_number")
    if room:
        msg += f"\n\n📍 Room **{room}** has been noted in your complaint."

    # Add tracking tip
    msg += "\n\n💡 Use your **Request ID** to track real-time status on the Track Status page."

    return urgency_prefix + msg


# ═══════════════════════════════════════════════════════════════════
#  MAIN PIPELINE ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def analyze(raw_query: str) -> dict:
    """
    Full NLP pipeline. Returns structured result:
    {
      "clean_query":   str,
      "intent":        dict,
      "entities":      dict,
      "role":          str | None,
      "role_confidence": float,
      "category":      str,
    }
    """
    clean = normalize_text(raw_query)
    intent = detect_intent(clean)
    entities = extract_entities(clean)
    role, role_conf = detect_role(clean, entities)

    # Determine category
    if role:
        category = ROLE_TO_CATEGORY.get(role, "Hostel")
    elif intent["type"] == "inquiry":
        category = "Academic"
    elif intent["type"] == "emergency":
        category = "Emergency"
    else:
        category = "Hostel"

    return {
        "clean_query":     clean,
        "intent":          intent,
        "entities":        entities,
        "role":            role,
        "role_confidence": role_conf,
        "category":        category,
    }
