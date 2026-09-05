# server.py — AI-RMS Backend (v4.0 — Full NLP Upgrade, All Bugs Fixed)
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os, uuid, pickle
from dotenv import load_dotenv

load_dotenv()  # loads .env for local dev

import database as db
from ai.academic_ai import generate_response as academic_ai_response
from ai.certificate_verifier import verify_certificate as ai_verify_cert, get_file_extension, ALLOWED_EXTENSIONS
import ai.nlp_engine as nlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder="frontend", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "rms-ai-secret-key-2024")
CORS(app, supports_credentials=True)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# ── ML Model (fallback category classifier) ───────────────────────────────────
_ml_model, _ml_vectorizer = None, None
try:
    mf = os.path.join(BASE_DIR, "model.pkl")
    vf = os.path.join(BASE_DIR, "vectorizer.pkl")
    if os.path.exists(mf) and os.path.exists(vf):
        _ml_model = pickle.load(open(mf, "rb"))
        _ml_vectorizer = pickle.load(open(vf, "rb"))
        print("[OK] ML model loaded")
except Exception as e:
    print(f"[WARN] Model load warning: {e}")

# ── Init DB ───────────────────────────────────────────────────────────────────
db.init_db()


# ═════════════════════════════════════════════════════════════════════════════
#  ROUTE HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _ml_predict_category(query: str) -> str | None:
    """Use trained ML model as secondary category predictor."""
    if _ml_model and _ml_vectorizer:
        try:
            return _ml_model.predict(_ml_vectorizer.transform([query]))[0]
        except Exception as e:
            print(f"[WARN] ML predict error: {e}")
    return None


def find_technician(role: str, student_time: int | None = None):
    """
    Find the best available technician for a given role.
    Returns (name, start_time, end_time, assigned_slot, status_code).
    Time matching is fixed: parses 'HH:MM' format correctly.
    """
    techs = db.get_technicians_by_role(role)
    free = [t for t in (techs or []) if str(t.get("status", "")).lower() == "free"]

    if not free:
        return None, None, None, None, "no_technician"

    # Parse HH:MM time format into integer hours
    def parse_hour(time_str: str) -> int | None:
        try:
            if ":" in str(time_str):
                return int(str(time_str).split(":")[0])
            return int(time_str)
        except (ValueError, TypeError):
            return None

    # Try to match student's preferred time
    if student_time is not None:
        for t in free:
            start = parse_hour(t.get("start_time", ""))
            end   = parse_hour(t.get("end_time", ""))
            if start is not None and end is not None:
                if start <= int(student_time) <= end:
                    return t["name"], t["start_time"], t["end_time"], student_time, "matched"

    # No time preference — assign technician with lowest load
    best = free[0]
    return (best["name"], best["start_time"], best["end_time"],
            parse_hour(best.get("start_time", "")), "assigned")


# ═════════════════════════════════════════════════════════════════════════════
#  AUTH DECORATOR
# ═════════════════════════════════════════════════════════════════════════════
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized. Admin login required."}), 401
        return f(*args, **kwargs)
    return decorated


# ═════════════════════════════════════════════════════════════════════════════
#  STUDENT ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    sid  = str(data.get("student_id", "")).strip()
    pwd  = str(data.get("password",   "")).strip()
    student = db.get_student(sid, pwd)
    if student:
        return jsonify({"status": "success", "name": student["name"], "student_id": sid})
    return jsonify({"status": "error", "message": "Invalid ID or password"}), 401


