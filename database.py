# database.py – SQLite backend for RMS AI

import sqlite3

DB_NAME = "rms.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Students
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT,
        password TEXT
    );
    """)

    # Technicians
    cur.execute("""
    CREATE TABLE IF NOT EXISTS technicians (
        name TEXT PRIMARY KEY,
        role TEXT,
        start_time TEXT,
        end_time TEXT,
        current_load INTEGER DEFAULT 0,
        status TEXT DEFAULT 'free',
        password TEXT
    );
    """)

    # Requests
    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id TEXT PRIMARY KEY,
        student_id TEXT,
        query TEXT,
        category TEXT,
        technician TEXT,
        start_time TEXT,
        end_time TEXT,
        assigned_time TEXT,
        student_free_time TEXT,
        status TEXT
    );
    """)

    conn.commit()
    conn.close()


# -----------------------------
# INSERT request
# -----------------------------
def insert_request(data):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["request_id"],
        data["student_id"],
        data["query"],
        data["category"],
        data["technician"],
        data["start_time"],
        data["end_time"],
        data["assigned_time"],
        data["student_free_time"],
        data["status"]
    ))

    conn.commit()
    conn.close()


# -----------------------------
# GET request history
# -----------------------------
def get_requests_by_student(student_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM requests WHERE student_id=?", (student_id,))
    rows = cur.fetchall()

    conn.close()
    return rows


# -----------------------------
# UPDATE request status
# -----------------------------
def update_request_status(request_id, new_status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE requests SET status=? WHERE request_id=?", (new_status, request_id))
    conn.commit()
    conn.close()


# -----------------------------
# GET technicians by role
# -----------------------------
def get_available_technicians(role):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT name, role, start_time, end_time, current_load, status
    FROM technicians
    WHERE role=?
    ORDER BY current_load ASC
    """, (role,))

    rows = cur.fetchall()
    conn.close()
    return rows


# -----------------------------
# Technician load operations
# -----------------------------
def increment_load(name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE technicians
    SET current_load = current_load + 1,
        status = 'busy'
    WHERE name=?
    """, (name,))

    conn.commit()
    conn.close()


def decrement_load(name):
    conn = get_connection()
    cur = conn.cursor()

    # Load cannot be negative
    cur.execute("""
    UPDATE technicians
    SET current_load = MAX(current_load - 1, 0),
        status = CASE WHEN current_load - 1 <= 0 THEN 'free' ELSE 'busy' END
    WHERE name=?
    """, (name,))

    conn.commit()
    conn.close()
