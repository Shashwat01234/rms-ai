# ai/academic_ai.py — LPU Academic AI Advisor powered by Gemini 2.0
import os
import hashlib
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Simple in-memory response cache (avoids duplicate API calls) ──────────────
_response_cache: dict = {}   # key: hash(question) → (answer, timestamp)
_CACHE_TTL_SEC = 600         # 10 minutes


def _cache_get(question: str) -> str | None:
    key = hashlib.md5(question.lower().strip().encode()).hexdigest()
    entry = _response_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL_SEC:
        return entry["answer"]
    return None


def _cache_set(question: str, answer: str):
    key = hashlib.md5(question.lower().strip().encode()).hexdigest()
    _response_cache[key] = {"answer": answer, "ts": time.time()}


# ── Per-student short-term conversation memory ────────────────────────────────
_conversation_memory: dict[str, list[dict]] = {}
_MAX_MEMORY_TURNS = 4   # keep last 4 Q&A pairs per student


def _get_memory(student_id: str) -> list[dict]:
    return _conversation_memory.get(student_id, [])


def _push_memory(student_id: str, q: str, a: str):
    if student_id not in _conversation_memory:
        _conversation_memory[student_id] = []
    _conversation_memory[student_id].append({"role": "user", "parts": [q]})
    _conversation_memory[student_id].append({"role": "model", "parts": [a]})
    # Trim to max turns (each turn = 2 entries)
    if len(_conversation_memory[student_id]) > _MAX_MEMORY_TURNS * 2:
        _conversation_memory[student_id] = _conversation_memory[student_id][-(
            _MAX_MEMORY_TURNS * 2):]


# ── Category definitions ──────────────────────────────────────────────────────
CATEGORIES = {
    "Fee & Finance": {
        "keywords": ["fee", "payment", "scholarship", "emi", "fine", "challan",
                     "dues", "refund", "hostel fee", "balance", "receipt",
                     "pending fee", "fee waiver", "late fee", "tuition"],
        "synonyms": ["money", "pay", "cost", "amount", "outstanding", "financial",
                     "bank", "upi", "net banking", "debit", "credit"],
    },
    "Examinations": {
        "keywords": ["exam", "date sheet", "backlog", "re-exam", "grace", "practical",
                     "viva", "hall ticket", "seating", "examination", "test", "quiz",
                     "mid term", "end term", "sessional"],
        "synonyms": ["paper", "appear", "attempt", "sit for", "write exam", "exam form"],
    },
    "Results & Grades": {
        "keywords": ["result", "cgpa", "grade", "marks", "recheck", "re-evaluation",
                     "transcript", "marksheet", "sgpa", "pass", "fail", "score"],
        "synonyms": ["gpa", "performance", "percentage", "appear", "cleared",
                     "credit", "gradesheet"],
    },
    "UMS Portal": {
        "keywords": ["ums", "portal", "login", "attendance", "timetable", "assignment",
                     "password", "username", "upload", "link", "student portal"],
        "synonyms": ["website", "online", "access", "sign in", "dashboard", "account",
                     "forgot password", "reset password", "otp"],
    },
    "Documents & Certificates": {
        "keywords": ["bonafide", "character certificate", "noc", "migration", "tc",
                     "transfer", "certificate", "verification", "document", "letter",
                     "leaving certificate", "clearance"],
        "synonyms": ["attestation", "apostille", "stamp", "official", "proof",
                     "letter head", "letterhead"],
    },
    "Admissions": {
        "keywords": ["admission", "lateral entry", "programme change", "branch change",
                     "application", "prospectus", "seat", "registration", "enroll",
                     "course change", "transfer to"],
        "synonyms": ["apply", "joining", "intake", "new admission"],
    },
    "Scholarships": {
        "keywords": ["scholarship", "merit", "government", "stipend", "financial aid",
                     "waiver", "pm", "state scholarship", "fellowship", "nsp",
                     "national scholarship"],
        "synonyms": ["grant", "bursary", "fee concession", "free ship", "sisgp",
                     "post matric"],
    },
    "Placement & Career": {
        "keywords": ["placement", "internship", "company", "career", "job", "cdc",
                     "campus", "interview", "offer", "resume", "cv", "drive"],
        "synonyms": ["recruit", "hire", "job offer", "ppo", "off campus", "on campus",
                     "aptitude", "coding test"],
    },
    "Library": {
        "keywords": ["library", "book", "fine", "issue", "return", "e-resource",
                     "digital", "journal", "research", "reading room", "overdue",
                     "renew", "extend"],
        "synonyms": ["borrow", "checkout", "ieee", "springer", "elsevier", "thesis"],
    },
    "Hostel & Campus": {
        "keywords": ["hostel", "mess", "room", "wifi", "campus", "canteen", "sports",
                     "gym", "medical", "health", "bus", "shuttle", "room change",
                     "hostel room"],
        "synonyms": ["dorm", "accommodation", "stay", "residential"],
    },
    "Departments & Faculty": {
        "keywords": ["department", "faculty", "professor", "dean", "hod", "contact",
                     "cse", "ece", "me", "mba", "law", "agriculture", "pharmacy",
                     "phd", "research guide"],
        "synonyms": ["teacher", "lecturer", "prof", "instructor", "school of"],
    },
}

