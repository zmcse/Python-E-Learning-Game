import pygame
import os
import pyodbc
import io
from PIL import Image
from confirmPlay import ConfirmPlay
import sys
from PyQt5 import QtWidgets
from database_conn import connect_db

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1440, 810  # 75% of 1920x1080 to match individual levels
PLAYER_SIZE = (60, 100)
PLAYER_SPEED = 15

# Paths
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Get paths relative to the project root
PLAYER_PATH = get_resource_path("images/player1.png")


class Ui_MainWindow(object):
    def __init__(self, tp_number):
        self.tp_number = tp_number
        self.conn = None
        self.cursor = None
        self.ensure_connection()

    def ensure_connection(self):
        """Ensure we have an active database connection"""
        if self.conn is None:
            try:
                self.conn = connect_db()
                if self.conn is None:
                    QtWidgets.QMessageBox.critical(None, "Error", "Database connection failed!")
                    return False
                self.cursor = self.conn.cursor()
                return True
            except pyodbc.Error as e:
                print(f"Database error: {e}")
                return False
        return True
    
    def close(self):
        """Safely close the database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except:
            pass
        finally:
            self.conn = None
            self.cursor = None
                
    def get_equipped_item(self, tp_number):
        """Get the image data of the currently equipped item"""
        if not self.ensure_connection():
            return None
        try:
            # First try to get equipped item
            self.cursor.execute("""
                SELECT i.item_data 
                FROM Inventory inv
                JOIN Items i ON inv.ItemID = i.ItemID
                WHERE inv.TP_Number = ? AND inv.status = 1
            """, (tp_number,))
            result = self.cursor.fetchone()
            
            if result:
                return result[0]
            
            # If no equipped item, get default background
            self.cursor.execute("""
                SELECT item_data 
                FROM Items 
                WHERE ItemID = 'ITM001'
            """)
            default_result = self.cursor.fetchone()
            return default_result[0] if default_result else None
            
        except pyodbc.Error as e:
            print(f"Error fetching equipped item: {e}")
            return None

    def get_level_info(self, level_id):
        if not self.ensure_connection():
            return None
        try:
            self.cursor.execute("SELECT Name, Description FROM Levels WHERE LevelID = ?", level_id)
            return self.cursor.fetchone()
        except pyodbc.Error as e:
            print(f"Error fetching level info: {e}")
            return None

    def get_student_progress(self, tp_number):
        # Get existing progress from DB
        self.cursor.execute("""
            SELECT s.current_level, ls.LevelID, ls.is_locked, ls.is_completed 
            FROM Students s
            JOIN LevelSelection ls ON s.TP_Number = ls.TP_Number
            WHERE s.TP_Number = ?
            ORDER BY ls.LevelID
        """, (tp_number,))
        db_results = self.cursor.fetchall()

        # Create default entries for all 5 levels
        progress = []
        for level_num in range(1, 6):
            level_id = f"LVL{level_num:03d}"
            # Find matching record or use defaults
            match = next((r for r in db_results if r[1] == level_id), None)
            if match:
                progress.append(match)
            else:
                # Default: locked if level > current_level, unlocked otherwise
                is_locked = 1 if level_num > db_results[0][0] else 0
                progress.append((db_results[0][0], level_id, is_locked, 0))

        return progress

    def get_level_images(self):
        """Get level images from database"""
        try:
            # Get map images for each level by joining Levels and Maps tables
            self.cursor.execute("""
                SELECT m.Image 
                FROM Levels l
                JOIN Maps m ON l.MapsID = m.MapsID
                ORDER BY l.LevelID
            """)
            results = self.cursor.fetchall()
            
            # Convert results to list of image data
            level_images = [result[0] if result and result[0] else None for result in results]
            
            # Ensure we have exactly 5 levels
            while len(level_images) < 5:
                level_images.append(None)
            
            return level_images[:5]  # Return only first 5 levels
        except pyodbc.Error as e:
            print(f"Error fetching level images: {e}")
            return [None] * 5



class Player:
    def __init__(self, game, x, y):
        self.game = game
        self.image = pygame.image.load(PLAYER_PATH)
        self.image = pygame.transform.scale(self.image, PLAYER_SIZE)
        self.rect = pygame.Rect(x, y, PLAYER_SIZE[0], PLAYER_SIZE[1])
        self.speed = PLAYER_SPEED
        self.font = pygame.font.Font(None, 24)
        self.screen = game.screen

    def move(self, keys, walls):
        new_rect = self.rect.copy()
        # Arrow keys and WASD controls
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  # Left arrow or A
            new_rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:  # Right arrow or D
            new_rect.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:  # Up arrow or W
            new_rect.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:  # Down arrow or S
            new_rect.y += self.speed

        if not any(new_rect.colliderect(wall) for wall in walls):
            self.rect = new_rect

    def check_level_interaction(self, keys):
        # Refresh progress before checking
        self.game.refresh_student_progress()

        for i, (level_x, level_y) in enumerate(self.game.level_positions):
            level_rect = pygame.Rect(level_x, level_y, 50, 50)
            if self.rect.colliderect(level_rect):
                # Show level number when near
                level_text = self.font.render(f"Level {i + 1}", True, (255, 255, 255))
                self.game.screen.blit(level_text, (level_x, level_y - 30))

                if keys[pygame.K_RETURN]:
                    progress = self.game.student_progress[i]
                    if progress.is_locked:
                        self.show_message("Level is locked!")
                    else:
                        ConfirmPlay(self.game.screen, i + 1, self.game.tp_number).run()

    def show_message(self, text):
        msg_surface = pygame.Surface((300, 50))
        msg_surface.fill((50, 50, 50))
        text_render = self.font.render(text, True, (255, 255, 255))
        msg_surface.blit(text_render, (10, 10))
        self.screen.blit(msg_surface, (WIDTH // 2 - 150, HEIGHT // 2 - 25))
        pygame.display.flip()
        pygame.time.delay(1000)

    def draw(self, screen):
        screen.blit(self.image, self.rect.topleft)


class levelSelection:
    def __init__(self, screen, tp_number):
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
            
        # Set consistent window size
        self.width = 1440
        self.height = 810
        
        # Create new screen if none provided
        if screen is None:
            self.screen = pygame.display.set_mode((self.width, self.height))
        else:
            # If screen is provided, recreate it with new size
            self.screen = pygame.display.set_mode((self.width, self.height))
            
        pygame.display.set_caption("Level Selection")
        
        self.tp_number = tp_number
        # Initialize database
        self.db = Ui_MainWindow(self.tp_number)
        if not self.db.ensure_connection():
            self.running = False
            return

        # Button properties
        self.button_font = pygame.font.Font(None, 28)
        self.button_color = (70, 130, 180)
        self.button_hover_color = (100, 150, 200)
        self.button_text_color = (255, 255, 255)
        self.button_height = 40
        self.button_width = 100

        # Create button rectangles
        self.back_button_rect = pygame.Rect(20, 20, self.button_width, self.button_height)
        self.history_button_rect = pygame.Rect(self.width - 240, 20, self.button_width, self.button_height)
        self.shop_button_rect = pygame.Rect(self.width - 120, 20, self.button_width, self.button_height)

        # Initialize background
        self.current_bg = pygame.Surface((self.width, self.height))
        self.current_bg.fill((50, 50, 50))  # Default gray background
        self.refresh_student_progress()
        
        self.player = Player(self, 80, 180)
        self.last_refresh_time = 0
        self.refresh_interval = 5000
        
        # Level button properties
        self.level_button_size = 80  # Increased from 50 to 80
        self.level_button_border = 10  # Border thickness
        self.level_button_color = (70, 130, 180)  # Button color
        self.level_button_hover_color = (100, 150, 200)  # Hover color
        self.level_button_border_color = (255, 255, 255)  # Border color
        
        # Adjusted level positions for larger buttons
        self.level_positions = [
            (250, 430), (500, 570), (800, 630),
            (1100, 470), (1200, 230)
        ]

        # Load level images from database
        level_image_data = self.db.get_level_images()
        self.level_images = []
        for img_data in level_image_data:
            if img_data:
                try:
                    image_stream = io.BytesIO(img_data)
                    pil_image = Image.open(image_stream)
                    pil_image = pil_image.resize((self.level_button_size, self.level_button_size))
                    mode = pil_image.mode
                    size = pil_image.size
                    data = pil_image.tobytes()
                    pygame_image = pygame.image.fromstring(data, size, mode)
                    self.level_images.append(pygame_image)
                except Exception as e:
                    print(f"Error converting level image: {e}")
                    # Create a placeholder if image conversion fails
                    placeholder = pygame.Surface((self.level_button_size, self.level_button_size))
                    placeholder.fill((100, 100, 100))
                    self.level_images.append(placeholder)
            else:
                # Create a placeholder if no image data
                placeholder = pygame.Surface((self.level_button_size, self.level_button_size))
                placeholder.fill((100, 100, 100))
                self.level_images.append(placeholder)

        border_thickness = 5
        self.walls = [
            pygame.Rect(0, 0, WIDTH, border_thickness),
            pygame.Rect(0, HEIGHT - border_thickness, WIDTH, border_thickness),
            pygame.Rect(0, 0, border_thickness, HEIGHT),
            pygame.Rect(WIDTH - border_thickness, 0, border_thickness, HEIGHT),
            pygame.Rect(0, 0, 590, 170)
        ]
        self.running = True

    def draw_button(self, rect, text, icon=None, hover=False):
        """Draw a button with optional icon"""
        color = self.button_hover_color if hover else self.button_color
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=5)  # Border

        # Draw icon if provided (using text as simple icon)
        if icon:
            icon_surface = self.button_font.render(icon, True, self.button_text_color)
            self.screen.blit(icon_surface, (rect.x + 10, rect.y + 10))

        # Draw text
        text_surface = self.button_font.render(text, True, self.button_text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Store TP number before cleanup
                tp_number = self.tp_number
                
                # Proper cleanup before returning to play screen
                if hasattr(self, 'db') and self.db is not None:
                    self.db.close()
                
                pygame.quit()
                pygame.init()
                
                # Create new display with consistent size
                screen = pygame.display.set_mode((1440, 810))
                from login import PlayScreen
                play_screen = PlayScreen(screen, tp_number)
                play_screen.run()
                
                self.running = False  # Ensure we exit the level selection loop
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.back_button_rect.collidepoint(pos):
                    # Store TP number before cleanup
                    tp_number = self.tp_number
                    
                    # Proper cleanup before returning to play screen
                    if hasattr(self, 'db') and self.db is not None:
                        try:
                            self.db.close()
                        except:
                            pass  # Ignore any errors during close
                    
                    pygame.quit()
                    pygame.init()
                    
                    # Create new display with consistent size
                    screen = pygame.display.set_mode((1440, 810))
                    from login import PlayScreen
                    play_screen = PlayScreen(screen, tp_number)
                    play_screen.run()
                    
                    self.running = False  # Ensure we exit the level selection loop
                    return
                elif self.history_button_rect.collidepoint(pos):
                    from quizHistory import QuizHistory
                    quiz_history = QuizHistory(self.screen, self.tp_number)
                    result = quiz_history.run()
                    if result == "level_selection":
                        return None
                elif self.shop_button_rect.collidepoint(pos):
                    from shop import StudentShop
                    shop = StudentShop(self.screen, self.tp_number)
                    shop.run()
        return None

    def refresh_background(self):
        try:
            equipped_bg = self.db.get_equipped_item(self.tp_number)
            if equipped_bg:
                image_stream = io.BytesIO(equipped_bg)
                original = pygame.image.load(image_stream)

                # Scale up with nearest-neighbor (sharp pixels)
                scaled_bg = pygame.transform.scale(
                    original,
                    (1440, 810)  # Directly scale to target size
                )
                self.current_bg = scaled_bg
            else:
                self.current_bg = pygame.Surface((self.width, self.height))
                self.current_bg.fill((50, 50, 50))
        except Exception as e:
            print(f"Error loading background: {e}")
            self.current_bg = pygame.Surface((self.width, self.height))
            self.current_bg.fill((50, 50, 50))

    def refresh_student_progress(self):
        """Refresh both progress and background"""
        self.student_progress = self.db.get_student_progress(self.tp_number)
        self.refresh_background()


    def close(self):
        if self.db:
            conn = self.db
            conn.close()

    def run(self):
        try:
            while self.running:
                # Check connection before each iteration
                if not self.db.ensure_connection():
                    self.show_message("Database connection lost!")
                    break

                current_time = pygame.time.get_ticks()
                if current_time - self.last_refresh_time > self.refresh_interval:
                    self.refresh_student_progress()
                    self.last_refresh_time = current_time

                # Get mouse position for hover effects
                mouse_pos = pygame.mouse.get_pos()
                back_hover = self.back_button_rect.collidepoint(mouse_pos)
                history_hover = self.history_button_rect.collidepoint(mouse_pos)
                shop_hover = self.shop_button_rect.collidepoint(mouse_pos)

                # Draw background
                self.screen.blit(self.current_bg, (0, 0))

                self.draw_button(self.back_button_rect, "Back", None, back_hover)
                self.draw_button(self.history_button_rect, "History", None, history_hover)
                self.draw_button(self.shop_button_rect, "Shop", None, shop_hover)

                # Handle player movement and level interaction
                keys = pygame.key.get_pressed()
                self.player.move(keys, self.walls)
                self.player.check_level_interaction(keys)

                # Draw levels with lock status and borders
                for i, (level_x, level_y) in enumerate(self.level_positions):
                    if i >= len(self.student_progress):
                        continue
                        
                    # Create level button rectangle
                    level_rect = pygame.Rect(level_x, level_y, self.level_button_size, self.level_button_size)
                    
                    # Check if mouse is hovering over the level
                    is_hovering = level_rect.collidepoint(mouse_pos)
                    
                    # Draw button background
                    button_color = self.level_button_hover_color if is_hovering else self.level_button_color
                    pygame.draw.rect(self.screen, button_color, level_rect)
                    
                    # Draw border
                    pygame.draw.rect(self.screen, self.level_button_border_color, level_rect, self.level_button_border)
                    
                    # Draw level image
                    if i < len(self.level_images):
                        self.screen.blit(self.level_images[i], (level_x, level_y))
                    
                    # Draw lock if level is locked
                    if self.student_progress[i].is_locked:
                        lock_icon = pygame.Surface((self.level_button_size, self.level_button_size), pygame.SRCALPHA)
                        lock_icon.fill((0, 0, 0, 128))
                        self.screen.blit(lock_icon, (level_x, level_y))

                self.player.draw(self.screen)
                pygame.display.update()

                # Handle events
                self.handle_events()
                pygame.time.delay(30)

        finally:
            # Only close the connection when we're completely done with it
            if hasattr(self, 'db') and self.db:
                self.db.close()
