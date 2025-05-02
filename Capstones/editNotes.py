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


def edit_notes(lecturer_id=None, chapter_number=1):
    if lecturer_id:
        set_user(lecturer_id)
    elif len(sys.argv) > 1:
        set_user(sys.argv[1])

    if len(sys.argv) > 2:
        try:
            chapter_number = int(sys.argv[2])
        except ValueError:
            chapter_number = 1

    def load_notes():
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
            level_id = f"LVL{chapter_number:03d}"

            cursor.execute("""SELECT NotesID, Title, Content, Hint from Notes where LevelID = ? order by NotesID""", (level_id,))

            notes = cursor.fetchall()
            return notes

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occured: {str(e)}")
            return []
        finally:
            conn.close()

    current_note = {'id': None}

    def populate_note_fields(event):
        selected_item = notes_tree.focus()
        if not selected_item:
            return

        note_data = notes_tree.item(selected_item)['values']

        entry_title.delete("1.0", tk.END)
        entry_title.insert("1.0", note_data[1])

        entry_content.delete("1.0", tk.END)
        content = note_data[2].replace('\\n', '\n')
        entry_content.insert("1.0", content)

        entry_hint.delete("1.0", tk.END)
        hint = note_data[3].replace('\\n', '\n') if note_data[3] else ''
        entry_hint.insert("1.0", hint)

        current_note['id'] = note_data[0]

    def update_note():
        if not current_note['id']:
            messagebox.showerror("Error", "No note selected!")
            return

        title = entry_title.get("1.0", "end-1c").strip()
        content = entry_content.get("1.0", "end-1c").strip().replace('\n','\\n')
        hint = entry_hint.get("1.0", "end-1c").strip().replace('\n','\\n')

        if not title or not content:
            messagebox.showerror("Error", "Title and Content are required!")
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

            cursor.execute("""UPDATE Notes set Title = ?, Content = ?, Hint = ?, LecturerID = ? where NotesID = ? and LevelID = ?""", (title, content, hint, lecturer_id, current_note['id'], level_id))

            if cursor.rowcount == 0:
                messagebox.showerror("Error", "No rows updated. Note may not exist or you do not have permission")
            else:
                conn.commit()
                messagebox.showinfo("Success", "Note updated successfully!")
                refresh_notes_list()
                current_note['id'] = None
                clear_fields()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
        finally:
            conn.close()

    def refresh_notes_list():
        notes = load_notes()
        notes_tree.delete(*notes_tree.get_children())
        for n in notes:
            notes_tree.insert("", "end", values=(n[0], n[1], n[2], n[3]))

    def clear_fields():
        entry_title.delete("1.0", tk.END)
        entry_content.delete("1.0", tk.END)
        entry_hint.delete("1.0", tk.END)
        current_note['id'] = None

    def go_back():
        root.destroy()
        lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
        chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        subprocess.run([sys.executable, f"Chapter{chapter_number}.py", str(lecturer_id)])

    root = tk.Tk()
    root.title(f"Edit Notes - Chapter {chapter_number}")
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

    title_label = tk.Label(main_frame, text=f"Edit Notes - Chapter {chapter_number}", font=("Arial", 18, "bold"),
                           bg=bg_color, fg=text_color)
    title_label.grid(row=0, column=0, columnspan=2, pady=20)

    list_frame = tk.Frame(main_frame, bg=bg_color)
    list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    notes_tree = ttk.Treeview(list_frame, columns=("ID", "Title", "Content", "Hint"), show="headings", height=15)
    notes_tree.heading("ID", text="ID")
    notes_tree.heading("Title", text="Title")
    notes_tree.heading("Content", text="Content")
    notes_tree.heading("Hint", text="Hint")

    notes_tree.column("ID", width=80, anchor="center")
    notes_tree.column("Title", width=200)
    notes_tree.column("Content", width=300)
    notes_tree.column("Hint", width=200)

    notes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=notes_tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    notes_tree.configure(yscrollcommand=scrollbar.set)

    notes_tree.bind("<<TreeviewSelect>>", populate_note_fields)

    edit_frame = tk.Frame(main_frame, bg=bg_color)
    edit_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    title_label = tk.Label(edit_frame, text="Title:", font=("Arial", 12),
                           bg=bg_color, fg=text_color, anchor="w")
    title_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    entry_title = tk.Text(edit_frame, height=1, width=40, font=("Arial", 12),
                          wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_title.grid(row=0, column=1, sticky="we", padx=5, pady=5)

    content_label = tk.Label(edit_frame, text="Content:", font=("Arial", 12),
                             bg=bg_color, fg=text_color, anchor="w")
    content_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    entry_content = tk.Text(edit_frame, height=8, width=40, font=("Arial", 12),
                            wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_content.grid(row=1, column=1, sticky="we", padx=5, pady=5)

    hint_label = tk.Label(edit_frame, text="Hint:", font=("Arial", 12),
                          bg=bg_color, fg=text_color, anchor="w")
    hint_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
    entry_hint = tk.Text(edit_frame, height=2, width=40, font=("Arial", 12),
                         wrap=tk.WORD, bg=entry_bg, bd=2, relief=tk.SUNKEN)
    entry_hint.grid(row=2, column=1, sticky="we", padx=5, pady=5)

    button_frame = tk.Frame(edit_frame, bg=bg_color)
    button_frame.grid(row=3, column=0, columnspan=2, pady=30)

    update_btn = tk.Button(button_frame, text="Update Note", command=update_note,
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

    refresh_notes_list()
    root.mainloop()


if __name__ == "__main__":
    lecturer_id = sys.argv[1] if len(sys.argv) > 1 else None
    chapter_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    edit_notes(lecturer_id, chapter_number)
