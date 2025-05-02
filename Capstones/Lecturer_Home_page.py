import tkinter as tk
from Navigation_Bar import create_navbar
from database_conn import connect_db
from UserData import get_user_details
import sys
import tkinter.messagebox as messagebox


def show_lecturer_home_page():
    # Get user data
    user_data = get_user_details()
    if not user_data:
        print("No user data found. Please log in!")
        return
        
    root = tk.Tk()
    root.title("Lecturer Home Page")
    root.state("zoomed")

    # Set window close protocol to use confirmation dialog
    def on_closing():
        if messagebox.askyesno("Log Out", "Are you sure you want to log out and close the application?"):
            root.destroy()
            sys.exit(0)  # Close the application completely
    
    root.protocol("WM_DELETE_WINDOW", on_closing)

    conn = connect_db()
    if conn:
        print("Database connected successfully")
        conn.close()  # Close the connection after use

    # Pass the lecturer ID to create_navbar
    create_navbar(root, user_data['LecturerID'])

    content_frame = tk.Frame(root)
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    welcome_text = f"Welcome {user_data['Name']} to the Lecturer Page"
    welcome_label = tk.Label(content_frame, text=welcome_text, font=("Arial", 20, "bold"))
    welcome_label.pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    show_lecturer_home_page()