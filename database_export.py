import sqlite3

conn = sqlite3.connect("rms.db")
cursor = conn.cursor()

with open("database.sql", "w") as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()
print("database.sql exported successfully!")

