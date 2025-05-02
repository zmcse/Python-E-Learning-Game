import pygame
import pyodbc
import sys

import os
from UserData import set_user, get_user_details
from database_conn import connect_db
# Get the directory where this script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to the script location
images_dir = os.path.join(current_dir, "images")
fonts_dir = os.path.join(current_dir, "fonts")

# Create directories if they don't exist
os.makedirs(images_dir, exist_ok=True)
os.makedirs(fonts_dir, exist_ok=True)

# Move font files if they exist in current directory
for font_file in ["Gameplay.ttf", "Gumela.ttf"]:
    src_path = os.path.join(current_dir, font_file)
    dst_path = os.path.join(fonts_dir, font_file)
    if os.path.exists(src_path) and not os.path.exists(dst_path):
        import shutil
        shutil.move(src_path, dst_path)

connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=Capstones;"
    "Trusted_Connection=yes;"
)

try:
    # Establish the connection
    conn = pyodbc.connect(connection_string)
    print("Database connection successful!")

    # Create a cursor object to test a query
    cursor = conn.cursor()
    cursor.execute("SELECT 1")  # A simple test query
    print("Test query executed successfully.")

    # Close connection
    conn.close()
    print("Connection closed.")

except pyodbc.Error as e:
    print("Error connecting to database:", e)


def connect_db():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=Capstones;"
            "Trusted_Connection=yes;"
        )
        return conn
    except pyodbc.Error as e:
        print("Database connection failed:", e)
        return None


