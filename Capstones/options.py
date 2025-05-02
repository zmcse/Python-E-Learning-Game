import pygame
from pygame.locals import *
from levelSelection import levelSelection
from database_conn import connect_db


class Options:
    def __init__(self, screen, tp_number, level, time, dialog_type='pause'):
        self.screen = screen
        self.tp_number = tp_number
        self.level = level
        self.dialog_type = dialog_type
        self.running = True
        self.result = None
        self.time_remaining = time

        self.conn = connect_db()
        self.cursor = self.conn.cursor()

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (100, 100, 100)
        self.LIGHT_GRAY = (200, 200, 200)

        # Fonts
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 48)

        # Button properties
        self.button_width = 200
        self.button_height = 50
        self.button_margin = 20

        # Create buttons based on dialog type
        screen_width, screen_height = self.screen.get_size()
        center_x = screen_width // 2
        center_y = screen_height // 2

        self.return_button = {
            'rect': pygame.Rect(
                center_x - self.button_width // 2,
                center_y - self.button_height - self.button_margin,
                self.button_width,
                self.button_height
            ),
            'text': 'Return to Play',
            'hover': False
        }

        self.exit_button = {
            'rect': pygame.Rect(
                center_x - self.button_width // 2,
                center_y + self.button_margin,
                self.button_width,
                self.button_height
            ),
            'text': 'Exit Game',
            'hover': False
        }

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
                self.result = 'exit'
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                    self.result = 'return'
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_pos = pygame.mouse.get_pos()
                    if self.return_button['rect'].collidepoint(mouse_pos):
                        self.running = False
                        self.result = 'return'
                    elif self.exit_button['rect'].collidepoint(mouse_pos):
                        try:
                            self.cursor.execute("""
                                UPDATE LevelSelection
                                SET time_remaining = ?
                                WHERE TP_Number = ? AND LevelID = ?
                                """, self.time_remaining, self.tp_number, self.level)
                            self.conn.commit()
                        except Exception as e:
                            self.conn.rollback()
                            print(f"Database error: {e}")
                        self.running = False
                        levelSelection(self.screen, self.tp_number).run()
                        self.result = 'exit'

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        self.return_button['hover'] = self.return_button['rect'].collidepoint(mouse_pos)
        self.exit_button['hover'] = self.exit_button['rect'].collidepoint(mouse_pos)

    def render(self):
        # Create semi-transparent overlay
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # Draw title
        title_text = self.title_font.render('Game Paused', True, self.WHITE)
        title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, 100))
        self.screen.blit(title_text, title_rect)

        # Draw buttons
        buttons = [self.return_button, self.exit_button]
        for button in buttons:
            color = self.LIGHT_GRAY if button['hover'] else self.GRAY
            pygame.draw.rect(self.screen, color, button['rect'])
            pygame.draw.rect(self.screen, self.WHITE, button['rect'], 2)

            text = self.font.render(button['text'], True, self.BLACK)
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            pygame.display.flip()
            pygame.time.Clock().tick(60)

        return self.result
