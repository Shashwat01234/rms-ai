# server_sql.py – SQL upgraded RMS backend (FINAL VERSION)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import uuid
import pickle
import os
import sqlite3

from database import (
    create_tables,
    insert_request,
    get_requests_by_student,
    update_request_status,
    get_available_technicians,
    increment_load,
    decrement_load
)

# ------------------------------
# Setup
# ------------------------------
app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

create_tables()  # IMPORTANT: create DB tables on server start

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_FILE = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_FILE = os.path.join(BASE_DIR, "vectorizer.pkl")

model, vectorizer = None, None
try:
    if os.path.exists(MODEL_FILE) and os.path.exists(VECTORIZER_FILE):
        model = pickle.load(open(MODEL_FILE, "rb"))
        vectorizer = pickle.load(open(VECTORIZER_FILE, "rb"))
        print("ML Model Loaded")
    else:
        print("No ML model found — using fallback rules.")
except Exception as e:
    print("Model Load Error:", e)
    
def auto_seed_if_empty():
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    # Check if students table exists & has data
    cur.execute("""
    SELECT name FROM sqlite_master WHERE type='table' AND name='students'
    """)
    table_exists = cur.fetchone()

    if not table_exists:
        print("Creating tables because database is empty...")
        from database import create_tables
        create_tables()

    # Check if students already inserted
    cur.execute("SELECT COUNT(*) FROM students")
    count = cur.fetchone()[0]

    if count == 0:
        print("Seeding DB... (first run only)")
        # Import and run seeds
        try:
            from seed_data import seed_database
            seed_database()
            print("Seed successful!")
        except Exception as e:
            print("Seeding failed:", e)

    conn.close()

# Run auto-seed once during server start
auto_seed_if_empty()
# ---------------------------------------------------


# ------------------------------
# Clean query
# ------------------------------
def clean_query_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()

    corrections = {
        "wokring": "working", "wrkng": "working",
        "plz": "please", "pls": "please",
        "ac": "air conditioner",
        "leek": "leak", "lakage": "leakage",
        "hstl": "hostel"
    }
    for w, r in corrections.items():
        text = text.replace(w, r)

    return " ".join(text.split())


# ------------------------------
# Duplicate check (SQL)
# ------------------------------
def sql_duplicate_check(query):
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
# Keyword role detection
# ------------------------------
maintenance_keywords = {
    "electrician": ["fan", "light", "switch", "socket", "ac", "air conditioner"],
    "plumber": ["leak", "water", "tap", "pipe", "flush"],
    "carpenter": ["door", "bed", "window", "table"],
}


def keyword_boost(query):
    for role, words in maintenance_keywords.items():
        for w in words:
            if w in query:
                return "Hostel", role
    return None, None


# ------------------------------
# Extract time
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

        try:
            s = int(start)
            e = int(end)
        except:
            continue

        if student_time is None:
            if load < lowest_load:
                best = (name, s, e)
                lowest_load = load
        else:
            if s <= student_time <= e and load < lowest_load:
                best = (name, s, e)
                lowest_load = load

    if best:
        return best[0], best[1], best[2], student_time, "matched"

    # Fallback lowest-load free tech
    name, role, start, end, load, status = techs[0]
    return name, int(start), int(end), int(start), "no_time_match"


# ------------------------------
# Submit request
# ------------------------------
@app.route("/submit_request", methods=["POST"])
def submit_request():
    data = request.json or {}

    student_id = data.get("student_id", "")
    query_raw = data.get("query", "")
    query_clean = clean_query_text(query_raw)

    is_dup, dup_id = sql_duplicate_check(query_clean)
    student_time = extract_time(query_clean)

    # Category/Role Detection
    cat_boost, role_boost = keyword_boost(query_clean)

    if role_boost:
        category = cat_boost
        role = role_boost
    else:
        # ML fallback
        if model and vectorizer:
            try:
                q_vec = vectorizer.transform([query_clean])
                category = model.predict(q_vec)[0]
            except:
                category = "Hostel"
        else:
            category = "Hostel"

        # basic fallback
        role = None

    # Assign technician
    if role:
        tech, s, e, assigned_time, status = assign_technician(role, student_time)
    else:
        tech, s, e, assigned_time, status = (None, None, None, None, "no_technician")

    if tech:
        increment_load(tech)

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
# Get status
# ------------------------------
@app.route("/get_status")
def get_status():
    req_id = request.args.get("id")

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
# Student history
# ------------------------------
@app.route("/api/history/<student_id>")
def history(student_id):
    rows = get_requests_by_student(student_id)
    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]
    return jsonify([dict(zip(keys, r)) for r in rows])


# ------------------------------
# Admin update
# ------------------------------
@app.route("/admin/update_status", methods=["POST"])
def admin_update():
    data = request.json or {}
    req_id = data["request_id"]
    status = data["status"]

    update_request_status(req_id, status)

    if status == "resolved":
        conn = sqlite3.connect("rms.db")
        cur = conn.cursor()
        cur.execute("SELECT technician FROM requests WHERE request_id=?", (req_id,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            decrement_load(row[0])

    return {"message": "updated"}


# ------------------------------
# Admin — get all requests
# ------------------------------
@app.route("/admin/get_all_requests")
def admin_get_all_requests():
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests")
    rows = cur.fetchall()
    conn.close()

    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]

    return jsonify([dict(zip(keys, r)) for r in rows])


# ------------------------------
# Technicians list
# ------------------------------
@app.route("/admin/get_technicians")
def admin_get_technicians():
    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM technicians")
    rows = cur.fetchall()
    conn.close()

    keys = ["name","role","start_time","end_time","current_load","status","password"]

    return jsonify([dict(zip(keys, r)) for r in rows])


# ------------------------------
# Student Login
# ------------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    student_id = data.get("student_id", "")
    password = data.get("password", "")

    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM students WHERE student_id=? AND password=?", (student_id, password))
    row = cur.fetchone()
    conn.close()

    if row:
        return {"status": "success", "name": row[0]}
    else:
        return {"status": "error", "message": "Invalid credentials"}


# ------------------------------
# Technician Login
# ------------------------------
@app.route("/technician/login", methods=["POST"])
def technician_login():
    data = request.json or {}
    name = data.get("name", "")
    password = data.get("password", "")

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
@app.route("/technician/get_tasks")
def technician_get_tasks():
    name = request.args.get("name", "")

    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE technician=?", (name,))
    rows = cur.fetchall()
    conn.close()

    keys = ["request_id","student_id","query","category","technician",
            "start_time","end_time","assigned_time","student_free_time","status"]

    return jsonify([dict(zip(keys, r)) for r in rows])


# ------------------------------
# Serve frontend
# ------------------------------
@app.route("/")
def home():
    return send_from_directory("frontend", "homepage.html")

@app.route("/<path:filename>")
def serve_frontend(filename):
    return send_from_directory("frontend", filename)

# ------------------------------
# Start server
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
