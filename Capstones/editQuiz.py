import tkinter as tk
from tkinter import messagebox, ttk
from database_conn import connect_db
from UserData import get_user_details, set_user
import sys
import subprocess
from PIL import Image, ImageTk
import io


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


def edit_quiz(lecturer_id=None, chapter_number=1):
    if lecturer_id:
        set_user(lecturer_id)
    elif len(sys.argv) > 1:
        set_user(sys.argv[1])

    if len(sys.argv) > 2:
        try:
            chapter_number = int(sys.argv[2])
        except ValueError:
            chapter_number = 1

    def load_questions():
        user_data = get_user_details()
        if not user_data:
            messagebox.showerror("Error", "No user logged in. Please log in to proceed!")
            return []

        lecturer_id = user_data.get('LecturerID', '')
        if not lecturer_id:
            messagebox.showerror("Error", "Could not determine lecturer ID!")
            return []

        conn = connect_db()
        if not conn:
            messagebox.showerror("Error", "Could not connect to database!")
            return []

        try:
            cursor = conn.cursor()
            level_id = f"LVL{chapter_number:03d}"  # Format: LVL001, LVL002, etc.

            cursor.execute("""SELECT q.QuestionID, q.Question_text, q.correct_answer, q.passcode, q.MapsItemsID 
            FROM QuestionDetails q 
            WHERE q.LecturerID = ? AND q.LevelID = ? 
            ORDER BY q.QuestionID""", (lecturer_id, level_id))

            questions = cursor.fetchall()
            return questions

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
            return []
        finally:
            conn.close()
    current_question = {'id' : None}

    def populate_question_fields(event):
        selected_item = question_tree.focus()
        if not selected_item:
            return

        question_data = question_tree.item(selected_item)['values']

        entry_question.delete("1.0", tk.END)
        entry_question.insert("1.0", question_data[1])

        entry_answer.delete("1.0", tk.END)
        entry_answer.insert("1.0", question_data[2])

        entry_passcode.delete(0, tk.END)
        entry_passcode.insert(0, question_data[3])

        current_question['id'] = question_data[0]

    def update_question():
        if not current_question['id']:
            messagebox.showerror("Error", "No question selected!")
            return

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

            level_id = f"LVL{chapter_number:03d}"

            cursor.execute("""UPDATE QuestionDetails set Question_text = ?, correct_answer = ?, passcode = ? where
             QuestionID = ? and LecturerID = ? and LevelID = ?""", (question_text, correct_answer, passcode, current_question['id'], lecturer_id, level_id))

            if cursor.rowcount == 0:
                messagebox.showerror("Error", "No rows updated. Question may not exist or you dont have permission.")
            else:
                conn.commit()
                messagebox.showinfo("Success", "Question updated successfully!")
                refresh_question_list()
                current_question['id'] = None
                clear_fields()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
        finally:
            conn.close()

    def refresh_question_list():
        questions = load_questions()
        question_tree.delete(*question_tree.get_children())
        for q in questions:
            question_tree.insert("", "end", values=(q[0], q[1], q[2], q[3]))

    def clear_fields():
        entry_question.delete("1.0", tk.END)
        entry_answer.delete("1.0", tk.END)
        entry_passcode.delete(0, tk.END)
        current_question['id'] = None

    def go_back():
        root.destroy()
        lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
        chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        subprocess.run([sys.executable, f"Chapter{chapter_number}.py", str(lecturer_id)])

    root = tk.Tk()
    root.title(f"Edit Quiz - Chapter {chapter_number}")
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
    main_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=1300, height=600)

    bg_color = "#424242"
    entry_bg = "#f0f0f0"
    text_color = "white"
    button_bg = "#333333"
    tree_bg = "#f0f0f0"
    tree_fg = "black"

    title_label = tk.Label(main_frame, text=f"Edit Quiz Questions - Chapter {chapter_number}", font=("Arial", 18, "bold"), bg=bg_color, fg=text_color)
    title_label.grid(row=0, column=0, columnspan=2, pady=20)

    list_frame = tk.Frame(main_frame, bg=bg_color)
    list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    question_tree = ttk.Treeview(list_frame, columns=("ID", "Question", "Answer", "Passcode"), show="headings", height=15)
    question_tree.heading("ID", text="ID")
    question_tree.heading("Question", text="Question")
    question_tree.heading("Answer", text="Correct Answer")
    question_tree.heading("Passcode", text="Passcode")

    question_tree.column("ID", width=80, anchor="center")
    question_tree.column("Question", width=300)
    question_tree.column("Answer", width=200)
    question_tree.column("Passcode", width=100, anchor="center")

    question_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=question_tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    question_tree.configure(yscrollcommand=scrollbar.set)

    question_tree.bind("<<TreeviewSelect>>", populate_question_fields)

    edit_frame = tk.Frame(main_frame, bg=bg_color)
    edit_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    question_label = tk.Label(edit_frame, text="Question Text:", font=("Arial", 12),
                              bg=bg_color, fg=text_color, anchor="w")
    question_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
    entry_question = tk.Text(edit_frame, height=8, width=40, font=("Arial", 12),
                             wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_question.grid(row=0, column=1, sticky="we", padx=5, pady=5)

    answer_label = tk.Label(edit_frame, text="Correct Answer:", font=("Arial", 12),
                            bg=bg_color, fg=text_color, anchor="w")
    answer_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
    entry_answer = tk.Text(edit_frame, height=5, width=40, font=("Arial", 12),
                           wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_answer.grid(row=1, column=1, sticky="we", padx=5, pady=5)

    passcode_label = tk.Label(edit_frame, text="Passcode (1 digit 0-9):", font=("Arial", 12),
                              bg=bg_color, fg=text_color, anchor="w")
    passcode_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
    entry_passcode = tk.Entry(edit_frame, font=("Arial", 12), width=20,
                              bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_passcode.grid(row=2, column=1, sticky="w", padx=5, pady=5)

    button_frame = tk.Frame(edit_frame, bg=bg_color)
    button_frame.grid(row=3, column=0, columnspan=2, pady=30)

    update_btn = tk.Button(button_frame, text="Update Question", command=update_question,
                           bg=button_bg, fg="white", font=("Arial", 12, "bold"),
                           width=20, height=2, bd=2, relief=tk.RAISED)
    update_btn.pack(side=tk.LEFT, padx=10)

    clear_btn = tk.Button(button_frame, text="Clear Fields", command=clear_fields,
                          bg=button_bg, fg="white", font=("Arial", 12, "bold"),
                          width=20, height=2, bd=2, relief=tk.RAISED)
    clear_btn.pack(side=tk.LEFT, padx=10)

    back_btn = tk.Button(root, text="Back", command=go_back, bg="#333333",
                         fg="white", font=("Arial", 12, "bold"), width=10)
    back_btn.place(x=20, y=20)

    refresh_question_list()
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        set_user(sys.argv[1])

    lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
    chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    edit_quiz(lecturer_id, chapter_number)


