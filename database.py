# database.py — Dual SQLite/PostgreSQL backend for RMS AI
# Automatically uses SQLite locally and PostgreSQL on Render (via DATABASE_URL env var)

import os
import re
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_POSTGRES = DATABASE_URL.startswith("postgres")


# ──────────────────────────────────────────────
#  Connection
# ──────────────────────────────────────────────
def get_connection():
    if IS_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    conn = sqlite3.connect("rms.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _q(sql):
    """Convert SQLite ? placeholders → %s for PostgreSQL."""
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql


def execute(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(_q(sql), params)
        if commit:
            conn.commit()
        if fetchone:
            row = cur.fetchone()
            if row is None:
                return None
            if IS_POSTGRES:
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
            return dict(row)
        if fetchall:
            rows = cur.fetchall()
            if IS_POSTGRES:
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
            return [dict(r) for r in rows]
        return None
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Schema + Seed
# ──────────────────────────────────────────────
def init_db():
    """Create tables if not exist, then seed demo data."""
    conn = get_connection()
    cur = conn.cursor()

    ts_type = "TIMESTAMP" if IS_POSTGRES else "DATETIME"

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        password   TEXT NOT NULL
    )""")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS technicians (
        name         TEXT PRIMARY KEY,
        role         TEXT NOT NULL,
        start_time   TEXT,
        end_time     TEXT,
        current_load INTEGER DEFAULT 0,
        status       TEXT DEFAULT 'free',
        password     TEXT NOT NULL
    )""")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS requests (
        request_id        TEXT PRIMARY KEY,
        student_id        TEXT,
        query             TEXT,
        category          TEXT,
        technician        TEXT,
        start_time        TEXT,
        end_time          TEXT,
        assigned_time     TEXT,
        student_free_time TEXT,
        status            TEXT DEFAULT 'pending',
        ai_response       TEXT DEFAULT '',
        created_at        {ts_type} DEFAULT CURRENT_TIMESTAMP
    )""")

    try:
        cur.execute("ALTER TABLE requests ADD COLUMN ai_response TEXT DEFAULT ''")
    except Exception:
        pass

    # ── NEW: Academic queries
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS academic_queries (
        query_id       TEXT PRIMARY KEY,
        student_id     TEXT,
        question       TEXT,
        category       TEXT,
        ai_response    TEXT,
        department_ref TEXT,
        ai_powered     INTEGER DEFAULT 1,
        admin_note     TEXT DEFAULT '',
        status         TEXT DEFAULT 'ai_answered',
        created_at     {ts_type} DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── NEW: Certificate verifications
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS certificate_verifications (
        verify_id        TEXT PRIMARY KEY,
        student_id       TEXT,
        filename         TEXT,
        cert_name        TEXT,
        cert_institution TEXT,
        cert_degree      TEXT,
        cert_date        TEXT,
        cert_number      TEXT,
        verdict          TEXT,
        confidence       INTEGER DEFAULT 0,
        pass_rate        INTEGER DEFAULT 0,
        flags            TEXT DEFAULT '[]',
        ai_summary       TEXT,
        admin_override   TEXT DEFAULT '',
        status           TEXT DEFAULT 'pending_review',
        created_at       {ts_type} DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ── Seed students
    cur.execute("SELECT COUNT(*) FROM students")
    if cur.fetchone()[0] == 0:
        seeds = [
            ("12345",    "Rahul Sharma",  "pass123"),
            ("12411793", "Ananya Verma",  "pass234"),
            ("12419010", "Aman Gupta",    "pass345"),
        ]
        for s in seeds:
            if IS_POSTGRES:
                cur.execute(
                    "INSERT INTO students VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", s)
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO students VALUES (?,?,?)", s)

    # ── Seed technicians
    cur.execute("SELECT COUNT(*) FROM technicians")
    if cur.fetchone()[0] == 0:
        seeds = [
            # Core roles
            ("Ravi",     "electrician",  "8:00",  "18:00", 0, "free", "tech123"),
            ("Vikram",   "electrician",  "12:00", "21:00", 0, "free", "tech123"),
            ("Suresh",   "plumber",      "9:00",  "17:00", 0, "free", "tech123"),
            ("Deepak",   "plumber",      "13:00", "21:00", 0, "free", "tech123"),
            ("Aman",     "carpenter",    "8:00",  "16:00", 0, "free", "tech123"),
            ("Neha",     "painter",      "10:00", "18:00", 0, "free", "tech123"),
            # Extended roles
            ("Priya",    "housekeeping", "6:00",  "14:00", 0, "free", "tech123"),
            ("Sunita",   "housekeeping", "14:00", "22:00", 0, "free", "tech123"),
            ("Karan",    "it_support",   "9:00",  "18:00", 0, "free", "tech123"),
            ("Rohit",    "security",     "0:00",  "12:00", 0, "free", "tech123"),
            ("Manoj",    "security",     "12:00", "24:00", 0, "free", "tech123"),
            ("Santosh",  "mess_manager", "6:00",  "15:00", 0, "free", "tech123"),
            ("Lakshmi",  "laundry",      "8:00",  "17:00", 0, "free", "tech123"),
        ]
        for t in seeds:
            if IS_POSTGRES:
                cur.execute(
                    "INSERT INTO technicians VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", t)
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO technicians VALUES (?,?,?,?,?,?,?)", t)
    else:
        # Ensure extended-role technicians exist (upsert-safe)
        extended = [
            ("Vikram",  "electrician",  "12:00", "21:00"),
            ("Deepak",  "plumber",      "13:00", "21:00"),
            ("Priya",   "housekeeping", "6:00",  "14:00"),
            ("Sunita",  "housekeeping", "14:00", "22:00"),
            ("Karan",   "it_support",   "9:00",  "18:00"),
            ("Rohit",   "security",     "0:00",  "12:00"),
            ("Manoj",   "security",     "12:00", "24:00"),
            ("Santosh", "mess_manager", "6:00",  "15:00"),
            ("Lakshmi", "laundry",      "8:00",  "17:00"),
        ]
        for name, role, s, e in extended:
            if IS_POSTGRES:
                cur.execute(
                    "INSERT INTO technicians (name,role,start_time,end_time,current_load,status,password) "
                    "VALUES (%s,%s,%s,%s,0,'free','tech123') ON CONFLICT DO NOTHING",
                    (name, role, s, e))
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO technicians (name,role,start_time,end_time,current_load,status,password) "
                    "VALUES (?,?,?,?,0,'free','tech123')",
                    (name, role, s, e))

    conn.commit()
    conn.close()
    print(f"[OK] DB initialised ({'PostgreSQL' if IS_POSTGRES else 'SQLite'})")


# ──────────────────────────────────────────────
#  Students
# ──────────────────────────────────────────────
def get_student(student_id, password):
    return execute(
        "SELECT * FROM students WHERE student_id=? AND password=?",
        (student_id, password), fetchone=True
    )


# ──────────────────────────────────────────────
#  Technicians
# ──────────────────────────────────────────────
def get_technicians_by_role(role):
    return execute(
        "SELECT * FROM technicians WHERE role=? ORDER BY current_load ASC",
        (role,), fetchall=True
    )


def get_all_technicians():
    return execute(
        "SELECT name, role, start_time, end_time, current_load, status FROM technicians",
        fetchall=True
    )


def get_technician_by_credentials(name, password):
    return execute(
        "SELECT * FROM technicians WHERE name=? AND password=?",
        (name, password), fetchone=True
    )


def increment_load(name: str):
    """Increment load. Mark busy only when load exceeds 3 concurrent tasks."""
    execute("""
        UPDATE technicians
        SET current_load = current_load + 1,
            status = CASE WHEN current_load + 1 >= 3 THEN 'busy' ELSE 'free' END
        WHERE name=?
    """, (name,), commit=True)


def decrement_load(name: str):
    """Decrement load. Reset to free when no tasks remain."""
    if IS_POSTGRES:
        execute("""
            UPDATE technicians
            SET current_load = GREATEST(current_load - 1, 0),
                status = CASE WHEN GREATEST(current_load - 1, 0) < 3 THEN 'free' ELSE 'busy' END
            WHERE name=?
        """, (name,), commit=True)
    else:
        execute("""
            UPDATE technicians
            SET current_load = MAX(current_load - 1, 0),
                status = CASE WHEN MAX(current_load - 1, 0) < 3 THEN 'free' ELSE 'busy' END
            WHERE name=?
        """, (name,), commit=True)


def reset_technician_loads():
    """Admin tool: reset all technicians to free/0 load (use when data is stale)."""
    execute(
        "UPDATE technicians SET current_load=0, status='free'",
        commit=True
    )


def get_technicians_by_role(role: str):
    """Returns ALL technicians for a role ordered by current load (lowest first)."""
    return execute(
        "SELECT * FROM technicians WHERE role=? ORDER BY current_load ASC, status ASC",
        (role,), fetchall=True
    )


def get_all_technicians():
    return execute(
        "SELECT name, role, start_time, end_time, current_load, status FROM technicians",
        fetchall=True
    )


# ──────────────────────────────────────────────
#  Requests
# ──────────────────────────────────────────────
def insert_request(request_id, student_id, query, category, technician,
                   start_time, end_time, assigned_time, student_free_time, status, ai_response=""):
    execute("""
        INSERT INTO requests
        (request_id, student_id, query, category, technician,
         start_time, end_time, assigned_time, student_free_time, status, ai_response)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (request_id, student_id, query, category, technician,
          start_time, end_time, assigned_time, student_free_time, status, ai_response),
          commit=True)


