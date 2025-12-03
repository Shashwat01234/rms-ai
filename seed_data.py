# seed_data.py – Insert initial users & technicians safely
import sqlite3
from database import create_tables

def seed_database():
    print("Seeding database...")

    # Ensure tables exist
    create_tables()

    conn = sqlite3.connect("rms.db")
    cur = conn.cursor()

    # ------------------------------
    # Students
    # ------------------------------
    students = [
        ("101", "Shashwat Dubey", "1234"),
        ("102", "Ravi Kumar", "1234"),
        ("103", "Aman Singh", "1234"),
        
    ]

    cur.executemany("""
        INSERT OR IGNORE INTO students (student_id, name, password)
        VALUES (?, ?, ?)
    """, students)

    # ------------------------------
    # Technicians
    # ------------------------------
    technicians = [
        ("Ramesh", "electrician", "9", "18", 0, "free", "1234"),
        ("Suresh", "plumber", "10", "19", 0, "free", "1234"),
        ("Mahesh", "carpenter", "9", "17", 0, "free", "1234")
    ]

    cur.executemany("""
        INSERT OR IGNORE INTO technicians 
        (name, role, start_time, end_time, current_load, status, password)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, technicians)

    conn.commit()
    conn.close()

    print("Seeding completed.")

# Allow running this file manually
if __name__ == "__main__":
    seed_database()
