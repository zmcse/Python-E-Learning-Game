import tkinter as tk
from Navigation_Bar import create_navbar
from database_conn import connect_db
from PIL import Image, ImageTk
from UserData import get_user, get_user_details, set_user
import subprocess
import sys
import io
from tkinter import messagebox
import os


def get_background_image(chapter_id="Maps01"):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT Image from Maps where MapsID = ?", (chapter_id,))
        image_data = cursor.fetchone()
        if image_data:
            return image_data[0]
        return None
    except Exception as e:
        print(f"Error retrieving image from database: {e}")
        return None
    finally:
        if conn:
            conn.close()


def show_content_management(lecturer_id=None):
    if lecturer_id:
        set_user(lecturer_id)
    else:
        lecturer_id = get_user()

    user_data = get_user_details()

    root = tk.Tk()
    root.state('zoomed')

    if user_data:
        root.title(f"Content Management - Logged in as {user_data['Name']}")
    else:
        root.title("Content Management - No user logged in!")

    # Add window close protocol
    def on_closing():
        if messagebox.askyesno("Log Out", "Are you sure you want to log out and close the application?"):
            root.destroy()
            sys.exit(0)  # Close the application completely

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Pass the lecturer ID to create_navbar
    current_lecturer_id = lecturer_id if lecturer_id else (user_data['LecturerID'] if user_data else None)
    create_navbar(root, current_lecturer_id)

    background_label = tk.Label(root)
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    background_label.lower()

    def resize_background(chapter_id="Maps01"):
        try:
            width = root.winfo_width()
            height = root.winfo_height()

            if width > 1 and height > 1:
                image_data = get_background_image(chapter_id)
                if image_data:
                    image_stream = io.BytesIO(image_data)
                    bg_image = Image.open(image_stream)
                    bg_image = bg_image.resize((width, height), Image.Resampling.LANCZOS)
                    bg_photo = ImageTk.PhotoImage(bg_image)

                background_label.config(image=bg_photo)
                background_label.image = bg_photo

        except Exception as e:
            print(f"Error loading image: {e}")

    def on_window_resize(event):
        resize_background("Maps01")  # the background default is Maps1

    root.bind("<Configure>", on_window_resize)

    def change_background(chapter_id):
        resize_background(chapter_id)

    def open_chapter(chapter_file):
        lecturer_id = get_user_details().get('LecturerID', '') if get_user_details() else ''

        try:
            # Get the current directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            chapter_path = os.path.join(current_dir, chapter_file)

            print(f"Attempting to open chapter: {chapter_path}")
            print(f"Lecturer ID: {lecturer_id}")

            if not os.path.exists(chapter_path):
                raise FileNotFoundError(f"Chapter file not found at: {chapter_path}")

            # Create the command
            cmd = [sys.executable, chapter_path]
            if lecturer_id:
                cmd.append(str(lecturer_id))

            print(f"Running command: {' '.join(cmd)}")

            # Destroy the current window first
            root.destroy()

            # Then start the new process
            subprocess.run(cmd)

        except Exception as e:
            print(f"Error loading chapter: {e}")
            messagebox.showerror("Error", f"Failed to open chapter: {str(e)}")
            # Don't destroy the window if there was an error
            return

    def show_content_management_buttons():
        chapters = {
            "Chapter 1": "Maps01",
            "Chapter 2": "Maps02",
            "Chapter 3": "Maps03",
            "Chapter 4": "Maps04",
            "Chapter 5": "Maps05"
        }
        chapter_files = ["Chapter1.py", "Chapter2.py", "Chapter3.py", "Chapter4.py", "Chapter5.py"]

        button_positions = [
            (450, 300),  # Chapter 1 (Centered in first row)
            (700, 300),  # Chapter 2
            (950, 300),  # Chapter 3
            (550, 450),  # Chapter 4 (Centered in second row)
            (850, 450),  # Chapter 5
        ]

        for idx, (x, y) in enumerate(button_positions):
            chapter_name = list(chapters.keys())[idx]
            btn = tk.Button(
                root, text=chapter_name, width=15, height=2,
                bg="#333333", fg="white", font=("Arial", 14, "bold"),
                relief="raised", bd=5,
                command=lambda file=chapter_files[idx]: open_chapter(file)
            )
            btn.bind("<Enter>", lambda event, cid=chapters[chapter_name]: change_background(cid))
            btn.place(x=x, y=y)

    show_content_management_buttons()

    def open_student_analytics():
        root.destroy()
        subprocess.run([sys.executable, "Student_Analytics.py", str(current_lecturer_id)])

    def open_theme_shop():
        root.destroy()
        subprocess.run([sys.executable, "Theme_Shop.py", str(current_lecturer_id)])

    root.after(100, lambda: resize_background("Maps01"))
    root.mainloop()


if __name__ == "__main__":
    lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
    show_content_management(lecturer_id)