def get_request_by_id(request_id):
    return execute(
        "SELECT * FROM requests WHERE request_id=?",
        (request_id,), fetchone=True
    )


def get_requests_by_student(student_id):
    return execute(
        "SELECT * FROM requests WHERE student_id=? ORDER BY created_at DESC",
        (student_id,), fetchall=True
    )


def get_requests_by_technician(tech_name):
    return execute(
        "SELECT * FROM requests WHERE technician=? ORDER BY created_at DESC",
        (tech_name,), fetchall=True
    )


def get_all_requests():
    return execute(
        "SELECT * FROM requests ORDER BY created_at DESC",
        fetchall=True
    )


def get_recent_requests(limit=20):
    return execute(
        f"SELECT * FROM requests ORDER BY created_at DESC LIMIT {int(limit)}",
        fetchall=True
    )


def update_request_status(request_id, new_status):
    execute(
        "UPDATE requests SET status=? WHERE request_id=?",
        (new_status, request_id), commit=True
    )


def get_analytics():
    rows = execute(
        "SELECT category, COUNT(*) as cnt FROM requests GROUP BY category",
        fetchall=True
    )
    return {r["category"]: r["cnt"] for r in rows} if rows else {}


def get_status_counts():
    rows = execute(
        "SELECT status, COUNT(*) as cnt FROM requests GROUP BY status",
        fetchall=True
    )
    result = {"pending": 0, "resolved": 0, "assigned": 0, "in_progress": 0, "no_technician": 0}
    for r in (rows or []):
        result[r["status"]] = r["cnt"]
    return result