@app.route("/submit_request", methods=["POST"])
def submit_request():
    data       = request.json or {}
    student_id = str(data.get("student_id", "")).strip()
    raw_query  = str(data.get("query", "")).strip()

    if not raw_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # ── 1. Run NLP pipeline ─────────────────────────────────────────────
    nlp_result = nlp.analyze(raw_query)
    clean_query = nlp_result["clean_query"]
    intent      = nlp_result["intent"]
    entities    = nlp_result["entities"]
    role        = nlp_result["role"]
    category    = nlp_result["category"]

    # ── 2. Duplicate detection (fixed algorithm) ────────────────────────
    recent = db.get_recent_requests(30)
    is_dup, dup_id = nlp.is_duplicate_query(clean_query, recent or [], student_id)

    # ── 3. Determine routing: academic inquiry vs maintenance ────────────
    ai_answer = ""
    dept_ref  = ""
    tech      = None
    s_t = e_t = slot = None
    student_time = entities.get("time_hour")

    if intent["type"] == "emergency":
        # Emergency: generate warning response + still try to assign technician
        ai_answer = nlp.EMERGENCY_RESPONSE
        status = "emergency"
        if role:
            tech, s_t, e_t, slot, _ = find_technician(role, student_time)

    elif intent["type"] == "maintenance" or (role is not None):
        # Physical maintenance complaint → route to technician
        if role:
            tech, s_t, e_t, slot, status = find_technician(role, student_time)
        else:
            # NLP detected maintenance but couldn't identify role — use ML fallback
            ml_cat = _ml_predict_category(clean_query)
            if ml_cat:
                category = ml_cat
            status = "pending"

        # Build human-like confirmation message
        ai_answer = nlp.build_human_response(
            intent, role, tech, s_t, e_t,
            entities.get("time_hour"), entities, clean_query
        )

    else:
        # Academic / inquiry → send to Academic AI
        academic_res = academic_ai_response(clean_query, student_id)
        ai_answer    = academic_res.get("answer", "")
        dept_ref     = academic_res.get("department_ref", "")
        category     = academic_res.get("category", category)
        status       = "ai_resolved"

    # ── 4. Update technician load ────────────────────────────────────────
    if tech:
        db.increment_load(tech)

    # ── 5. Persist request ───────────────────────────────────────────────
    req_id = str(uuid.uuid4())
    assigned_time = student_time if student_time is not None else slot

    db.insert_request(
        req_id, student_id, clean_query, category,
        tech or "",
        s_t  or "",
        e_t  or "",
        str(assigned_time) if assigned_time is not None else "",
        str(student_time)  if student_time  is not None else "",
        status,
        ai_answer,
    )

    # ── 6. Build response ────────────────────────────────────────────────
    return jsonify({
        "request_id":        req_id,
        "category":          category,
        "technician":        tech,
        "start_time":        s_t,
        "end_time":          e_t,
        "assigned_time":     assigned_time,
        "student_free_time": student_time,
        "status":            status,
        "ai_response":       ai_answer,
        "department_ref":    dept_ref,
        "is_duplicate":      is_dup,
        "duplicate_id":      dup_id,
        "intent":            intent["type"],
        "urgency":           entities.get("urgency", "medium"),
        "room_detected":     entities.get("room_number"),
        "nlp_confidence":    nlp_result.get("role_confidence", 0),
    })


@app.route("/get_status", methods=["GET"])
def get_status():
    req_id = (request.args.get("id") or request.args.get("request_id", "")).strip()
    row = db.get_request_by_id(req_id)
    if not row:
        return jsonify({"error": "Request not found"}), 404
    return jsonify(dict(row))


@app.route("/api/history/<student_id>", methods=["GET"])
def api_history(student_id):
    rows = db.get_requests_by_student(student_id)
    return jsonify(rows or [])


