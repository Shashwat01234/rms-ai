# seed_data.py – Insert initial users & technicians into rms.db

import sqlite3

conn = sqlite3.connect("rms.db")
cur = conn.cursor()

print("Seeding database...")

# ----------------------------------
# Students
# ----------------------------------
students = [
    ("101", "Shashwat Dubey", "1234"),
    ("102", "Ravi Kumar", "1234"),
    ("103", "Aman Singh", "1234")
]

cur.executemany("INSERT OR IGNORE INTO students VALUES (?, ?, ?)", students)


# ----------------------------------
# Technicians
# ----------------------------------
technicians = [
    ("Ramesh", "electrician", "9", "18", 0, "free", "1234"),
    ("Suresh", "plumber", "10", "19", 0, "free", "1234"),
    ("Mahesh", "carpenter", "9", "17", 0, "free", "1234")
]

cur.executemany("INSERT OR IGNORE INTO technicians VALUES (?, ?, ?, ?, ?, ?, ?)", technicians)


conn.commit()
conn.close()

print("Database seeded successfully!")
