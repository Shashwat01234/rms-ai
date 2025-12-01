# server.py - Final cleaned backend (matches 10-column requests.csv)
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import pickle
import re
import csv
import uuid
import os

# -----------------------------
# Basic setup & debug paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print("SERVER DIRECTORY:", BASE_DIR)

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

# -----------------------------
# Files / constants
# -----------------------------
MODEL_FILE = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_FILE = os.path.join(BASE_DIR, "vectorizer.pkl")
TECH_CSV = os.path.join(BASE_DIR, "technicians.csv")
STUDENTS_CSV = os.path.join(BASE_DIR, "students.csv")
MAINTENANCE_CSV = os.path.join(BASE_DIR, "maintenance.csv")
REQUESTS_CSV = os.path.join(BASE_DIR, "requests.csv")

# Actual CSV header you specified (10 columns)
REQUESTS_HEADER = [
    "request_id",
    "student_id",
    "query",
    "category",
    "technician",
    "start_time",
    "end_time",
    "assigned_time",
    "student_free_time",
    "status"
]

print("REQUESTS CSV PATH:", REQUESTS_CSV)

# Ensure requests.csv exists with correct header
def ensure_requests_csv():
    if not os.path.exists(REQUESTS_CSV):
        with open(REQUESTS_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(REQUESTS_HEADER)

ensure_requests_csv()

# -----------------------------
# Safe model load (optional)
# -----------------------------
model = None
vectorizer = None
try:
    if os.path.exists(MODEL_FILE) and os.path.exists(VECTORIZER_FILE):
        model = pickle.load(open(MODEL_FILE, "rb"))
        vectorizer = pickle.load(open(VECTORIZER_FILE, "rb"))
        print("Model and vectorizer loaded.")
    else:
        print("Model/vectorizer not found — running without ML fallback.")
except Exception as e:
    print("Warning loading model/vectorizer:", e)
    model = None
    vectorizer = None

# -----------------------------
# Short canned responses
# -----------------------------
responses = {
    "Academic": "Your question has been forwarded to the Academic Department.",
    "Hostel": "Your issue has been sent to the Hostel Administration.",
    "Finance": "Finance department has been notified.",
    "Library": "Library department will handle your request.",
    "IT": "IT Support has been informed about your issue."
}

# -----------------------------
# Text cleaning & slang corrections
# -----------------------------
def clean_query_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    corrections = {
        "wokring": "working", "workin": "working", "wrkng": "working",
        "not wrking": "not working", "nt working": "not working",
        "plz": "please", "pls": "please",
        "ac": "air conditioner", "a.c": "air conditioner",
        "eletrician": "electrician", "electrican": "electrician",
        "leek": "leak", "lakage": "leakage", "watet": "water",
        "bathrom": "bathroom", "hstl": "hostel", "clg": "college",
        "wokr": "work", "woking": "working",
        "urgnt": "urgent"
    }
    for wrong, right in corrections.items():
        text = text.replace(wrong, right)
    return " ".join(text.split())

# -----------------------------
# Duplicate request checker (simple)
# -----------------------------
def check_duplicate_request(query):
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        recent = df.tail(20)
        for _, row in recent.iterrows():
            old = str(row.get("query", "")).lower()
            if not old:
                continue
            words_old = set(old.split())
            words_new = set(query.split())
            match_ratio = len(words_old & words_new) / max(len(words_old), 1)
            if match_ratio > 0.6:
                return True, row["request_id"]
    except Exception:
        pass
    return False, None

# -----------------------------
# Keyword mapping for maintenance
# -----------------------------
maintenance_keywords = {
    "electrician": ["fan", "light", "switch", "socket", "ac", "air conditioner", "charger", "plug"],
    "plumber": ["leak", "water", "tap", "flush", "pipe", "drain", "burst"],
    "carpenter": ["door", "bed", "cupboard", "window", "table", "hinge"],
    "painter": ["paint", "wall", "colour", "color", "peel"]
}

def keyword_boost(query):
    q = query.lower()
    for role, words in maintenance_keywords.items():
        for w in words:
            if w in q:
                return "Hostel", role
    return None, None

# -----------------------------
# Technicians utilities
# -----------------------------
def load_technicians():
    if not os.path.exists(TECH_CSV):
        # create sample header if missing
        with open(TECH_CSV, "w", newline="") as f:
            csv.writer(f).writerow(["name","role","start_time","end_time","current_load","status","password"])
    try:
        df = pd.read_csv(TECH_CSV, dtype=str).fillna("")
        if "current_load" not in df.columns:
            df["current_load"] = 0
        # ensure numeric int
        df["current_load"] = df["current_load"].apply(lambda x: int(float(x)) if str(x).strip() != "" else 0)
        return df
    except Exception:
        return pd.DataFrame(columns=["name","role","start_time","end_time","current_load","status","password"])

def save_technicians_df(df):
    df.to_csv(TECH_CSV, index=False)

def increment_technician_load(name):
    if not name:
        return
    try:
        df = load_technicians()
        if name in df["name"].values:
            df.loc[df["name"] == name, "current_load"] = df.loc[df["name"] == name, "current_load"].astype(int) + 1
            df.loc[df["name"] == name, "status"] = "busy"
            save_technicians_df(df)
    except Exception as e:
        print("increment_technician_load error:", e)

def decrement_technician_load(name):
    if not name:
        return
    try:
        df = load_technicians()
        if name in df["name"].values:
            cur = int(df.loc[df["name"] == name, "current_load"].fillna(0).values[0] or 0)
            new = max(cur - 1, 0)
            df.loc[df["name"] == name, "current_load"] = new
            if new == 0:
                df.loc[df["name"] == name, "status"] = "free"
            save_technicians_df(df)
    except Exception as e:
        print("decrement_technician_load error:", e)

def time_to_int(t):
    if t is None or str(t).strip() == "":
        return None
    s = str(t).strip()
    m = re.search(r'(\d{1,2})', s)
    if m:
        return int(m.group(1))
    return None

# -----------------------------
# Maintenance CSV fallback
# -----------------------------
def detect_technician(query):
    try:
        if not os.path.exists(MAINTENANCE_CSV):
            return "unknown"
        df = pd.read_csv(MAINTENANCE_CSV, dtype=str).fillna("")
        q = query.lower()
        for _, row in df.iterrows():
            issues = str(row.get("issue", "")).lower().split()
            for w in issues:
                if w in q:
                    return row.get("technician", "unknown")
    except Exception:
        pass
    return "unknown"

def extract_time(query):
    if not isinstance(query, str):
        return None
    q = query.lower()
    m = re.search(r'(\d{1,2})\s?(am|pm)', q)
    if m:
        hour = int(m.group(1))
        period = m.group(2)
        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        return hour
    m2 = re.search(r'after (\d{1,2})', q)
    if m2:
        return int(m2.group(1))
    m3 = re.search(r'around (\d{1,2})', q)
    if m3:
        return int(m3.group(1))
    if "morning" in q:
        return 10
    if "afternoon" in q:
        return 14
    if "evening" in q:
        return 18
    if "night" in q:
        return 20
    return None

# -----------------------------
# Auto role from keywords
# -----------------------------
def auto_role_from_words(query):
    q = query.lower()
    electrician_words = ["fan", "light", "switch", "ac", "air conditioner", "tube", "socket"]
    plumber_words = ["leak", "tap", "flush", "water", "pipe", "drain", "washroom"]
    carpenter_words = ["door", "bed", "table", "window", "cupboard", "wood"]
    for w in electrician_words:
        if w in q:
            return "electrician"
    for w in plumber_words:
        if w in q:
            return "plumber"
    for w in carpenter_words:
        if w in q:
            return "carpenter"
    return None

# -----------------------------
# Find available technician
# returns: name, start_time, end_time, assigned_slot, status
# -----------------------------
def find_available_technician(role, student_time=None):
    df = load_technicians()
    filtered = df[df["role"] == role]
    if filtered.empty:
        return None, None, None, None, "no_technician"

    best = None
    lowest = 10**9

    for _, row in filtered.iterrows():
        try:
            name = row["name"]
            status = str(row.get("status", "")).strip().lower()
            start_hour = time_to_int(row.get("start_time", "0"))
            end_hour = time_to_int(row.get("end_time", "23"))
            load = int(row.get("current_load", 0) or 0)
        except Exception:
            continue

        # If student_time not provided -> pick lowest-load free tech
        if student_time is None:
            if status == "free" and load < lowest:
                best = row
                lowest = load
            continue

        # If student's hour fits tech window
        if start_hour is None or end_hour is None:
            continue
        try:
            if start_hour <= int(student_time) <= end_hour and status == "free":
                if load < lowest:
                    best = row
                    lowest = load
        except Exception:
            continue

    if best is not None:
        return best["name"], best.get("start_time", ""), best.get("end_time", ""), (student_time if student_time is not None else best.get("start_time", "")), "matched"

    # fallback: free tech with lowest load
    fallback = filtered[filtered["status"] == "free"].sort_values("current_load").head(1)
    if not fallback.empty:
        row = fallback.iloc[0]
        return row["name"], row.get("start_time", ""), row.get("end_time", ""), row.get("start_time", ""), "no_time_match"

    return None, None, None, None, "no_technician"

# -----------------------------
# log_request() matching your 10-column CSV exactly
# signature: student_id, query, category, technician,
#            start_time, end_time, assigned_time, student_free_time, status
# -----------------------------
def log_request(student_id, query, category, technician,
                start_time, end_time, assigned_time,
                student_free_time, status):
    request_id = str(uuid.uuid4())
    try:
        with open(REQUESTS_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                request_id,
                student_id or "",
                query or "",
                category or "",
                technician or "",
                start_time if start_time is not None else "",
                end_time if end_time is not None else "",
                assigned_time if assigned_time is not None else "",
                student_free_time if student_free_time is not None else "",
                status or "pending"
            ])
    except Exception as e:
        print("ERROR writing to requests.csv:", e)
        raise
    return request_id

