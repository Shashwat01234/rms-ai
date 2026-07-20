# ai/academic_ai.py — LPU Academic AI Advisor powered by Gemini
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Category definitions ──────────────────────────────────────────
CATEGORIES = {
    "Fee & Finance":          ["fee","payment","scholarship","emi","fine","challan","dues","refund","hostel fee","balance","receipt"],
    "Examinations":           ["exam","date sheet","backlog","re-exam","grace","practical","viva","hall ticket","seating","examination"],
    "Results & Grades":       ["result","cgpa","grade","marks","recheck","re-evaluation","transcript","marksheet","sgpa","pass"],
    "UMS Portal":             ["ums","portal","login","attendance","timetable","assignment","password","username","upload","link"],
    "Documents & Certificates":["bonafide","character certificate","noc","migration","tc","transfer","certificate","verification","document","letter"],
    "Admissions":             ["admission","lateral entry","programme change","branch change","application","prospectus","seat","registration"],
    "Scholarships":           ["scholarship","merit","government","stipend","financial aid","waiver","pm","state scholarship","fellowship"],
    "Placement & Career":     ["placement","internship","company","career","job","cdc","campus","interview","offer","resume","cv"],
    "Library":                ["library","book","fine","issue","return","e-resource","digital","journal","research","reading room"],
    "Hostel & Campus":        ["hostel","mess","room","wifi","campus","canteen","sports","gym","medical","health","bus","shuttle"],
    "Departments & Faculty":  ["department","faculty","professor","dean","hod","contact","cse","ece","me","mba","law","agriculture","pharmacy"],
}

DEPARTMENT_CONTACTS = {
    "Fee & Finance":           "Finance Department — UMS > Fee Section | finance@lpu.co.in | Finance Block, LPU Campus",
    "Examinations":            "Examination Department — exams@lpu.co.in | Exam Block, LPU Campus | +91-1824-517000",
    "Results & Grades":        "Controller of Examinations — UMS > Results | exam.queries@lpu.co.in",
    "UMS Portal":              "IT Help Desk — ithelpdesk@lpu.co.in | UMS > Help | +91-1824-517000",
    "Documents & Certificates":"Registrar Office — registrar@lpu.co.in | Administrative Block, LPU",
    "Admissions":              "Admissions Department — admission@lpu.co.in | +91-1824-517000",
    "Scholarships":            "Scholarship Section — scholarship@lpu.co.in | UMS > Scholarship Portal",
    "Placement & Career":      "Career Development Centre — cdc@lpu.co.in | CDC Block, LPU",
    "Library":                 "Central Library — library@lpu.co.in | Central Library Building, LPU",
    "Hostel & Campus":         "Hostel Administration — hostel@lpu.co.in | Hostel Office, LPU",
    "Departments & Faculty":   "Respective Department Office | UMS > Faculty Directory",
    "General Academic":        "Student Services — studentservices@lpu.co.in | +91-1824-517000",
}

