import pandas as pd
import pickle
import re
import csv
import uuid

# --------------------------------------------------------------
# Load AI model + vectorizer
# --------------------------------------------------------------
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# --------------------------------------------------------------
# Responses for each category
# --------------------------------------------------------------
responses = {
    "Academic": "Your question has been forwarded to the Academic Department.",
    "Hostel": "Your issue has been sent to the Hostel Administration.",
    "Finance": "Finance department has been notified.",
    "Library": "Library department will handle your request.",
    "IT": "IT Support has been informed about your issue."
}

# --------------------------------------------------------------
# Slang + Spelling Correction (Auto-Rewrite)
# --------------------------------------------------------------
def clean_query_text(text):
    text = text.lower().strip()

    corrections = {
        "wokring": "working",
        "workin": "working",
        "wrkng": "working",
        "not wrking": "not working",
        "nt working": "not working",

        "plz": "please",
        "pls": "please",
        "plss": "please",
        "plsss": "please",
        "pls fix": "please fix",

        "ac": "air conditioner",
        "a.c": "air conditioner",
        "a c": "air conditioner",

        "eletrician": "electrician",
        "electrican": "electrician",
        "elctrician": "electrician",

        "carpentr": "carpenter",
        "plumbr": "plumber",
        "plumer": "plumber",

        "teh": "the",
        "dat": "that",
        "dats": "that is",
        "bcs": "because",
        "becoz": "because",
        "coz": "because",

        "leek": "leak",
        "leeking": "leaking",
        "lakage": "leakage",
        "lekage": "leakage",

        "bathrom": "bathroom",
        "bathrm": "bathroom",
        "bathrrom": "bathroom",

        "urgent": "urgent",
        "urgnt": "urgent",

        "fan nt wrking": "fan not working",
        "fan not wokring": "fan not working",
        "fan no working": "fan not working",
        "fan not wrking": "fan not working",

        "no cooling": "not cooling",
        "ac no cool": "air conditioner not cooling",

        "watet": "water",
        "watr": "water",
        "pipe brst": "pipe burst",
        "brst": "burst",

        "switch brkn": "switch broken",
        "brkn": "broken",

        "washrom": "washroom",
        "hstl": "hostel",
        "clg": "college"
    }

    for wrong, right in corrections.items():
        text = text.replace(wrong, right)

    text = " ".join(text.split())
    return text

# --------------------------------------------------------------
# Duplicate Request Checker
# --------------------------------------------------------------
def check_duplicate_request(query):
    try:
        df = pd.read_csv("requests.csv")

        recent = df.tail(10)

        for _, row in recent.iterrows():
            old_query = str(row["query"]).lower()

            words_old = set(old_query.split())
            words_new = set(query.split())

            match_ratio = len(words_old & words_new) / max(len(words_old), 1)

            if match_ratio > 0.5:
                return True, row["request_id"]

    except Exception:
        pass

    return False, None

# --------------------------------------------------------------
# Keyword boosting for technician types
# --------------------------------------------------------------
maintenance_keywords = {
    "electrician": ["fan", "light", "tube light", "switch", "ac", "air conditioner"],
    "plumber": ["leakage", "water", "tap", "flush", "pipe", "drainage"],
    "carpenter": ["door", "cupboard", "window", "bed", "table"]
}

def keyword_boost(query):
    query = query.lower()

    for word in maintenance_keywords["electrician"]:
        if word in query:
            return "Hostel", "electrician"

    for word in maintenance_keywords["plumber"]:
        if word in query:
            return "Hostel", "plumber"

    for word in maintenance_keywords["carpenter"]:
        if word in query:
            return "Hostel", "carpenter"

    return None, None

# --------------------------------------------------------------
# Technician CSV utilities
# --------------------------------------------------------------
def load_technicians():
    return pd.read_csv("technicians.csv")

def time_to_int(t):
    return int(t.split(":")[0])

# ----------------------
# Workload-balancing helpers
# ----------------------
def save_technicians_df(df):
    """Save technicians dataframe back to CSV (safe overwrite)."""
    df.to_csv("technicians.csv", index=False)

def increment_technician_load(technician_name):
    try:
        df = pd.read_csv("technicians.csv")

        if technician_name in df["name"].values:
            # get current load safely
            current = int(df.loc[df["name"] == technician_name, "current_load"].fillna(0).values[0])
            new_load = current + 1

            # update load
            df.loc[df["name"] == technician_name, "current_load"] = new_load

            # mark busy if load > 0
            df.loc[df["name"] == technician_name, "status"] = "busy"

            df.to_csv("technicians.csv", index=False)

    except Exception as e:
        print("Warning: Could not update technician load:", e)


def decrement_technician_load(technician_name):
    """Decrease current_load by 1 when a request is completed."""
    try:
        df = pd.read_csv("technicians.csv")
        if technician_name in df["name"].values:
            # ensure integer and not negative
            cur = int(df.loc[df["name"] == technician_name, "current_load"].fillna(0).values[0])
            new = max(cur - 1, 0)
            df.loc[df["name"] == technician_name, "current_load"] = new
            # if load becomes 0, set status to free
            if new == 0:
                df.loc[df["name"] == technician_name, "status"] = "free"
            save_technicians_df(df)
    except Exception as e:
        print("Warning: couldn't decrement technician load:", e)


