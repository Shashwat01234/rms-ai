# server_sql.py – SQL upgraded version of server.py (Option A)
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import uuid
import pickle
import os
import pandas as pd

from database import (
    insert_request,
    get_requests_by_student,
    update_request_status,
    get_available_technicians
)

# ------------------------------
# Setup
# ------------------------------
app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_FILE = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_FILE = os.path.join(BASE_DIR, "vectorizer.pkl")

model, vectorizer = None, None
try:
    if os.path.exists(MODEL_FILE) and os.path.exists(VECTORIZER_FILE):
        model = pickle.load(open(MODEL_FILE, "rb"))
        vectorizer = pickle.load(open(VECTORIZER_FILE, "rb"))
except:
    pass


# ------------------------------
# Clean query function
# ------------------------------
def clean_query_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()

    corrections = {
        "wokring": "working", "workin": "working", "wrkng": "working",
        "not wrking": "not working",
        "plz": "please", "pls": "please",
        "ac": "air conditioner", "a.c": "air conditioner",
        "leek": "leak", "lakage": "leakage",
        "hstl": "hostel"
    }
    for w, r in corrections.items():
        text = text.replace(w, r)

    return " ".join(text.split())


# ------------------------------
# Duplicate detection (SQL version)
# ------------------------------
def sql_duplicate_check(query):
    # Load last 20 requests from SQL (simple method)
    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()
    cur.execute("SELECT request_id, query FROM requests ORDER BY rowid DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()

    q_new = set(query.split())

    for req_id, old in rows:
        if not isinstance(old, str):
            continue
        q_old = set(old.lower().split())
        overlap = len(q_new & q_old) / max(len(q_old), 1)
        if overlap > 0.6:
            return True, req_id

    return False, None


# ------------------------------
# Keyword boost mapping
# ------------------------------
maintenance_keywords = {
    "electrician": ["fan", "light", "switch", "socket", "ac", "air conditioner"],
    "plumber": ["leak", "water", "tap", "pipe", "flush"],
    "carpenter": ["door", "bed", "window", "table"]
}


def keyword_boost(query):
    for role, words in maintenance_keywords.items():
        for w in words:
            if w in query:
                return "Hostel", role
    return None, None


# ------------------------------
# Extract time logic
# ------------------------------
def extract_time(query):
    q = query.lower()
    m = re.search(r"(\d{1,2})\s?(am|pm)", q)
    if m:
        h = int(m.group(1))
        if m.group(2) == "pm" and h != 12:
            h += 12
        if m.group(2) == "am" and h == 12:
            h = 0
        return h

    if "morning" in q:
        return 10
    if "afternoon" in q:
        return 14
    if "evening" in q:
        return 18
    if "night" in q:
        return 20

    return None


# ------------------------------
# Technician assignment
# ------------------------------
def assign_technician(role, student_time):
    techs = get_available_technicians(role)
    if not techs:
        return None, None, None, None, "no_technician"

    best = None
    lowest_load = 9999

    for name, role, start, end, load, status in techs:
        if status != "free":
            continue

        # Convert to int safely
        try:
            s = int(start)
            e = int(end)
        except:
            continue

        if student_time is None:
            if load < lowest_load:
                best = (name, start, end)
                lowest_load = load
        else:
            if s <= student_time <= e and load < lowest_load:
                best = (name, start, end)
                lowest_load = load

    if best:
        return best[0], best[1], best[2], student_time, "matched"

    # fallback lowest load
    first = techs[0]
    return first[0], first[2], first[3], first[2], "no_time_match"


# ------------------------------
# Submit Request
# ------------------------------
@app.route("/submit_request", methods=["POST"])
def submit_request():
    data = request.json or {}
    student_id = data.get("student_id", "")
    query_raw = data.get("query", "")
    query_clean = clean_query_text(query_raw)

    # Duplicate check
    is_dup, dup_id = sql_duplicate_check(query_clean)

    # Extract time
    student_time = extract_time(query_clean)

    # Category detection
    cat_boost, role_boost = keyword_boost(query_clean)

    if role_boost:
        category = cat_boost
        role = role_boost
    else:
        if model and vectorizer:
            try:
                q_vec = vectorizer.transform([query_clean])
                category = model.predict(q_vec)[0]
            except:
                category = "Hostel"
        else:
            category = "Hostel"

        # Default role for hostel
        role = "electrician" if "fan" in query_clean else None

    # assign technician
    if role:
        tech, s, e, assigned_time, status = assign_technician(role, student_time)
    else:
        tech, s, e, assigned_time, status = (None, None, None, None, "no_technician")

    req_id = str(uuid.uuid4())

    insert_request({
        "request_id": req_id,
        "student_id": student_id,
        "query": query_clean,
        "category": category,
        "technician": tech,
        "start_time": s,
        "end_time": e,
        "assigned_time": assigned_time,
        "student_free_time": student_time,
        "status": status
    })

    return jsonify({
        "request_id": req_id,
        "category": category,
        "technician": tech,
        "start_time": s,
        "end_time": e,
        "assigned_time": assigned_time,
        "student_free_time": student_time,
        "status": status,
        "is_duplicate": is_dup,
        "duplicate_id": dup_id
    })


# ------------------------------
# GET STATUS
# ------------------------------
@app.route("/get_status", methods=["GET"])
def get_status():
    req_id = request.args.get("id")
    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE request_id=?", (req_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"error": "not found"}

    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]

    return dict(zip(keys, row))


