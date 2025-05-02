import pygame
from pygame.locals import *
from PyQt5 import QtCore, QtGui, QtWidgets
from database_conn import connect_db

# Constants
WIDTH, HEIGHT = 1440, 810
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREEN = (0, 200, 0)
COLOR_RED = (200, 0, 0)
COLOR_GRAY = (200, 200, 200)
COLOR_BLUE = (0, 0, 200)
BG_COLOR = (3, 70, 63)  # New background color

class QuizHistoryDB:
    def __init__(self, tp_number):
        self.tp_number = tp_number
        self.conn = connect_db()
        if self.conn is None:
            QtWidgets.QMessageBox.critical(None, "Error", "Database connection failed!")
            return
        self.cursor = self.conn.cursor()

    def get_level_history(self):
        self.cursor.execute("""
            SELECT 
                l.LevelID,
                l.Name AS level_name,
                COUNT(CASE WHEN s.status = 1 THEN 1 END) AS correct_answers,
                COUNT(*) AS total_questions
            FROM Submissions s
            JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
            JOIN Levels l ON q.LevelID = l.LevelID
            WHERE s.TP_Number = ?
            GROUP BY l.LevelID, l.Name
            ORDER BY l.LevelID
        """, (self.tp_number,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


class QuizHistory:
    def __init__(self, screen, tp_number):
        self.screen = screen
        self.tp_number = tp_number
        pygame.display.set_caption("Quiz History")

        # Initialize fonts
        self.font_title = pygame.font.Font(None, 50)
        self.font_header = pygame.font.Font(None, 36)
        self.font_text = pygame.font.Font(None, 28)
        self.button_font = pygame.font.Font(None, 28)

        # Initialize database
        self.db = QuizHistoryDB(self.tp_number)
        self.level_data = self.db.get_level_history()

        # UI setup
        self.current_page = 0
        self.entries_per_page = 4

        # Button properties (matching levelSelection style)
        self.button_color = (70, 130, 180)
        self.button_hover_color = (100, 150, 200)
        self.button_text_color = (255, 255, 255)
        self.button_height = 40
        self.button_width = 100

        # Create buttons
        self.back_button = pygame.Rect(20, 20, self.button_width, self.button_height)
        self.prev_button = pygame.Rect(50, HEIGHT - 60, self.button_width, self.button_height)
        self.next_button = pygame.Rect(WIDTH - 150, HEIGHT - 60, self.button_width, self.button_height)

        # Remove background image and use solid color
        self.background = None
        self.running = True

    def draw_button(self, rect, text, icon=None, hover=False):
        """Draw a button with optional icon (matches levelSelection style)"""
        color = self.button_hover_color if hover else self.button_color
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=5)  # Border

        # Draw icon if provided
        if icon:
            icon_surface = self.button_font.render(icon, True, self.button_text_color)
            self.screen.blit(icon_surface, (rect.x + 10, rect.y + 10))

        # Draw text
        text_surface = self.button_font.render(text, True, self.button_text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
                return "quit"
            elif event.type == MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.back_button.collidepoint(pos):
                    self.running = False
                    return "level_selection"
                elif self.prev_button.collidepoint(pos) and self.current_page > 0:
                    self.current_page -= 1
                elif self.next_button.collidepoint(pos) and (self.current_page + 1) * self.entries_per_page < len(
                        self.level_data):
                    self.current_page += 1
        return None

    def draw(self):
        # Draw solid color background
        self.screen.fill(BG_COLOR)

        # Get mouse position for hover effects
        mouse_pos = pygame.mouse.get_pos()
        back_hover = self.back_button.collidepoint(mouse_pos)
        prev_hover = self.prev_button.collidepoint(mouse_pos) and self.current_page > 0
        next_hover = self.next_button.collidepoint(mouse_pos) and (self.current_page + 1) * self.entries_per_page < len(
            self.level_data)

        # Draw back button (matches levelSelection style)
        self.draw_button(self.back_button, "Back", None, back_hover)

        # Draw title with TP number
        title = self.font_title.render(f"Quiz History for {self.tp_number}", True, COLOR_WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

        # Draw level entries
        start_idx = self.current_page * self.entries_per_page
        end_idx = start_idx + self.entries_per_page
        visible_levels = self.level_data[start_idx:end_idx]

        for i, level in enumerate(visible_levels):
            level_id, level_name, correct_answers, total_questions = level
            y_pos = 120 + i * 100

            # Draw level card
            card_rect = pygame.Rect(50, y_pos, WIDTH - 100, 80)
            pygame.draw.rect(self.screen, (255, 255, 255, 200), card_rect, border_radius=5)
            pygame.draw.rect(self.screen, COLOR_BLACK, card_rect, 2, border_radius=5)

            # Draw level info
            level_text = self.font_header.render(f"{level_name} ({level_id})", True, COLOR_BLUE)
            self.screen.blit(level_text, (60, y_pos + 15))

            # Draw score
            score_text = self.font_text.render(f"Score: {correct_answers}/{total_questions}", True, COLOR_BLACK)
            self.screen.blit(score_text, (60, y_pos + 45))

            # Draw percentage
            percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            percent_text = self.font_text.render(f"{percentage:.0f}%", True,
                                            COLOR_GREEN if percentage >= 50 else COLOR_RED)
            self.screen.blit(percent_text, (WIDTH - 120, y_pos + 30))

        # Draw pagination
        total_pages = (len(self.level_data) + self.entries_per_page - 1) // self.entries_per_page
        page_text = self.font_text.render(f"Page {self.current_page + 1}/{total_pages}", True, COLOR_WHITE)
        self.screen.blit(page_text, (WIDTH // 2 - page_text.get_width() // 2, HEIGHT - 50))

        # Navigation buttons (matches levelSelection style)
        if self.current_page > 0:
            self.draw_button(self.prev_button, "Previous", None, prev_hover)

        if (self.current_page + 1) * self.entries_per_page < len(self.level_data):
            self.draw_button(self.next_button, "Next", None, next_hover)

        pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()
        try:
            while self.running:
                result = self.handle_events()
                if result == "level_selection":
                    if self.db:
                        try:
                            self.db.close()
                        except:
                            pass
                    return "level_selection"
                elif result == "quit":
                    if self.db:
                        try:
                            self.db.close()
                        except:
                            pass
                    return None

                self.draw()
                clock.tick(60)

        except Exception as e:
            print(f"Error in quiz history: {e}")
            if self.db:
                try:
                    self.db.close()
                except:
                    pass
            return None

        finally:
            if self.db:
                try:
                    self.db.close()
                except:
                    pass
            return None