# ── NLP Analysis Preview (new endpoint) ──────────────────────────────────────
@app.route("/api/nlp/analyze", methods=["POST"])
def nlp_analyze():
    """
    Preview NLP analysis of a query before submitting.
    Returns detected intent, entities, role, and category.
    """
    data  = request.json or {}
    query = str(data.get("query", "")).strip()
    if not query:
        return jsonify({"error": "Query required"}), 400

    result = nlp.analyze(query)
    return jsonify({
        "intent":          result["intent"]["type"],
        "intent_confidence": result["intent"]["confidence"],
        "is_urgent":       result["intent"]["is_urgent"],
        "category":        result["category"],
        "role":            result["role"],
        "role_confidence": result["role_confidence"],
        "entities": {
            "room":          result["entities"].get("room_number"),
            "time":          result["entities"].get("time_hour"),
            "urgency":       result["entities"].get("urgency"),
            "objects_found": result["entities"].get("issue_objects", []),
        },
        "clean_query":     result["clean_query"],
    })


# ═════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json or {}
    pwd  = str(data.get("password", "")).strip()
    if pwd == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Wrong admin password"}), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"status": "success"})


@app.route("/admin/check_auth", methods=["GET"])
def admin_check_auth():
    return jsonify({"authenticated": bool(session.get("admin_logged_in"))})


@app.route("/admin/get_all_requests", methods=["GET"])
@admin_required
def admin_get_all_requests():
    return jsonify(db.get_all_requests() or [])


@app.route("/admin/update_status", methods=["POST"])
@admin_required
def admin_update_status():
    data       = request.json or {}
    req_id     = data.get("request_id", "")
    new_status = data.get("status", "")
    row = db.get_request_by_id(req_id)
    if not row:
        return jsonify({"error": "Request not found"}), 404
    db.update_request_status(req_id, new_status)
    if new_status == "resolved" and row.get("technician"):
        db.decrement_load(row["technician"])
    return jsonify({"message": "Status updated"})


@app.route("/admin/get_technicians", methods=["GET"])
@admin_required
def admin_get_technicians():
    return jsonify(db.get_all_technicians() or [])


@app.route("/admin/analytics", methods=["GET"])
@admin_required
def admin_analytics():
    return jsonify({
        "by_category": db.get_analytics(),
        "by_status":   db.get_status_counts(),
    })