# -----------------------------
# Authentication: students
# -----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    student_id = str(data.get("student_id", "")).strip()
    password = str(data.get("password", "")).strip()
    try:
        if not os.path.exists(STUDENTS_CSV):
            return jsonify({"status": "error", "message": "students.csv missing"}), 500
        df = pd.read_csv(STUDENTS_CSV, dtype=str).fillna("")
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        user = df[(df["student_id"] == student_id) & (df["password"] == password)]
        if not user.empty:
            return jsonify({"status": "success", "message": "Login successful", "name": user.iloc[0]["name"]})
        else:
            return jsonify({"status": "error", "message": "Invalid ID or password"})
    except Exception as e:
        return jsonify({"status": "error", "message": "Server error: " + str(e)}), 500

# -----------------------------
# Submit Request (final)
# -----------------------------
@app.route("/submit_request", methods=["POST"])
def submit_request():
    data = request.json or {}

    # 1. Student ID
    student_id = str(data.get("student_id", "")).strip()

    # 2. Clean query
    query_raw = data.get("query", "")
    query_clean = clean_query_text(query_raw)

    # 3. Duplicate check
    is_dup, dup_id = check_duplicate_request(query_clean)

    # 4. Extract student preferred time
    student_time = extract_time(query_clean)

    # 5. Category detection (keyword boost -> ML fallback -> Hostel)
    boost_cat, boost_role = keyword_boost(query_clean)

    if boost_role:
        category = boost_cat
        technician_role = boost_role
    else:
        try:
            if model is not None and vectorizer is not None:
                q_vec = vectorizer.transform([query_clean])
                category = model.predict(q_vec)[0]
            else:
                category = "Hostel"
        except Exception:
            category = "Hostel"
        technician_role = None

    # 6. Detect by maintenance.csv (if any)
    if technician_role is None and category == "Hostel":
        detected = detect_technician(query_clean)
        if detected and detected != "unknown":
            tech_df = load_technicians()
            row = tech_df[tech_df["name"] == detected]
            if not row.empty:
                technician_role = row.iloc[0]["role"]

    # 7. Final fallback: auto role by keywords
    if technician_role is None:
        technician_role = auto_role_from_words(query_clean)

    # 8. Assign technician (always returns 5-items)
    if technician_role:
        tech_name, start_time, end_time, assigned_slot, status = find_available_technician(technician_role, student_time)
    else:
        tech_name, start_time, end_time, assigned_slot, status = (None, None, None, None, "no_technician")

    # 9. Final assigned_time for CSV: prefer student's provided time (option 3 behavior)
    assigned_time = student_time if student_time is not None else (assigned_slot if assigned_slot is not None else "")

    # 10. If tech assigned, increment load
    if tech_name:
        increment_technician_load(tech_name)

    # 11. Write to CSV (matches 10 columns)
    try:
        req_id = log_request(
            student_id,
            query_clean,
            category,
            tech_name,
            start_time,
            end_time,
            assigned_time,
            student_time,
            status
        )
    except Exception as e:
        return jsonify({"error": "Could not save request", "details": str(e)}), 500

    # 12. Return response
    return jsonify({
        "request_id": req_id,
        "category": category,
        "technician": tech_name,
        "start_time": start_time,
        "end_time": end_time,
        "assigned_time": assigned_time,
        "student_free_time": student_time,
        "status": status,
        "is_duplicate": is_dup,
        "duplicate_id": dup_id
    })

