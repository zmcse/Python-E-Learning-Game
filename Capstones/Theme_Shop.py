import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyodbc
from PIL import Image, ImageTk
import io
from tkinter import font as tkfont
import sys
from database_conn import connect_db



class ThemeShop:
    def __init__(self, root, lecturer_id):
        self.root = root
        self.lecturer_id = lecturer_id
        self.root.title("Theme Shop")
        self.root.state('zoomed')  # Make window full screen
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        from Navigation_Bar import create_navbar
        create_navbar(self.root, self.lecturer_id)

        #Make Window resizeable and set the minimum size (change)
        self.root.minsize(800,600)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Custom color scheme (change)
        self.bg_color = "#f0f2f5"
        self.primary_color = "#4e73df"
        self.secondary_color = "#858796"
        self.success_color = "#1cc88a"
        self.danger_color = "#e74a3b"
        self.warning_color = "#f6c23e"
        self.text_color = "#5a5c69"
        self.card_color = "#ffffff"

        # Configure root window background
        self.root.configure(bg=self.bg_color)

        # Track PhotoImage objects to prevent garbage collection
        self.image_references = []

        # Initialize database connection
        self.conn = self.database_connect()
        if self.conn is None:
            messagebox.showerror("Error", "Failed to connect to database. Application will close.")
            self.root.destroy()
            return

        self.cursor = self.conn.cursor()

        # Custom fonts (change)
        self.title_font = tkfont.Font(family="Helvetica", size=16, weight="bold")
        self.header_font = tkfont.Font(family="Helvetica", size=12, weight="bold")
        self.normal_font = tkfont.Font(family="Helvetica", size=10)
        self.button_font = tkfont.Font(family="Helvetica", size=10, weight="bold")

        # UI Setup
        self.setup_ui()

        # Load items from database
        self.load_items()

    def database_connect(self):
        """Connect to SQL Server database"""
        try:
            conn = connect_db()
            return conn
        except pyodbc.Error as e:
            print("Database connection error:", e)
            return None

    def setup_ui(self):
        """Set up the user interface"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header frame with gradient background
        header_frame = ttk.Frame(main_container, style='Header.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Title label
        title_label = ttk.Label(
            header_frame,
            text="Theme Shop Management",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Admin controls
        admin_frame = ttk.Frame(header_frame)
        admin_frame.pack(side=tk.RIGHT, padx=10)

        add_btn = ttk.Button(
            admin_frame,
            text="Add Item",
            command=self.add_item_dialog
        )
        add_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(
            admin_frame,
            text="Delete Item",
            command=self.delete_item_dialog
        )
        delete_btn.pack(side=tk.LEFT, padx=5)

        manage_btn = ttk.Button(
            admin_frame,
            text="View Statistics",
            command=self.show_statistics
        )
        manage_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(
            admin_frame,
            text="Refresh",
            command=self.refresh_shop
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Main content frame with canvas and scrollbar
        self.content_frame = ttk.Frame(main_container)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.content_frame, bg=self.bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.content_frame,
            orient="vertical",
            command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)

        def on_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.scrollable_frame.bind("<Configure>", on_configure)

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind the canvas resize event to adjust the scrollable frame width
        def on_canvas_resize(event):
            canvas_width = event.width
            self.canvas.itemconfig(1, width=canvas_width)  # 1 is the window ID of scrollable frame

    def load_image_from_data(self, image_data):
        """Convert binary image data to PhotoImage"""
        try:
            if not image_data:
                return None

            image = Image.open(io.BytesIO(image_data))
            # Make images larger to fill more space (adjust size as needed)
            image = image.resize((150, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.image_references.append(photo)  # Prevent garbage collection
            return photo
        except Exception as e:
            print(f"Image loading error: {e}")
            return None

    def load_items(self):
        """Load items from database and display them"""
        # Clear existing items and images
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_references.clear()

        try:
            # Get all items from database
            query = "SELECT ItemID, Name, Description, Price, item_data FROM Items WHERE LecturerID = ?"
            self.cursor.execute(query, (self.lecturer_id,))
            items = self.cursor.fetchall()

            if not items:
                no_items_label = ttk.Label(
                    self.scrollable_frame,
                    text="No items available in the shop. Click 'Add Item' to create new items.",
                    font=('Arial', 12)
                )
                no_items_label.grid(row=0, column=0, columnspan=6, pady=50)  # Span all columns
                return

            # Calculate number of columns based on window width (4 columns for wider screens)
            num_columns = 6

            # Configure grid columns with equal weight
            for i in range(num_columns):
                self.scrollable_frame.columnconfigure(i, weight=1, uniform="cols")

            # Display items in a grid
            for i, item in enumerate(items):
                row = i // num_columns
                col = i % num_columns

                item_frame = ttk.Frame(
                    self.scrollable_frame,
                    borderwidth=2,
                    relief="groove",
                    padding=10
                )
                item_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                item_frame.columnconfigure(0, weight=1)
                item_frame.rowconfigure(0, weight=1)  # Make the frame expandable

                # Item image - make it larger to fill more space
                photo = self.load_image_from_data(item.item_data)
                if photo:
                    img_label = ttk.Label(item_frame, image=photo)
                    img_label.image = photo
                    img_label.pack(expand=True, fill=tk.BOTH, pady=(0, 10))
                else:
                    no_img_label = ttk.Label(item_frame, text="No Image", font=('Arial', 10))
                    no_img_label.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

                # Item details - in a separate frame to control layout
                details_frame = ttk.Frame(item_frame)
                details_frame.pack(fill=tk.X, expand=True)

                ttk.Label(
                    details_frame,
                    text=item.Name,
                    font=('Arial', 12, 'bold')
                ).pack(fill=tk.X)

                desc_label = ttk.Label(
                    details_frame,
                    text=item.Description,
                    wraplength=200  # Adjust based on column width
                )
                desc_label.pack(fill=tk.X)

                ttk.Label(
                    details_frame,
                    text=f"Price: {item.Price} points",
                    font=('Arial', 10)
                ).pack(fill=tk.X)

                # Action buttons
                btn_frame = ttk.Frame(item_frame)
                btn_frame.pack(fill=tk.X, pady=5)

                edit_btn = ttk.Button(
                    btn_frame,
                    text="Edit",
                    command=lambda i=item: self.edit_item_dialog(i)
                )
                edit_btn.pack(side=tk.LEFT, padx=5, expand=True)

                delete_btn = ttk.Button(
                    btn_frame,
                    text="Delete",
                    command=lambda i=item: self.delete_item(i.ItemID)
                )
                delete_btn.pack(side=tk.LEFT, padx=5, expand=True)

        except pyodbc.Error as e:
            messagebox.showerror("Database Error", f"Failed to load items:\n{str(e)}")

    def add_item_dialog(self):
        """Show dialog to add new item"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Theme Item")
        dialog.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Item name
        ttk.Label(main_frame, text="Item Name:", font=('Arial', 10)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        name_entry = ttk.Entry(main_frame, width=40, font=('Arial', 10))
        name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        name_entry.focus_set()

        # Description
        ttk.Label(main_frame, text="Description:", font=('Arial', 10)).grid(row=2, column=0, sticky="w", pady=(0, 5))

        desc_frame = ttk.Frame(main_frame)
        desc_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        desc_entry = tk.Text(desc_frame, width=40, height=4, font=('Arial', 10))
        desc_scroll = ttk.Scrollbar(desc_frame, orient="vertical", command=desc_entry.yview)

        desc_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        desc_entry.config(yscrollcommand=desc_scroll.set)

        # Price
        ttk.Label(main_frame, text="Price (points):", font=('Arial', 10)).grid(row=4, column=0, sticky="w", pady=(0, 5))
        price_entry = ttk.Entry(main_frame, width=10, font=('Arial', 10))
        price_entry.grid(row=5, column=0, sticky="w", pady=(0, 10))
        price_entry.insert(0, "100")

        # Image
        ttk.Label(main_frame, text="Item Image:", font=('Arial', 10)).grid(row=6, column=0, sticky="w", pady=(0, 5))
        image_path = tk.StringVar()

        # Image preview frame
        img_frame = ttk.Frame(main_frame)
        img_frame.grid(row=7, column=0, sticky="nsew", pady=(0, 10))

        preview_label = ttk.Label(img_frame)
        preview_label.pack(side=tk.TOP, pady=5)

        def browse_image():
            file_path = filedialog.askopenfilename(
                title="Select Item Image",
                filetypes=[("Image files", "*.jpg *.jpeg *.png")]
            )
            if file_path:
                image_path.set(file_path)
                try:
                    img = Image.open(file_path)
                    img.thumbnail((150, 150))
                    photo = ImageTk.PhotoImage(img)
                    preview_label.config(image=photo)
                    preview_label.image = photo
                except Exception as e:
                    messagebox.showerror("Error", f"Could not load image: {str(e)}")

        browse_btn = ttk.Button(
            img_frame,
            text="Browse Image",
            command=browse_image
        )
        browse_btn.pack(side=tk.TOP, pady=5)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, sticky="e", pady=(10, 0))

        def submit():
            name = name_entry.get().strip()
            description = desc_entry.get("1.0", tk.END).strip()
            price = price_entry.get().strip()
            img_data = None

            # Validation
            if not name:
                messagebox.showerror("Error", "Item name is required!")
                return
            if not description:
                messagebox.showerror("Error", "Description is required!")
                return
            if not price:
                messagebox.showerror("Error", "Price is required!")
                return
            if not image_path.get():
                messagebox.showerror("Error", "Item image is required!")
                return

            try:
                price = int(price)
                if price <= 0:
                    raise ValueError("Price must be positive")
            except ValueError:
                messagebox.showerror("Error", "Price must be a positive integer")
                return

            if image_path.get():
                try:
                    with open(image_path.get(), 'rb') as f:
                        img_data = f.read()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read image file: {str(e)}")
                    return

            if self.add_item(name, description, price, img_data):
                dialog.destroy()
                self.refresh_shop()

        submit_btn = ttk.Button(
            button_frame,
            text="Add Item",
            command=submit
        )
        submit_btn.pack(side=tk.RIGHT, padx=5)

        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        for i in range(9):  # Number of rows
            main_frame.rowconfigure(i, weight=1 if i in (3, 7) else 0)

        # Make the window adjust to its content
        dialog.update_idletasks()
        dialog.minsize(dialog.winfo_width(), dialog.winfo_height())

    def add_item(self, name, description, price, image_data=None):
        """Add new item to database"""
        if name.strip().lower() == "default":
            messagebox.showerror("Error", "That name is not allowed.")
            return

        try:
            # Get next ItemID
            self.cursor.execute("SELECT MAX(ItemID) FROM Items")
            result = self.cursor.fetchone()
            if result[0]:
                last_id = int(result[0][3:])  # Extract numeric part after 'ITM'
                new_id = f"ITM{last_id + 1:03d}"
            else:
                new_id = "ITM001"

            # Insert new item
            query = """
            INSERT INTO Items (ItemID, Name, Description, Price, item_data, LecturerID)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (new_id, name, description, price, image_data, self.lecturer_id))
            self.conn.commit()

            messagebox.showinfo("Success", "Item added successfully!")
            return True
        except pyodbc.Error as e:
            self.conn.rollback()
            messagebox.showerror("Database Error", f"Failed to add item:\n{str(e)}")
            return False

    def edit_item_dialog(self, item):
        """Show dialog to edit existing item"""
        if item.Name.strip().lower() == "default":
            messagebox.showerror("Error", "This item cannot be edited.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Item: {item.Name}")
        dialog.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Item name
        ttk.Label(main_frame, text="Item Name:", font=('Arial', 10)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        name_entry = ttk.Entry(main_frame, width=40, font=('Arial', 10))
        name_entry.insert(0, item.Name)
        name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        name_entry.focus_set()

        # Description
        ttk.Label(main_frame, text="Description:", font=('Arial', 10)).grid(row=2, column=0, sticky="w", pady=(0, 5))

        desc_frame = ttk.Frame(main_frame)
        desc_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        desc_entry = tk.Text(desc_frame, width=40, height=4, font=('Arial', 10))
        desc_scroll = ttk.Scrollbar(desc_frame, orient="vertical", command=desc_entry.yview)

        desc_entry.insert("1.0", item.Description)
        desc_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        desc_entry.config(yscrollcommand=desc_scroll.set)

        # Price
        ttk.Label(main_frame, text="Price (points):", font=('Arial', 10)).grid(row=4, column=0, sticky="w", pady=(0, 5))
        price_entry = ttk.Entry(main_frame, width=10, font=('Arial', 10))
        price_entry.insert(0, str(item.Price))
        price_entry.grid(row=5, column=0, sticky="w", pady=(0, 10))

        # Image
        ttk.Label(main_frame, text="Current Image:", font=('Arial', 10)).grid(row=6, column=0, sticky="w", pady=(0, 5))
        image_path = tk.StringVar()

        # Image preview frame
        img_frame = ttk.Frame(main_frame)
        img_frame.grid(row=7, column=0, sticky="nsew", pady=(0, 10))

        preview_label = ttk.Label(img_frame)
        preview_label.pack(side=tk.TOP, pady=5)

        if item.item_data:
            try:
                img = Image.open(io.BytesIO(item.item_data))
                img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(img)
                preview_label.config(image=photo)
                preview_label.image = photo
                self.image_references.append(photo)  # Keep reference
            except Exception as e:
                preview_label.config(text="Current image not available")

        def browse_image():
            file_path = filedialog.askopenfilename(
                title="Select New Image",
                filetypes=[("Image files", "*.jpg *.jpeg *.png")]
            )
            if file_path:
                image_path.set(file_path)
                try:
                    img = Image.open(file_path)
                    img.thumbnail((150, 150))
                    photo = ImageTk.PhotoImage(img)
                    preview_label.config(image=photo)
                    preview_label.image = photo
                    self.image_references.append(photo)  # Keep reference
                except Exception as e:
                    messagebox.showerror("Error", f"Could not load image: {str(e)}")

        browse_btn = ttk.Button(
            img_frame,
            text="Change Image",
            command=browse_image
        )
        browse_btn.pack(side=tk.TOP, pady=5)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, sticky="e", pady=(10, 0))

        def submit():
            name = name_entry.get().strip()
            description = desc_entry.get("1.0", tk.END).strip()
            price = price_entry.get().strip()
            img_data = item.item_data  # Keep current image by default

            # Validation
            if not name:
                messagebox.showerror("Error", "Item name is required!")
                return
            if not description:
                messagebox.showerror("Error", "Description is required!")
                return
            if not price:
                messagebox.showerror("Error", "Price is required!")
                return
            if not image_path.get():
                messagebox.showerror("Error", "Item image is required!")
                return
            if item.Name.strip().lower() == "default":
                messagebox.showerror("Error", "That name is not allowed.")
                return

            try:
                price = int(price)
                if price <= 0:
                    raise ValueError("Price must be positive")
            except ValueError:
                messagebox.showerror("Error", "Price must be a positive integer")
                return

            if image_path.get():
                try:
                    with open(image_path.get(), 'rb') as f:
                        img_data = f.read()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read image file: {str(e)}")
                    return

            if self.edit_item(item.ItemID, name, description, price, img_data):
                dialog.destroy()
                self.refresh_shop()

        submit_btn = ttk.Button(
            button_frame,
            text="Save Changes",
            command=submit
        )
        submit_btn.pack(side=tk.RIGHT, padx=5)

        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        for i in range(9):  # Number of rows
            main_frame.rowconfigure(i, weight=1 if i in (3, 7) else 0)

        # Make the window adjust to its content
        dialog.update_idletasks()
        dialog.minsize(dialog.winfo_width(), dialog.winfo_height())

    def edit_item(self, item_id, name, description, price, image_data=None):
        """Update item in database"""
        if name.strip().lower() == "default":
            messagebox.showerror("Error", "That name is not allowed.")
            return

        try:
            query = """
            UPDATE Items 
            SET Name = ?, Description = ?, Price = ?, item_data = ?
            WHERE ItemID = ?
            """
            self.cursor.execute(query, (name, description, price, image_data, item_id))
            self.conn.commit()

            messagebox.showinfo("Success", "Item updated successfully!")
            return True
        except pyodbc.Error as e:
            self.conn.rollback()
            messagebox.showerror("Database Error", f"Failed to update item:\n{str(e)}")
            return False

    def delete_item_dialog(self):
        """Show dialog to select item to delete"""
        try:
            self.cursor.execute("SELECT ItemID, Name FROM Items WHERE LecturerID = ? ORDER BY Name",
                                (self.lecturer_id,))
            items = self.cursor.fetchall()

            if not items:
                messagebox.showinfo("Info", "No items available to delete.")
                return

            dialog = tk.Toplevel(self.root)
            dialog.title("Delete Item")
            dialog.resizable(False, False)

            # Main frame
            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                main_frame,
                text="Select Item to Delete:",
                font=('Arial', 12, 'bold')
            ).pack(pady=10)

            # Create a frame for the listbox and scrollbar
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill=tk.BOTH, expand=True)

            # Create a scrollbar
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Create the listbox
            item_listbox = tk.Listbox(
                list_frame,
                width=50,
                height=15,
                yscrollcommand=scrollbar.set,
                font=('Arial', 10)
            )
            item_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Configure the scrollbar
            scrollbar.config(command=item_listbox.yview)

            # Add items to the listbox
            for item in items:
                item_listbox.insert(tk.END, f"{item.ItemID} - {item.Name}")

            # Button frame
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(pady=10)

            def delete_selected():
                selection = item_listbox.curselection()
                if not selection:
                    messagebox.showerror("Error", "Please select an item to delete")
                    return

                item_id = items[selection[0]].ItemID
                if item_id == "ITM001":
                    messagebox.showerror("Error", "This item cannot be deleted.")
                    return
                confirm = messagebox.askyesno(
                    "Confirm Delete",
                    f"Are you sure you want to delete item {item_id}?\n"
                    "This action cannot be undone."
                )

                if confirm:
                    if self.delete_item(item_id):
                        dialog.destroy()
                        self.refresh_shop()

            delete_btn = ttk.Button(
                btn_frame,
                text="Delete Selected",
                command=delete_selected
            )
            delete_btn.pack(side=tk.LEFT, padx=10)

            cancel_btn = ttk.Button(
                btn_frame,
                text="Cancel",
                command=dialog.destroy
            )
            cancel_btn.pack(side=tk.LEFT, padx=10)

            # Make the window adjust to its content
            dialog.update_idletasks()
            dialog.minsize(400, 400)

        except pyodbc.Error as e:
            messagebox.showerror("Database Error", f"Failed to load items:\n{str(e)}")

    def delete_item(self, item_id):
        """Delete item from database"""
        if item_id == "ITM001":
            messagebox.showerror("Error", "This item cannot be deleted.")
            return

        try:
            # First check if any students have this item
            self.cursor.execute(
                "SELECT COUNT(*) FROM Inventory WHERE ItemID = ?",
                (item_id,)
            )
            count = self.cursor.fetchone()[0]

            if count > 0:
                confirm = messagebox.askyesno(
                    "Warning",
                    f"This item is owned by {count} student(s).\n"
                    "Deleting it will remove it from their inventories too.\n"
                    "Are you sure you want to proceed?"
                )
                if not confirm:
                    return False

            # Delete from Inventory first (foreign key constraint)
            self.cursor.execute(
                "DELETE FROM Inventory WHERE ItemID = ?",
                (item_id,)
            )

            # Then delete from Items
            self.cursor.execute(
                "DELETE FROM Items WHERE ItemID = ?",
                (item_id,)
            )

            self.conn.commit()
            messagebox.showinfo("Success", "Item deleted successfully!")
            return True
        except pyodbc.Error as e:
            self.conn.rollback()
            messagebox.showerror("Database Error", f"Failed to delete item:\n{str(e)}")
            return False

    def show_statistics(self):
        """Show statistics about items and purchases"""
        try:
            # Get all items with purchase counts
            query = """
            SELECT i.ItemID, i.Name, i.Price, COUNT(inv.InventoryID) as purchase_count
            FROM Items i
            LEFT JOIN Inventory inv ON i.ItemID = inv.ItemID
            WHERE i.LecturerID = ?
            GROUP BY i.ItemID, i.Name, i.Price
            ORDER BY purchase_count DESC
            """
            self.cursor.execute(query, (self.lecturer_id,))
            items = self.cursor.fetchall()

            # Get total items and total purchases
            self.cursor.execute("SELECT COUNT(*) FROM Items WHERE LecturerID = ?", (self.lecturer_id,))
            total_items = self.cursor.fetchone()[0]

            self.cursor.execute(
                "SELECT COUNT(*) FROM Inventory i JOIN Items it ON i.ItemID = it.ItemID WHERE it.LecturerID = ?",
                (self.lecturer_id,))
            total_purchases = self.cursor.fetchone()[0]

            # Create statistics window
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Shop Statistics")
            stats_window.geometry("800x600")
            stats_window.resizable(True, True)

            # Main frame
            main_frame = ttk.Frame(stats_window, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Statistics frame
            stats_frame = ttk.Frame(main_frame)
            stats_frame.pack(fill=tk.X, pady=10)

            ttk.Label(
                stats_frame,
                text="Shop Statistics",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=0, columnspan=2, pady=5)

            ttk.Label(
                stats_frame,
                text="Total Items:",
                font=('Arial', 10, 'bold')
            ).grid(row=1, column=0, sticky=tk.W, padx=5)
            ttk.Label(
                stats_frame,
                text=str(total_items),
                font=('Arial', 10)
            ).grid(row=1, column=1, sticky=tk.W)

            ttk.Label(
                stats_frame,
                text="Total Purchases:",
                font=('Arial', 10, 'bold')
            ).grid(row=2, column=0, sticky=tk.W, padx=5)
            ttk.Label(
                stats_frame,
                text=str(total_purchases),
                font=('Arial', 10)
            ).grid(row=2, column=1, sticky=tk.W)

            # Items list with Treeview
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)

            columns = ("ID", "Name", "Price", "Purchases")
            tree = ttk.Treeview(
                tree_frame,
                columns=columns,
                show="headings",
                selectmode="browse"
            )

            # Configure columns
            tree.column("ID", width=100, anchor=tk.CENTER)
            tree.column("Name", width=300, anchor=tk.W)
            tree.column("Price", width=100, anchor=tk.CENTER)
            tree.column("Purchases", width=100, anchor=tk.CENTER)

            # Configure headings
            for col in columns:
                tree.heading(col, text=col)

            # Add data to treeview
            for item in items:
                tree.insert("", tk.END, values=(
                    item.ItemID,
                    item.Name,
                    f"{item.Price} pts",
                    item.purchase_count
                ))

            # Add scrollbar
            scrollbar = ttk.Scrollbar(
                tree_frame,
                orient=tk.VERTICAL,
                command=tree.yview
            )
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Add double-click event to edit items
            def on_double_click(event):
                item = tree.selection()[0]
                item_id = tree.item(item, "values")[0]
                self.edit_item_by_id(item_id)

            tree.bind("<Double-1>", on_double_click)

        except pyodbc.Error as e:
            messagebox.showerror("Database Error", f"Failed to load statistics:\n{str(e)}")

    def edit_item_by_id(self, item_id):
        """Edit item by its ID"""
        try:
            query = "SELECT ItemID, Name, Description, Price, item_data FROM Items WHERE ItemID = ?"
            self.cursor.execute(query, (item_id,))
            item = self.cursor.fetchone()

            if item:
                self.edit_item_dialog(item)
            else:
                messagebox.showerror("Error", "Item not found in database")

        except pyodbc.Error as e:
            messagebox.showerror("Database Error", f"Failed to load item:\n{str(e)}")

    def refresh_shop(self):
        """Refresh the shop display"""
        self.load_items()

    def on_close(self):
        """Handle window closing"""
        if messagebox.askyesno("Log Out", "Are you sure you want to log out and close the application?"):
            self.root.destroy()
            sys.exit(0)  # Close the application completely


def open_theme_shop(lecturer_id):
    """Function to open the theme shop management interface"""
    root = tk.Tk()
    app = ThemeShop(root, lecturer_id)
    root.mainloop()


if __name__ == "__main__":  # Fixed: Changed _main_ to __main__
    if len(sys.argv) > 1:
        open_theme_shop(sys.argv[1])
    else:
        open_theme_shop('LT0001')