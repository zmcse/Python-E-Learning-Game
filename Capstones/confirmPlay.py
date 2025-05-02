import pygame
from PyQt5 import QtWidgets
from database_conn import connect_db

pygame.init()

# Constants
BG_COLOR = (3, 70, 63)  # Solid background color
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 150, 200)
BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_HEIGHT = 60
BUTTON_WIDTH = 200


class ConfirmPlayDB:
    def __init__(self, tp_number):
        self.tp_number = tp_number
        self.conn = connect_db()
        if self.conn is None:
            QtWidgets.QMessageBox.critical(None, "Error", "Database connection failed!")
            return
        self.cursor = self.conn.cursor()

    def get_level_info(self, level_id):
        self.cursor.execute("SELECT Name, Description FROM Levels WHERE LevelID = ?", level_id)
        result = self.cursor.fetchone()
        return result if result else ("Unknown Level", "No description available")

    def get_student_progress(self):
        self.cursor.execute("""
            SELECT s.current_level, ls.LevelID, ls.is_locked, ls.is_completed 
            FROM Students s
            JOIN LevelSelection ls ON s.TP_Number = ls.TP_Number
            WHERE s.TP_Number = ?
            ORDER BY ls.LevelID
        """, (self.tp_number,))
        db_results = self.cursor.fetchall()

        progress = []
        for level_num in range(1, 6):
            level_id = f"LVL{level_num:03d}"
            match = next((r for r in db_results if r[1] == level_id), None)
            if match:
                progress.append(match)
            else:
                current_level = db_results[0][0] if db_results else 1
                is_locked = 1 if level_num > current_level else 0
                progress.append((current_level, level_id, is_locked, 0))
        return progress

    def close(self):
        self.conn.close()


class ConfirmPlay:
    def __init__(self, screen, level_number, tp_number):
        self.screen = screen
        self.level_number = level_number
        self.tp_number = tp_number
        self.level_id = f"LVL{level_number:03d}"
        self.running = True

        # Initialize database
        self.db = ConfirmPlayDB(self.tp_number)
        self.level_name, self.level_desc = self.db.get_level_info(self.level_id)

        # UI Setup
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 26)
        self.title_font = pygame.font.Font(None, 48)
        self.instruction_font = pygame.font.Font(None, 20)  # Font for the escape instruction

        # Create play button at bottom center
        self.play_button_rect = pygame.Rect(
            self.screen.get_width() // 2 - BUTTON_WIDTH // 2,
            self.screen.get_height() - BUTTON_HEIGHT - 50,  # 50 pixels from bottom
            BUTTON_WIDTH,
            BUTTON_HEIGHT
        )

        # Split description into paragraphs at '\n'
        self.level_desc_paragraphs = self.level_desc.split('\\n') if '\\n' in self.level_desc else [self.level_desc]

    def draw_button(self, rect, text, hover=False):
        """Draw a styled button with hover effect"""
        color = BUTTON_HOVER_COLOR if hover else BUTTON_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=10)  # Border

        # Draw text
        text_surface = self.font.render(text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def run(self):
        clock = pygame.time.Clock()

        while self.running:
            # Get mouse position for hover effect
            mouse_pos = pygame.mouse.get_pos()
            play_hover = self.play_button_rect.collidepoint(mouse_pos)

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return "levelSelection"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if play_hover:
                        self.start_game()
                        return "game"

            # Clear screen
            self.screen.fill(BG_COLOR)

            # Draw "Press Escape to go back" instruction in top left
            escape_text = self.instruction_font.render("Press [Esc] to go back", True, (200, 200, 200))
            self.screen.blit(escape_text, (20, 20))

            # Draw level information
            title_text = self.title_font.render(f"Level {self.level_number}: {self.level_name}", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, 100))
            self.screen.blit(title_text, title_rect)

            # Render each paragraph with spacing
            y_offset = 170
            line_height = 30  # Space between lines
            paragraph_spacing = 20  # Extra space between paragraphs

            for paragraph in self.level_desc_paragraphs:
                desc_text = self.small_font.render(paragraph, True, (200, 200, 200))
                desc_rect = desc_text.get_rect(center=(self.screen.get_width() // 2, y_offset))
                self.screen.blit(desc_text, desc_rect)
                y_offset += line_height + paragraph_spacing

            # Draw play button
            self.draw_button(self.play_button_rect, "Play Level", play_hover)

            pygame.display.flip()
            clock.tick(60)

        self.db.close()
        return "levelSelection"  # Default return when exiting normally

    def start_game(self):
        # Check if level is unlocked
        progress = self.db.get_student_progress()
        level_index = self.level_number - 1
        if level_index < len(progress) and progress[level_index][2] == 1:  # is_locked is 1
            # Show error message if level is locked
            error_msg = QtWidgets.QMessageBox()
            error_msg.setIcon(QtWidgets.QMessageBox.Warning)
            error_msg.setText("Level is locked!")
            error_msg.setInformativeText("You need to complete previous levels first.")
            error_msg.setWindowTitle("Level Locked")
            error_msg.exec_()
            return

        # Create user data dictionary
        user_data = {
            'username': self.tp_number,
            'level': self.level_number
        }

        # Import and create the game level instance
        from game_level import GameLevel
        game = GameLevel(user_data)

        # Run the game
        game.run()
        self.running = False


if __name__ == "__main__":
    # For testing only
    screen = pygame.display.set_mode((800, 600))
    confirm = ConfirmPlay(screen, 1, "TP_TEST_123")
    confirm.run()
    pygame.quit()