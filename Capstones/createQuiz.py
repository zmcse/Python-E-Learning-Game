import tkinter as tk
from tkinter import messagebox
import sys
import subprocess
from database_conn import connect_db
from UserData import get_user_details, set_user
from PIL import Image, ImageTk
import io
import random


def get_background_image(chapter_id="Maps01"):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT Image FROM Maps WHERE MapsID = ?", (chapter_id,))
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


def get_random_maps_item(chapter_number):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT m.MapsItemsID
            FROM MapsItems m
            LEFT JOIN QuestionDetails q ON m.MapsItemsID = q.MapsItemsID
            WHERE q.MapsItemsID IS NULL;
        """)
        result = cursor.fetchall()
        if result and int(result[0][0][-1]) <= 6:
            item_number = result[0][0][-1]
            print("Selected: ", item_number)
            print("missing IDs: ", result[0][0])
        else:
            item_number = random.randint(1, 6)
            print("Randomly selected: ", item_number)
    except Exception as e:
        item_number = 1
        print(f"Error retrieving null IDs: {e}")
    return f"MIT{chapter_number}0{item_number}"


def create_quiz(lecturer_id=None, chapter_number=1):
    if lecturer_id:
        set_user(lecturer_id)
    elif len(sys.argv) > 1:
        set_user(sys.argv[1])

    if len(sys.argv) > 2:
        try:
            chapter_number = int(sys.argv[2])
        except ValueError:
            chapter_number = 1

    def submit_question():
        question_text = entry_question.get("1.0", "end-1c").strip()
        correct_answer = entry_answer.get("1.0", "end-1c").strip()
        passcode = entry_passcode.get().strip()

        if not question_text or not correct_answer or not passcode:
            messagebox.showerror("Error", "All fields are required!")
            return

        if not passcode.isdigit() or len(passcode) != 1:
            messagebox.showerror("Error", "Passcode must be a single digit (0-9).")
            return

        user_data = get_user_details()
        if not user_data:
            messagebox.showerror("Error", "No user logged in!")
            return

        lecturer_id = user_data.get('LecturerID', '')
        if not lecturer_id:
            messagebox.showerror("Error", "Could not determine lecturer ID!")
            return

        conn = connect_db()
        if not conn:
            messagebox.showerror("Error", "Could not connect to database!")
            return

        try:
            cursor = conn.cursor()

            cursor.execute("select max(QuestionID) from QuestionDetails")
            max_id = cursor.fetchone()[0]

            if max_id:
                last_num = int(max_id[3:])
                new_num = last_num + 1
                question_id = f"QST{new_num:03d}"
            else:
                question_id = "QST101"

            level_id = f"LVL{chapter_number:03d}"
            maps_items_id = get_random_maps_item(chapter_number)

            cursor.execute("insert into QuestionDetails (QuestionID, Question_text, correct_answer, passcode, MapsItemsID, LevelID, LecturerID) "
                           "values (?, ?, ?, ?, ?, ?, ?)", (question_id, question_text, correct_answer, passcode, maps_items_id, level_id, lecturer_id))
            conn.commit()
            messagebox.showinfo("Success", "Question created successfully!")

            entry_question.delete("1.0", tk.END)
            entry_answer.delete("1.0", tk.END)
            entry_passcode.delete(0, tk.END)

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
        finally:
            conn.close()

    def go_back():
        root.destroy()
        lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
        chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        subprocess.run([sys.executable, f"Chapter{chapter_number}.py", str(lecturer_id)])

    root = tk.Tk()
    root.title(f"Create Quiz - Chapter {chapter_number}")
    root.state("zoomed")

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
                maps_id = f"Maps{chapter_number:02d}"
                image_data = get_background_image(maps_id)
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
    root.after(100, resize_background)

    main_frame = tk.Frame(root, bg="#424242", bd=5, relief=tk.RIDGE)
    main_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=600, height=500)

    bg_color = "#424242"
    entry_bg = "#f0f0f0"
    text_color = "white"
    button_bg = "#333333"

    title_label = tk.Label(main_frame, text=f"Create New Quiz Question - Chapter {chapter_number}", font=("Arial", 18, "bold"), bg=bg_color, fg=text_color)
    title_label.pack(pady=20)

    question_label = tk.Label(main_frame, text="Question Text:", font=("Arial", 12), bg=bg_color, fg=text_color, anchor="w")
    question_label.pack(fill=tk.X, padx=20)
    entry_question = tk.Text(main_frame, height=5, width=50, font=("Arial", 12), wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_question.pack(padx=20, pady=5)

    answer_label = tk.Label(main_frame, text="Correct Answer:", font=("Arial", 12), bg=bg_color, fg=text_color, anchor="w")
    answer_label.pack(fill=tk.X, padx=20)
    entry_answer = tk.Text(main_frame, height=3, width=50, font=("Arial", 12), wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_answer.pack(padx=20, pady=5)

    passcode_label = tk.Label(main_frame, text="Passcode (1 digit 0-9):", font=("Arial", 12), bg=bg_color, fg=text_color, anchor="w")
    passcode_label.pack(fill=tk.X, padx=20)
    entry_passcode = tk.Entry(main_frame, font=("Arial", 12), width=20, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_passcode.pack(padx=20, pady=5)

    submit_btn = tk.Button(main_frame, text="Submit Question", command=submit_question, bg=button_bg, fg="white", font=("Arial", 12, "bold"), width=20, bd=2, relief=tk.RAISED)
    submit_btn.pack(pady=20)

    back_btn = tk.Button(root, text="Back", command=go_back, bg="#333333", fg="white", font=("Arial", 12, "bold"), width=10)
    back_btn.place(x=20, y=20)

    root.mainloop()


if __name__ == "__main__":
    lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
    chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    create_quiz(lecturer_id)