# -----------------------------
# Test log route (for debugging)
# -----------------------------
@app.route("/test_log")
def test_log():
    try:
        # This uses the 9-argument signature (excluding request_id — generated inside)
        req_id = log_request("TEST_STUDENT", "fan not working", "Hostel", "Ravi", "10:00", "18:00", 12, 12, "matched")
        return {"message": "Test log written", "request_id": req_id}
    except Exception as e:
        return {"error": str(e)}, 500

# -----------------------------
# Get status
# -----------------------------
@app.route("/get_status", methods=["GET"])
def get_status():
    req_id = request.args.get("id") or request.args.get("request_id")
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        row = df[df["request_id"] == req_id]
        if row.empty:
            return jsonify({"error": "Request not found"}), 404
        row = row.iloc[0]
        return jsonify({
            "request_id": row["request_id"],
            "student_id": row["student_id"],
            "query": row["query"],
            "category": row["category"],
            "technician": row["technician"],
            "start_time": row.get("start_time", ""),
            "end_time": row.get("end_time", ""),
            "assigned_time": row.get("assigned_time", ""),
            "student_free_time": row.get("student_free_time", ""),
            "status": row.get("status", "")
        })
    except Exception as e:
        return jsonify({"error": "Server error: " + str(e)}), 500

# -----------------------------
# Student history
# -----------------------------
@app.route("/api/history/<student_id>", methods=["GET"])
def api_history(student_id):
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        student_records = df[df["student_id"] == str(student_id)]
        return jsonify(student_records.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Admin endpoints
# -----------------------------
@app.route("/admin/get_all_requests", methods=["GET"])
def admin_get_all_requests():
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        return jsonify(df.to_dict(orient="records"))
    except Exception:
        return jsonify([])

@app.route("/admin/update_status", methods=["POST"])
def admin_update_status():
    data = request.json or {}
    req_id = data.get("request_id")
    new_status = data.get("status")
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        if req_id in df["request_id"].values:
            df.loc[df["request_id"] == req_id, "status"] = new_status
            df.to_csv(REQUESTS_CSV, index=False)
            # if resolved, decrement technician load (if tech present)
            tech = df.loc[df["request_id"] == req_id, "technician"].values[0]
            if new_status == "resolved" and tech:
                decrement_technician_load(tech)
            return jsonify({"message": "Status updated"})
        else:
            return jsonify({"error": "Request ID not found"}), 404
    except Exception as e:
        return jsonify({"error": "Server error: " + str(e)}), 500

@app.route("/admin/get_technicians", methods=["GET"])
def admin_get_technicians():
    try:
        df = load_technicians()
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Technician APIs
# -----------------------------
@app.route("/technician/login", methods=["POST"])
def technician_login():
    data = request.json or {}
    name = str(data.get("name", "")).strip()
    password = str(data.get("password", "")).strip()
    try:
        df = load_technicians().fillna("")
        user = df[(df["name"] == name) & (df["password"] == password)]
        if not user.empty:
            return jsonify({"status": "success", "role": user.iloc[0]["role"], "name": name})
        else:
            return jsonify({"status": "error", "message": "Invalid Credentials"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": "Server error: " + str(e)}), 500

@app.route("/technician/get_tasks", methods=["GET"])
def technician_get_tasks():
    tech_name = request.args.get("name")
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        assigned = df[df["technician"] == str(tech_name)]
        return jsonify(assigned.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/technician/update_task", methods=["POST"])
def technician_update_task():
    data = request.json or {}
    req_id = data.get("request_id")
    new_status = data.get("status")
    tech_name = data.get("technician")
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        if req_id in df["request_id"].values:
            df.loc[df["request_id"] == req_id, "status"] = new_status
            df.to_csv(REQUESTS_CSV, index=False)
            if new_status == "resolved" and tech_name:
                decrement_technician_load(tech_name)
            return jsonify({"message": "Task updated"})
        else:
            return jsonify({"error": "Invalid Request ID"}), 404
    except Exception as e:
        return jsonify({"error": "Server error: " + str(e)}), 500

# -----------------------------
# Admin analytics (simple)
# -----------------------------
@app.route("/admin/analytics", methods=["GET"])
def admin_analytics():
    try:
        df = pd.read_csv(REQUESTS_CSV, dtype=str).fillna("")
        counts = df["category"].value_counts().to_dict()
        return jsonify({"by_category": counts})
    except Exception:
        return jsonify({"by_category": {}})

# -----------------------------
# Serve frontend static files
# -----------------------------
@app.route("/")
def root():
    return send_from_directory("frontend", "login.html")

@app.route("/<path:filename>")
def serve_frontend(filename):
    return send_from_directory("frontend", filename)

# -----------------------------
# Run app
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