# ------------------------------
# Student History
# ------------------------------
@app.route("/api/history/<student_id>")
def history(student_id):
    rows = get_requests_by_student(student_id)
    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]
    return jsonify([dict(zip(keys, r)) for r in rows])


# ------------------------------
# Admin ops
# ------------------------------
@app.route("/admin/update_status", methods=["POST"])
def admin_update():
    data = request.json or {}
    update_request_status(data["request_id"], data["status"])
    return {"message": "updated"}


# ------------------------------
# Frontend serving
# ------------------------------
@app.route("/")
def home():
    return send_from_directory("frontend", "login.html")
# ------------------------------
# Student Login (SQL version)
# ------------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    student_id = data.get("student_id", "")
    password = data.get("password", "")

    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    cur.execute("SELECT name FROM students WHERE student_id=? AND password=?", (student_id, password))
    row = cur.fetchone()

    conn.close()

    if row:
        return jsonify({"status": "success", "message": "Login successful", "name": row[0]})
    else:
        return jsonify({"status": "error", "message": "Invalid ID or password"})
# ------------------------------
# Technician Login (SQL version)
# ------------------------------
@app.route("/technician/login", methods=["POST"])
def technician_login():
    data = request.json or {}
    name = data.get("name", "")
    password = data.get("password", "")

    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    cur.execute("SELECT role FROM technicians WHERE name=? AND password=?", (name, password))
    row = cur.fetchone()
    conn.close()

    if row:
        return {"status": "success", "name": name, "role": row[0]}
    else:
        return {"status": "error", "message": "Invalid credentials"}
# ------------------------------
# Technician Tasks
# ------------------------------
@app.route("/technician/get_tasks", methods=["GET"])
def technician_get_tasks():
    tech_name = request.args.get("name", "")

    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM requests WHERE technician=?", (tech_name,))
    rows = cur.fetchall()
    conn.close()

    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]

    return jsonify([dict(zip(keys, r)) for r in rows])
# ------------------------------
# Admin — Get All Requests (SQL)
# ------------------------------
@app.route("/admin/get_all_requests")
def admin_get_all_requests():
    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM requests")
    rows = cur.fetchall()
    conn.close()

    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]

    return jsonify([dict(zip(keys, r)) for r in rows])
# ------------------------------
# Admin — Get All Technicians
# ------------------------------
@app.route("/admin/get_technicians")
def admin_get_technicians():
    import sqlite3
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM technicians")
    rows = cur.fetchall()
    conn.close()

    keys = ["name","role","start_time","end_time","current_load","status","password"]

    return jsonify([dict(zip(keys, r)) for r in rows])


# ------------------------------
# Run server
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