DEPARTMENT_CONTACTS = {
    "Fee & Finance":            "Finance Department — UMS > Fee Section | finance@lpu.co.in | Finance Block, LPU Campus",
    "Examinations":             "Examination Department — exams@lpu.co.in | Exam Block, LPU Campus | +91-1824-517000",
    "Results & Grades":         "Controller of Examinations — UMS > Results | exam.queries@lpu.co.in",
    "UMS Portal":               "IT Help Desk — ithelpdesk@lpu.co.in | UMS > Help | +91-1824-517000",
    "Documents & Certificates": "Registrar Office — registrar@lpu.co.in | Administrative Block, LPU",
    "Admissions":               "Admissions Department — admission@lpu.co.in | +91-1824-517000",
    "Scholarships":             "Scholarship Section — scholarship@lpu.co.in | UMS > Scholarship Portal",
    "Placement & Career":       "Career Development Centre — cdc@lpu.co.in | CDC Block, LPU",
    "Library":                  "Central Library — library@lpu.co.in | Central Library Building, LPU",
    "Hostel & Campus":          "Hostel Administration — hostel@lpu.co.in | Hostel Office, LPU",
    "Departments & Faculty":    "Respective Department Office | UMS > Faculty Directory",
    "General Academic":         "Student Services — studentservices@lpu.co.in | +91-1824-517000",
}