# ──────────────────────────────────────────────
#  Academic Queries
# ──────────────────────────────────────────────
def insert_academic_query(query_id, student_id, question, category,
                          ai_response, department_ref, ai_powered):
    execute("""
        INSERT INTO academic_queries
        (query_id, student_id, question, category, ai_response, department_ref, ai_powered)
        VALUES (?,?,?,?,?,?,?)
    """, (query_id, student_id, question, category, ai_response, department_ref, int(ai_powered)),
         commit=True)


def get_academic_queries_by_student(student_id):
    return execute(
        "SELECT * FROM academic_queries WHERE student_id=? ORDER BY created_at DESC",
        (student_id,), fetchall=True
    )


def get_all_academic_queries():
    return execute(
        "SELECT * FROM academic_queries ORDER BY created_at DESC",
        fetchall=True
    )


def update_academic_note(query_id, note, status="reviewed"):
    execute(
        "UPDATE academic_queries SET admin_note=?, status=? WHERE query_id=?",
        (note, status, query_id), commit=True
    )


def get_academic_stats():
    total = execute("SELECT COUNT(*) as cnt FROM academic_queries", fetchone=True)
    by_cat = execute(
        "SELECT category, COUNT(*) as cnt FROM academic_queries GROUP BY category",
        fetchall=True
    )
    return {
        "total": total["cnt"] if total else 0,
        "by_category": {r["category"]: r["cnt"] for r in (by_cat or [])},
    }


# ──────────────────────────────────────────────
#  Certificate Verifications
# ──────────────────────────────────────────────
def insert_certificate_verification(verify_id, student_id, filename,
                                    cert_name, cert_institution, cert_degree,
                                    cert_date, cert_number, verdict,
                                    confidence, pass_rate, flags, ai_summary):
    import json
    flags_str = json.dumps(flags) if isinstance(flags, list) else str(flags)
    execute("""
        INSERT INTO certificate_verifications
        (verify_id, student_id, filename, cert_name, cert_institution,
         cert_degree, cert_date, cert_number, verdict, confidence,
         pass_rate, flags, ai_summary)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (verify_id, student_id, filename, cert_name, cert_institution,
          cert_degree, cert_date, cert_number, verdict, confidence,
          pass_rate, flags_str, ai_summary),
         commit=True)


def get_certificate_verifications_by_student(student_id):
    return execute(
        "SELECT * FROM certificate_verifications WHERE student_id=? ORDER BY created_at DESC",
        (student_id,), fetchall=True
    )


def get_all_certificate_verifications():
    return execute(
        "SELECT * FROM certificate_verifications ORDER BY created_at DESC",
        fetchall=True
    )


def override_certificate_verdict(verify_id, override_verdict, admin_note=""):
    execute(
        "UPDATE certificate_verifications SET admin_override=?, status=? WHERE verify_id=?",
        (f"{override_verdict}|{admin_note}", "admin_reviewed", verify_id),
        commit=True
    )


if __name__ == "__main__":
    init_db()

