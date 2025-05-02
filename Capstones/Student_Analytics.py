import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
from database_conn import connect_db  # Import the standardized connection function
import pyodbc
from datetime import datetime
from UserData import get_user
from Navigation_Bar import create_navbar  # Add navigation bar
import math


class StudentAnalytics:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Analytics")
        self.root.state('zoomed')

        # Get lecturer ID from command line arguments
        if len(sys.argv) > 1:
            self.lecturer_id = sys.argv[1]
        else:
            self.lecturer_id = get_user()

        if not self.lecturer_id:
            messagebox.showerror("Error", "No lecturer ID found. Please log in again.")
            self.root.destroy()
            return

        print(f"Student Analytics initialized with lecturer ID: {self.lecturer_id}")

        # Create navigation bar with lecturer ID
        create_navbar(self.root, self.lecturer_id)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._details_window = None

        # Initialize database connection
        self.conn = connect_db()  # Use the standardized connection function
        if not self.conn:
            messagebox.showerror("Database Error", "Failed to connect to database. Please check your connection.")
            self.root.destroy()
            return

        # Data setup
        self.levels = self.get_levels_from_db()
        if not self.levels:
            messagebox.showerror("Error", "No levels found in database")
            self.root.destroy()
            return

        self.players = self.fetch_player_data()
        if not self.players:
            messagebox.showerror("Error", "No player data found in database")
            self.root.destroy()
            return

        self.current_player = None

        # UI Setup
        self.create_sidebar()
        self.create_main_content()

        # Show default view
        self.show_player_overview()

    def on_close(self):
        """Handle window close event"""
        if messagebox.askyesno("Log Out", "Are you sure you want to log out and close the application?"):
            self.cleanup()
            try:
                self.root.quit()  # Stop mainloop first
                self.root.destroy()  # Then destroy windows
            except:
                pass
            sys.exit(0)  # Force exit

    def cleanup(self):
        """Clean up resources"""
        # Close all matplotlib figures
        plt.close('all')
        # Close database connections
        if hasattr(self, 'cursor'):
            try:
                self.cursor.close()
            except:
                pass
        if hasattr(self, 'conn'):
            try:
                self.conn.close()
            except:
                pass
        # Destroy any remaining child windows
        for child in self.root.winfo_children():
            if isinstance(child, tk.Toplevel):
                try:
                    child.destroy()
                except:
                    pass

    def close_details_window(self):
        """Properly close details window"""
        if hasattr(self, '_details_window'):
            self._details_window.destroy()
            del self._details_window

    def database_connect(self):
        """Connect to SQL Server database using the standardized connection"""
        return connect_db()  # Simply return the standardized connection

    def get_levels_from_db(self):
        """Fetch levels from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT LevelID, Name FROM Levels ORDER BY LevelID")
            return [f"{row.LevelID} - {row.Name}" for row in cursor.fetchall()]
        except pyodbc.Error as e:
            print("Error fetching levels:", e)
            return []

    def fetch_player_data(self):
        """Fetch player data from database"""
        players = []
        try:
            # Fetch basic player info
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    TP_Number, 
                    Name, 
                    Email,
                    Score,
                    current_level
                FROM Students
            """)

            for row in cursor.fetchall():
                player = {
                    "id": row.TP_Number,
                    "name": row.Name,
                    "email": row.Email,
                    "points": row.Score if row.Score is not None else 0,
                    "current_level": row.current_level if row.current_level is not None else 1,
                    "progress": {},
                    "attempts": {},
                    "performance": {}
                }

                # Initialize level data
                for level in self.levels:
                    player["progress"][level] = 0
                    player["attempts"][level] = 0
                    player["performance"][level] = {
                        "correct": 0,
                        "total": 0,
                        "time_spent": "0 mins"
                    }

                players.append(player)

            # Fetch progress data if we have players
            if players:
                cursor.execute("""
                    SELECT 
                        s.TP_Number, 
                        q.LevelID, 
                        COUNT(*) AS Attempts,
                        SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS Correct
                    FROM Submissions s
                    JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                    GROUP BY s.TP_Number, q.LevelID
                """)

                for row in cursor.fetchall():
                    level = f"Level {row.LevelID} - {next((l.split(' - ')[1] for l in self.levels if l.startswith(f'Level {row.LevelID}')), '')}"
                    student_id = row.TP_Number

                    # Find the player
                    player = next((p for p in players if p["id"] == student_id), None)
                    if player:
                        # Calculate progress (assuming 5 questions per level based on sample data)
                        progress = min(100, (row.Correct / 5) * 100) if row.Attempts > 0 else 0

                        player["progress"][level] = progress
                        player["attempts"][level] = row.Attempts
                        player["performance"][level] = {
                            "correct": row.Correct,
                            "total": row.Attempts,
                            "time_spent": "0 mins"
                        }

            return players

        except pyodbc.Error as e:
            print("Error fetching player data:", e)
            return []

    def create_header(self):
        """Create the header section with logo"""
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(side="top", fill="x")

        # Game title
        title_label = tk.Label(
            header_frame,
            text="Player Performance Dashboard",
            font=("Arial", 20, "bold"),
            bg="#2c3e50",
            fg="white",
            anchor="w",
            padx=30
        )
        title_label.pack(side="left", fill="x", expand=True)

    def create_sidebar(self):
        """Create the sidebar navigation"""
        sidebar_frame = tk.Frame(self.root, bg="#34495e", width=200)
        sidebar_frame.pack(side="left", fill="y")

        # Menu title
        menu_title = tk.Label(
            sidebar_frame,
            text="Menu",
            font=("Arial", 15, "bold"),
            bg="#34495e",
            fg="white"
        )
        menu_title.pack(fill="x", pady=10)

        # Menu buttons
        buttons = [
            ("Player Overview", self.show_player_overview),
            ("Level Analytics", self.show_level_analytics),
            ("Progress Tracking", self.show_progress_tracking),
            ("Performance Reports", self.show_performance_reports),
            ("Student Inventory", self.show_inventory_system)
        ]

        for text, command in buttons:
            btn = tk.Button(
                sidebar_frame,
                text=text,
                font=("Arial", 12),
                bg="#34495e",
                fg="white",
                bd=0,
                padx=20,
                pady=10,
                anchor="w",
                command=command
            )
            btn.pack(fill="x")

            # Create proper event handler functions
            def on_enter(event, button=btn):
                button.config(bg="#2c3e50")

            def on_leave(event, button=btn):
                button.config(bg="#34495e")

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def create_main_content(self):
        """Create the main content area"""
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def clear_main_frame(self):
        """Clear the main content frame"""
        # First destroy any matplotlib figures
        for widget in self.main_frame.winfo_children():
            if hasattr(widget, 'get_tk_widget'):  # Matplotlib canvas
                try:
                    widget.get_tk_widget().destroy()
                except:
                    pass
            widget.destroy()
        plt.close('all')  # Close any remaining figures

    def show_player_overview(self):
        """Show player overview dashboard"""
        self.clear_main_frame()

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="Player Overview",
            font=("Arial", 20, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)

        # Search frame
        search_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        search_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(search_frame, text="Search Player:", bg="#f0f0f0").pack(side="left")
        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        search_btn = tk.Button(search_frame, text="Search", command=self.search_players)
        search_btn.pack(side="left", padx=5)

        # Player stats frame
        stats_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        stats_frame.pack(fill="x", pady=10, padx=20)

        # Calculate overall stats with zero division protection
        total_players = len(self.players)
        avg_points = sum(p["points"] for p in self.players) / total_players if total_players > 0 else 0
        avg_progress = sum(sum(p["progress"].values()) for p in self.players) / (
                    total_players * len(self.levels)) if total_players > 0 else 0
        active_players = len([p for p in self.players if p["points"] > 100])

        # Stat cards
        stats = [
            ("Total Players", total_players, "#3498db"),
            ("Avg Points", f"{avg_points:.1f}", "#2ecc71"),
            ("Avg Progress", f"{avg_progress:.1f}%", "#e74c3c"),
            ("Active Players", active_players, "#f39c12")
        ]

        for i, (title, value, color) in enumerate(stats):
            card = tk.Frame(stats_frame, bg=color, bd=2, relief=tk.RIDGE)
            card.grid(row=0, column=i, padx=5, ipadx=10, ipady=5, sticky="nsew")

            tk.Label(card, text=title, font=("Arial", 12, "bold"),
                     bg=color, fg="white").pack()
            tk.Label(card, text=value, font=("Arial", 14, "bold"),
                     bg=color, fg="white").pack()

        # Player table
        tree_frame = tk.Frame(self.main_frame)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        scroll_y = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scroll_y.pack(side="right", fill="y")

        self.player_tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Points", "Current Level", "Progress"),
            show="headings",
            yscrollcommand=scroll_y.set
        )

        # Configure columns
        self.player_tree.heading("ID", text="ID")
        self.player_tree.heading("Name", text="Name")
        self.player_tree.heading("Points", text="Points")
        self.player_tree.heading("Current Level", text="Current Level")
        self.player_tree.heading("Progress", text="Overall Progress")

        self.player_tree.column("ID", width=80, anchor="center")
        self.player_tree.column("Name", width=150, anchor="w")
        self.player_tree.column("Points", width=80, anchor="center")
        self.player_tree.column("Current Level", width=80, anchor="center")
        self.player_tree.column("Progress", width=120, anchor="center")

        self.player_tree.pack(fill="both", expand=True)
        scroll_y.config(command=self.player_tree.yview)

        # Populate table
        self.populate_player_tree()

        # View details button
        details_btn = tk.Button(
            self.main_frame,
            text="View Player Details",
            command=self.view_player_details,
            font=("Arial", 12),
            bg="#3498db",
            fg="white"
        )
        details_btn.pack(pady=10)

    def populate_player_tree(self, players=None):
        """Populate the player treeview"""
        for item in self.player_tree.get_children():
            self.player_tree.delete(item)

        players = players or self.players
        for player in players:
            avg_progress = sum(player["progress"].values()) / len(self.levels) if len(self.levels) > 0 else 0
            self.player_tree.insert("", tk.END, values=(
                player["id"],
                player["name"],
                player["points"],
                player["current_level"],
                f"{avg_progress:.1f}%"
            ))

    def search_players(self):
        """Search players based on search term"""
        query = self.search_entry.get().lower()
        if not query:
            self.populate_player_tree()
            return

        filtered = [
            p for p in self.players
            if query in str(p["id"]).lower()
               or query in p["name"].lower()
        ]
        self.populate_player_tree(filtered)

    def view_player_details(self):
        """Show detailed view of selected player"""
        selected = self.player_tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a player first")
            return

        item = self.player_tree.item(selected)
        player_id = item["values"][0]

        try:
            cursor = self.conn.cursor()

            # Fetch basic player info
            cursor.execute("""
                SELECT 
                    TP_Number, 
                    Name, 
                    Email,
                    Score,
                    current_level
                FROM Students
                WHERE TP_Number = ?
            """, player_id)
            player_data = cursor.fetchone()

            if not player_data:
                messagebox.showerror("Error", "Player not found")
                return

            # Fetch level progress
            cursor.execute("""
                SELECT 
                    ls.LevelID,
                    l.Name AS LevelName,
                    ls.is_locked,
                    ls.is_completed,
                    ls.time_remaining
                FROM LevelSelection ls
                JOIN Levels l ON ls.LevelID = l.LevelID
                WHERE ls.TP_Number = ?
                ORDER BY ls.LevelID
            """, player_id)
            level_progress = cursor.fetchall()

            # Fetch performance statistics
            cursor.execute("""
                SELECT 
                    q.LevelID,
                    l.Name AS LevelName,
                    SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS correct_attempts
                FROM Submissions s
                JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                JOIN Levels l ON q.LevelID = l.LevelID
                WHERE s.TP_Number = ?
                GROUP BY q.LevelID, l.Name
                ORDER BY q.LevelID
            """, player_id)
            performance_stats = cursor.fetchall()

            # Create details window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"Player Details - {player_data.Name}")
            details_window.geometry("800x600")
            details_window.protocol("WM_DELETE_WINDOW", self.close_details_window)

            # Store reference to avoid garbage collection
            self._details_window = details_window

            # Player info frame
            info_frame = tk.Frame(details_window, padx=10, pady=10)
            info_frame.pack(fill="x")

            tk.Label(info_frame, text=f"ID: {player_data.TP_Number}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(info_frame, text=f"Name: {player_data.Name}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(info_frame, text=f"Email: {player_data.Email}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(info_frame, text=f"Score: {player_data.Score}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(info_frame, text=f"Current Level: {player_data.current_level}", font=("Arial", 12)).pack(anchor="w")

            # Progress frame
            progress_frame = tk.LabelFrame(details_window, text="Level Progress", font=("Arial", 12, "bold"))
            progress_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Create progress bars for each level
            for i, level in enumerate(level_progress):
                level_name = f"{level.LevelID} - {level.LevelName}"
                status = "Completed" if level.is_completed else "Locked" if level.is_locked else "In Progress"
                time_spent = f"{int((600 - level.time_remaining) / 60)}m {int((600 - level.time_remaining) % 60)}s" if level.time_remaining is not None else "N/A"

                tk.Label(progress_frame, text=level_name, width=20, anchor="w").grid(row=i, column=0, padx=5, pady=2, sticky="w")
                tk.Label(progress_frame, text=status, width=15, anchor="w").grid(row=i, column=1, padx=5, pady=2, sticky="w")
                tk.Label(progress_frame, text=f"Time: {time_spent}", width=15, anchor="w").grid(row=i, column=2, padx=5, pady=2, sticky="w")

            # Performance stats
            stats_frame = tk.LabelFrame(details_window, text="Performance Statistics", font=("Arial", 12, "bold"))
            stats_frame.pack(fill="x", padx=10, pady=10)

            # Headers
            tk.Label(stats_frame, text="Level", width=20, anchor="w", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=2, sticky="w")
            tk.Label(stats_frame, text="Correct Answers", width=15, anchor="w", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky="w")

            # Performance data
            for i, stat in enumerate(performance_stats, start=1):
                level_name = f"{stat.LevelID} - {stat.LevelName}"

                tk.Label(stats_frame, text=level_name, width=20, anchor="w").grid(row=i, column=0, padx=5, pady=2, sticky="w")
                tk.Label(stats_frame, text=str(stat.correct_attempts), width=15, anchor="w").grid(row=i, column=1, padx=5, pady=2, sticky="w")

        except pyodbc.Error as e:
            messagebox.showerror("Database Error", f"Error fetching player details: {str(e)}")

    def show_level_analytics(self):
        """Show level analytics dashboard"""
        self.clear_main_frame()

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="Level Analytics",
            font=("Arial", 20, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)

        # Level selection
        level_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        level_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(level_frame, text="Select Level:", bg="#f0f0f0").pack(side="left")
        self.level_var = tk.StringVar()
        level_dropdown = ttk.Combobox(level_frame, textvariable=self.level_var, values=self.levels, width=30)
        level_dropdown.pack(side="left", padx=5)
        level_dropdown.current(0)
        level_btn = tk.Button(level_frame, text="Show Analytics", command=self.update_level_analytics)
        level_btn.pack(side="left", padx=5)

        # Create frame for charts
        self.chart_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Show initial analytics
        self.update_level_analytics()

    def update_level_analytics(self):
        """Update the level analytics charts based on selected level"""
        # Clear previous charts
        plt.close('all')
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        selected_level = self.level_var.get()
        if not selected_level:
            return

        try:
            print(f"Debug - Selected level string: '{selected_level}'")

            # First try to get the actual LevelID from your data structure
            level_id = self.get_level_id_from_selection(selected_level)

            if level_id is None:
                raise ValueError(f"No LevelID found for selection: '{selected_level}'")

            print(f"Debug - Using LevelID: {level_id} (Type: {type(level_id)})")

            # Fetch level analytics data from database
            cursor = self.conn.cursor()

            # Parameterized query - let the database handle type conversion
            cursor.execute("""
                SELECT 
                    s.TP_Number,
                    COUNT(*) AS total_attempts,
                    SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS correct_attempts
                FROM Submissions s
                JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                WHERE q.LevelID = ?
                GROUP BY s.TP_Number
            """, (level_id,))

            progress_data = cursor.fetchall()

            # Calculate progress percentages
            progress_values = []
            for row in progress_data:
                try:
                    progress = (row.correct_attempts / 5) * 100  # 5 questions per level
                    progress_values.append(min(100, progress))
                except TypeError:
                    print(f"Warning: Invalid data for TP_Number {row.TP_Number}")
                    continue

            # Attempts distribution query
            cursor.execute("""
                SELECT 
                    s.TP_Number,
                    COUNT(*) AS attempt_count
                FROM Submissions s
                JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                WHERE q.LevelID = ?
                GROUP BY s.TP_Number
            """, (level_id,))

            attempts_data = cursor.fetchall()
            attempt_counts = [row.attempt_count for row in attempts_data if row.attempt_count is not None]

            # Create and display charts
            self.display_analytics_charts(selected_level, progress_values, attempt_counts)

        except pyodbc.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error processing analytics: {str(e)}")

    def get_level_id_from_selection(self, selected_level):
        """Helper method to get LevelID from selection"""
        # Option 1: If you have a mapping dictionary
        if hasattr(self, 'level_mapping'):
            return self.level_mapping.get(selected_level)

        # Option 2: Extract from string pattern (e.g., "LVL001 - Basics")
        try:
            import re
            match = re.match(r'(LVL\d+)', selected_level.split('-')[0].strip())
            if match:
                return match.group(1)  # Returns 'LVL001'
        except:
            pass

        # Option 3: Try to extract numeric ID
        try:
            return int(re.search(r'\d+', selected_level).group())
        except:
            pass

        return None

    def display_analytics_charts(self, title, progress_values, attempt_counts):
        """Display the analytics charts with enhanced visuals"""
        # Create figure with modern styling
        plt.style.use('default')  # Reset to default for clean slate
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Set figure background to match your UI
        fig.patch.set_facecolor('#f0f0f0')

        # Main title
        fig.suptitle(f"Analytics for {title}",
                     fontsize=16,
                     fontweight='bold',
                     color='#333333',
                     y=0.97)

        # Progress distribution chart
        if progress_values:
            bars = ax1.hist(progress_values,
                            bins=10,
                            range=(0, 100),
                            color='#4285F4',  # Google blue
                            edgecolor='white',
                            linewidth=1.5,
                            alpha=0.9)

            # Add subtle data labels on top bars
            for rect in bars[2]:
                height = rect.get_height()
                if height > 0:
                    ax1.text(rect.get_x() + rect.get_width() / 2., height,
                             f'{int(height)}',
                             ha='center', va='bottom',
                             fontsize=9, color='#333333')

            ax1.set_title("Progress Distribution",
                          pad=12,
                          fontweight='semibold',
                          color='#333333')
            ax1.set_xlabel("Progress (%)",
                           labelpad=8,
                           fontweight='normal')
            ax1.set_ylabel("Number of Players",
                           labelpad=8,
                           fontweight='normal')
            ax1.grid(axis='y',
                     linestyle=':',
                     alpha=0.7)
            ax1.set_facecolor('#f9f9f9')
        else:
            ax1.text(0.5, 0.5, "No progress data available",
                     ha='center', va='center',
                     fontsize=12,
                     color='#666666')
            ax1.set_title("Progress Distribution",
                          pad=12,
                          fontweight='semibold',
                          color='#333333')

        # Attempts distribution chart
        if attempt_counts:
            max_attempts = max(attempt_counts) if attempt_counts else 1
            bars = ax2.hist(attempt_counts,
                            bins=range(0, max_attempts + 2),
                            color='#34A853',  # Google green
                            edgecolor='white',
                            linewidth=1.5,
                            alpha=0.9)

            # Add subtle data labels on top bars
            for rect in bars[2]:
                height = rect.get_height()
                if height > 0:
                    ax2.text(rect.get_x() + rect.get_width() / 2., height,
                             f'{int(height)}',
                             ha='center', va='bottom',
                             fontsize=9, color='#333333')

            ax2.set_title("Attempts Distribution",
                          pad=12,
                          fontweight='semibold',
                          color='#333333')
            ax2.set_xlabel("Number of Attempts",
                           labelpad=8,
                           fontweight='normal')
            ax2.set_ylabel("Number of Players",
                           labelpad=8,
                           fontweight='normal')
            ax2.grid(axis='y',
                     linestyle=':',
                     alpha=0.7)
            ax2.set_facecolor('#f9f9f9')
        else:
            ax2.text(0.5, 0.5, "No attempts data available",
                     ha='center', va='center',
                     fontsize=12,
                     color='#666666')
            ax2.set_title("Attempts Distribution",
                          pad=12,
                          fontweight='semibold',
                          color='#333333')

        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.85)  # Adjust title spacing

        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def show_error(self, message):
        """Display error message in UI"""
        print(message)
        error_label = tk.Label(
            self.chart_frame,
            text=message,
            font=("Arial", 12),
            fg="red",
            wraplength=400
        )
        error_label.pack(pady=50)

    def show_progress_tracking(self):
        """Show progress tracking view with timeline of player progress"""
        self.clear_main_frame()

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="Progress Tracking",
            font=("Arial", 20, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)

        # Player selection
        player_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        player_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(player_frame, text="Select Player:", bg="#f0f0f0").pack(side="left")
        self.progress_player_var = tk.StringVar()
        player_dropdown = ttk.Combobox(
            player_frame,
            textvariable=self.progress_player_var,
            values=[f"{p['id']} - {p['name']}" for p in self.players],
            width=30
        )
        player_dropdown.pack(side="left", padx=5)
        if self.players:
            player_dropdown.current(0)
        player_btn = tk.Button(player_frame, text="Show Progress", command=self.update_progress_tracking)
        player_btn.pack(side="left", padx=5)

        # Create frame for progress chart
        self.progress_chart_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.progress_chart_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Show initial progress if players exist
        if self.players:
            self.update_progress_tracking()

    def update_progress_tracking(self):
        """Update the progress tracking chart"""
        # Clear previous chart
        plt.close('all')
        for widget in self.progress_chart_frame.winfo_children():
            widget.destroy()

        selected_player = self.progress_player_var.get()
        if not selected_player:
            return

        # Get player ID from selection
        player_id = selected_player.split()[0]

        try:
            cursor = self.conn.cursor()

            # Get all submissions for this player with timestamps (using current time as proxy)
            cursor.execute("""
                    SELECT 
                        q.LevelID,
                        l.Name AS LevelName,
                        COUNT(*) AS total_questions,
                        SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS correct_answers
                    FROM Submissions s
                    JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                    JOIN Levels l ON q.LevelID = l.LevelID
                    WHERE s.TP_Number = ?
                    GROUP BY q.LevelID, l.Name
                    ORDER BY q.LevelID
                """, player_id)

            progress_data = cursor.fetchall()

            if not progress_data:
                tk.Label(self.progress_chart_frame, text="No progress data available for this player",
                         font=("Arial", 12)).pack(pady=50)
                return

            # Prepare data for chart
            levels = [f"{row.LevelID} - {row.LevelName}" for row in progress_data]
            completion = [(row.correct_answers / row.total_questions * 100) if row.total_questions > 0 else 0 for row in
                          progress_data]

            # Create progress chart
            fig, ax = plt.subplots(figsize=(10, 6))

            # Bar chart for level completion
            bars = ax.bar(levels, completion, color='#3498db')

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom')

            ax.set_title(f"Progress by Level for {selected_player}")
            ax.set_xlabel("Level")
            ax.set_ylabel("Completion (%)")
            ax.set_ylim(0, 110)

            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45, ha='right')

            # Adjust layout
            plt.tight_layout()

            # Display chart in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.progress_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except pyodbc.Error as e:
            print(f"Error fetching progress data for player {player_id}:", e)
            tk.Label(self.progress_chart_frame, text="Error loading progress data", font=("Arial", 12)).pack(pady=50)

    def show_performance_reports(self):
        """Show performance reports with detailed statistics"""
        plt.close('all')
        self.clear_main_frame()

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="Performance Reports",
            font=("Arial", 20, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)

        # Create notebook for different report tabs
        report_notebook = ttk.Notebook(self.main_frame)
        report_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        tabs = {
            "Overall Performance": self.create_overall_performance_tab,
            "Level-wise Performance": self.create_level_performance_tab,
            "Player Comparison": self.create_player_comparison_tab
        }

        # Initialize tabs
        for tab_name, tab_func in tabs.items():
            tab_frame = ttk.Frame(report_notebook)
            report_notebook.add(tab_frame, text=tab_name)
            tab_func(tab_frame)

    def create_overall_performance_tab(self, tab):
        """Create content for overall performance tab"""
        try:
            with self.conn.cursor() as cursor:
                # Get overall statistics
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT TP_Number) AS total_players,
                        AVG(Score) AS avg_score,
                        MAX(Score) AS max_score,
                        MIN(Score) AS min_score
                    FROM Students
                """)
                overall_stats = cursor.fetchone()

                # Get level completion rates
                cursor.execute("""
                    SELECT 
                        l.LevelID,
                        l.Name,
                        COUNT(DISTINCT ls.TP_Number) AS players_completed,
                        (SELECT COUNT(DISTINCT TP_Number) FROM Students) AS total_players
                    FROM LevelSelection ls
                    JOIN Levels l ON ls.LevelID = l.LevelID
                    WHERE ls.is_completed = 1
                    GROUP BY l.LevelID, l.Name
                    ORDER BY l.LevelID
                """)
                level_completion = cursor.fetchall()

            # Create frames for content
            stats_frame = tk.Frame(tab, bg="#f0f0f0")
            stats_frame.pack(fill="x", padx=10, pady=10)

            chart_frame = tk.Frame(tab, bg="#f0f0f0")
            chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Display overall statistics
            tk.Label(stats_frame, text="Overall Performance Statistics",
                     font=("Arial", 14, "bold"), bg="#f0f0f0").pack(anchor="w")

            stats_text = f"""
                Total Players: {overall_stats.total_players}
                Average Score: {overall_stats.avg_score:.1f}
                Highest Score: {overall_stats.max_score}
                Lowest Score: {overall_stats.min_score}
                """
            tk.Label(stats_frame, text=stats_text, justify="left",
                     font=("Arial", 12), bg="#f0f0f0").pack(anchor="w", pady=10)

            # Create level completion chart
            if level_completion:
                levels = [f"{row.LevelID} - {row.Name}" for row in level_completion]
                completion_rates = [(row.players_completed / row.total_players * 100)
                                    for row in level_completion]

                # Create figure with adjusted subplot parameters
                fig, ax = plt.subplots(figsize=(10, 5), facecolor="#f0f0f0")

                # Adjust the bottom margin to make room for the xlabel
                fig.subplots_adjust(bottom=0.15)  # You can adjust this value as needed

                bars = ax.barh(levels, completion_rates, color='#2ecc71')

                ax.set_title("Level Completion Rates", pad=10)
                ax.set_xlabel("Completion Rate (%)")
                ax.set_xlim(0, 100)
                ax.set_facecolor("#f0f0f0")

                # Add value labels
                for bar in bars:
                    width = bar.get_width()
                    ax.text(width + 1, bar.get_y() + bar.get_height() / 2.,
                            f'{width:.1f}%',
                            va='center')

                canvas = FigureCanvasTkAgg(fig, master=chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
            else:
                tk.Label(chart_frame, text="No level completion data available",
                         font=("Arial", 12), bg="#f0f0f0").pack(pady=50)

        except Exception as e:
            print("Error in overall performance tab:", e)
            tk.Label(tab, text="Error loading performance data",
                     font=("Arial", 12), bg="#f0f0f0").pack(pady=50)

    def create_level_performance_tab(self, tab):
        """Create content for level performance tab"""
        try:
            with self.conn.cursor() as cursor:
                # Get level performance statistics
                cursor.execute("""
                    SELECT 
                        q.LevelID,
                        l.Name AS LevelName,
                        COUNT(DISTINCT s.TP_Number) AS players_attempted,
                        COUNT(*) AS total_attempts,
                        SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS correct_attempts,
                        AVG(CAST(ls.time_remaining AS FLOAT)) AS avg_time_remaining
                    FROM Submissions s
                    JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                    JOIN Levels l ON q.LevelID = l.LevelID
                    LEFT JOIN LevelSelection ls ON s.TP_Number = ls.TP_Number AND ls.LevelID = q.LevelID
                    GROUP BY q.LevelID, l.Name
                    ORDER BY q.LevelID
                """)
                level_performance = cursor.fetchall()

            # Create frame for stats table
            stats_frame = tk.Frame(tab, bg="#f0f0f0")
            stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

            tk.Label(stats_frame, text="Level Performance Statistics",
                     font=("Arial", 14, "bold"), bg="#f0f0f0").pack(anchor="w")

            if level_performance:
                # Create table for level stats
                columns = ("Level", "Players Attempted", "Total Attempts", "Accuracy", "Avg Time Spent")
                tree = ttk.Treeview(stats_frame, columns=columns, show="headings", height=10)

                for col in columns:
                    tree.heading(col, text=col)
                    tree.column(col, width=140, anchor="center")

                for row in level_performance:
                    accuracy = (row.correct_attempts / row.total_attempts * 100) if row.total_attempts > 0 else 0
                    avg_time_remaining = row.avg_time_remaining if row.avg_time_remaining is not None else 600
                    avg_time_spent = 600 - avg_time_remaining

                    tree.insert("", tk.END, values=(
                        f"{row.LevelID} - {row.LevelName}",
                        row.players_attempted,
                        row.total_attempts,
                        f"{accuracy:.1f}%",
                        f"{int(avg_time_spent // 60)}m {int(avg_time_spent % 60)}s"
                    ))

                # Add scrollbar
                scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                scrollbar.pack(side="right", fill="y")
                tree.pack(fill="both", expand=True, pady=10)
            else:
                tk.Label(stats_frame, text="No level performance data available",
                         font=("Arial", 12), bg="#f0f0f0").pack(pady=50)

        except Exception as e:
            print("Error in level performance tab:", e)
            tk.Label(tab, text="Error loading level performance data",
                     font=("Arial", 12), bg="#f0f0f0").pack(pady=50)

    def create_player_comparison_tab(self, tab):
        """Create content for player comparison tab"""
        # Main container
        main_container = tk.Frame(tab, bg="#f0f0f0")
        main_container.pack(fill="both", expand=True)

        # Player selection frame
        selection_frame = tk.Frame(main_container, bg="#f0f0f0", padx=10, pady=10)
        selection_frame.pack(fill="x")

        # Title
        tk.Label(selection_frame, text="Compare Player Performance",
                 font=("Arial", 14, "bold"), bg="#f0f0f0").grid(row=0, column=0, columnspan=4, pady=(0, 10), sticky="w")

        # Player selection dropdowns
        player_options = [f"{p['id']} - {p['name']}" for p in self.players] if self.players else []

        tk.Label(selection_frame, text="Player 1:", bg="#f0f0f0").grid(row=1, column=0, sticky="e")
        self.compare_player1_var = tk.StringVar()
        player1_dropdown = ttk.Combobox(
            selection_frame,
            textvariable=self.compare_player1_var,
            values=player_options,
            width=30,
            state="readonly"
        )
        player1_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        if player_options:
            player1_dropdown.current(0)

        tk.Label(selection_frame, text="Player 2:", bg="#f0f0f0").grid(row=1, column=2, sticky="e")
        self.compare_player2_var = tk.StringVar()
        player2_dropdown = ttk.Combobox(
            selection_frame,
            textvariable=self.compare_player2_var,
            values=player_options,
            width=30,
            state="readonly"
        )
        player2_dropdown.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        if len(player_options) > 1:
            player2_dropdown.current(1)

        # Compare button
        compare_btn = tk.Button(
            selection_frame,
            text="Compare Players",
            command=self.update_player_comparison,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        compare_btn.grid(row=2, column=0, columnspan=4, pady=10)

        # Create scrollable canvas for comparison results - CHANGE HERE
        self.comparison_canvas = tk.Canvas(main_container, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.comparison_canvas.yview)
        self.comparison_content_frame = tk.Frame(self.comparison_canvas, bg="#f0f0f0")

        def update_scrollregion(event):
            self.comparison_canvas.configure(scrollregion=self.comparison_canvas.bbox("all"))

        self.comparison_content_frame.bind("<Configure>", update_scrollregion)

        self.comparison_canvas.create_window((0, 0), window=self.comparison_content_frame, anchor="nw")
        self.comparison_canvas.configure(yscrollcommand=scrollbar.set)

        self.comparison_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Show initial comparison if players exist
        if self.players and len(self.players) > 1:
            self.update_player_comparison()

    def update_player_comparison(self):
        """Update the player comparison with current selections"""
        # Clear previous content
        for widget in self.comparison_content_frame.winfo_children():
            widget.destroy()

        # Get player selections
        player1 = self.compare_player1_var.get()
        player2 = self.compare_player2_var.get()

        # Validate selections
        if not player1 or not player2:
            tk.Label(self.comparison_content_frame,
                     text="Please select two players to compare",
                     font=("Arial", 12), bg="#f0f0f0").pack(pady=50)
            return

        if player1 == player2:
            tk.Label(self.comparison_content_frame,
                     text="Please select two different players",
                     font=("Arial", 12), bg="#f0f0f0").pack(pady=50)
            return

        try:
            # Extract player IDs and names
            player1_id, player1_name = player1.split(" - ", 1)
            player2_id, player2_name = player2.split(" - ", 1)

            with self.conn.cursor() as cursor:
                # Get player comparison data
                query = """
                SELECT 
                    s.TP_Number,
                    s.Name,
                    s.Score,
                    s.current_level,
                    COUNT(DISTINCT ls.LevelID) AS levels_completed,
                    (SELECT COUNT(DISTINCT LevelID) FROM Levels) AS total_levels,
                    (SELECT COUNT(*) FROM Submissions sub 
                     WHERE sub.TP_Number = s.TP_Number AND sub.status = 1) AS correct_answers,
                    (SELECT COUNT(*) FROM Submissions sub 
                     WHERE sub.TP_Number = s.TP_Number) AS total_answers,
                    (SELECT AVG(600 - ls2.time_remaining) 
                     FROM LevelSelection ls2 
                     WHERE ls2.TP_Number = s.TP_Number) AS avg_time_spent
                FROM Students s
                LEFT JOIN LevelSelection ls ON s.TP_Number = ls.TP_Number AND ls.is_completed = 1
                WHERE s.TP_Number IN (?, ?)
                GROUP BY s.TP_Number, s.Name, s.Score, s.current_level
                """
                cursor.execute(query, (player1_id, player2_id))
                players_data = {row.TP_Number: row for row in cursor.fetchall()}

                if len(players_data) != 2:
                    raise ValueError("Could not retrieve data for both players")

                # Get level-wise performance data
                level_query = """
                SELECT 
                    s.TP_Number,
                    q.LevelID,
                    l.Name AS LevelName,
                    COUNT(*) AS total_attempts,
                    SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS correct_attempts,
                    ls.time_remaining
                FROM Submissions s
                JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                JOIN Levels l ON q.LevelID = l.LevelID
                LEFT JOIN LevelSelection ls ON s.TP_Number = ls.TP_Number AND ls.LevelID = q.LevelID
                WHERE s.TP_Number IN (?, ?)
                GROUP BY s.TP_Number, q.LevelID, l.Name, ls.time_remaining
                ORDER BY q.LevelID
                """
                cursor.execute(level_query, (player1_id, player2_id))
                level_data = cursor.fetchall()

            # Organize level data
            player_levels = {player1_id: {}, player2_id: {}}
            for row in level_data:
                player_levels[row.TP_Number][row.LevelID] = {
                    'name': row.LevelName,
                    'total_attempts': row.total_attempts,
                    'correct_attempts': row.correct_attempts,
                    'time_remaining': row.time_remaining if row.time_remaining is not None else 600
                }

            # Get all levels for consistent comparison
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT LevelID, Name FROM Levels ORDER BY LevelID")
                all_levels = cursor.fetchall()

            # Display comparison header
            header_frame = tk.Frame(self.comparison_content_frame, bg="#f0f0f0", padx=10, pady=10)
            header_frame.pack(fill="x")

            tk.Label(header_frame, text="PLAYER PERFORMANCE COMPARISON",
                     font=("Arial", 14, "bold"), bg="#f0f0f0").pack()

            # Player info display
            info_frame = tk.Frame(header_frame, bg="#f0f0f0")
            info_frame.pack(pady=10)

            # Player 1 info
            p1_data = players_data[player1_id]
            p1_frame = tk.Frame(info_frame, bg="#f0f0f0")
            p1_frame.pack(side="left", padx=20)
            tk.Label(p1_frame, text=player1_name,
                     font=("Arial", 12, "bold"), fg="#3498db", bg="#f0f0f0").pack()
            tk.Label(p1_frame, text=f"Score: {p1_data.Score:,}", bg="#f0f0f0").pack(anchor="w")
            tk.Label(p1_frame, text=f"Current Level: {p1_data.current_level}", bg="#f0f0f0").pack(anchor="w")
            tk.Label(p1_frame, text=f"Levels Completed: {p1_data.levels_completed}/{p1_data.total_levels}",
                     bg="#f0f0f0").pack(anchor="w")

            # Player 2 info
            p2_data = players_data[player2_id]
            p2_frame = tk.Frame(info_frame, bg="#f0f0f0")
            p2_frame.pack(side="left", padx=20)
            tk.Label(p2_frame, text=player2_name,
                     font=("Arial", 12, "bold"), fg="#e74c3c", bg="#f0f0f0").pack()
            tk.Label(p2_frame, text=f"Score: {p2_data.Score:,}", bg="#f0f0f0").pack(anchor="w")
            tk.Label(p2_frame, text=f"Current Level: {p2_data.current_level}", bg="#f0f0f0").pack(anchor="w")
            tk.Label(p2_frame, text=f"Levels Completed: {p2_data.levels_completed}/{p2_data.total_levels}",
                     bg="#f0f0f0").pack(anchor="w")

            # Calculate metrics
            p1_accuracy = (p1_data.correct_answers / p1_data.total_answers * 100) if p1_data.total_answers > 0 else 0
            p2_accuracy = (p2_data.correct_answers / p2_data.total_answers * 100) if p2_data.total_answers > 0 else 0
            p1_avg_time = p1_data.avg_time_spent if p1_data.avg_time_spent is not None else 0
            p2_avg_time = p2_data.avg_time_spent if p2_data.avg_time_spent is not None else 0

            # Create metric cards
            metrics_frame = tk.Frame(header_frame, bg="#f0f0f0")
            metrics_frame.pack(fill="x", pady=10)

            metrics = [
                ("Overall Accuracy", f"{p1_accuracy:.1f}%", f"{p2_accuracy:.1f}%", "#2ecc71"),
                ("Avg Time/Level",
                 f"{int(p1_avg_time // 60)}m {int(p1_avg_time % 60)}s",
                 f"{int(p2_avg_time // 60)}m {int(p2_avg_time % 60)}s",
                 "#3498db"),
                ("Completion Rate",
                 f"{(p1_data.levels_completed / p1_data.total_levels) * 100:.1f}%",
                 f"{(p2_data.levels_completed / p2_data.total_levels) * 100:.1f}%",
                 "#f39c12")
            ]

            for i, (title, p1_val, p2_val, color) in enumerate(metrics):
                card = tk.Frame(metrics_frame, bg=color, bd=2, relief=tk.RIDGE, padx=10, pady=5)
                card.grid(row=0, column=i, padx=5, ipadx=5, ipady=5, sticky="nsew")

                tk.Label(card, text=title, font=("Arial", 10, "bold"),
                         bg=color, fg="white").pack()

                # Player 1 value
                p1_val_frame = tk.Frame(card, bg=color)
                p1_val_frame.pack(fill="x", pady=2)
                tk.Label(p1_val_frame, text="P1:", bg=color, fg="white").pack(side="left")
                tk.Label(p1_val_frame, text=p1_val, font=("Arial", 10, "bold"),
                         bg=color, fg="white").pack(side="left", padx=5)

                # Player 2 value
                p2_val_frame = tk.Frame(card, bg=color)
                p2_val_frame.pack(fill="x", pady=2)
                tk.Label(p2_val_frame, text="P2:", bg=color, fg="white").pack(side="left")
                tk.Label(p2_val_frame, text=p2_val, font=("Arial", 10, "bold"),
                         bg=color, fg="white").pack(side="left", padx=5)

            # Create charts if we have level data
            if all_levels:
                chart_frame = tk.Frame(self.comparison_content_frame, bg="#f0f0f0")
                chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Prepare data for charts
                levels = [f"Level {level.LevelID}\n{level.Name}" for level in all_levels]
                p1_acc, p2_acc = [], []
                p1_time, p2_time = [], []

                for level in all_levels:
                    # Player 1 data
                    p1_level = player_levels[player1_id].get(level.LevelID, {})
                    p1_total = p1_level.get('total_attempts', 0)
                    p1_acc.append((p1_level.get('correct_attempts', 0) / p1_total * 100) if p1_total > 0 else 0)
                    p1_time.append(600 - p1_level.get('time_remaining', 600))

                    # Player 2 data
                    p2_level = player_levels[player2_id].get(level.LevelID, {})
                    p2_total = p2_level.get('total_attempts', 0)
                    p2_acc.append((p2_level.get('correct_attempts', 0) / p2_total * 100) if p2_total > 0 else 0)
                    p2_time.append(600 - p2_level.get('time_remaining', 600))

                # Create figure with two subplots
                fig = plt.figure(figsize=(10, 8), facecolor="#f0f0f0")
                gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.4)

                # Accuracy comparison chart
                ax1 = fig.add_subplot(gs[0])
                self._create_comparison_chart(
                    ax1, levels, p1_acc, p2_acc,
                    "Accuracy Comparison", "Accuracy (%)",
                    player1_name, player2_name
                )

                # Time spent comparison chart
                ax2 = fig.add_subplot(gs[1])
                self._create_comparison_chart(
                    ax2, levels, p1_time, p2_time,
                    "Time Spent Comparison", "Time Spent (seconds)",
                    player1_name, player2_name,
                    is_time=True
                )

                # Embed chart in Tkinter
                canvas = FigureCanvasTkAgg(fig, master=chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)

            # Add footer
            footer = tk.Label(self.comparison_content_frame,
                              text=f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                              font=("Arial", 8),
                              fg="#95a5a6", bg="#f0f0f0")
            footer.pack(side="bottom", pady=5)

            # Reset scroll position
            self.comparison_canvas.yview_moveto(0)

        except Exception as e:
            print(f"Error in player comparison: {e}")
            tk.Label(self.comparison_content_frame,
                     text=f"Error generating comparison: {str(e)}",
                     font=("Arial", 12),
                     fg="red", bg="#f0f0f0").pack(pady=50)

    def _create_comparison_chart(self, ax, levels, p1_data, p2_data, title, ylabel, p1_name, p2_name, is_time=False):
        """Helper method to create consistent comparison charts"""
        x = range(len(levels))
        width = 0.35

        # Create bars
        p1_bars = ax.bar([i - width / 2 for i in x], p1_data, width,
                         label=p1_name, color="#3498db", alpha=0.8)
        p2_bars = ax.bar([i + width / 2 for i in x], p2_data, width,
                         label=p2_name, color="#e74c3c", alpha=0.8)

        # Configure chart appearance
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(levels, fontsize=8, rotation=45, ha="right")
        ax.legend(frameon=False)
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        ax.set_facecolor("#f0f0f0")

        # Set appropriate y-axis limits
        if is_time:
            max_time = max(max(p1_data or [0]), max(p2_data or [0])) or 1  # Avoid division by zero
            ax.set_ylim(0, min(max_time * 1.2, 600))  # Cap at 600 seconds
        else:
            ax.set_ylim(0, 110)  # For percentages

        # Style adjustments
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#dddddd')

        # Add value labels
        for bars in [p1_bars, p2_bars]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:  # Only label non-zero values
                    label = f"{height:.0f}s" if is_time else f"{height:.1f}%"
                    ax.text(bar.get_x() + bar.get_width() / 2, height + 1,
                            label, ha='center', va='bottom', fontsize=8)

    def _get_player_data(self, player_id):
        """Get player data with validation"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    q.LevelID,
                    l.Name AS LevelName,
                    COUNT(*) AS total_attempts,
                    SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS correct_attempts,
                    ls.time_remaining
                FROM Submissions s
                JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                JOIN Levels l ON q.LevelID = l.LevelID
                JOIN LevelSelection ls ON s.TP_Number = ls.TP_Number AND ls.LevelID = q.LevelID
                WHERE s.TP_Number = ?
                GROUP BY q.LevelID, l.Name, ls.time_remaining
                ORDER BY q.LevelID
            """, player_id)
            return {row.LevelID: row for row in cursor.fetchall()}
        finally:
            cursor.close()

    def _get_all_levels(self):
        """Get all levels with validation"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT LevelID, Name FROM Levels ORDER BY LevelID")
            return cursor.fetchall()
        finally:
            cursor.close()

    def _validate_and_convert_value(self, value, default=0.0):
        """
        Absolutely safe value conversion with all possible edge cases handled
        Returns a finite float number no matter what input is provided
        """
        if value is None:
            return default

        # First try direct conversion for most common case
        try:
            num = float(value)
            if math.isfinite(num):
                return num
        except (TypeError, ValueError):
            pass

        # Handle special string cases
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ('', 'nan', 'none', 'null', 'inf', '-inf'):
                return default
            try:
                num = float(value)
                if math.isfinite(num):
                    return num
            except ValueError:
                pass

        # Final fallback for any other case
        return default

    def _prepare_comparison_data(self, player1_data, player2_data, all_levels, player1_name, player2_name):
        """Prepare data for comparison with military-grade validation"""
        levels = []
        player1_acc = []
        player2_acc = []
        player1_time = []
        player2_time = []

        for level in all_levels:
            levels.append(f"{level.LevelID} - {level.Name}")

            # Player 1 data with atomic safety
            p1_row = player1_data.get(level.LevelID)
            p1_acc = 0.0
            p1_time = 0.0
            if p1_row:
                try:
                    attempts = self._validate_and_convert_value(p1_row.total_attempts, 0.0)
                    correct = self._validate_and_convert_value(p1_row.correct_attempts, 0.0)
                    remaining = self._validate_and_convert_value(p1_row.time_remaining, 600.0)

                    p1_acc = (correct / attempts * 100) if attempts > 0 else 0.0
                    p1_time = 600.0 - remaining
                except Exception:
                    p1_acc = 0.0
                    p1_time = 0.0

            # Player 2 data with same protection
            p2_row = player2_data.get(level.LevelID)
            p2_acc = 0.0
            p2_time = 0.0
            if p2_row:
                try:
                    attempts = self._validate_and_convert_value(p2_row.total_attempts, 0.0)
                    correct = self._validate_and_convert_value(p2_row.correct_attempts, 0.0)
                    remaining = self._validate_and_convert_value(p2_row.time_remaining, 600.0)

                    p2_acc = (correct / attempts * 100) if attempts > 0 else 0.0
                    p2_time = 600.0 - remaining
                except Exception:
                    p2_acc = 0.0
                    p2_time = 0.0

            # Final validation layer
            player1_acc.append(self._validate_and_convert_value(p1_acc))
            player2_acc.append(self._validate_and_convert_value(p2_acc))
            player1_time.append(self._validate_and_convert_value(p1_time))
            player2_time.append(self._validate_and_convert_value(p2_time))

        return {
            'levels': levels,
            'player1_name': player1_name,
            'player2_name': player2_name,
            'player1_acc': player1_acc,
            'player2_acc': player2_acc,
            'player1_time': player1_time,
            'player2_time': player2_time,
            'valid': bool(levels)  # Flag indicating if we have valid data
        }

    def _create_comparison_charts(self, data):
        """Create matplotlib charts with validation"""
        fig = plt.figure(figsize=(10, 10), facecolor="#f8f9fa")
        fig.suptitle("Performance Comparison", fontsize=14, fontweight="bold", y=1.02)

        gs = fig.add_gridspec(2, 1, hspace=0.4)
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])

        x = range(len(data['levels']))
        width = min(0.35, 0.8 / max(1, len(data['levels'])))

        # Safe player name extraction
        def get_name(full_str):
            parts = str(full_str).split('-')
            return parts[-1].strip() if len(parts) > 1 else full_str.strip()

        # Accuracy chart
        bars1 = ax1.bar([i - width / 2 for i in x], data['player1_acc'], width,
                        label=get_name(data['player1_name']),
                        color='#3498db', edgecolor='white', linewidth=0.7)
        bars2 = ax1.bar([i + width / 2 for i in x], data['player2_acc'], width,
                        label=get_name(data['player2_name']),
                        color='#e74c3c', edgecolor='white', linewidth=0.7)

        # Time spent chart
        bars3 = ax2.bar([i - width / 2 for i in x], data['player1_time'], width,
                        label=get_name(data['player1_name']),
                        color='#3498db', edgecolor='white', linewidth=0.7)
        bars4 = ax2.bar([i + width / 2 for i in x], data['player2_time'], width,
                        label=get_name(data['player2_name']),
                        color='#e74c3c', edgecolor='white', linewidth=0.7)

        # Configure charts
        self._configure_chart(ax1, "Accuracy Comparison", "Accuracy (%)", data['levels'])
        self._configure_chart(ax2, "Time Spent Comparison", "Time Spent (seconds)", data['levels'])

        # Add value labels
        self._add_bar_labels(ax1, bars1 + bars2, "%", "{:.1f}%")
        self._add_bar_labels(ax2, bars3 + bars4, "s", "{:.0f}s")

        fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        return fig

    def _configure_chart(self, ax, title, ylabel, levels):
        """Configure chart appearance"""
        ax.set_title(title, pad=20, fontweight="bold")
        ax.set_ylabel(ylabel, labelpad=10)
        ax.set_xticks(range(len(levels)))
        ax.set_xticklabels([level.split('-')[-1].strip() for level in levels],
                           rotation=45, ha='right')
        ax.legend(frameon=False)
        ax.set_ylim(0, 110 if ylabel == "Accuracy (%)" else None)
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # Style adjustments
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#dddddd')
        ax.tick_params(colors='#555555')
        ax.yaxis.label.set_color('#555555')
        ax.xaxis.label.set_color('#555555')
        ax.title.set_color('#2c3e50')

    def _add_bar_labels(self, ax, bars, unit, fmt):
        """Add labels to bars with validation"""
        for bar in bars:
            try:
                height = bar.get_height()
                if height > 0:  # Only label non-zero values
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            fmt.format(height),
                            ha='center', va='bottom',
                            fontsize=8)
            except Exception:
                continue  # Skip if there's any error with a bar

    def _display_charts(self, fig, container):
        """Display charts in Tkinter with error handling"""
        try:
            canvas = FigureCanvasTkAgg(fig, master=container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        except Exception as e:
            raise ValueError(f"Failed to display charts: {str(e)}")

    def _create_comparison_header(self, container, player1, player2):
        """Create the comparison header section"""
        header_frame = tk.Frame(container, bg="#f8f9fa")
        header_frame.pack(fill="x", pady=(0, 20))

        tk.Label(header_frame,
                 text="PLAYER PERFORMANCE COMPARISON",
                 font=("Segoe UI", 14, "bold"),
                 bg="#f8f9fa", fg="#2c3e50").pack(side="top")

        players_frame = tk.Frame(header_frame, bg="#f8f9fa")
        players_frame.pack(side="top", pady=10)

        tk.Label(players_frame,
                 text=f"Player 1: {player1}",
                 font=("Segoe UI", 11, "bold"),
                 fg="#3498db", bg="#f8f9fa").pack(side="left", padx=10)

        tk.Label(players_frame,
                 text=f"Player 2: {player2}",
                 font=("Segoe UI", 11, "bold"),
                 fg="#e74c3c", bg="#f8f9fa").pack(side="left", padx=10)

    def _add_footer(self, container):
        """Add footer with timestamp"""
        footer = tk.Label(container,
                          text=f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                          font=("Segoe UI", 8),
                          fg="#95a5a6", bg="#f8f9fa")
        footer.pack(side="bottom", pady=5)

    def _show_error_message(self, title, details):
        """Show error message consistently"""
        error_frame = tk.Frame(self.comparison_chart_frame, bg="#f8f9fa")
        error_frame.pack(fill="both", expand=True)

        tk.Label(error_frame,
                 text=title,
                 font=("Segoe UI", 12, "bold"),
                 fg="#e74c3c", bg="#f8f9fa").pack(pady=5)

        tk.Label(error_frame,
                 text=details,
                 font=("Segoe UI", 9),
                 fg="#95a5a6", bg="#f8f9fa").pack()

        tk.Button(error_frame,
                  text="Try Again",
                  command=self.update_player_comparison,
                  font=("Segoe UI", 9),
                  bg="#3498db", fg="white",
                  relief="flat").pack(pady=10)

    def show_inventory_system(self):
        """Show student inventory"""
        self.clear_main_frame()

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="Student Inventory",
            font=("Arial", 20, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)

        # Player selection
        player_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        player_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(player_frame, text="Select Player:", bg="#f0f0f0").pack(side="left")
        self.reward_player_var = tk.StringVar()
        player_dropdown = ttk.Combobox(
            player_frame,
            textvariable=self.reward_player_var,
            values=[f"{p['id']} - {p['name']}" for p in self.players],
            width=30
        )
        player_dropdown.pack(side="left", padx=5)
        if self.players:
            player_dropdown.current(0)
        player_btn = tk.Button(player_frame, text="Show Items", command=self.update_reward_system)
        player_btn.pack(side="left", padx=5)

        # Create notebook for reward tabs
        reward_notebook = ttk.Notebook(self.main_frame)
        reward_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Inventory Tab
        inventory_tab = ttk.Frame(reward_notebook)
        reward_notebook.add(inventory_tab, text="Inventory")

        # Shop Tab
        shop_tab = ttk.Frame(reward_notebook)
        reward_notebook.add(shop_tab, text="Shop")

        # Store tabs for later updates
        self.inventory_tab = inventory_tab
        self.shop_tab = shop_tab

        # Show initial reward data if players exist
        if self.players:
            self.update_reward_system()

    def update_reward_system(self):
        """Update the reward system tabs with current player data"""
        selected_player = self.reward_player_var.get()
        if not selected_player:
            messagebox.showwarning("Warning", "Please select a player first")
            return

        # Get player ID from selection
        try:
            player_id = selected_player.split()[0]
        except Exception:
            messagebox.showerror("Error", "Invalid player selection")
            return

        # Clear previous content
        for widget in self.inventory_tab.winfo_children():
            widget.destroy()
        for widget in self.shop_tab.winfo_children():
            widget.destroy()

        try:
            cursor = self.conn.cursor()

            # INVENTORY TAB - WITH SCROLLBAR
            # Create container frame
            inventory_container = tk.Frame(self.inventory_tab)
            inventory_container.pack(fill="both", expand=True)

            # Create canvas and scrollbar
            inventory_canvas = tk.Canvas(inventory_container)
            scrollbar = ttk.Scrollbar(inventory_container, orient="vertical", command=inventory_canvas.yview)
            scrollable_inventory_frame = tk.Frame(inventory_canvas)

            # Configure scroll region
            scrollable_inventory_frame.bind(
                "<Configure>",
                lambda e: inventory_canvas.configure(
                    scrollregion=inventory_canvas.bbox("all")
                )
            )

            # Create window in canvas
            inventory_canvas.create_window((0, 0), window=scrollable_inventory_frame, anchor="nw")
            inventory_canvas.configure(yscrollcommand=scrollbar.set)

            # Pack canvas and scrollbar
            inventory_canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Make frame width follow canvas width
            def on_inventory_canvas_configure(event):
                canvas_width = event.width
                inventory_canvas.itemconfig("all", width=canvas_width)

            inventory_canvas.bind("<Configure>", on_inventory_canvas_configure)

            # Add content to scrollable frame
            tk.Label(scrollable_inventory_frame, text="Player Inventory",
                     font=("Arial", 14, "bold")).pack(anchor="w", pady=10)

            # Get player's inventory
            cursor.execute("""
                SELECT 
                    i.ItemID,
                    i.Name,
                    i.Description,
                    i.Price,
                    inv.status
                FROM Inventory inv
                JOIN Items i ON inv.ItemID = i.ItemID
                WHERE inv.TP_Number = ?
            """, (player_id,))

            inventory_items = cursor.fetchall()

            if inventory_items:
                for item in inventory_items:
                    frame = tk.Frame(scrollable_inventory_frame, bd=1, relief=tk.RIDGE)
                    frame.pack(fill="x", padx=10, pady=5)

                    status = "Equipped" if item.status else "Owned"
                    tk.Label(frame, text=f"{item.Name} ({status})",
                             font=("Arial", 12)).pack(anchor="w")
                    tk.Label(frame, text=item.Description).pack(anchor="w")
            else:
                tk.Label(scrollable_inventory_frame, text="No items in inventory").pack(pady=20)

            # SHOP TAB - WITH SCROLLBAR
            # Create container frame
            shop_container = tk.Frame(self.shop_tab)
            shop_container.pack(fill="both", expand=True)

            # Create canvas and scrollbar
            shop_canvas = tk.Canvas(shop_container)
            scrollbar = ttk.Scrollbar(shop_container, orient="vertical", command=shop_canvas.yview)
            scrollable_shop_frame = tk.Frame(shop_canvas)

            # Configure scroll region
            scrollable_shop_frame.bind(
                "<Configure>",
                lambda e: shop_canvas.configure(
                    scrollregion=shop_canvas.bbox("all")
                )
            )

            # Create window in canvas
            shop_canvas.create_window((0, 0), window=scrollable_shop_frame, anchor="nw")
            shop_canvas.configure(yscrollcommand=scrollbar.set)

            # Pack canvas and scrollbar
            shop_canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Make frame width follow canvas width
            def on_shop_canvas_configure(event):
                canvas_width = event.width
                shop_canvas.itemconfig("all", width=canvas_width)

            shop_canvas.bind("<Configure>", on_shop_canvas_configure)

            # Add content to scrollable frame
            tk.Label(scrollable_shop_frame, text="Item Shop",
                     font=("Arial", 14, "bold")).pack(anchor="w", pady=10)

            # Get all available items
            cursor.execute("SELECT ItemID, Name, Description, Price FROM Items")
            shop_items = cursor.fetchall()

            if shop_items:
                for item in shop_items:
                    frame = tk.Frame(scrollable_shop_frame, bd=1, relief=tk.RIDGE)
                    frame.pack(fill="x", padx=10, pady=5)

                    tk.Label(frame, text=item.Name,
                             font=("Arial", 12)).pack(anchor="w")
                    tk.Label(frame, text=item.Description).pack(anchor="w")
                    tk.Label(frame, text=f"Price: {item.Price} points").pack(anchor="w")

                    # Check if player already owns this item
                    cursor.execute("""
                        SELECT 1 
                        FROM Inventory 
                        WHERE TP_Number = ? AND ItemID = ?
                    """, (player_id, item.ItemID))

                    owns_item = cursor.fetchone() is not None

                    if owns_item:
                        tk.Label(frame, text="Already purchased",
                                 fg="green").pack(side="right", padx=5)
                    else:
                        tk.Label(frame, text="Not purchased",
                                 fg="gray").pack(side="right", padx=5)
            else:
                tk.Label(scrollable_shop_frame, text="No items available in shop").pack(pady=20)

        except pyodbc.Error as e:
            print("Error fetching reward system data:", e)
            tk.Label(self.inventory_tab, text="Error loading inventory data",
                     font=("Arial", 12)).pack(pady=50)
        except Exception as e:
            print("Unexpected error in update_reward_system:", e)
            tk.Label(self.inventory_tab, text="An unexpected error occurred",
                     font=("Arial", 12)).pack(pady=50)
        finally:
            cursor.close()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = StudentAnalytics(root)
        root.mainloop()
    except Exception as e:
        print(f"Error: {e}")
        root.destroy()
        sys.exit(1)
