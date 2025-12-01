from database import create_tables, get_connection

create_tables()
print("Tables created.")

conn = get_connection()
cur = conn.cursor()

sample_students = [
    ("1001", "Shashwat", "123"),
    ("1002", "Rohan", "123")
]

sample_techs = [
    ("Ravi", "electrician", "9", "18", 0, "free", "123"),
    ("Suresh", "plumber", "10", "17", 0, "free", "123"),
    ("Amit", "carpenter", "11", "19", 0, "free", "123")
]

cur.executemany("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", sample_students)
cur.executemany("INSERT OR REPLACE INTO technicians VALUES (?, ?, ?, ?, ?, ?, ?)", sample_techs)

conn.commit()
conn.close()

print("Sample data inserted.")
