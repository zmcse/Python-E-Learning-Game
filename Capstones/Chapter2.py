from database_conn import connect_db
from Navigation_Bar import create_navbar
import subprocess
import sys
import tkinter as tk
from PIL import Image, ImageTk
from UserData import get_user, set_user
import io
import tkinter.messagebox as messagebox



def get_background_image(chapter_id="Maps02"):
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


def go_back():
    lecturer_id = get_user()
    root.destroy()
    subprocess.run([sys.executable, "Content_Management_Main_page.py", str(lecturer_id)])


def open_create_quiz():
    lecturer_id = get_user()
    root.destroy()
    subprocess.run([sys.executable, "createQuiz.py", str(lecturer_id), "2"])


def open_edit_quiz():
    lecturer_id = get_user()
    root.destroy()
    subprocess.run([sys.executable, "editQuiz.py", str(lecturer_id), "2"])


def open_delete_quiz():
    lecturer_id = get_user()
    root.destroy()
    subprocess.run([sys.executable, "deleteQuiz.py", str(lecturer_id), "2"])


def open_edit_notes():
    lecturer_id = get_user()
    root.destroy()
    subprocess.run([sys.executable, "editNotes.py", str(lecturer_id), "2"])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        set_user(sys.argv[1])

root = tk.Tk()
root.title("Chapter 2")
root.state("zoomed")

# Get lecturer ID
lecturer_id = get_user()
if not lecturer_id:
    messagebox.showerror("Error", "No lecturer ID found!")
    root.destroy()
    sys.exit(1)

# Create navigation bar with lecturer ID
create_navbar(root, lecturer_id)

# Set window close protocol to use go_back function
root.protocol("WM_DELETE_WINDOW", go_back)

background_label = tk.Label(root)
background_label.place(x=0, y=0, relwidth=1, relheight=1)
background_label.lower()


def resize_background():
    try:
        width = root.winfo_width()
        height = root.winfo_height()
        if width > 1 and height > 1:
            image_data = get_background_image("Maps02")
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
    resize_background()


root.bind("<Configure>", on_window_resize)

btn_create = tk.Button(root, text="Create Quiz", command=open_create_quiz, width=15, height=2, bg="#333333", fg="white",
                font=("Arial", 14, "bold"))
btn_edit = tk.Button(root, text="Edit Quiz", command=open_edit_quiz, width=15, height=2, bg="#333333", fg="white",
                font=("Arial", 14, "bold"))
btn_delete = tk.Button(root, text="Delete Quiz", command=open_delete_quiz, width=15, height=2, bg="#333333", fg="white",
                font=("Arial", 14, "bold"))


btn_edit_notes = tk.Button(root, text="Edit Notes", command=open_edit_notes, width=15, height=2, bg="#333333",
                           fg="white", font=("Arial", 14, "bold"))


btn_create.place(x=500, y=380)
btn_edit.place(x=500, y=480)
btn_delete.place(x=800, y=380)


btn_edit_notes.place(x=800, y=480)

back_btn = tk.Button(root, text="Back", command=go_back, bg="#333333", fg="white", font=("Arial", 12, "bold"), width=10)
back_btn.place(x=20, y=180)

root.after(100, resize_background)
root.mainloop()