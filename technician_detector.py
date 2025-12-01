import pandas as pd

def detect_technician(query):
    df = pd.read_csv("maintenance.csv")
    query = query.lower()

    # Smart keyword matching
    for _, row in df.iterrows():
        issue_words = row["issue"].split()
        match_count = 0

        for word in issue_words:
            if word in query:
                match_count += 1

        if match_count >= 1:
            return row["technician"]

    return "unknown"
