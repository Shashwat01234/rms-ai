import pandas as pd
import os

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_requests():
    clear()
    print("===== ALL REQUESTS =====\n")
    df = pd.read_csv("requests.csv")
    print(df.to_string(index=False))
    input("\nPress Enter to return to menu...")

def show_pending_requests():
    clear()
    print("===== PENDING REQUESTS =====\n")
    df = pd.read_csv("requests.csv")
    pending = df[df["status"] == "pending"]
    print(pending.to_string(index=False))
    input("\nPress Enter to return to menu...")

def show_completed_requests():
    clear()
    print("===== COMPLETED REQUESTS =====\n")
    df = pd.read_csv("requests.csv")
    completed = df[df["status"] == "completed"]
    print(completed.to_string(index=False))
    input("\nPress Enter to return to menu...")

def show_technicians():
    clear()
    print("===== TECHNICIAN LIST =====\n")
    df = pd.read_csv("technicians.csv")
    print(df.to_string(index=False))
    input("\nPress Enter to return to menu...")

def main_menu():
    while True:
        clear()
        print("=========== ADMIN DASHBOARD ===========")
        print("1. View All Requests")
        print("2. View Pending Requests")
        print("3. View Completed Requests")
        print("4. View Technicians")
        print("5. Exit")
        print("=======================================\n")

        choice = input("Enter choice: ")

        if choice == "1":
            show_requests()
        elif choice == "2":
            show_pending_requests()
        elif choice == "3":
            show_completed_requests()
        elif choice == "4":
            show_technicians()
        elif choice == "5":
            print("Exiting dashboard...")
            break
        else:
            input("Invalid choice! Press Enter to continue...")

if __name__ == "__main__":
    main_menu()
