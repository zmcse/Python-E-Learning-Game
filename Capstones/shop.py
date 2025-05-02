import pygame
import pyodbc
from PIL import Image
import io
import os
from database_conn import connect_db

BASE_DIR = os.path.dirname(__file__)


class StudentShop:
    def __init__(self, screen, tp_number):
        self.screen = screen
        self.tp_number = tp_number

        # Initialize screen dimensions first
        pygame.init()
        self.screen_width = 1440
        self.screen_height = 810

        self.conn = self.connect_to_db()
        if not self.conn:
            self.show_pygame_message("Error", "Failed to connect to database")

        self.cursor = self.conn.cursor()

        # Create back button rectangle (replacing the image-based button)
        self.back_button_rect = pygame.Rect(20, 20, 100, 40)

        self.load_student_data()
        self.load_shop_items()
        self.load_inventory()

        self.font = pygame.font.SysFont('Arial', 20)
        self.title_font = pygame.font.SysFont('Arial', 30, bold=True)
        self.button_color = (70, 130, 180)
        self.button_hover_color = (100, 150, 200)
        self.bg_color = (3, 70, 63)
        self.text_color = (0, 0, 0)
        self.item_bg_color = (255, 255, 255)
        self.item_border_color = (200, 200, 200)

        self.current_page = 0
        self.items_per_page = 6
        self.current_tab = "shop"

        self.running = True
        self.run()

    def connect_to_db(self):
        try:
            conn = connect_db()
            return conn
        except pyodbc.Error as e:
            print(f"Database connection failed: {e}")
            return None

    def load_student_data(self):
        query = "SELECT Name, Score FROM Students WHERE TP_Number = ?"
        self.cursor.execute(query, (self.tp_number,))
        result = self.cursor.fetchone()
        if result:
            self.student_name = result.Name
            self.student_score = result.Score
        else:
            self.show_pygame_message("Error", "Student not found in database")
            raise Exception("Student not found in database")

    def load_shop_items(self):
        query = "SELECT ItemID, Name, Description, Price, item_data FROM Items"
        self.cursor.execute(query)
        self.shop_items = self.cursor.fetchall()

    def load_inventory(self):
        # Load from database
        query = """
        SELECT i.ItemID, i.Name, i.Description, i.Price, i.item_data, inv.status 
        FROM Inventory inv
        JOIN Items i ON inv.ItemID = i.ItemID
        WHERE inv.TP_Number = ?
        """
        self.cursor.execute(query, (self.tp_number,))
        self.inventory_items = list(self.cursor.fetchall())  # Convert to list
        self.display_items = self.inventory_items  # Use only inventory items

    def show_pygame_message(self, title, message):
        """Show a message using Pygame instead of Tkinter"""
        # Create overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Draw message box
        box_width, box_height = 400, 200
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(self.screen, (0, 0, 0), (box_x, box_y, box_width, box_height), 2)

        # Draw title
        title_surf = self.title_font.render(title, True, (0, 0, 0))
        self.screen.blit(title_surf, (box_x + (box_width - title_surf.get_width()) // 2, box_y + 20))

        # Draw message
        y_offset = box_y + 60
        for line in message.split('\n'):
            msg_surf = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(msg_surf, (box_x + (box_width - msg_surf.get_width()) // 2, y_offset))
            y_offset += 30

        # Draw OK button
        ok_rect = pygame.Rect(box_x + (box_width - 100) // 2, box_y + box_height - 50, 100, 30)
        pygame.draw.rect(self.screen, (70, 130, 180), ok_rect)
        ok_text = self.font.render("OK", True, (255, 255, 255))
        self.screen.blit(ok_text, (ok_rect.x + (ok_rect.width - ok_text.get_width()) // 2,
                                   ok_rect.y + (ok_rect.height - ok_text.get_height()) // 2))

        pygame.display.flip()

        # Wait for user to click OK
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if ok_rect.collidepoint(event.pos):
                        waiting = False

    def draw_button(self, x, y, width, height, text, hover=False):
        color = self.button_hover_color if hover else self.button_color
        pygame.draw.rect(self.screen, color, (x, y, width, height), border_radius=5)
        text_surf = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(x + width / 2, y + height / 2))
        self.screen.blit(text_surf, text_rect)
        return pygame.Rect(x, y, width, height)

    def draw_text(self, text, x, y, color=None, font=None, center=False):
        color = color or self.text_color
        font = font or self.font
        text_surf = font.render(text, True, color)
        if center:
            text_rect = text_surf.get_rect(center=(x, y))
        else:
            text_rect = text_surf.get_rect(topleft=(x, y))
        self.screen.blit(text_surf, text_rect)
        return text_rect

    def draw_item(self, item, x, y, width, height, owned=False, equipped=False):
        # Draw item background
        pygame.draw.rect(self.screen, self.item_bg_color, (x, y, width, height), border_radius=5)
        pygame.draw.rect(self.screen, self.item_border_color, (x, y, width, height), 2, border_radius=5)

        # Draw item image if available
        if item.item_data:
            try:
                image = Image.open(io.BytesIO(item.item_data))
                image = image.resize((100, 100), Image.Resampling.LANCZOS)
                py_image = pygame.image.fromstring(
                    image.tobytes(),
                    image.size,
                    image.mode
                )
                self.screen.blit(py_image, (x + 10, y + 10))
            except Exception as e:
                print(f"Error loading image: {e}")
                self.draw_text("No Image", x + 10, y + 10)
        else:
            self.draw_text("No Image", x + 10, y + 10)

        # Draw item details
        self.draw_text(item.Name, x + 120, y + 10)

        # Limit description to 3 lines
        desc_lines = []
        words = item.Description.split()
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if self.font.size(test_line)[0] < width - 130:
                current_line = test_line
            else:
                desc_lines.append(current_line)
                current_line = word + " "
        desc_lines.append(current_line)

        for i, line in enumerate(desc_lines[:3]):  # Only show first 3 lines
            self.draw_text(line, x + 120, y + 40 + i * 20)

        # Draw price
        self.draw_text(f"Price: {item.Price} points", x + 120, y + 100)

        # Draw owned/equipped status
        if owned:
            status_text = "Equipped" if equipped else "Owned"
            status_color = (0, 128, 0) if equipped else (0, 0, 128)
            self.draw_text(status_text, x + width - 80, y + 100, color=status_color)

        return pygame.Rect(x, y, width, height)

    def purchase_item(self, item_id, price):
        if self.student_score < price:
            self.show_pygame_message("Insufficient Points", "You don't have enough points to purchase this item.")
            return False

        try:
            # Check if item already in inventory
            query = "SELECT InventoryID FROM Inventory WHERE TP_Number = ? AND ItemID = ?"
            self.cursor.execute(query, (self.tp_number, item_id))
            if self.cursor.fetchone():
                self.show_pygame_message("Already Owned", "You already own this item.")
                return False

            # Add to inventory
            self.cursor.execute("SELECT MAX(InventoryID) FROM Inventory")
            result = self.cursor.fetchone()
            if result[0]:
                last_id = int(result[0][3:])
                new_id = f"INV{last_id + 1:03d}"
            else:
                new_id = "INV001"

            insert_query = """
            INSERT INTO Inventory (InventoryID, ItemID, TP_Number, status)
            VALUES (?, ?, ?, 0)
            """
            self.cursor.execute(insert_query, (new_id, item_id, self.tp_number))

            # Deduct points
            update_query = "UPDATE Students SET Score = Score - ? WHERE TP_Number = ?"
            self.cursor.execute(update_query, (price, self.tp_number))

            self.conn.commit()

            # Update local data
            self.student_score -= price
            self.load_inventory()

            self.show_pygame_message("Purchase Successful", "Item purchased successfully!")
            return True
        except pyodbc.Error as e:
            self.conn.rollback()
            self.show_pygame_message("Database Error", f"Failed to purchase item:\n{str(e)}")
            return False

    def equip_item(self, item_id):
        try:
            # First unequip ALL items (both in DB and locally)
            if self.inventory_items:  # Only update DB if we have inventory items
                self.cursor.execute(
                    "UPDATE Inventory SET status = 0 WHERE TP_Number = ?",
                    (self.tp_number,))

            # Update local status for all items (including default)
            for item in self.inventory_items:
                item.status = 0

            # Now equip the selected item
            if item_id == "DEFAULT001":
                for item in self.inventory_items:
                    item.status = 1
            else:
                # Update database status for the selected item
                self.cursor.execute(
                    "UPDATE Inventory SET status = 1 WHERE TP_Number = ? AND ItemID = ?",
                    (self.tp_number, item_id))

                # Update local status
                for item in self.inventory_items:
                    if item.ItemID == item_id:
                        item.status = 1

            self.conn.commit()
            return True

        except pyodbc.Error as e:
            self.conn.rollback()
            self.show_pygame_message("Error", f"Failed to equip item:\n{str(e)}")
            return False

    def run(self):
        clock = pygame.time.Clock()

        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_clicked = True
                    if self.back_button_rect.collidepoint(event.pos):
                        self.running = False

            # Clear screen
            self.screen.fill(self.bg_color)

            # Get mouse position for hover effect
            back_hover = self.back_button_rect.collidepoint(mouse_pos)

            # Draw header (removed "Welcome" text)
            pygame.draw.rect(self.screen, (50, 50, 50), (0, 0, self.screen_width, 60))
            # Only show points now
            self.draw_text(f"Points: {self.student_score}", self.screen_width - 150, 20, (255, 255, 255))

            # Draw back button with hover effect
            self.draw_button(self.back_button_rect.x, self.back_button_rect.y - 10,
                             self.back_button_rect.width, self.back_button_rect.height,
                             "Back", back_hover)

            # Draw arrow icon on back button
            arrow_points = [
                (self.back_button_rect.x + 15, self.back_button_rect.centery - 10),
                (self.back_button_rect.x + 25, self.back_button_rect.centery - 20),
                (self.back_button_rect.x + 25, self.back_button_rect.centery)
            ]
            pygame.draw.polygon(self.screen, (255, 255, 255), arrow_points)

            # Draw tabs
            shop_tab_rect = self.draw_button(220, 70, 100, 40, "Shop",
                                             hover=self.current_tab == "shop" or pygame.Rect(20, 70, 100,
                                                                                             40).collidepoint(
                                                 mouse_pos))
            inventory_tab_rect = self.draw_button(330, 70, 100, 40, "Inventory",
                                                  hover=self.current_tab == "inventory" or pygame.Rect(130, 70, 100,
                                                                                                       40).collidepoint(
                                                      mouse_pos))

            # Handle tab clicks
            if mouse_clicked:
                if shop_tab_rect.collidepoint(mouse_pos):
                    self.current_tab = "shop"
                    self.current_page = 0
                elif inventory_tab_rect.collidepoint(mouse_pos):
                    self.current_tab = "inventory"
                    self.current_page = 0

            # Get items to display based on current tab
            if self.current_tab == "shop":
                items_to_display = self.shop_items
                title = "Shop Items"
            else:
                items_to_display = self.display_items  # Use display_items which includes default item
                title = "Your Inventory"

            self.draw_text(title, 220, 120, font=self.title_font, color=(255, 255, 255))

            # Draw items in grid
            item_rects = []
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, len(items_to_display))

            for i in range(start_idx, end_idx):
                item = items_to_display[i]
                row = (i - start_idx) // 2
                col = (i - start_idx) % 2
                if col == 0:
                    x = 220 + col * (self.screen_width // 2 - 250)
                else:
                    x = 280 + col * (self.screen_width // 2 - 250)
                y = 170 + row * 150

                # Determine owned and equipped status
                if self.current_tab == "shop":
                    owned = any(inv.ItemID == item.ItemID for inv in self.inventory_items)
                    equipped = any(inv.ItemID == item.ItemID and inv.status == 1 for inv in self.inventory_items)
                else:
                    owned = True  # All items in inventory are owned
                    equipped = item.status == 1

                item_rect = self.draw_item(item, x, y, self.screen_width // 2 - 250, 140,
                                           owned=owned, equipped=equipped)
                item_rects.append((item_rect, item))

            # Handle item clicks
            if mouse_clicked:
                for item_rect, item in item_rects:
                    if item_rect.collidepoint(mouse_pos):
                        if self.current_tab == "shop":
                            if not any(inv.ItemID == item.ItemID for inv in self.inventory_items):
                                self.purchase_item(item.ItemID, item.Price)
                        else:  # INVENTORY TAB
                            # Allow clicking on default item or any non-equipped item
                            if item.ItemID == "DEFAULT001" or not getattr(item, 'status', 0) == 1:
                                success = self.equip_item(item.ItemID)
                                if success:
                                    # Force UI refresh
                                    self.load_inventory()
                                    pygame.display.flip()

            # Draw pagination controls
            total_pages = max(1, (len(items_to_display) + self.items_per_page - 1) // self.items_per_page)

            prev_page_rect = self.draw_button(self.screen_width // 2 - 100, self.screen_height - 60, 80, 40, "Previous",
                                              hover=pygame.Rect(self.screen_width // 2 - 100, self.screen_height - 60,
                                                                80, 40).collidepoint(mouse_pos))
            next_page_rect = self.draw_button(self.screen_width // 2 + 20, self.screen_height - 60, 80, 40, "Next",
                                              hover=pygame.Rect(self.screen_width // 2 + 20, self.screen_height - 60,
                                                                80, 40).collidepoint(mouse_pos))

            self.draw_text(f"Page {self.current_page + 1} of {total_pages}", self.screen_width // 2,
                           self.screen_height - 80, (255, 255, 255), center=True)

            # Handle pagination clicks
            if mouse_clicked:
                if prev_page_rect.collidepoint(mouse_pos) and self.current_page > 0:
                    self.current_page -= 1
                elif next_page_rect.collidepoint(mouse_pos) and (self.current_page + 1) * self.items_per_page < len(
                        items_to_display):
                    self.current_page += 1

            pygame.display.flip()
            clock.tick(60)

    def open_student_shop(screen, tp_number):
        try:
            shop = StudentShop(screen, tp_number)
        except Exception as e:
            # Create a minimal Pygame display for the error if needed
            pygame.init()
            error_screen = pygame.display.set_mode((800, 200))
            error_screen.fill((255, 255, 255))
            font = pygame.font.SysFont('Arial', 24)
            text = font.render(f"Error: {str(e)}", True, (255, 0, 0))
            error_screen.blit(text, (20, 80))
            pygame.display.flip()
            pygame.time.wait(3000)
            pygame.quit()

    def load_default_image(self):
        """Load a default image for the default item"""
        try:
            # Create a simple default image
            default_image = Image.new('RGB', (100, 100), color=(200, 200, 200))

            # Convert to bytes
            img_byte_arr = io.BytesIO()
            default_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            return img_byte_arr
        except Exception as e:
            print(f"Error creating default image: {e}")
            return None