class PlayScreen:
    def __init__(self, screen, tp_number):
        print(f"Initializing PlayScreen with TP: {tp_number}")
        self.screen = screen
        self.tp_number = tp_number

        self.screen = screen
        self.WIDTH, self.HEIGHT = 1440, 810
        self.background = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "loginScreen.png")), (self.WIDTH, self.HEIGHT))
        self.font = pygame.font.Font(os.path.join(fonts_dir, "Gameplay.ttf"), 12)
        self.running = True

        dialog_width = 600
        dialog_height = 150
        self.dialog_box = pygame.Rect(
            (self.WIDTH - dialog_width) // 2,
            (self.HEIGHT - dialog_height) // 2,
            dialog_width,
            dialog_height
        )

        button_width = 180
        button_height = 60
        button_y = self.dialog_box.y + self.dialog_box.height - button_height - 20

        self.confirm_yes_button = pygame.Rect(
            self.dialog_box.centerx - button_width - 10,
            button_y,
            button_width,
            button_height
        )
        self.confirm_no_button = pygame.Rect(
            self.dialog_box.centerx + 10,
            button_y,
            button_width,
            button_height
        )

        self.logo = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "logo.png")), (500, 250))
        self.logo_rect = self.logo.get_rect(center=(self.WIDTH // 2, 225))

        self.play_button = pygame.image.load(os.path.join(images_dir, "playButton.png"))
        self.play_button = pygame.transform.scale(self.play_button, (300, 375))
        self.play_rect = self.play_button.get_rect(center=(self.WIDTH // 2.5, 420))

        self.exit_button = pygame.image.load(os.path.join(images_dir, "exitButton.png"))
        self.exit_button = pygame.transform.scale(self.exit_button, (300, 375))
        self.exit_rect = self.exit_button.get_rect(center=(self.WIDTH // 1.62, 420))

        # Confirmation dialog properties
        self.show_confirm_dialog = False
        self.show_exit_confirm = False
        self.confirm_font = pygame.font.Font(os.path.join(fonts_dir, "Gameplay.ttf"), 24)
        self.confirm_text = "Are you sure you want to exit?"
        self.exit_confirm_text = "Are you sure you want to exit?"
        self.confirm_text_surface = self.confirm_font.render(self.confirm_text, True, (0, 0, 0))
        self.exit_confirm_text_surface = self.confirm_font.render(self.exit_confirm_text, True, (0, 0, 0))
        self.confirm_text_rect = self.confirm_text_surface.get_rect(center=(self.WIDTH // 2, self.dialog_box.y + 20))
        self.exit_confirm_text_rect = self.exit_confirm_text_surface.get_rect(
            center=(self.WIDTH // 2, self.dialog_box.y + 20))
        self.yes_text = self.confirm_font.render("Yes", True, (255, 255, 255))
        self.no_text = self.confirm_font.render("No", True, (255, 255, 255))

    def draw_confirmation_dialog(self, is_exit=False):
        # Draw semi-transparent background
        overlay = pygame.Surface((self.WIDTH, self.HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        # Draw dialog box with increased width
        dialog_box = pygame.Rect((self.WIDTH // 2 - 300), 300, 600, 200)
        pygame.draw.rect(self.screen, (255, 255, 255), dialog_box)
        pygame.draw.rect(self.screen, (0, 0, 0), dialog_box, 2)

        # Draw text
        if is_exit:
            self.screen.blit(self.exit_confirm_text_surface, self.exit_confirm_text_rect)
        else:
            self.screen.blit(self.confirm_text_surface, self.confirm_text_rect)

        # Draw buttons
        pygame.draw.rect(self.screen, (255, 0, 0), self.confirm_yes_button)
        pygame.draw.rect(self.screen, (0, 255, 0), self.confirm_no_button)

        # Draw button text
        yes_text_rect = self.yes_text.get_rect(center=self.confirm_yes_button.center)
        no_text_rect = self.no_text.get_rect(center=self.confirm_no_button.center)
        self.screen.blit(self.yes_text, yes_text_rect)
        self.screen.blit(self.no_text, no_text_rect)

    def run(self):
        while self.running:
            self.screen.blit(self.background, (0, 0))

            # Draw UI elements
            shadow_offset = (5, 5)
            shadow = self.logo.copy()
            shadow.fill((0, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(shadow, (self.logo_rect.x + shadow_offset[0], self.logo_rect.y + shadow_offset[1]))
            self.screen.blit(self.logo, self.logo_rect.topleft)
            self.screen.blit(self.play_button, self.play_rect.topleft)
            self.screen.blit(self.exit_button, self.exit_rect.topleft)

            if self.show_confirm_dialog:
                self.draw_confirmation_dialog(is_exit=False)
            elif self.show_exit_confirm:
                self.draw_confirmation_dialog(is_exit=True)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.show_confirm_dialog:
                            if self.confirm_yes_button.collidepoint(event.pos):
                                return "home"
                            elif self.confirm_no_button.collidepoint(event.pos):
                                self.show_confirm_dialog = False
                        elif self.show_exit_confirm:
                            if self.confirm_yes_button.collidepoint(event.pos):
                                pygame.quit()
                                sys.exit(0)
                            elif self.confirm_no_button.collidepoint(event.pos):
                                self.show_exit_confirm = False
                        else:
                            if self.play_rect.collidepoint(event.pos):
                                print("Play button clicked!")
                                from levelSelection import levelSelection
                                level_selection = levelSelection(self.screen, self.tp_number)
                                result = level_selection.run()
                                # Just continue running PlayScreen after returning from level selection
                                continue
                            elif self.exit_rect.collidepoint(event.pos):
                                self.show_exit_confirm = True

            pygame.display.update()
        return None


class LoginPage:
    def __init__(self, screen):
        self.screen = screen
        self.background = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "loginScreen.png")), (1440, 810))
        self.font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), 30)
        self.label_font = pygame.font.Font(os.path.join(fonts_dir, "Gameplay.ttf"), 25)
        self.running = True

        self.logo = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "logo.png")), (500, 250))
        self.logo_rect = self.logo.get_rect(topleft=((self.screen.get_width() - self.logo.get_width()) // 2, 0))
        self.error_message = []

        # Input box variables
        box_x = (self.screen.get_width() - 300) // 2
        self.id_input_box = pygame.Rect(box_x + 100, 270, 300, 50)
        self.password_input_box = pygame.Rect(box_x + 100, 370, 300, 50)
        self.inactive_color = pygame.Color("lightskyblue3")
        self.active_color = pygame.Color("dodgerblue2")

        self.id_text = ""
        self.password = ""
        self.id_active = False
        self.password_active = False
        self.running = True

        # Cursor variables
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_speed = 500  # milliseconds
        self.id_cursor_pos = 0
        self.password_cursor_pos = 0

        # Login button
        self.login_button = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "login.png")).convert_alpha(), (300, 375))
        self.login_rect = self.login_button.get_rect(topleft=((self.screen.get_width() - self.login_button.get_width()) // 2, 350))

        self.esc_text = self.font.render("Press ESC to go back to homepage", True, (0, 0, 0))
        self.esc_text = pygame.transform.scale(self.esc_text, (245, 20))
        self.esc_text_rect = self.esc_text.get_rect(topleft=(5, 5))

        # Add input box order for tab navigation
        self.input_order = [self.id_input_box, self.password_input_box]
        self.current_input_index = 0

        # Confirmation dialog properties
        self.show_confirm_dialog = False
        self.confirm_font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), 24)
        button_x = (self.screen.get_width() - 100) // 2
        self.confirm_yes_button = pygame.Rect(button_x - 100, 410, 100, 40)
        self.confirm_no_button = pygame.Rect(button_x + 100, 410, 100, 40)
        self.confirm_text = "Are you sure you want to exit?"
        self.confirm_text_surface = self.confirm_font.render(self.confirm_text, True, (0, 0, 0))
        self.confirm_text_rect = self.confirm_text_surface.get_rect(center=(self.screen.get_width() // 2, 370))
        self.yes_text = self.confirm_font.render("Yes", True, (255, 255, 255))
        self.no_text = self.confirm_font.render("No", True, (255, 255, 255))

    def draw_confirmation_dialog(self):
        # Draw semi-transparent background
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        # Draw dialog box
        dialog_x = (self.screen.get_width() - 600) // 2
        dialog_y = (self.screen.get_height() - 150) // 2
        dialog_box = pygame.Rect(dialog_x, dialog_y, 600, 150)
        pygame.draw.rect(self.screen, (255, 255, 255), dialog_box)
        pygame.draw.rect(self.screen, (0, 0, 0), dialog_box, 2)

        # Draw text
        self.screen.blit(self.confirm_text_surface, self.confirm_text_rect)

        # Draw buttons
        pygame.draw.rect(self.screen, (255, 0, 0), self.confirm_yes_button)
        pygame.draw.rect(self.screen, (0, 255, 0), self.confirm_no_button)

        # Draw button text
        yes_text_rect = self.yes_text.get_rect(center=self.confirm_yes_button.center)
        no_text_rect = self.no_text.get_rect(center=self.confirm_no_button.center)
        self.screen.blit(self.yes_text, yes_text_rect)
        self.screen.blit(self.no_text, no_text_rect)

    def draw_cursor(self, text, rect, cursor_pos, is_active):
        if is_active and self.cursor_visible:
            # Calculate cursor position more accurately
            text_before_cursor = text[:cursor_pos]
            # Use the same font that's used for rendering the text
            cursor_x = rect.x + 10 + self.font.size(text_before_cursor)[0]
            # Center the cursor vertically in the input box
            cursor_y = rect.y + (rect.height - 30) // 2
            cursor_height = 30  # Match the font height

            # Draw cursor line
            pygame.draw.line(self.screen, (0, 0, 0),
                           (cursor_x, cursor_y),
                           (cursor_x, cursor_y + cursor_height), 2)

    def draw_input_box(self, rect, is_active):
        """Draws an input box with transparency."""
        color = self.active_color if is_active else self.inactive_color
        pygame.draw.rect(self.screen, (255, 255, 255, 100), rect, border_radius=5)
        pygame.draw.rect(self.screen, color, rect, 2)

    def login_user(self):
        conn = connect_db()
        if not conn:
            self.error_message.append(("Database connection failed",
                                       (self.id_input_box.x - 40, self.password_input_box.y + 50)))
            return None

        cursor = conn.cursor()
        try:
            # Convert ID to uppercase for comparison
            id_upper = self.id_text.upper()
            
            if id_upper.startswith("TP"):
                # Student login
                cursor.execute("""
                SELECT COUNT(*) FROM Students 
                WHERE TP_Number = ? AND Password = ?
                """, (id_upper, self.password))

                if cursor.fetchone()[0] > 0:
                    print("Student login successful.")
                    return "play", id_upper  # Return uppercase ID
                else:
                    self.error_message.append(("Invalid student credentials",
                                               (self.id_input_box.x - 150, self.password_input_box.y + 60)))

            elif id_upper.startswith("LT"):
                # Lecturer login
                cursor.execute("""
                SELECT LecturerID FROM Lecturers 
                WHERE LecturerID = ? AND Password = ?
                """, (id_upper, self.password))

                user = cursor.fetchone()
                if user:
                    print("Lecturer login successful.")
                    set_user(user[0])
                    # Close pygame window cleanly
                    pygame.quit()
                    from Lecturer_Home_page import show_lecturer_home_page
                    show_lecturer_home_page()
                    # Launch lecturer home page
                    sys.exit(0)
                else:
                    self.error_message.append(("Invalid lecturer credentials",
                                               (self.id_input_box.x - 150, self.password_input_box.y + 60)))
            else:
                self.error_message.append(("ID must start with 'TP' or 'LT'",
                                           (self.id_input_box.x - 150, self.password_input_box.y + 60)))

        except pyodbc.Error as e:
            self.error_message.append((f"Database error: {str(e)}",
                                       (self.id_input_box.x - 150, self.password_input_box.y + 60)))
        finally:
            cursor.close()
            conn.close()
        return None

    def handle_event(self, event):
        """Handles keyboard and mouse events for input fields."""
        if event.type == pygame.QUIT:
            self.show_confirm_dialog = True
            return None
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.show_confirm_dialog = True
                return None
            elif event.key == pygame.K_TAB:
                # Move to next input box
                self.current_input_index = (self.current_input_index + 1) % len(self.input_order)
                self.id_active = self.current_input_index == 0
                self.password_active = self.current_input_index == 1
            elif event.key == pygame.K_RETURN:
                # Try to login when Enter is pressed
                if self.id_text.strip() and self.password.strip():
                    print(f"Logging in with ID: {self.id_text}, Password: {self.password}")
                    result = self.login_user()
                    if result and result[0] == "play":  # Check the first element of the tuple
                        return result  # Return the whole tuple
                else:
                    print("Error: ID and password cannot be empty!")
                    self.error_message.append(("ID and password cannot be empty!",
                                               (self.id_input_box.x - 95, self.password_input_box.y + 50)))
            elif self.id_active:
                if event.key == pygame.K_BACKSPACE:
                    if self.id_cursor_pos > 0:
                        self.id_text = self.id_text[:self.id_cursor_pos - 1] + self.id_text[self.id_cursor_pos:]
                        self.id_cursor_pos -= 1
                elif event.key == pygame.K_DELETE:
                    if self.id_cursor_pos < len(self.id_text):
                        self.id_text = self.id_text[:self.id_cursor_pos] + self.id_text[self.id_cursor_pos + 1:]
                elif event.key == pygame.K_LEFT:
                    self.id_cursor_pos = max(0, self.id_cursor_pos - 1)
                elif event.key == pygame.K_RIGHT:
                    self.id_cursor_pos = min(len(self.id_text), self.id_cursor_pos + 1)
                else:
                    self.id_text = self.id_text[:self.id_cursor_pos] + event.unicode + self.id_text[self.id_cursor_pos:]
                    self.id_cursor_pos += 1
            elif self.password_active:
                if event.key == pygame.K_BACKSPACE:
                    if self.password_cursor_pos > 0:
                        self.password = self.password[:self.password_cursor_pos - 1] + self.password[self.password_cursor_pos:]
                        self.password_cursor_pos -= 1
                elif event.key == pygame.K_DELETE:
                    if self.password_cursor_pos < len(self.password):
                        self.password = self.password[:self.password_cursor_pos] + self.password[self.password_cursor_pos + 1:]
                elif event.key == pygame.K_LEFT:
                    self.password_cursor_pos = max(0, self.password_cursor_pos - 1)
                elif event.key == pygame.K_RIGHT:
                    self.password_cursor_pos = min(len(self.password), self.password_cursor_pos + 1)
                else:
                    self.password = self.password[:self.password_cursor_pos] + event.unicode + self.password[self.password_cursor_pos:]
                    self.password_cursor_pos += 1
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # First check input boxes
            if self.id_input_box.collidepoint(event.pos):
                self.id_active = True
                self.password_active = False
                self.current_input_index = 0
                # Set cursor position based on click with improved accuracy
                mouse_x = event.pos[0] - self.id_input_box.x - 10
                text_width = 0
                self.id_cursor_pos = 0
                
                for i, char in enumerate(self.id_text):
                    char_width = self.font.size(char)[0]
                    if text_width + char_width / 2 > mouse_x:
                        self.id_cursor_pos = i
                        break
                    text_width += char_width
                    self.id_cursor_pos = i + 1
            elif self.password_input_box.collidepoint(event.pos):
                self.id_active = False
                self.password_active = True
                self.current_input_index = 1
                # Set cursor position based on click with improved accuracy
                mouse_x = event.pos[0] - self.password_input_box.x - 10
                text_width = 0
                self.password_cursor_pos = 0
                
                for i, char in enumerate(self.password):
                    char_width = self.font.size(char)[0]
                    if text_width + char_width / 2 > mouse_x:
                        self.password_cursor_pos = i
                        break
                    text_width += char_width
                    self.password_cursor_pos = i + 1
            # Then check login button
            elif self.login_rect.collidepoint(event.pos):
                if self.id_text.strip() and self.password.strip():
                    result = self.login_user()
                    print(f"Login result: {result}")  # Debug
                    if result and result[0] == "play":  # Check if tuple exists
                        return result  # Return the full tuple
                else:
                    print("Error: ID and password cannot be empty!")
                    self.error_message.append(("ID and password cannot be empty!",
                                               (self.id_input_box.x - 170, self.password_input_box.y + 60)))
        return None

    def run(self):
        while self.running:
            current_time = pygame.time.get_ticks()

            # Update cursor blink
            if current_time - self.cursor_timer > self.cursor_blink_speed:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time

            self.screen.blit(self.background, (0, 0))

            shadow_offset = (5, 5)
            shadow = self.logo.copy()
            shadow.fill((50, 50, 50, 150), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(shadow, (self.logo_rect.x + shadow_offset[0], self.logo_rect.y + shadow_offset[1]))
            self.screen.blit(self.logo, self.logo_rect.topleft)
            self.screen.blit(self.login_button, self.login_rect.topleft)
            self.screen.blit(self.esc_text, self.esc_text_rect)

            # Draw labels
            self.screen.blit(self.label_font.render("ID:", True, (0, 0, 0)), (490, 275))
            self.screen.blit(self.label_font.render("Password:", True, (0, 0, 0)), (490, 375))

            # Draw input boxes
            self.draw_input_box(self.id_input_box, self.id_active)
            self.draw_input_box(self.password_input_box, self.password_active)
            if not self.id_text.strip() or not self.password.strip():
                disabled_login = self.login_button.copy()
                disabled_login.fill((100, 100, 100, 150), special_flags=pygame.BLEND_RGBA_MULT)  # Grey out button
                self.screen.blit(disabled_login, self.login_rect.topleft)
            else:
                self.screen.blit(self.login_button, self.login_rect.topleft)

            # Display user input with cursor
            self.screen.blit(self.font.render(self.id_text, True, (0, 0, 0)),
                             (self.id_input_box.x + 10, self.id_input_box.y + 5))
            self.screen.blit(self.font.render("*" * len(self.password), True, (0, 0, 0)),
                             (self.password_input_box.x + 10, self.password_input_box.y + 5))

            # Draw cursors
            self.draw_cursor(self.id_text, self.id_input_box, self.id_cursor_pos, self.id_active)
            self.draw_cursor(self.password, self.password_input_box, self.password_cursor_pos, self.password_active)

            # Error Message if exists
            for message, position in self.error_message:
                error_surface = self.font.render(message, True, (255, 0, 0))
                self.screen.blit(error_surface, position)

            # Draw confirmation dialog if active
            if self.show_confirm_dialog:
                self.draw_confirmation_dialog()

            for event in pygame.event.get():
                if self.show_confirm_dialog:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.confirm_yes_button.collidepoint(event.pos):
                            self.running = False
                            return "home"
                        elif self.confirm_no_button.collidepoint(event.pos):
                            self.show_confirm_dialog = False
                    continue

                next_page = self.handle_event(event)
                if next_page:
                    print(f"Exiting login with: {next_page}")  # Debug
                    self.running = False
                    return next_page

            pygame.display.update()


class RegisterPage:
    def __init__(self, screen):
        self.screen = screen
        self.background = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "registerScreen.png")), (1440, 810))
        self.register_logo = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "logo.png")), (500, 250))
        self.register_logo_rect = self.register_logo.get_rect(topleft=((self.screen.get_width() - self.register_logo.get_width()) // 2, -35))

        self.WIDTH, self.HEIGHT = 1440, 810

        self.register_button = pygame.image.load(os.path.join(images_dir, "registerButton.png"))
        self.register_button = pygame.transform.scale(self.register_button, (300, 375))
        self.register_rect = self.register_button.get_rect(center=((self.screen.get_width()) // 2, 640))

        self.font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), 16)
        self.running = True

        self.error_message = None

        # input box variables
        self.input_boxes = {
            "Name": pygame.Rect(650, 170, 300, 40),
            "TP_Number": pygame.Rect(650, 250, 300, 40),
            "Email": pygame.Rect(650, 330, 300, 40),
            "Password": pygame.Rect(650, 420, 300, 40),
            "Confirm_Password": pygame.Rect(650, 490, 300, 40)
        }

        self.active_box = None
        self.input_texts = {key: "" for key in self.input_boxes}
        self.inactive_color = pygame.Color("lightskyblue3")
        self.active_color = pygame.Color("dodgerblue2")

        self.input_font_sizes = {
            "Name": 20,
            "TP_Number": 20,
            "Email": 20,
            "Password": 20,
            "Confirm_Password": 20
        }

        self.esc_text = self.font.render("Press ESC to go back to homepage", True, (0, 0, 0))
        self.esc_text_rect = self.esc_text.get_rect(topleft=(5, 5))

        # Add cursor variables
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_speed = 500  # milliseconds
        self.cursor_positions = {key: 0 for key in self.input_boxes}

        # Confirmation dialog properties
        self.show_confirm_dialog = False
        self.confirm_font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), 24)
        button_x = (self.screen.get_width() - 100) // 2
        self.confirm_yes_button = pygame.Rect(button_x - 100, 410, 100, 40)
        self.confirm_no_button = pygame.Rect(button_x + 100, 410, 100, 40)
        self.confirm_text = "Are you sure you want to stop registration?"
        self.confirm_text_surface = self.confirm_font.render(self.confirm_text, True, (0, 0, 0))
        self.confirm_text_rect = self.confirm_text_surface.get_rect(center=(self.screen.get_width() // 2, 370))
        self.yes_text = self.confirm_font.render("Yes", True, (255, 255, 255))
        self.no_text = self.confirm_font.render("No", True, (255, 255, 255))

    def draw_confirmation_dialog(self):
        # Draw semi-transparent background
        overlay = pygame.Surface((self.WIDTH, self.HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        # Draw dialog box with increased width
        dialog_x = (self.screen.get_width() - 600) // 2
        dialog_y = (self.screen.get_height() - 150) // 2
        dialog_box = pygame.Rect(dialog_x, dialog_y, 600, 150)
        pygame.draw.rect(self.screen, (255, 255, 255), dialog_box)
        pygame.draw.rect(self.screen, (0, 0, 0), dialog_box, 2)

        # Draw text
        self.screen.blit(self.confirm_text_surface, self.confirm_text_rect)

        # Draw buttons
        pygame.draw.rect(self.screen, (255, 0, 0), self.confirm_yes_button)
        pygame.draw.rect(self.screen, (0, 255, 0), self.confirm_no_button)

        # Draw button text
        yes_text_rect = self.yes_text.get_rect(center=self.confirm_yes_button.center)
        no_text_rect = self.no_text.get_rect(center=self.confirm_no_button.center)
        self.screen.blit(self.yes_text, yes_text_rect)
        self.screen.blit(self.no_text, no_text_rect)

    def draw_cursor(self, text, rect, cursor_pos, is_active):
        if is_active and self.cursor_visible:
            # Calculate cursor position more accurately
            text_before_cursor = text[:cursor_pos]
            # Find the field name for this rect
            field_name = None
            for name, r in self.input_boxes.items():
                if r == rect:
                    field_name = name
                    break
            if field_name:
                font_size = self.input_font_sizes.get(field_name, 25)
                font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), font_size)
                cursor_x = rect.x + 10 + font.size(text_before_cursor)[0]
                # Center the cursor vertically in the input box
                cursor_y = rect.y + (rect.height - 30) // 2
                cursor_height = 30  # Match the font height

                # Draw cursor line
                pygame.draw.line(self.screen, (0, 0, 0),
                               (cursor_x, cursor_y),
                               (cursor_x, cursor_y + cursor_height), 2)

    def draw_input_box(self, rect, is_active):
        color = self.active_color if is_active else self.inactive_color
        pygame.draw.rect(self.screen, (255, 255, 255, 100), rect, border_radius=5)
        pygame.draw.rect(self.screen, color, rect, 2)

    def draw_input_text(self, text, rect, field_name):
        """Draws input text with a custom font size inside the given input box."""
        font_size = self.input_font_sizes.get(field_name, 25)  # Default to 25 if not found
        font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), font_size)

        text_surface = font.render(text, True, (0, 0, 0))
        self.screen.blit(text_surface, (rect.x + 10, rect.y + (rect.height - text_surface.get_height()) // 2))

    def validate_registration(self):
        """Check if passwords match before registration."""
        # Check if any field is empty
        for key, value in self.input_texts.items():
            if not value.strip():  # If any field is empty
                self.error_message = f"{key.replace('_', ' ').title()} cannot be empty!"
                return False

        if self.input_texts["Password"] != self.input_texts["Confirm_Password"]:
            self.error_message = "Error: Passwords do not match!"
            self.input_texts["Confirm_Password"] = ""  # Clear confirm password field
            self.active_box = "Confirm_Password"
            return False  # Stop registration

        # If everything is valid, clear the error message and process the registration
        self.error_message = ""
        return True  # Successfully validated

    def register_user(self):
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            try:
                # Insert into Students table
                cursor.execute("""
                    INSERT INTO Students (TP_Number, Name, Email, Password, Score, current_level)
                    VALUES (?, ?, ?, ?, 0, 1)
                """, (self.input_texts["TP_Number"].upper(), self.input_texts["Name"],
                      self.input_texts["Email"], self.input_texts["Password"]))

                # First find the highest existing LevelSelectionID to avoid duplicates
                cursor.execute("SELECT MAX(LevelSelectionID) FROM LevelSelection")
                result = cursor.fetchone()
                last_id = result[0] if result[0] else "LS0000"

                # Extract the numeric part and increment from there
                try:
                    last_number = int(last_id[2:])
                    start_number = last_number + 1
                except (ValueError, TypeError):
                    start_number = 1

                # Insert default LevelSelection entries for levels 1–5
                for level_num in range(1, 6):
                    level_id = f"LVL{level_num:03d}"
                    level_selection_id = f"LS{start_number:04d}"  # Create unique ID
                    is_locked = 1 if level_num > 1 else 0  # Only Level 1 is unlocked
                    is_completed = 0
                    time_remaining = 600  # seconds

                    cursor.execute("""
                        INSERT INTO LevelSelection (LevelSelectionID, is_locked, is_completed, 
                                                    time_remaining, TP_Number, LevelID)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (level_selection_id, is_locked, is_completed, time_remaining,
                          self.input_texts["TP_Number"].upper(), level_id))

                    start_number += 1  # Increment for the next level

                # Add default inventory item (ITM001) for the new user
                # First, find the highest existing InventoryID
                cursor.execute("SELECT MAX(InventoryID) FROM Inventory")
                inv_result = cursor.fetchone()
                last_inv_id = inv_result[0] if inv_result[0] else "INV000"

                # Extract the numeric part and increment
                try:
                    last_inv_number = int(last_inv_id[3:])
                    new_inv_number = last_inv_number + 1
                except (ValueError, TypeError):
                    new_inv_number = 1

                # Create new inventory ID
                inventory_id = f"INV{new_inv_number:03d}"

                # Insert default inventory entry - ITM001 with status 1 (equipped)
                cursor.execute("""
                    INSERT INTO Inventory (InventoryID, ItemID, TP_Number, status)
                    VALUES (?, 'ITM001', ?, 1)
                """, (inventory_id, self.input_texts["TP_Number"].upper()))

                conn.commit()
                print("User registered successfully with all default values and default background.")
                return "login"

            except pyodbc.Error as e:
                self.error_message = f"Database error: {e}"
                print("Error during registration:", e)

            finally:
                cursor.close()
                conn.close()

        return None

    def handle_event(self, event):
        """Handles keyboard and mouse events for registration fields."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "home"
            elif event.key == pygame.K_TAB:
                # Get the list of input box keys
                keys = list(self.input_boxes.keys())
                if not self.active_box:
                    # If no box is active, activate the first one
                    self.active_box = keys[0]
                else:
                    # Find current active box and move to next
                    current_index = keys.index(self.active_box)
                    next_index = (current_index + 1) % len(keys)
                    self.active_box = keys[next_index]
                return None

            # Input handling
            if self.active_box:
                key = self.active_box  # Currently active input box
                if event.key == pygame.K_BACKSPACE:
                    if self.cursor_positions[key] > 0:
                        self.input_texts[key] = self.input_texts[key][:self.cursor_positions[key] - 1] + \
                                                self.input_texts[key][self.cursor_positions[key]:]
                        self.cursor_positions[key] -= 1
                elif event.key == pygame.K_DELETE:
                    if self.cursor_positions[key] < len(self.input_texts[key]):
                        self.input_texts[key] = self.input_texts[key][:self.cursor_positions[key]] + \
                                                self.input_texts[key][self.cursor_positions[key] + 1:]
                elif event.key == pygame.K_RETURN:
                    # Move to the next input field
                    keys = list(self.input_boxes.keys())
                    index = keys.index(key)
                    if index < len(keys) - 1:
                        self.active_box = keys[index + 1]
                    else:
                        self.active_box = None  # No more fields
                elif event.key == pygame.K_LEFT:
                    self.cursor_positions[key] = max(0, self.cursor_positions[key] - 1)
                elif event.key == pygame.K_RIGHT:
                    self.cursor_positions[key] = min(len(self.input_texts[key]), self.cursor_positions[key] + 1)
                else:
                    self.input_texts[key] = self.input_texts[key][:self.cursor_positions[key]] + event.unicode + \
                                            self.input_texts[key][self.cursor_positions[key]:]
                    self.cursor_positions[key] += 1

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.active_box = None  # Reset active input field
            for key, rect in self.input_boxes.items():
                if rect.collidepoint(event.pos):
                    self.active_box = key
                    # Set cursor position based on click with improved accuracy
                    mouse_x = event.pos[0] - rect.x - 10
                    text_width = 0
                    self.cursor_positions[key] = 0
                    
                    for i, char in enumerate(self.input_texts[key]):
                        font_size = self.input_font_sizes.get(key, 25)
                        font = pygame.font.Font(os.path.join(fonts_dir, "Gumela.ttf"), font_size)
                        char_width = font.size(char)[0]
                        if text_width + char_width / 2 > mouse_x:
                            self.cursor_positions[key] = i
                            break
                        text_width += char_width
                        self.cursor_positions[key] = i + 1

            # Register button click
            if self.register_rect.collidepoint(event.pos):
                if self.validate_registration():
                    return self.register_user()
                else:
                    return None
        return None

    def run(self):
        """Main loop for the Register Page."""
        while self.running:
            current_time = pygame.time.get_ticks()

            # Update cursor blink
            if current_time - self.cursor_timer > self.cursor_blink_speed:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time

            self.screen.blit(self.background, (0, 0))
            self.screen.blit(self.register_logo, self.register_logo_rect.topleft)
            self.screen.blit(self.register_button, self.register_rect.topleft)
            self.screen.blit(self.esc_text, self.esc_text_rect)

            self.draw_register_logo_with_shadow()

            # Draw input boxes
            for key, rect in self.input_boxes.items():
                self.draw_input_box(rect, self.active_box == key)
                self.draw_input_text(
                    self.input_texts[key] if "password" not in key.lower() else "*" * len(self.input_texts[key]),
                    rect,
                    key
                )
                self.draw_cursor(
                    self.input_texts[key] if "password" not in key.lower() else "*" * len(self.input_texts[key]),
                    rect,
                    self.cursor_positions[key],
                    self.active_box == key
                )

            # Register button
            self.draw_register_button_with_shadow()

            # Display error messages
            if self.error_message:
                error_surface = self.font.render(self.error_message, True, (255, 0, 0))
                self.screen.blit(error_surface, ((self.screen.get_width() - error_surface.get_width()) // 2, 550))  # Show error message at bottom

            # Define font sizes for each label
            label_font_sizes = {
                "Name:": 20,
                "TP Number:": 20,
                "Email:": 20,
                "Password:": 20,
                "Confirm Password:": 20
            }

            # Define custom positions for each label
            label_positions = {
                "Name:": (490, 178),
                "TP Number:": (490, 260),
                "Email:": (490, 338),
                "Password:": (490, 425),
                "Confirm Password:": (490, 470)
            }

            labels = ["Name:", "TP Number:", "Email:", "Password:", "Confirm Password:"]

            for label in labels:
                font_size = label_font_sizes.get(label, 25)  # Default font size 25 if not found
                font = pygame.font.Font(os.path.join(fonts_dir, "Gameplay.ttf"), font_size)

                if label == "Confirm Password:":
                    # Split into two lines
                    confirm_surface = font.render("Confirm", True, (0, 0, 0))
                    password_surface = font.render("Password:", True, (0, 0, 0))

                    self.screen.blit(confirm_surface, label_positions[label])  # First line
                    self.screen.blit(password_surface,
                                     (label_positions[label][0], label_positions[label][1] + 30))  # Second line
                else:
                    text_surface = font.render(label, True, (0, 0, 0))
                    position = label_positions.get(label, (490, 150))  # Default position if missing
                    self.screen.blit(text_surface, position)

            # Draw the confirmation dialog if active
            if self.show_confirm_dialog:
                self.draw_confirmation_dialog()

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.show_confirm_dialog = True
                    continue  # Skip regular event handling when showing dialog

                if self.show_confirm_dialog:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.confirm_yes_button.collidepoint(event.pos):
                            self.running = False
                            return "home"  # Return to login page
                        elif self.confirm_no_button.collidepoint(event.pos):
                            self.show_confirm_dialog = False
                    continue  # Skip regular event handling when dialog is shown

                # If ESC key is pressed, show confirmation dialog
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.show_confirm_dialog = True
                    continue

                # Process regular events when not showing dialog
                next_page = self.handle_event(event)
                if next_page:
                    self.running = False
                    return next_page

            pygame.display.update()

    def draw_register_logo_with_shadow(self):
        shadow_offset = 10
        shadow = self.register_logo.copy()
        shadow.fill((0, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(shadow, (self.register_logo_rect.x + shadow_offset, self.register_logo_rect.y + shadow_offset))
        self.screen.blit(self.register_logo, self.register_logo_rect.topleft)

    def draw_register_button_with_shadow(self):
        """Draws the register button with a shadow effect and disables it if inputs are empty."""
        shadow_offset = 5
        shadow = self.register_button.copy()
        shadow.fill((50, 50, 50, 100), special_flags=pygame.BLEND_RGBA_MULT)

        # Check if all fields are filled
        if all(self.input_texts.values()):
            self.screen.blit(shadow, (self.register_rect.x + shadow_offset, self.register_rect.y + shadow_offset))
            self.screen.blit(self.register_button, self.register_rect)
        else:
            disabled_button = self.register_button.copy()
            disabled_button.fill((100, 100, 100, 150), special_flags=pygame.BLEND_RGBA_MULT)  # Greyed-out effect
            self.screen.blit(disabled_button, self.register_rect)


class homePage:
    def __init__(self):
        pygame.init()
        self.WIDTH, self.HEIGHT = 1440, 810
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Home Screen")
        self.load_assets()
        self.current_page = "home"
        self.running = True
        self.tp_number = None  # 👈 Add this to store the TP number

    def load_assets(self):
        self.background = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "homeScreen.png")), (self.WIDTH, self.HEIGHT))
        self.logo = pygame.transform.scale(pygame.image.load(os.path.join(images_dir, "logo.png")), (500, 250))

        self.login_button = pygame.transform.scale(
            pygame.image.load(os.path.join(images_dir, "login.png")).convert_alpha(), (300, 375))
        self.register_button = pygame.transform.scale(
            pygame.image.load(os.path.join(images_dir, "registerButton.png")).convert_alpha(),
            (300, 375))

        self.login_x, self.login_y = 450, 250
        self.register_x, self.register_y = 680, 250  # Increase Y to prevent overlap

        # Set button rects WITHOUT inflating them
        self.login_rect = self.login_button.get_rect(topleft=(self.login_x, self.login_y))
        self.register_rect = self.register_button.get_rect(topleft=(self.register_x, self.register_y))

        self.logo_x = self.WIDTH // 2 - self.logo.get_width() // 2
        self.logo_y = 100

    def run(self):
        while self.running:
            if self.current_page == "home":
                self.run_home()
            elif self.current_page == "login":
                login_page = LoginPage(self.screen)
                result = login_page.run()
                print(f"Got from login: {result}")  # Debug

                if isinstance(result, tuple) and result[0] == "play":
                    _, self.tp_number = result  # Store TP number
                    print(f"Creating PlayScreen with TP: {self.tp_number}")
                    play_screen = PlayScreen(self.screen, self.tp_number)
                    result = play_screen.run()  # Run PlayScreen and get its return
                    self.current_page = result if result else "home"
                else:
                    self.current_page = result if result else "home"
            elif self.current_page == "register":
                register_page = RegisterPage(self.screen)
                self.current_page = register_page.run()
            elif self.current_page == "play":
                if self.tp_number:  # 👈 Check we have a TP number
                    print(f"Creating PlayScreen with TP: {self.tp_number}")  # Debug
                    play_screen = PlayScreen(self.screen, self.tp_number)
                    self.current_page = play_screen.run()
                else:
                    print("Error: No TP number available!")  # Debug
                    self.current_page = "home"  # Fallback to home

            if self.current_page is None:
                self.running = False

        pygame.quit()

    def run_home(self):
        while self.current_page == "home":
            self.screen.blit(self.background, (0, 0))

            shadow_offset = (5, 5)
            shadow = self.logo.copy()
            shadow.fill((0, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(shadow, (self.logo_x + shadow_offset[0], self.logo_y + shadow_offset[1]))

            self.screen.blit(self.logo, (self.logo_x, self.logo_y))
            self.screen.blit(self.login_button, (self.login_x, self.login_y))
            self.screen.blit(self.register_button, (self.register_x, self.register_y))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.current_page = None
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    if self.login_rect.collidepoint(mouse_x, mouse_y):
                        self.current_page = "login"
                    elif self.register_rect.collidepoint(mouse_x, mouse_y):
                        self.current_page = "register"

            pygame.display.update()


if __name__ == "__main__":
    app = homePage()
    app.run()