FALLBACK_KB = {
    "Fee & Finance": """**LPU Fee & Finance — Step-by-Step Guide:**

1. **View Dues**: Log in to [ums.lpu.in](http://ums.lpu.in) → Fee Section → Outstanding Dues
2. **Pay Online**: UMS → Fee → Pay Fee → select Net Banking / UPI / Debit Card
3. **Download Receipt**: UMS → Fee → Payment History → Download Receipt
4. **EMI / Payment Plan**: Visit Finance Block in person with your student ID
5. **Fine Waiver**: Submit a written application at Finance Block with supporting documents
6. **Hostel Fee**: Paid separately via UMS → Hostel Fee section
7. **Scholarship Adjustment**: Status visible under UMS → Fee → Scholarship Details

📧 **finance@lpu.co.in** | 📍 Finance Block, LPU Campus | ☎️ +91-1824-517000""",

    "Examinations": """**LPU Examinations — Complete Guide:**

1. **Date Sheet**: UMS → Examination → Date Sheet (published ~15 days before exams)
2. **Admit Card / Hall Ticket**: UMS → Examination → Hall Ticket (download & print)
3. **Backlog Registration**: UMS → Examination → Backlog Registration (check registration window dates)
4. **Re-exam Form**: Submit through UMS within the prescribed deadline
5. **Grace Marks**: Subject to LPU examination regulations — check UMS Notices
6. **Practical/Viva**: Scheduled by respective departments — check UMS or ask your HoD

📧 **exams@lpu.co.in** | 📍 Exam Block, LPU Campus | ☎️ +91-1824-517000""",

    "Results & Grades": """**LPU Results & Grades — Complete Guide:**

1. **View Results**: UMS → Academics → Result (available after declaration)
2. **CGPA/SGPA**: UMS → Result Dashboard → Semester-wise breakdown
3. **Re-evaluation Application**: UMS → Examination → Re-evaluation (apply within 15 days of result)
4. **Marks Verification/Recheck**: Apply via UMS within the deadline after result
5. **Official Transcripts**: UMS → Documents → Official Transcript Request (takes 5-7 working days)
6. **Marksheet**: Download provisional from UMS; original issued at convocation

📧 **exam.queries@lpu.co.in** | Visit Examination Block for urgent matters""",

    "UMS Portal": """**LPU UMS Portal — Complete Guide:**

1. **Portal URL**: [ums.lpu.in](http://ums.lpu.in) — use your LPU Registration ID as username
2. **Forgot Password**: UMS Login → "Forgot Password" → OTP on registered mobile/email
3. **Attendance**: UMS → Academics → Attendance (updated daily — check after 8 PM)
4. **Timetable**: UMS → Academics → Time Table
5. **Submit Assignment**: UMS → Academics → Assignments → Select → Submit
6. **UMS Down**: Contact IT Help Desk immediately or use the LPU app as fallback
7. **Update Profile/Contact**: UMS → My Profile → Edit Details

📧 **ithelpdesk@lpu.co.in** | +91-1824-517000 (IT Help Desk)""",

    "Documents & Certificates": """**LPU Documents & Certificates — Complete Guide:**

1. **Bonafide Certificate**: UMS → Documents → Bonafide Certificate (ready in 3-5 working days)
2. **Character Certificate**: Apply at Registrar Office with ID proof and application form
3. **Migration Certificate**: Registrar Office — submit clearance from all departments first
4. **Transfer Certificate (TC)**: Registrar Office — requires signed clearance from: Hostel, Library, Finance, Exam
5. **NOC (Hostel)**: Hostel Office with room clearance | **NOC (Library)**: Library Counter
6. **Official Transcripts**: UMS → Documents → Transcript Request (7-10 working days)
7. **Degree Certificate**: Issued at convocation; duplicate requires application to Registrar

📧 **registrar@lpu.co.in** | 📍 Administrative Block, LPU""",

    "Scholarships": """**LPU Scholarship — Complete Guide:**

1. **LPU Merit Scholarship**: Auto-applied based on 12th/graduation marks — check UMS → Scholarship
2. **Government Scholarships (NSP)**: Apply on [scholarships.gov.in](http://scholarships.gov.in) AND submit to LPU Scholarship Section
3. **State Scholarships**: Apply on respective state portal + submit documents to Scholarship Section
4. **Check Status**: UMS → Fee → Scholarship Details
5. **Renewal**: Maintain required CGPA (varies by scholarship — check your award letter)
6. **Required Documents**: Bonafide Certificate, Fee Receipt, Bank Passbook (first page), Income Certificate

📧 **scholarship@lpu.co.in** | 📍 UMS > Scholarship Portal""",

    "Placement & Career": """**LPU Placement & Career — Complete Guide:**

1. **CDC Registration**: UMS → Career Development Centre → Register for Placement
2. **Upcoming Drives**: UMS → CDC → Upcoming Drives (notifications sent to registered email)
3. **Upload Resume**: UMS → CDC → Profile → Resume → Upload (PDF preferred)
4. **Internship**: UMS → CDC → Internship Portal → Apply
5. **Eligibility**: Typically 60%+ aggregate, no active backlogs (varies by company)
6. **Off-Campus**: Follow CDC notice board + LPU Placement LinkedIn page
7. **Mock Interviews**: CDC conducts preparation sessions — check CDC notice board

📧 **cdc@lpu.co.in** | 📍 CDC Block, LPU""",

    "Library": """**LPU Library — Complete Guide:**

1. **Issue Books**: Present student ID at circulation desk or use self-checkout machine
2. **Return Books**: On or before due date — check UMS → Library for due dates
3. **Fine Payment**: UMS → Library → Fine Payment (₹2/day per book typically)
4. **Renew Books**: UMS → Library → My Issues → Renew (if no reservation on the book)
5. **E-Resources**: UMS → Library → E-Resources (access IEEE, Springer, Elsevier etc.)
6. **Library Card**: Issued automatically — collect from library with student ID
7. **Reading Room**: Generally 8 AM – 10 PM (check library notice for current hours)

📧 **library@lpu.co.in** | 📍 Central Library Building, LPU""",
}


