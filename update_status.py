import pandas as pd

def update_request_status(request_id):
    # Load request database
    df = pd.read_csv("requests.csv")

    if request_id not in df["id"].values:
        print("❌ Invalid Request ID")
        return

    # Update status in requests.csv
    df.loc[df["id"] == request_id, "status"] = "completed"
    df.to_csv("requests.csv", index=False)
    print("✅ Request marked as completed.")

    # Get technician assigned to this request
    technician = df.loc[df["id"] == request_id, "technician"].values[0]

    # Update technician availability
    update_technician_status(technician)


def update_technician_status(technician_name):
    df = pd.read_csv("technicians.csv")

    # Set technician status to free
    df.loc[df["name"] == technician_name, "status"] = "free"

    df.to_csv("technicians.csv", index=False)
    print(f"🔧 Technician '{technician_name}' is now free.")


def main():
    print("===== UPDATE REQUEST STATUS =====")
    request_id = input("Enter Request ID: ")
    update_request_status(request_id)


if __name__ == "__main__":
    main()
