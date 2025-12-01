import pandas as pd

REQUESTS_FILE = "requests.csv"
TECHNICIANS_FILE = "technicians.csv"

# ----------------------------------------------------------
# Decrease technician load when request is completed
# ----------------------------------------------------------
def decrement_technician_load(technician_name):
    try:
        tech_df = pd.read_csv(TECHNICIANS_FILE)

        if technician_name in tech_df["name"].values:
            current = int(
                tech_df.loc[tech_df["name"] == technician_name, "current_load"]
                .fillna(0)
                .values[0]
            )

            new_load = max(current - 1, 0)
            tech_df.loc[tech_df["name"] == technician_name, "current_load"] = new_load

            # If technician becomes free
            if new_load == 0:
                tech_df.loc[tech_df["name"] == technician_name, "status"] = "free"

            tech_df.to_csv(TECHNICIANS_FILE, index=False)
            print(f"Updated technician load → {technician_name} now has {new_load} active jobs.")

    except Exception as e:
        print("Error updating technician load:", e)


# ----------------------------------------------------------
# Update request status: pending → working → completed
# ----------------------------------------------------------
def update_request_status():
    try:
        df = pd.read_csv(REQUESTS_FILE)
        print("\n======= CURRENT REQUESTS =======\n")

        if df.empty:
            print("No requests found.")
            return

        # Display last 15 requests
        print(df.tail(15).to_string(index=False))

        request_id = input("\nEnter Request ID to update: ").strip()

        if request_id not in df["request_id"].values:
            print("❌ Invalid Request ID.")
            return

        print("\nChoose new status:")
        print("1. pending")
        print("2. working")
        print("3. completed")

        choice = input("Enter choice (1/2/3): ").strip()

        new_status = {
            "1": "pending",
            "2": "working",
            "3": "completed"
        }.get(choice)

        if not new_status:
            print("Invalid choice.")
            return

        # Get technician name
        tech_name = df.loc[df["request_id"] == request_id, "technician"].values[0]

        # Update status
        df.loc[df["request_id"] == request_id, "status"] = new_status
        df.to_csv(REQUESTS_FILE, index=False)

        print(f"\n✔ Request {request_id} updated to '{new_status}'.")

        # If completed → decrement workload
        if new_status == "completed" and tech_name != "unknown":
            decrement_technician_load(tech_name)

        print("\nUpdate finished.\n")

    except Exception as e:
        print("Error:", e)


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
if __name__ == "__main__":
    while True:
        print("\n========= ADMIN UPDATE MENU =========")
        print("1. Update a request status")
        print("2. Exit")

        option = input("Enter option: ")

        if option == "1":
            update_request_status()
        elif option == "2":
            print("Exiting update panel.")
            break
        else:
            print("Invalid choice. Try again.")