# ── Improved category classifier ──────────────────────────────────────────────

def classify_query(question: str) -> str:
    """
    Multi-signal classifier:
    1. Keyword score (weighted)
    2. Synonym expansion score
    3. Tie-break by question word detection
    Returns the best matching category.
    """
    q = question.lower()
    scores: dict[str, float] = {}

    for cat, data in CATEGORIES.items():
        score = 0.0
        # Primary keywords — higher weight
        for kw in data["keywords"]:
            if kw in q:
                # Longer keywords are more specific → give more weight
                score += 1.0 + (len(kw.split()) - 1) * 0.5
        # Synonyms — lower weight
        for syn in data.get("synonyms", []):
            if syn in q:
                score += 0.4
        if score > 0:
            scores[cat] = score

    if not scores:
        return "General Academic"

    # If there's a tie, prefer the category whose keyword appeared earliest in the query
    max_score = max(scores.values())
    top_cats = [c for c, s in scores.items() if s == max_score]
    if len(top_cats) == 1:
        return top_cats[0]

    # Tie-break: find which category's keyword appears first in the query
    for i, word in enumerate(q.split()):
        for cat in top_cats:
            if any(word in kw or kw in word
                   for kw in CATEGORIES[cat]["keywords"]):
                return cat

    return top_cats[0]


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_response(question: str, student_id: str = "") -> dict:
    """Generate AI response. Uses Gemini 2.0 Flash if key present, else rule-based fallback."""
    category = classify_query(question)
    dept_ref = DEPARTMENT_CONTACTS.get(category, DEPARTMENT_CONTACTS["General Academic"])

    if GEMINI_API_KEY and GEMINI_API_KEY.strip() not in ("", "YOUR_KEY_HERE"):
        # Check cache first
        cached = _cache_get(question)
        if cached:
            return {
                "answer":         cached,
                "category":       category,
                "department_ref": dept_ref,
                "ai_powered":     True,
                "from_cache":     True,
            }
        try:
            answer = _call_gemini(question, student_id)
            _cache_set(question, answer)
            if student_id:
                _push_memory(student_id, question, answer)
            return {
                "answer":         answer,
                "category":       category,
                "department_ref": dept_ref,
                "ai_powered":     True,
                "from_cache":     False,
            }
        except Exception as e:
            print(f"[WARN] Gemini academic error: {e}")

    # Rule-based fallback
    fallback = FALLBACK_KB.get(
        category,
        f"For help with this query, please contact the relevant LPU department.\n\n"
        f"📧 {dept_ref}\n\n☎️ General Helpline: +91-1824-517000"
    )
    return {
        "answer":         fallback,
        "category":       category,
        "department_ref": dept_ref,
        "ai_powered":     False,
        "from_cache":     False,
    }


def _call_gemini(question: str, student_id: str = "") -> str:
    """Call Gemini 2.0 Flash with conversation memory."""
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    system_prompt = """You are Aria, the official AI Academic Advisor for Lovely Professional University (LPU), Phagwara, Punjab, India — one of India's largest private universities with 30,000+ students.

Your personality: Warm, empathetic, knowledgeable, and clear. You treat every student as a person — acknowledge their concern before diving into the solution.

Help students with: fee payment, scholarships, exam schedule, results, UMS portal, bonafide/certificates, admissions, placements, hostel, library, and department queries.

Response guidelines:
- **Start with a brief empathetic acknowledgment** (1 sentence) — e.g. "I understand this can be stressful…"
- Give **clear, numbered step-by-step guidance** (most important)
- Always **reference UMS (ums.lpu.in)** when relevant
- Mention the **correct LPU department and contact email**
- Keep it **150–250 words** — concise but complete
- Use **bold** for important terms and department names
- **Do NOT make up specific dates** — guide to official channels
- End with the department contact (email/phone)
- If you don't know something specific, say so and guide to the right contact"""

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt,
    )

    # Build conversation history if student has memory
    history = _get_memory(student_id) if student_id else []

    if history:
        chat = model.start_chat(history=history)
        resp = chat.send_message(question)
    else:
        resp = model.generate_content(question)

    return resp.text.strip()