# --------------------------------------------------------------
# Extract student time from natural language
# --------------------------------------------------------------
def extract_time(query):
    query = query.lower()

    match = re.search(r'(\d{1,2})\s?(am|pm)', query)
    if match:
        hour = int(match.group(1))
        period = match.group(2)

        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0

        return hour

    match2 = re.search(r'after (\d{1,2})', query)
    if match2:
        return int(match2.group(1))

    match3 = re.search(r'around (\d{1,2})', query)
    if match3:
        return int(match3.group(1))

    if "morning" in query:
        return 10
    if "afternoon" in query:
        return 14
    if "evening" in query:
        return 18
    if "night" in query:
        return 20

    return None

# --------------------------------------------------------------
# Technician finder with fallback if no exact time match
# --------------------------------------------------------------
def find_available_technician(role, student_time=None):
    df = load_technicians()

    # Ensure current_load column exists
    if "current_load" not in df.columns:
        df["current_load"] = 0

    # Filter by role only
    filtered = df[df["role"] == role]

    # ---------------------------------------------
    # 1) Exact time match + LOWEST current load
    # ---------------------------------------------
    best_match = None
    lowest_load = 9999

    for _, row in filtered.iterrows():
        if row["status"] != "free":
            continue

        tech_start = time_to_int(row["start_time"])
        tech_end = time_to_int(row["end_time"])

        if student_time:
            student_hour = (
                student_time if isinstance(student_time, int)
                else time_to_int(student_time)
            )

            if tech_start <= student_hour <= tech_end:
                # choose tech with LOWEST current_load
                load = int(row["current_load"]) if "current_load" in row else 0
                if load < lowest_load:
                    lowest_load = load
                    best_match = row

    if best_match is not None:
        return (
            best_match["name"],
            best_match["start_time"],
            best_match["end_time"],
            "matched"
        )

    # ---------------------------------------------------
    # 2) No exact time match → suggest free technician
    #    with LOWEST current load (fallback)
    # ---------------------------------------------------
    fallback = None
    lowest_load = 9999

    for _, row in filtered.iterrows():
        if row["status"] == "free":
            load = int(row["current_load"]) if "current_load" in row else 0
            if load < lowest_load:
                lowest_load = load
                fallback = row

    if fallback is not None:
        return (
            fallback["name"],
            fallback["start_time"],
            fallback["end_time"],
            "no_time_match"
        )

    # ---------------------------------------------------
    # 3) No technician available at all
    # ---------------------------------------------------
    return None, None, None, "no_technician"

# --------------------------------------------------------------
# Technician detection (backup)
# --------------------------------------------------------------
def detect_technician(query):
    try:
        df = pd.read_csv("maintenance.csv")
        query = query.lower()

        for _, row in df.iterrows():
            for word in row["issue"].split():
                if word in query:
                    return row["technician"]
    except:
        pass

    return "unknown"

# --------------------------------------------------------------
# Save student request
# --------------------------------------------------------------
def log_request(query, category, technician):
    with open("requests.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([str(uuid.uuid4()), query, category, technician, "pending"])

def print_section(title):
    print("\n" + "─" * 50)
    print(f"{title.upper():^50}")
    print("─" * 50)

def get_technician_load(name):
    try:
        df = pd.read_csv("technicians.csv")
        load = int(df.loc[df["name"] == name, "current_load"].fillna(0).values[0])
        return load
    except:
        return 0


# --------------------------------------------------------------
# MAIN LOOP
# --------------------------------------------------------------
while True:
    query = input("Enter your query (or type 'exit' to quit): ")

    if query.lower() == "exit":
        break

    # Auto-correct slang / spelling
    query = clean_query_text(query)

    # Check duplicates
    is_dup, dup_id = check_duplicate_request(query)
    if is_dup:
        choice = input(
            f"⚠ A similar request (ID: {dup_id}) already exists.\n"
            "Do you want to submit again? (yes/no): "
        )
        if choice.lower() != "yes":
            print("Okay, not submitting.\n")
            continue

    # Extract time
    student_time = extract_time(query)

    if student_time is None:
        follow = input("You didn't mention your time. When are you free? (e.g., 4pm, morning): ")
        student_time = extract_time(follow)

    # ML Prediction + Keyword Boost
    boost_category, boost_tech = keyword_boost(query)
    q_vec = vectorizer.transform([query])

    if boost_category:
        category = boost_category
        technician = boost_tech
    else:
        category = model.predict(q_vec)[0]
        technician = None

    # Technician assignment
    if technician:
        result = find_available_technician(technician, student_time)

    elif category == "Hostel":
        technician = detect_technician(query)
        result = find_available_technician(technician, student_time)

    else:
        result = (None, None, None, "no_technician")

    name, start, end, status = result

    if status == "matched":
        load_value = get_technician_load(name)

        print_section("Technician Assigned")
        print(f"Issue            : {query}")
        print(f"Category         : {category}")
        print(f"Student Time     : {student_time}")
        print(f"Technician       : {name}")
        print(f"Availability     : {start} - {end}")
        print(f"Current Load     : {load_value} active jobs")
        print(f"Status           : Assigned")
        print("─" * 50)

        increment_technician_load(name)


    elif status == "no_time_match":
        load_value = get_technician_load(name)

        print_section("Technician Suggested")
        print("⚠ Technician not available at your requested time.")
        print(f"Suggested Tech   : {name}")
        print(f"Availability     : {start} - {end}")
        print(f"Current Load     : {load_value} active jobs")
        print("─" * 50)

        increment_technician_load(name)


    elif status == "no_technician":
        print_section("No Technician Available")
        print("❌ No technician free right now.")
        print("─" * 50)


    

    # Save to CSV
    log_request(query, category, technician)

    # Category response
    print("\nPredicted Category:", category)
    print("AI Response:", responses.get(category, "I am not sure."))
    print("----------------------------------------------------\n")