FALLBACK_KB = {
    "Fee & Finance": """**LPU Fee Guidance:**
1. Log in to UMS (ums.lpu.in) → Fee Section to view outstanding dues
2. Pay online via UMS → Net Banking / UPI / Debit Card
3. For fine waiver: Submit application to Finance Block with supporting documents
4. Hostel fee is separate — payable via UMS → Hostel Fee section
5. Fee receipts: Download from UMS → Fee → Payment History
6. For EMI / payment plan: Visit Finance Department directly

📧 Contact: finance@lpu.co.in | 📍 Finance Block, LPU""",

    "Examinations": """**LPU Examination Guidance:**
1. Date sheets are published on UMS → Examination → Date Sheet (usually 15 days before exams)
2. Admit Card: Download from UMS → Examination → Hall Ticket
3. For backlog registration: UMS → Examination → Backlog Registration (within the registration window)
4. Grace marks policy follows LPU examination regulations — check UMS Notices
5. Practical/Viva schedules: Notified by respective departments via UMS

📧 Contact: exams@lpu.co.in | 📍 Exam Block, LPU""",

    "Results & Grades": """**LPU Results & Grades Guidance:**
1. Results are published on UMS → Academics → Result
2. CGPA/SGPA: Visible on UMS → Result Dashboard
3. Re-evaluation: Apply within 15 days of result declaration via UMS → Examination → Re-evaluation
4. For re-checking (marks verification): Apply via UMS within the deadline
5. Official Transcripts: Request via Registrar Office or UMS → Documents → Transcript Request

📧 Contact: exam.queries@lpu.co.in""",

    "UMS Portal": """**LPU UMS Portal Guidance:**
1. Portal URL: ums.lpu.in — use your official LPU email/ID
2. Forgot Password: UMS login page → "Forgot Password" → OTP on registered mobile/email
3. Attendance: UMS → Academics → Attendance (updated daily by faculty)
4. Timetable: UMS → Academics → Time Table
5. Assignment upload: UMS → Academics → Assignments → Submit
6. If UMS is down: Contact IT Help Desk immediately

📧 Contact: ithelpdesk@lpu.co.in""",

    "Documents & Certificates": """**LPU Documents & Certificates Guidance:**
1. Bonafide Certificate: UMS → Documents → Bonafide (takes 3-5 working days)
2. Character Certificate: Apply at Registrar Office with ID proof
3. Migration Certificate: Apply at Registrar Office (submit TC form first)
4. Transfer Certificate (TC): Registrar Office — submit clearance form from all departments
5. NOC: Relevant department (Hostel NOC from Hostel Office, Library NOC from Library)
6. Transcripts: UMS → Documents → Official Transcript Request

📧 Contact: registrar@lpu.co.in | 📍 Administrative Block, LPU""",

    "Scholarships": """**LPU Scholarship Guidance:**
1. LPU Merit Scholarships: Auto-applied based on 12th/graduation marks — check UMS → Scholarship
2. Government Scholarships (NSP, State): Apply on National Scholarship Portal + submit to LPU Scholarship Section
3. Scholarship status: UMS → Fee → Scholarship Details
4. For scholarship renewal: Maintain required CGPA (check your scholarship terms)
5. PM Scholarship / State Scholarships: Required documents include bonafide, fee receipt, bank details

📧 Contact: scholarship@lpu.co.in | 📍 UMS > Scholarship Portal""",

    "Placement & Career": """**LPU Placement & Career Guidance:**
1. CDC Registration: UMS → Career Development Centre → Register for Placement
2. Company drives: Check UMS → CDC → Upcoming Drives (notifications via registered email)
3. Resume Upload: UMS → CDC → Profile → Upload Resume
4. Internship Portal: UMS → CDC → Internship
5. Eligibility criteria: Typically 60%+ aggregate, no active backlogs (varies by company)
6. Off-campus opportunities: CDC notice board and LPU Placement LinkedIn page

📧 Contact: cdc@lpu.co.in | 📍 CDC Block, LPU""",

    "Library": """**LPU Library Guidance:**
1. Book Issue: Present student ID at circulation desk or use self-checkout machine
2. Book return: On or before due date to avoid fines (Rs. 2/day per book typically)
3. Fine Payment: Pay at library counter or via UMS → Library → Fine Payment
4. E-Resources: Access via UMS → Library → E-Resources (IEEE, Springer, Elsevier etc.)
5. Library card: Issued automatically — collect from library with student ID
6. Reading room hours: Generally 8 AM - 10 PM (check library for current timings)

📧 Contact: library@lpu.co.in | 📍 Central Library Building""",
}

# ── Main function ──────────────────────────────────────────────────
def classify_query(question: str) -> str:
    q = question.lower()
    best_cat, best_score = "General Academic", 0
    for cat, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def generate_response(question: str, student_id: str = "") -> dict:
    """Generate AI response. Uses Gemini if key present, else rule-based fallback."""
    category    = classify_query(question)
    dept_ref    = DEPARTMENT_CONTACTS.get(category, DEPARTMENT_CONTACTS["General Academic"])

    if GEMINI_API_KEY:
        try:
            answer = _call_gemini(question)
            return {"answer": answer, "category": category, "department_ref": dept_ref, "ai_powered": True}
        except Exception as e:
            print(f"[WARN] Gemini academic error: {e}")

    fallback = FALLBACK_KB.get(category,
        f"Please contact the relevant LPU department.\n\n{dept_ref}\n\nFor general help: +91-1824-517000")
    return {"answer": fallback, "category": category, "department_ref": dept_ref, "ai_powered": False}


def _call_gemini(question: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="""You are the official AI Academic Advisor for Lovely Professional University (LPU), Phagwara, Punjab, India — one of India's largest private universities with 30,000+ students.

Help students with: fee payment, scholarships, exam schedule, results, UMS portal, bonafide/certificates, admissions, placements, hostel, library, and department queries.

Rules:
- Give clear, actionable, step-by-step guidance
- Reference UMS (ums.lpu.in) when relevant
- Mention the correct LPU department and contact email
- Be empathetic, professional, and concise (150-250 words)
- Format with numbered steps for instructions
- Do NOT make up specific dates — guide to official channels
- Use formatting: **bold** for important points, numbered lists for steps"""
    )
    resp = model.generate_content(question)
    return resp.text
