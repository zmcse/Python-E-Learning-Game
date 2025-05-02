import tkinter as tk
from PIL import Image, ImageTk
import os
import subprocess
import sys
from tkinter import messagebox
from UserData import get_user_details, get_user, set_user


def create_navbar(root, lecturer_id):
    """Creates and returns a navigation bar frame."""
    # Ensure lecturer_id is set in UserData
    if lecturer_id:
        set_user(lecturer_id)
    else:
        lecturer_id = get_user()

    nav_bar = tk.Frame(root, bg="#004080", height=160)
    nav_bar.pack(side="top", fill="x")
    nav_bar.pack_propagate(False)  # Prevent resizing

    try:
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the path to the logo image
        logo_path = os.path.join(current_dir, "images", "logo.png")

        logo_image = Image.open(logo_path)
        logo_image = logo_image.resize((200, 150))  # Resize the logo

        # Store images inside `root` to prevent garbage collection
        root.logo_photo = ImageTk.PhotoImage(logo_image)

    except FileNotFoundError:
        print("Image file not found")
        return nav_bar  # Return the navigation bar even if the image is missing

    # Add logo without click functionality
    logo_label = tk.Label(nav_bar, image=root.logo_photo, bg="#004080")
    logo_label.pack(side="left", padx=30, pady=20)

    def go_to_lecturer_home():
        try:
            root.destroy()
            subprocess.run([sys.executable, "Content_Management_Main_page.py", str(lecturer_id)])
        except Exception as e:
            print(f"Error navigating to lecturer home: {e}")
            messagebox.showerror("Error", "Failed to navigate to lecturer home page")

    def go_to_content_management():
        try:
            root.destroy()
            subprocess.run([sys.executable, "Content_Management_Main_page.py", str(lecturer_id)])
        except Exception as e:
            print(f"Error navigating to content management: {e}")
            messagebox.showerror("Error", "Failed to navigate to content management page")

    def on_hover(event, label):
        label.config(fg="black")

    def on_leave(event, label):
        label.config(fg="white")

    content_label = tk.Label(nav_bar, text="Content Management", fg="white", bg="#004080", font=("Arial", 12, "bold"),
                             cursor="hand2")
    content_label.pack(side="left", padx=30, pady=20)
    content_label.bind("<Button-1>", lambda e: go_to_content_management())
    content_label.bind("<Enter>", lambda e: on_hover(e, content_label))
    content_label.bind("<Leave>", lambda e: on_leave(e, content_label))

    def open_student_analytics():
        try:
            if not lecturer_id:
                messagebox.showerror("Error", "No lecturer ID found. Please log in again.")
                return
            root.destroy()
            subprocess.run([sys.executable, "Student_Analytics.py", str(lecturer_id)])
        except Exception as e:
            print(f"Error opening student analytics: {e}")
            messagebox.showerror("Error", "Failed to open Student Analytics")

    student_analytics_label = tk.Label(nav_bar, text="Student Analytics", fg="white", bg="#004080",
                                       font=("Arial", 12, "bold"), cursor="hand2")
    student_analytics_label.pack(side="left", padx=30, pady=20)
    student_analytics_label.bind("<Button-1>", lambda e: open_student_analytics())
    student_analytics_label.bind("<Enter>", lambda e: on_hover(e, student_analytics_label))
    student_analytics_label.bind("<Leave>", lambda e: on_leave(e, student_analytics_label))

    def open_theme_shop():
        try:
            if not lecturer_id:
                messagebox.showerror("Error", "No lecturer ID found. Please log in again.")
                return
            root.destroy()
            subprocess.run([sys.executable, "Theme_Shop.py", str(lecturer_id)])
        except Exception as e:
            print(f"Error opening theme shop: {e}")
            messagebox.showerror("Error", "Failed to open Theme Shop")

    theme_shop_label = tk.Label(nav_bar, text="Theme Shop", fg="white", bg="#004080",
                                font=("Arial", 12, "bold"), cursor="hand2")
    theme_shop_label.pack(side="left", padx=30, pady=20)
    theme_shop_label.bind("<Button-1>", lambda e: open_theme_shop())
    theme_shop_label.bind("<Enter>", lambda e: on_hover(e, theme_shop_label))
    theme_shop_label.bind("<Leave>", lambda e: on_leave(e, theme_shop_label))

    # Profile section
    profile_frame = tk.Frame(nav_bar, bg="#004080")
    profile_frame.pack(side="right", padx=30, pady=20)
    print(f"Profile frame geometry: {profile_frame.winfo_geometry()}")  # Debug print

    # Get user details
    user_data = get_user_details()
    print(f"User data retrieved: {user_data}")
    if user_data:
        profile_name = user_data.get('Name', 'Unknown')
        profile_email = user_data.get('Email', 'No email')
    else:
        profile_name = "Unknown"
        profile_email = "No email"

    # Try to load profile photo
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        profile_icon_path = os.path.join(current_dir, "images", "capstoneProfileIcon.jpg")
        profile_icon = Image.open(profile_icon_path)
        profile_icon = profile_icon.resize((40, 40))
        root.profile_photo = ImageTk.PhotoImage(profile_icon)
        has_profile_photo = True
        print("Debug: Profile image loaded successfully")
    except FileNotFoundError:
        print("Debug: Profile icon not found")
        has_profile_photo = False

    # Profile button with name
    if has_profile_photo:
        profile_button = tk.Label(profile_frame, image=root.profile_photo, bg="#004080", cursor="hand2")
    else:
        profile_button = tk.Label(profile_frame, text=profile_name, fg="white", bg="#004080",
                                  font=("Arial", 12, "bold"), cursor="hand2")
    profile_button.pack(side="right")

    # Create dropdown menu (initially hidden)
    dropdown_menu = tk.Frame(root, bg="white", bd=1, relief="solid", width=300, height=100)
    dropdown_menu.pack_propagate(False)

    def show_profile_dropdown():
        # Get the position of the profile button
        x = profile_button.winfo_rootx() - 230
        y = profile_button.winfo_rooty() + profile_button.winfo_height() + 34

        # Create and pack profile info
        profile_info = tk.Frame(dropdown_menu, bg="white")
        profile_info.pack(fill="x", padx=5, pady=5)

        name_label = tk.Label(profile_info, text=profile_name, font=("Arial", 12, "bold"), bg="white")
        name_label.pack(anchor="w")

        email_label = tk.Label(profile_info, text=profile_email, font=("Arial", 10), bg="white")
        email_label.pack(anchor="w")

        # Create logout option
        logout_option = tk.Label(dropdown_menu, text="Logout", font=("Arial", 10), bg="white",
                                 cursor="hand2")
        logout_option.pack(fill="x", padx=5, pady=5)

        def on_logout_release(event):
            logout_user()

        logout_option.bind("<ButtonRelease-1>", on_logout_release)

        separator = tk.Frame(dropdown_menu, height=1, bg="#c0c0c0")
        separator.pack(fill="x", pady=2)

        dropdown_menu.place(x=x, y=y)
        dropdown_menu.lift()

    def hide_profile_dropdown(event=None):
        dropdown_menu.place_forget()

    def logout_user():
        hide_profile_dropdown()
        if messagebox.askyesno("Log Out", "Are you sure you want to log out and close the application?"):
            root.destroy()
            subprocess.run([sys.executable, "Login.py"])

    profile_button.bind("<Button-1>", lambda e: show_profile_dropdown())
    root.bind("<Button-1>",
              lambda e: hide_profile_dropdown() if not e.widget in [profile_button, dropdown_menu] else None)

    if has_profile_photo:
        profile_button.bind("<Enter>", lambda e: profile_button.config(bg="#005599"))
        profile_button.bind("<Leave>", lambda e: profile_button.config(bg="#004080"))
    else:
        profile_button.bind("<Enter>", lambda e: profile_button.config(fg="black"))
        profile_button.bind("<Leave>", lambda e: profile_button.config(fg="white"))

    return nav_bar  # Return the navigation bar