@app.route("/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    counts = db.get_status_counts()
    techs  = db.get_all_technicians() or []
    total  = sum(counts.values())
    return jsonify({
        "total":       total,
        "pending":     counts.get("pending",     0),
        "resolved":    counts.get("resolved",    0),
        "in_progress": counts.get("in_progress", 0),
        "assigned":    counts.get("assigned",    0),
        "emergency":   counts.get("emergency",   0),
        "technicians": len(techs),
        "busy_techs":  sum(1 for t in techs if t.get("status") == "busy"),
    })


# ═════════════════════════════════════════════════════════════════════════════
#  TECHNICIAN ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/technician/login", methods=["POST"])
def technician_login():
    data = request.json or {}
    name = str(data.get("name", "")).strip()
    pwd  = str(data.get("password", "")).strip()
    tech = db.get_technician_by_credentials(name, pwd)
    if tech:
        return jsonify({"status": "success", "role": tech["role"], "name": name})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route("/technician/get_tasks", methods=["GET"])
def technician_get_tasks():
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name param required"}), 400
    return jsonify(db.get_requests_by_technician(name) or [])


@app.route("/api/technician/tasks/<tech_name>", methods=["GET"])
def api_technician_tasks(tech_name):
    return jsonify(db.get_requests_by_technician(tech_name) or [])


@app.route("/technician/update_task", methods=["POST"])
def technician_update_task():
    data       = request.json or {}
    req_id     = data.get("request_id", "")
    new_status = data.get("status", "")
    tech_name  = data.get("technician", "")
    row = db.get_request_by_id(req_id)
    if not row:
        return jsonify({"error": "Request not found"}), 404
    db.update_request_status(req_id, new_status)
    if new_status == "resolved" and tech_name:
        db.decrement_load(tech_name)
    return jsonify({"message": "updated"})


# ═════════════════════════════════════════════════════════════════════════════
#  ACADEMIC HELP DESK
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/academic/ask", methods=["POST"])
def academic_ask():
    data       = request.json or {}
    student_id = str(data.get("student_id", "")).strip()
    question   = str(data.get("question",   "")).strip()

    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    result = academic_ai_response(question, student_id)

    qid = str(uuid.uuid4())
    db.insert_academic_query(
        qid, student_id, question,
        result["category"], result["answer"],
        result["department_ref"], result.get("ai_powered", False)
    )

    return jsonify({
        "query_id":       qid,
        "question":       question,
        "answer":         result["answer"],
        "category":       result["category"],
        "department_ref": result["department_ref"],
        "ai_powered":     result.get("ai_powered", False),
        "from_cache":     result.get("from_cache", False),
    })


@app.route("/api/academic/history/<student_id>", methods=["GET"])
def academic_history(student_id):
    rows = db.get_academic_queries_by_student(student_id)
    return jsonify(rows or [])


@app.route("/admin/academic/get_all", methods=["GET"])
@admin_required
def admin_academic_all():
    return jsonify(db.get_all_academic_queries() or [])


@app.route("/admin/academic/add_note", methods=["POST"])
@admin_required
def admin_academic_note():
    data     = request.json or {}
    query_id = data.get("query_id", "")
    note     = data.get("note",     "")
    db.update_academic_note(query_id, note)
    return jsonify({"message": "Note saved"})


# ═════════════════════════════════════════════════════════════════════════════
#  CERTIFICATE VERIFICATION
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/certificate/verify", methods=["POST"])
def certificate_verify():
    student_id = request.form.get("student_id", "").strip()

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f   = request.files["file"]
    ext = get_file_extension(f.filename)
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported format. Upload: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    image_bytes = f.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        return jsonify({"error": "File too large. Max 10 MB."}), 400

    result = ai_verify_cert(image_bytes, f.filename, student_id)

    if result.get("error") and not result.get("ai_powered"):
        return jsonify({"error": result["error"], "verdict": result["verdict"]}), 503

    ext_data = result.get("extracted", {})
    vid = str(uuid.uuid4())
    db.insert_certificate_verification(
        vid, student_id, f.filename,
        ext_data.get("name", ""),
        ext_data.get("institution", ""),
        ext_data.get("degree_or_title", ""),
        ext_data.get("date", ""),
        ext_data.get("certificate_number", ""),
        result.get("verdict", "REQUIRES MANUAL REVIEW"),
        result.get("confidence", 0),
        result.get("pass_rate", 0),
        result.get("flags", []),
        result.get("summary", ""),
    )

    return jsonify({
        "verify_id":  vid,
        "filename":   f.filename,
        "extracted":  ext_data,
        "checks":     result.get("checks", {}),
        "flags":      result.get("flags", []),
        "verdict":    result.get("verdict"),
        "confidence": result.get("confidence", 0),
        "pass_rate":  result.get("pass_rate", 0),
        "summary":    result.get("summary", ""),
        "ai_powered": result.get("ai_powered", False),
    })


@app.route("/api/certificate/history/<student_id>", methods=["GET"])
def certificate_history(student_id):
    rows = db.get_certificate_verifications_by_student(student_id)
    return jsonify(rows or [])


@app.route("/admin/certificates/get_all", methods=["GET"])
@admin_required
def admin_certs_all():
    return jsonify(db.get_all_certificate_verifications() or [])


@app.route("/admin/certificates/override", methods=["POST"])
@admin_required
def admin_cert_override():
    data      = request.json or {}
    verify_id = data.get("verify_id", "")
    verdict   = data.get("verdict",   "")
    note      = data.get("note",      "")
    db.override_certificate_verdict(verify_id, verdict, note)
    return jsonify({"message": "Verdict overridden"})


# ═════════════════════════════════════════════════════════════════════════════
#  STATIC FILES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def root():
    return send_from_directory("frontend", "homepage.html")


@app.route("/<path:filename>")
def serve_frontend(filename):
    return send_from_directory("frontend", filename)


# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
