import tkinter as tk
from tkinter import messagebox, ttk
import sys
import subprocess
from database_conn import connect_db
from UserData import get_user_details, set_user
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


def delete_quiz(lecturer_id=None, chapter_number=1):
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
            messagebox.showerror("Error", "No user logged in!")
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
            level_id = f"LVL{chapter_number:03d}"

            cursor.execute("""SELECT QuestionID, Question_text, MapsItemsID from QuestionDetails where LecturerID = ?
             and LevelID = ?""", (lecturer_id, level_id))

            questions = cursor.fetchall()
            return questions

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
            return []
        finally:
            conn.close()

    def can_delete_questions():
        questions = load_questions()
        return len(questions) > 6

    def get_maps_item_count(maps_item_id):
        conn = connect_db()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) from QuestionDetails where MapsItemsID = ?", (maps_item_id,))
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error getting maps item count: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    def delete_selected():
        selected_item = question_tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a question to delete!")
            return

        question_data = question_tree.item(selected_item)['values']
        question_id = question_data[0]
        maps_item_id = question_data[2]

        # Check if this is the last question for this MapsItemID
        maps_item_count = get_maps_item_count(maps_item_id)
        if maps_item_count <= 1:
            messagebox.showerror("Cannot Delete",
                                 f"Cannot delete the only question for MapsItemID {maps_item_id}!\n"
                                 "Each MapsItem must have at least one question.")
            return

        user_data = get_user_details()
        if not user_data:
            messagebox.showerror("Error", "Could not determine lecturer ID!")
            return

        conn = connect_db()
        if not conn:
            messagebox.showerror("Error", "Could not connect to the database!")
            return

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) from Submissions where QuestionID = ?", (question_id,))
            submission_count = cursor.fetchone()[0]

            if submission_count > 0:
                confirm = messagebox.askyesno(
                    "Confirm Deletion",
                    f"This question has {submission_count} student submission.\n"
                    "Deleting it will also delete all related submissions.\n"
                    "Do you still want to proceed?"
                )
                if not confirm:
                    conn.close()
                    return

                cursor.execute("DELETE from Submissions where QuestionID = ?", (question_id,))

            cursor.execute("DELETE from QuestionDetails where QuestionID = ? and LecturerID = ?", (question_id, lecturer_id))
            conn.commit()
            if submission_count > 0:
                messagebox.showinfo("Success", f"Question and {submission_count} submission deleted successfully!")
            else:
                messagebox.showinfo("Success", "Question deleted successfully!")

            refresh_question_list()

        except Exception as e:
            conn.rollback()
            if "REFERENCE constraint" in str(e):
                messagebox.showerror("Cannot Delete", "This question has student submissions that could not be deleted\n"
                                     "Please contact the database Admin.")
            else:
                messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
        finally:
            conn.close()

    def refresh_question_list():
        questions = load_questions()
        question_tree.delete(*question_tree.get_children())
        for q_id, q_text, map_id in questions:
            question_tree.insert("", "end", values=(q_id, q_text, map_id))

        update_ui_status()

    def update_ui_status():
        question_count = len(load_questions())
        if question_count > 6:
            status_label.config(text=f"{question_count} questions", fg="white")
            delete_btn.config(state=tk.NORMAL)
        else:
            status_label.config(text=f"{question_count} questions (Minimum reached - cannot delete)", fg="#FFAAAA")
            delete_btn.config(state=tk.DISABLED)

    def go_back():
        root.destroy()
        lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
        chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        subprocess.run([sys.executable, f"Chapter{chapter_number}.py", str(lecturer_id)])

    root = tk.Tk()
    root.title(f"Delete Quiz - Chapter {chapter_number}")
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
    main_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=1000, height=600)

    bg_color = "#424242"
    text_color = "white"
    button_bg = "#333333"

    title_label = tk.Label(main_frame, text=f"Delete Quiz Questions - Chapter {chapter_number}", font=("Arial", 18, "bold"), bg=bg_color, fg=text_color)
    title_label.pack(pady=20)

    status_label = tk.Label(main_frame, font=("Arial", 10, "bold"), bg=bg_color, fg=text_color)
    status_label.pack()

    tree_frame = tk.Frame(main_frame, bg=bg_color)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    question_tree = ttk.Treeview(tree_frame,
                                 columns=("ID", "Question", "MapsItemID"),
                                 show="headings",
                                 height=15)

    question_tree.heading("ID", text="Question ID", anchor=tk.CENTER)
    question_tree.heading("Question", text="Question Text", anchor=tk.W)
    question_tree.heading("MapsItemID", text="Maps Item ID", anchor=tk.CENTER)

    question_tree.column("ID", width=100, anchor=tk.CENTER)
    question_tree.column("Question", width=600, anchor=tk.W)
    question_tree.column("MapsItemID", width=150, anchor=tk.CENTER)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=question_tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    question_tree.configure(yscrollcommand=scrollbar.set)
    question_tree.pack(fill=tk.BOTH, expand=True)

    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.pack(pady=20, padx=20)

    refresh_btn = tk.Button(button_frame, text="Refresh List", command=refresh_question_list, bg=button_bg, fg="white",
                            font=("Arial", 12, "bold"), width=15)
    refresh_btn.pack(side=tk.LEFT, padx=10)

    delete_btn = tk.Button(button_frame, text="Delete Selected", command=delete_selected, bg="#8D0000", fg="white", font=("Arial", 12, "bold"), width=15)
    delete_btn.pack(side=tk.LEFT, padx=10)

    back_btn = tk.Button(root, text="Back", command=go_back, bg="#333333", fg="white", font=("Arial", 12, "bold"), width=10)
    back_btn.place(x=20, y=20)

    update_ui_status()
    refresh_question_list()
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        set_user(sys.argv[1])

    lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
    chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    delete_quiz(lecturer_id)

