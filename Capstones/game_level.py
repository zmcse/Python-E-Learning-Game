import pygame
import pyodbc
import sys
import io
from pygame.locals import *
from database_conn import connect_db
import random
from options import Options
from levelSelection import levelSelection

class GameLevel:
    def __init__(self, user_data):
        pygame.init()
        self.user_data = user_data  # Store user information
        self.tp_number = user_data['username']
        self.level_number = user_data['level']
        self.level = f"LVL00{self.level_number}"

        # Get level-specific configuration
        self.level_config = self.get_level_config(self.level_number)

        # Initialize database connection
        self.conn = None
        self.cursor = None
        self.ensure_connection()

        # Get display info and set up display
        self.info = pygame.display.Info()
        self.original_width = 1920
        self.original_height = 1080

        # Calculate initial scale factor
        self.width = int(self.original_width * 0.75)  # Start at 75% of original size
        self.height = int(self.original_height * 0.75)
        self.scale_factor = 0.75

        # Create a non-resizable window
        pygame.display.init()
        pygame.key.set_repeat(200, 50)  # Enable key repeat
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(f"Level {self.level_number} - Player: {self.user_data.get('username', 'Guest')}")

        # Force window focus
        pygame.event.clear()  # Clear any initial events
        self.screen.fill((0, 0, 0))  # Clear screen
        pygame.display.flip()

        # Database connection
        self.conn = connect_db()
        self.cursor = self.conn.cursor()

        # Load assets
        self.load_assets()
        self.setup_game_objects()

        # Game state
        self.running = True
        self.clock = pygame.time.Clock()
        self.tel_cooldown = 500
        self.last_tel_time = 0
        self.is_completed = False

        try:
            self.cursor.execute(""" 
                SELECT time_remaining, is_completed
                FROM LevelSelection
                WHERE TP_Number = ? AND LevelID = ?
            """, self.tp_number, self.level)
            result = self.cursor.fetchone()
            tr_result = 0
            ic_result = 0

            if result:
                tr_result = result[0]
                ic_result = result[1]
            print(tr_result, ic_result)

            if ic_result == 1:
                self.is_completed = True

            if tr_result is not None:
                self.time_remaining = int(tr_result)

                # Reset timer if time remaining = 0 (student reattempting level)
                if self.time_remaining == 0:
                    self.time_remaining = 600
                    try:
                        self.cursor.execute("""
                            UPDATE LevelSelection 
                            SET time_remaining = ?
                            WHERE TP_Number = ? AND LevelID = ?
                        """, self.time_remaining, self.tp_number, self.level)
                        self.conn.commit()
                    except Exception as e:
                        print(f"Error updating time remaining: {e}")
            else:
                # Default time (10 minutes = 600 seconds)
                self.time_remaining = 600

                # Get LevelSelectionID
                self.cursor.execute("""
                    SELECT MAX(CAST(SUBSTRING(LevelSelectionID, 3, LEN(LevelSelectionID)) AS INT))
                    FROM LevelSelection
                    WHERE LevelSelectionID LIKE 'LS%'
                """)
                max_id = self.cursor.fetchone()[0] or 0
                next_id = f"LS{max_id + 1:04d}"
                print(next_id)

                # Insert new entry
                self.cursor.execute("""
                            INSERT INTO LevelSelection (LevelSelectionID, is_locked, is_completed, time_remaining, TP_Number, LevelID)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, next_id, 0, 0, self.time_remaining, self.tp_number, self.level)
                self.conn.commit()

        except Exception as e:
            print(f"Error handling time remaining: {e}")
            self.time_remaining = 600  # Default fallback

        # Convert seconds to minutes:seconds for display
        self.start_time = pygame.time.get_ticks()
        self.last_second = 0
        print(self.time_remaining, self.start_time)

        pygame.key.set_repeat(500, 50)  # Enable key repeat for backspace
        self.input_active = False
        self.input_text = ""
        self.input_font = pygame.font.Font(None, int(30 * self.scale_factor))
        self.input_rect = None
        self.is_correct = False

        # Mouse cursor setup
        self.default_cursor = pygame.SYSTEM_CURSOR_ARROW
        self.hover_cursor = pygame.SYSTEM_CURSOR_HAND
        self.text_cursor = pygame.SYSTEM_CURSOR_IBEAM
        pygame.mouse.set_cursor(self.default_cursor)

        self.active_door = None  # initialize door tracking
        self.points = 0

                # notes initialization
        self.show_notes = True
        self.note_title = "No notes available"
        self.note_content = ""
        self.note_hint = ""
        self.notes_surface = None
        self.notes_pos = (0, 0)
        self.hints_surface = None
        self.hints_pos = (0, 0)

        # feedback message initialization
        self.feedback_message = None
        self.feedback_color = (255, 255, 255)
        self.feedback_timestamp = 0

        # Initialize hint button properties
        self.hint_button_position = (self.width - 30, 65)
        self.hint_text_rect = None
        self.show_hints = False

        # unlock door message properties
        self.door_message_visible = True
        self.door_message_radius = 22
        self.door_message_font = pygame.font.Font(None, 38)
        self.door_message_text = "!"
        self.door_message_text_surface = self.door_message_font.render("!", True, (255, 0, 0))
        if self.level == "LVL001":
            self.door_message_position = (780 * self.scale_factor + 38, 160 * self.scale_factor - 25)
        elif self.level == "LVL002":
            self.door_message_position = (1407 * self.scale_factor + 150, 0 * self.scale_factor + 35)
        elif self.level == "LVL003":
            self.door_message_position = (840 * self.scale_factor + 88, 0 * self.scale_factor + 70)
        elif self.level == "LVL004":
            self.door_message_position = (520 * self.scale_factor + 38, 714 * self.scale_factor + 40)
        elif self.level == "LVL005":
            self.door_message_position = (1735 * self.scale_factor + 42, 107 * self.scale_factor + 40)

        # initialize all question IDs used in the current run
        self.question_ids = []
        try:
            print("\nDebug: Initializing question IDs for level:", self.level)
            
            # First, get all questions for Level 1
            self.cursor.execute("""
                SELECT QuestionID, MapsItemsID
                FROM QuestionDetails
                WHERE LevelID = ?
            """, self.level)
            all_questions = self.cursor.fetchall()
            print(f"Debug: All questions for Level {self.level}:", all_questions)

            # Group questions by MapsItemsID
            questions_by_item = {}
            for question_id, maps_items_id in all_questions:
                if maps_items_id not in questions_by_item:
                    questions_by_item[maps_items_id] = []
                questions_by_item[maps_items_id].append(question_id)

            print("Debug: Questions grouped by MapsItemsID:", questions_by_item)

            # Initialize question_ids list with None for all positions
            self.question_ids = [None] * 6  # We need exactly 6 questions

            # For each MapsItemsID from MIT101 to MIT106, get one random question
            for i in range(1, 7):
                maps_items_id = f'MIT{self.level[-1]}0{i}'  # Use the level number from self.level
                if maps_items_id in questions_by_item and questions_by_item[maps_items_id]:
                    # Randomly select one question for this MapsItemsID
                    random_question = random.choice(questions_by_item[maps_items_id])
                    self.question_ids[i-1] = random_question
                    print(f"Debug: Selected question {random_question} for {maps_items_id}")

            print("Debug: Final question_ids array:", self.question_ids)

        except Exception as e:
            print(f"Error getting question IDs: {e}")
            print("Debug: Exception traceback:", e.__traceback__)

        self.current_question = {
            'surface': None,
            'position': (0, 0),
            'visible': False,
            'input_properties': {}
        }

        self.current_passcode_input = {
            'surface': None,
            'position': (0, 0),
            'visible': False
        }

        self.completion_message = {
            'surface': None,
            'position': (0, 0),
            'visible': False
        }

        self.fail_message = {
            'surface': None,
            'position': (0, 0),
            'visible': False
        }
        self.passcode_visible = False
        self.passcode_inputs = []  # empty list to store passcode inputs
        self.passcode_feedback = False
        self.door_unlocked = False
        self.show_completion = False
        self.show_fail = False
        self.show_hints = False

    def get_level_config(self, level_number):
        """Get level-specific configuration"""
        configs = {
            1: {
                'maps_id': 'Maps01',
                'items_prefix': 'MIT10',
                'walls': [
                    (0, 378, 553, 90),  # room1h
                    (553, 0, 19, 452),  # room1v
                    (1154, 0, 19, 676),  # room2v
                    (1176, 594, 748, 90),  # room2 lower horizontal
                    (1176, 0, 744, 142),  # room2 upper horizontal
                    (0, 704, 574, 2),  # room3h
                    (558, 759, 14, 328),  # room3v
                    (574, 108, 580, 90)  # room4
                ],
                'objects': [
                    (968, 214, 118, 14),  # vending machine
                    (1100, 653, 54, 20),  # bookshelf
                    (1602, 702, 320, 20),  # lockers
                    (836, 756, 107, 79),  # table & chairs (left)
                    (968, 774, 40, 5),  # t&c (right)
                    (1095, 922, 240, 11),  # t&c (room3 right)
                    (257, 972, 259, 214),  # table and chair (room3 left)
                    (0, 808, 168, 90),  # chair (room3 left)
                    (1176, 706, 90, 8),  # plant
                    (1423, 150, 24, 8),  # podium (room2)
                    (1215, 163, 64, 20),  # drawers (left)
                    (1793, 163, 64, 20),  # drawers (right)
                    (1217, 324, 127, 130),  # t&c1 (room2)
                    (1471, 324, 127, 130),  # t&c2 (room2)
                    (1725, 324, 127, 130),  # t&c3 (room2)
                    (236, 0, 1, 382),  # t&c1 (room1)
                    (326, 0, 1, 382)  # t&c2 (room1)
                ],
                'doors': [
                    {
                        "door_area": (142, 436, 174, 149),
                        "floor_area": (142, 558, 144, 38),
                        "destination": (240, 254)
                    },
                    {
                        "door_area": (142, 436, 174, 149),
                        "floor_area": (142, 315, 144, 58),
                        "destination": (240, 474)
                    },
                    {
                        "door_area": (1420, 654, 176, 149),
                        "floor_area": (1420, 770, 176, 38),
                        "destination": (1450, 486)
                    },
                    {
                        "door_area": (1420, 654, 176, 149),
                        "floor_area": (1420, 533, 176, 58),
                        "destination": (1450, 692)
                    },
                    {
                        "door_area": (556, 920, 48, 123),
                        "floor_area": (576, 920, 54, 125),
                        "destination": (448, 864)
                    },
                    {
                        "door_area": (556, 920, 48, 125),
                        "floor_area": (529, 920, 54, 125),
                        "destination": (605, 864)
                    },
                    {
                        "door_area": (780, 160, 104, 133),
                        "floor_area": (780, 292, 104, 38),
                        "destination": (798, 0)
                    }
                ],
                'items': [
                    {'id': 'MIT101', 'type': 'bag', 'pos': (115, 29), 'size': (91, 59),
                    'stickynotes': [{'id': 'MIT107', 'offset': (32, 68)}]},

                    {'id': 'MIT102', 'type': 'computer', 'pos': (88, 788), 'size': (94, 77),
                    'stickynotes': [{'id': 'MIT107', 'offset': (-8, 80)}]},

                    {'id': 'MIT103', 'type': 'pencil', 'pos': (850, 776), 'size': (53, 43),
                    'stickynotes': [{'id': 'MIT107', 'offset': (58, 12)}]},

                    {'id': 'MIT104', 'type': 'picture', 'pos': (1218, 113), 'size': (59, 47),
                    'stickynotes': [{'id': 'MIT107', 'offset': (76, 33)}]},

                    {'id': 'MIT105', 'type': 'plant', 'pos': (1176, 707), 'size': (94, 95),
                    'stickynotes': [{'id': 'MIT107', 'offset': (-8, -43)}]},

                    {'id': 'MIT106', 'type': 'shoes', 'pos': (1390, 394), 'size': (90, 45),
                    'stickynotes': [{'id': 'MIT107', 'offset': (100, -59)}]}
                ]
            },
            2: {
                'maps_id': 'Maps02',
                'items_prefix': 'MIT20',
                'walls': [
                    (176, 324, 11, 68),  # stairs
                    (190, 324, 1706, 42),  # lower floor wall
                    (1473, 0, 448, 34)  # upper floor room
                ],
                'objects': [
                    (256, 594, 352, 2),  # t&c row1 column1
                    (256, 702, 352, 2),  # t&c r2c1
                    (256, 810, 352, 2),  # t&c r3c1
                    (256, 918, 352, 2),  # t&c r4c1
                    (768, 594, 352, 2),  # t&c r1c2
                    (768, 702, 352, 2),  # t&c r2c2
                    (768, 810, 352, 2),  # t&c r3c2
                    (768, 918, 352, 2),  # t&c r4c2
                    (1280, 594, 352, 2),  # t&c r1c3
                    (1280, 702, 352, 2),  # t&c r2c3
                    (1280, 810, 352, 2),  # t&c r3c3
                    (1280, 918, 352, 2),  # t&c r4c3
                    (1869, 592, 53, 34),  # bookshelf
                    (1780, 368, 69, 20),  # drum
                    (120, 55, 133, 10),  # piano
                    (788, 135, 43, 10),  # mic
                    (976, 176, 24, 8),  # podium
                    (1510, 45, 48, 8)  # guitar
                ],
                'doors': [
                    {
                        "door_area": (142, 436, 174, 149),
                        "floor_area": (142, 558, 144, 38),
                        "destination": (240, 254)
                    }
                ],
                'items': [
                    {'id': 'MIT201', 'type': 'basketball', 'pos': (710, 822), 'size': (48, 41),
                    'stickynotes': [{'id': 'MIT207', 'offset': (72, -2)}]},

                    {'id': 'MIT202', 'type': 'drum', 'pos': (1780, 415), 'size': (69, 68),
                    'stickynotes': [{'id': 'MIT207', 'offset': (15, -50)}]},

                    {'id': 'MIT203', 'type': 'guitar', 'pos': (1510, 45), 'size': (48, 97),
                    'stickynotes': [{'id': 'MIT207', 'offset': (-30, -30)}]},

                    {'id': 'MIT204', 'type': 'mic', 'pos': (788, 135), 'size': (43, 97),
                    'stickynotes': [{'id': 'MIT207', 'offset': (2, 30)}]},

                    {'id': 'MIT205', 'type': 'piano', 'pos': (120, 56), 'size': (133, 97),
                    'stickynotes': [{'id': 'MIT207', 'offset': (-10, 24)}]},

                    {'id': 'MIT206', 'type': 'racket', 'pos': (1643, 888), 'size': (67, 54),
                    'stickynotes': [{'id': 'MIT207', 'offset': (-61, 40)}]}
                ]
            },
            3: {
                'maps_id': 'Maps03',
                'items_prefix': 'MIT30',
                'walls': [
                    (0, 594, 552, 89),  # room1 lh
                    (0, 0, 552, 140),  # room1 uh
                    (554, 0, 21, 683),  # room1v
                    (1345, 0, 21, 683),  # room2v
                    (1367, 594, 552, 89),  # room2 lh
                    (1367, 0, 552, 140),  # room3 uh
                    (577, 0, 766, 120)  # room3
                ],
                'objects': [
                    (577, 216, 59, 459),  # lockers & bookshelf (left)
                    (1286, 216, 59, 461),  # lockers (right)
                    (1346, 700, 122, 25),  # bookshelf (right)
                    (85, 884, 50, 5),  # c1a
                    (128, 866, 128, 214),  # t1
                    (256, 973, 65, 5),  # c1b
                    (450, 866, 256, 214),  # t&c2
                    (1217, 973, 65, 5),  # c3a
                    (1282, 866, 128, 214),  # t3
                    (1410, 884, 65, 5),  # c3b
                    (1600, 866, 193, 214),  # t&c4
                    (1793, 884, 40, 5),  # c4
                    (321, 162, 127, 20),  # lockers (room1)
                    (1471, 162, 127, 20),  # lockers (room2)
                    (64, 324, 126, 26),  # t&c1 (room1)
                    (320, 324, 126, 26),  # t&c2 (room1)
                    (64, 487, 126, 26),  # t&c3 (room1)
                    (320, 487, 126, 26),  # t&c4 (room1)
                    (1473, 324, 126, 26),  # t&c1 (room2)
                    (1729, 324, 126, 26),  # t&c2 (room2)
                    (1473, 487, 126, 26),  # t&c3 (room2)
                    (1729, 487, 126, 26),  # t&c4 (room2)
                ],
                'doors': [
                    {
                        "door_area": (73, 650, 183, 130),
                        "floor_area": (73, 780, 183, 50),
                        "destination": (220, 480)
                    },
                    {
                        "door_area": pygame.Rect(73, 650, 183, 130),
                        "floor_area": pygame.Rect(73, 544, 183, 50),
                        "destination": (110, 690)
                    },
                    {
                        "door_area": pygame.Rect(1671, 650, 183, 130),
                        "floor_area": pygame.Rect(1671, 544, 183, 50),
                        "destination": (1700, 690)
                    },
                    {
                        "door_area": pygame.Rect(1671, 650, 183, 130),
                        "floor_area": pygame.Rect(1671, 780, 183, 50),
                        "destination": (1650, 480)
                    },
                    {
                        "door_area": pygame.Rect(840, 25, 230, 163),
                        "floor_area": pygame.Rect(840, 188, 230, 30),
                        "destination": (1700, 690)
                    }
                ],
                'items': [
                    {'id': 'MIT301', 'type': 'burger', 'pos': (355, 482), 'size': (91, 59),
                    'stickynotes': [{'id': 'MIT307', 'offset': (45, 48)}]},  # burger with note

                    {'id': 'MIT302', 'type': 'cake', 'pos': (358, 132), 'size': (94, 77),
                    'stickynotes': [{'id': 'MIT307', 'offset': (-23, 53)}]},  # cake with note

                    {'id': 'MIT303', 'type': 'chocolate', 'pos': (1720, 880), 'size': (53, 43),
                    'stickynotes': [{'id': 'MIT307', 'offset': (-40, 20)}]},  # chocolate with note

                    {'id': 'MIT304', 'type': 'donut', 'pos': (137, 970), 'size': (59, 47),
                    'stickynotes': [{'id': 'MIT307', 'offset': (8, -50)}]},  # donut with note

                    {'id': 'MIT305', 'type': 'drinks', 'pos': (1771, 302), 'size': (94, 95),
                    'stickynotes': [{'id': 'MIT307', 'offset': (37, 58)}]},  # drinks with note

                    {'id': 'MIT306', 'type': 'taco', 'pos': (1284, 975), 'size': (90, 45),
                    'stickynotes': [{'id': 'MIT307', 'offset': (16, -55)}]}  # taco with note
                ]
            },
            4: {
                'maps_id': 'Maps04',
                'items_prefix': 'MIT40',
                'walls': [
                    (680, 0, 22, 210),  # v1
                    (232, 180, 471, 5),  # h1
                    (232, 269, 22, 480),  # v2
                    (232, 749, 1456, 139),  # h2
                    (1664, 0, 24, 749),  # v3
                ],
                'objects': [
                    (385, 269, 126, 20),  # vending machine
                    (384, 447, 64, 3),  # chair1
                    (384, 553, 64, 3),  # chair2
                    (577, 647, 62, 3),  # chair3
                ],
                'doors': [
                    {
                        "door_area": pygame.Rect(520, 754, 110, 135),
                        "floor_area": pygame.Rect(520, 704, 170, 20),
                        "destination": (535, 800)
                    }
                ],
                'items': [
                    {'id': 'MIT401', 'type': 'bag', 'pos': (515, 240), 'size': (91, 59),
                     'stickynotes': [{'id': 'MIT407', 'offset': (32, 68)}]},

                    {'id': 'MIT402', 'type': 'ball', 'pos': (260, 588), 'size': (94, 77),
                     'stickynotes': [{'id': 'MIT407', 'offset': (-8, 80)}]},

                    {'id': 'MIT403', 'type': 'bat', 'pos': (850, 690), 'size': (53, 43),
                     'stickynotes': [{'id': 'MIT407', 'offset': (58, 12)}]},

                    {'id': 'MIT404', 'type': 'drink', 'pos': (1218, 113), 'size': (59, 47),
                     'stickynotes': [{'id': 'MIT407', 'offset': (76, 33)}]},

                    {'id': 'MIT405', 'type': 'gloves', 'pos': (1176, 640), 'size': (94, 95),
                     'stickynotes': [{'id': 'MIT407', 'offset': (-8, -43)}]},

                    {'id': 'MIT406', 'type': 'shoes', 'pos': (1390, 394), 'size': (90, 45),
                     'stickynotes': [{'id': 'MIT407', 'offset': (100, -59)}]}
                ]
            },
            5: {
                'maps_id': 'Maps05',
                'items_prefix': 'MIT50',
                'walls': [
                    (64, 163, 575, 10),  # fence1
                    (64, 1024, 575, 10),  # fence2
                    (1215, 1024, 575, 10),  # fence3
                    (1665, 0, 585, 140),  # room
                ],
                'objects': [
                    (1599, 109, 65, 20),  # vending machine
                ],
                'doors': [
                    {
                        "door_area": pygame.Rect(1735, 107, 111, 134),
                        "floor_area": pygame.Rect(1735, 241, 111, 30),
                        "destination": (535, 800)
                    }
                ],
                'items': [
                    {'id': 'MIT501', 'type': 'bag', 'pos': (514, 224), 'size': (91, 59),
                    'stickynotes': [{'id': 'MIT507', 'offset': (64, -14)}]},

                    {'id': 'MIT502', 'type': 'ball', 'pos': (1110, 631), 'size': (94, 77),
                    'stickynotes': [{'id': 'MIT507', 'offset': (-40, 39)}]},

                    {'id': 'MIT503', 'type': 'bush', 'pos': (662, 990), 'size': (53, 43),
                    'stickynotes': [{'id': 'MIT507', 'offset': (178, 10)}]},

                    {'id': 'MIT504', 'type': 'cone', 'pos': (1830, 856), 'size': (59, 47),
                    'stickynotes': [{'id': 'MIT507', 'offset': (-45, 4)}]},

                    {'id': 'MIT505', 'type': 'gloves', 'pos': (328, 735), 'size': (94, 95),
                    'stickynotes': [{'id': 'MIT507', 'offset': (-42, 35)}]},

                    {'id': 'MIT506', 'type': 'rock', 'pos': (1063, 125), 'size': (90, 45),
                    'stickynotes': [{'id': 'MIT507', 'offset': (97, 6)}]}
                ]
            }
        }
        return configs.get(level_number, configs[1])  # Default to level 1 config if not found

    def ensure_connection(self):
        """Ensure we have an active database connection"""
        if self.conn is None:
            try:
                self.conn = connect_db()
                if self.conn is None:
                    print("Error: Database connection failed!")
                    return False
                self.cursor = self.conn.cursor()
                return True
            except pyodbc.Error as e:
                print(f"Database error: {e}")
                return False
        return True

    def close_connection(self):
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

    def get_background_from_db(self):
        """Retrieve background image from database and convert to Pygame surface"""
        try:
            # Query the database for the image
            self.cursor.execute("SELECT Image FROM Maps WHERE MapsID = ?", self.level_config['maps_id'])
            row = self.cursor.fetchone()

            if row and row[0]:
                # Convert binary data to bytes
                image_data = bytes(row[0])

                # Create a file-like object from the bytes
                image_file = io.BytesIO(image_data)

                # Load the image with Pygame
                return pygame.image.load(image_file).convert()
            else:
                print(f"No image found for MapsID: {self.level_config['maps_id']}")
                # Fallback to a solid color if no image is found
                surf = pygame.Surface((self.width, self.height))
                surf.fill((50, 50, 50))  # Gray background
                return surf

        except Exception as e:
            print("Error loading image from database:", e)
            # Fallback to a solid color if there's an error
            surf = pygame.Surface((self.width, self.height))
            surf.fill((255, 0, 0))  # Red background to indicate error
            return surf

    def load_assets(self):
        """Load and scale all game assets"""
        # Background - loaded from database
        self.background = self.get_background_from_db()
        self.background = pygame.transform.scale(self.background, (self.width, self.height))

        # Character - loaded from database
        try:
            self.cursor.execute("""
                SELECT Item_Image 
                FROM MapsItems 
                WHERE MapsItemsID = ? AND MapsID = ?
            """, (f"{self.level_config['items_prefix']}9", self.level_config['maps_id']))
            row = self.cursor.fetchone()
            
            if row and row[0]:
                # Convert binary data to bytes
                image_data = bytes(row[0])
                image_file = io.BytesIO(image_data)
                self.character_img = pygame.image.load(image_file).convert_alpha()
            else:
                print("Error: Player image not found in database")
                # Fallback to a placeholder if image not found
                self.character_img = pygame.Surface((60, 100))
                self.character_img.fill((255, 0, 255))  # Magenta placeholder
        except Exception as e:
            print(f"Error loading player image from database: {e}")
            # Fallback to a placeholder if error occurs
            self.character_img = pygame.Surface((60, 100))
            self.character_img.fill((255, 0, 255))  # Magenta placeholder

        self.char_width, self.char_height = int(60 * self.scale_factor), int(100 * self.scale_factor)
        self.character = pygame.transform.scale(self.character_img, (self.char_width, self.char_height))
        self.char_x, self.char_y = (self.width // 2 - self.char_width // 2), (self.height // 2 - self.char_height // 2)

        # NPC
        try:
            self.cursor.execute("""
                SELECT Item_Image 
                FROM MapsItems 
                WHERE MapsItemsID = ? AND MapsID = ?
            """, (f"{self.level_config['items_prefix']}8", self.level_config['maps_id']))
            row = self.cursor.fetchone()

            if row and row[0]:
                # Convert binary data to bytes
                image_data = bytes(row[0])
                image_file = io.BytesIO(image_data)
                self.npc_img = pygame.image.load(image_file).convert_alpha()
            else:
                print("Error: NPC image not found in database")
                # Fallback to a placeholder if image not found
                self.npc_img = pygame.Surface((60, 100))
                self.npc_img.fill((255, 0, 255))  # Magenta placeholder
        except Exception as e:
            print(f"Error loading NPC image from database: {e}")
            # Fallback to a placeholder if error occurs
            self.npc_img = pygame.Surface((60, 100))
            self.npc_img.fill((255, 0, 255))  # Magenta placeholder

        self.npc_width, self.npc_height = 350, 350
        self.npc = pygame.transform.scale(self.npc_img, (self.npc_width, self.npc_height))
        self.npc_x, self.npc_y = (1050, self.screen.get_height() - self.npc_height + 15)

        # Text
        self.font = pygame.font.Font(None, int(36 * self.scale_factor))
        self.hover_text = self.font.render("F", False, "Black")

        # Load items from database with specific positions
        self.load_items_from_db()

        # Game speed
        self.speed = int(6 * self.scale_factor)

    def load_items_from_db(self):
        """Load items from database with their exact positions"""
        try:
            self.items = []
            self.item_positions = []
            self.item_rects = []
            self.item_info = {}  # stores item data by ID
            self.stickynote_to_item = {}  # maps note IDs to item IDs

            for prop in self.level_config['items']:
                # Get item from database
                self.cursor.execute("""
                    SELECT Item_Image 
                    FROM MapsItems 
                    WHERE MapsItemsID = ? AND MapsID = ?
                """, (prop['id'], self.level_config['maps_id']))

                row = self.cursor.fetchone()

                if row and row[0]:
                    # Convert binary data to surface
                    image_data = bytes(row[0])
                    image_file = io.BytesIO(image_data)
                    img = pygame.image.load(image_file).convert_alpha()

                    # Scale item
                    scaled_size = (
                        int(prop['size'][0] * self.scale_factor),
                        int(prop['size'][1] * self.scale_factor)
                    )
                    scaled_img = pygame.transform.scale(img, scaled_size)

                    # Scale position
                    scaled_pos = (
                        int(prop['pos'][0] * self.scale_factor),
                        int(prop['pos'][1] * self.scale_factor)
                    )

                    # add main items to lists
                    self.items.append(scaled_img)
                    self.item_positions.append(scaled_pos)
                    item_rect = pygame.Rect(scaled_pos[0], scaled_pos[1], scaled_size[0], scaled_size[1])
                    self.item_rects.append(item_rect)

                    # store item information
                    self.item_info[prop['id']] = {
                        'type': prop['type'],
                        'rect': item_rect,
                        'stickynotes': []
                    }

                    # associated sticky notes
                    for stickynote in prop['stickynotes']:
                        stickynote_pos = (
                            scaled_pos[0] + int(stickynote['offset'][0] * self.scale_factor),
                            scaled_pos[1] + int(stickynote['offset'][1] * self.scale_factor)
                        )

                        # load sticky note img
                        self.cursor.execute("SELECT Item_Image FROM MapsItems WHERE MapsItemsID = ?",
                                            stickynote['id'])
                        stickynote_img_data = self.cursor.fetchone()
                        if stickynote_img_data and stickynote_img_data[0]:
                            stickynote_img = pygame.image.load(
                                io.BytesIO(bytes(stickynote_img_data[0]))).convert_alpha()
                            stickynote_img = pygame.transform.scale(stickynote_img,
                                                                    (int(35 * self.scale_factor),
                                                                     int(34 * self.scale_factor)))

                            # Store sticky note data
                            self.items.append(stickynote_img)
                            self.item_positions.append(stickynote_pos)
                            stickynote_rect = pygame.Rect(stickynote_pos[0], stickynote_pos[1],
                                                          int(35 * self.scale_factor),
                                                          int(34 * self.scale_factor))
                            self.item_rects.append(stickynote_rect)

                            # map sticky notes to respective items
                            self.stickynote_to_item[stickynote['id']] = prop['id']
                            self.item_info[prop['id']]['stickynotes'].append({
                                'id': stickynote['id'],
                                'rect': stickynote_rect,
                                'position': stickynote_pos
                            })

                else:
                    print(f"Item {prop['id']} not found in database")
                    # Add placeholder if item missing
                    surf = pygame.Surface((10, 10))
                    surf.fill((255, 0, 255))  # Magenta placeholder
                    self.items.append(surf)
                    self.item_positions.append((
                        int(prop['pos'][0] * self.scale_factor),
                        int(prop['pos'][1] * self.scale_factor))
                    )

            print(f"Loaded {len(self.items)} items for map {self.level_config['maps_id']}")

        except Exception as e:
            print("Error loading items from database:", e)
            # Fallback to empty lists if error occurs
            self.items = []
            self.item_positions = []
            self.item_rects = []
            self.item_info = {}
            self.stickynotenote_to_item = {}

    def setup_game_objects(self):
        """Setup all game objects with collision"""
        def scale_rect(rect):
            return pygame.Rect(
                int(rect[0] * self.scale_factor),
                int(rect[1] * self.scale_factor),
                int(rect[2] * self.scale_factor),
                int(rect[3] * self.scale_factor)
            )

        # Walls
        self.walls = [scale_rect(wall) for wall in self.level_config['walls']]

        # Objects
        self.objects = [scale_rect(obj) for obj in self.level_config['objects']]

        # Doors
        def scale_door(door):
            return {
                "door_area": scale_rect(door["door_area"]),
                "floor_area": scale_rect(door["floor_area"]),
                "destination": (
                    int(door["destination"][0] * self.scale_factor),
                    int(door["destination"][1] * self.scale_factor)
                )
            }

        self.doors = [scale_door(door) for door in self.level_config['doors']]

    def check_collision(self, new_x, new_y):
        """Check for collisions with walls and objects"""
        char_rect = pygame.Rect(new_x, new_y, self.char_width, self.char_height)
        for wall in self.walls:
            if char_rect.colliderect(wall):
                return True
        for obj in self.objects:
            if char_rect.colliderect(obj):
                return True
        return False
    
    def handle_events(self):
        """Handle all pygame events"""
        for event in pygame.event.get():
            if event.type == QUIT:
                if self.ensure_connection():
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
                self.close_connection()
                self.running = False
                
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    # Create and run options menu
                    options = Options(self.screen, self.tp_number, self.level, self.time_remaining)
                    result = options.run()
                    if result == 'exit':
                        if self.ensure_connection():
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
                        self.close_connection()
                        self.running = False
                    # If result is 'return', continue the game
                elif event.key == K_TAB:
                    self.current_question['visible'] = False
                    self.current_passcode_input['visible'] = False
                    self.feedback_message = None
                    self.passcode_visible = False
                    for input_box in self.passcode_inputs:
                        input_box['active'] = False  # Only deactivate, don't clear
                    self.input_active = False
                    self.input_text = ""
                    self.show_notes = False
                    self.show_hints = False
                elif event.key == K_RETURN:
                    if self.show_notes:
                        self.show_notes = False
                    elif self.is_completed:
                        self.conn.autocommit = False
                        try:
                            self.cursor.execute("""
                                UPDATE s
                                SET s.student_answer = '', s.status = 0
                                FROM Submissions s
                                JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                                WHERE s.TP_Number = ? AND q.LevelID = ?
                            """, self.tp_number, self.level)
                            self.conn.commit()

                            self.cursor.execute("""
                                UPDATE LevelSelection
                                SET is_completed = 0, time_remaining = 600
                                WHERE TP_Number = ? AND LevelID = ?
                            """, self.tp_number, self.level)
                            self.time_remaining = 600
                            self.conn.commit()
                        except Exception as e:
                            self.conn.rollback()
                            print(f"Database error: {e}")
                        self.conn.autocommit = True
                        self.is_completed = False  # to levelSelection

                elif (event.key == K_p and not self.current_question['visible'] and not self.door_unlocked
                      and not self.passcode_visible and not self.is_completed and not self.show_completion and not self.show_fail
                      and not self.show_notes and not self.show_hints):
                    self.show_passcode_inputs()
                elif (event.key == K_e and not self.current_question['visible'] and not self.current_passcode_input[
                    'visible'] and not self.is_completed and not self.show_completion and not self.show_fail and not self.show_notes
                      and not self.show_hints):
                    self.handle_stickynote_call()

                elif event.key == K_q and (self.is_completed or self.show_completion or self.show_fail) and not(self.show_notes):
                    if self.is_completed:
                        self.conn.autocommit = False
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
                        finally:
                            self.conn.autocommit = True
                            # Proper cleanup before switching
                            pygame.quit()
                            pygame.init()
                            # Create new display with consistent size
                            level_selection_screen = pygame.display.set_mode((1024, 768))
                            levelSelection(level_selection_screen, self.tp_number).run()
                            self.running = False
                    elif self.show_completion or self.show_fail:
                        if self.show_completion:
                            self.conn.autocommit = False
                            try:
                                self.cursor.execute("""
                                    UPDATE LevelSelection
                                    SET time_remaining = ?, is_completed = ?
                                    WHERE TP_Number = ? AND LevelID = ?
                                """, self.time_remaining, 1, self.tp_number, self.level)

                                level_index = int(self.level[-1]) + 1
                                next_level = f"LVL00{level_index}"

                                self.cursor.execute("""
                                    SELECT current_level
                                    FROM Students
                                    WHERE TP_Number = ?
                                """, self.tp_number)
                                db_level = self.cursor.fetchone()

                                if db_level[0] < level_index:
                                    if self.level != "LVL005":
                                        self.cursor.execute("""
                                            UPDATE Students
                                            SET Score = Score + ?, current_level = ?
                                            WHERE TP_Number = ?
                                        """, self.points, level_index, self.tp_number)

                                        # unlock next level (not necessary for last level LVL005)
                                        self.cursor.execute("""
                                            UPDATE LevelSelection
                                            SET is_locked = 0
                                            WHERE TP_Number = ? AND LevelID = ?
                                        """, self.tp_number, next_level)
                                    else:
                                        self.cursor.execute("""
                                            UPDATE Students
                                            SET Score = Score + ?
                                            WHERE TP_Number = ?
                                        """, self.points, self.tp_number)

                                self.conn.commit()
                            except Exception as e:
                                self.conn.rollback()
                                print(f"Database error: {e}")

                        elif self.show_fail:
                            self.conn.autocommit = False
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

                        self.conn.autocommit = True
                        # Proper cleanup before switching
                        pygame.quit()
                        pygame.init()
                        # Create new display with consistent size
                        level_selection_screen = pygame.display.set_mode((1024, 768))
                        levelSelection(level_selection_screen, self.tp_number).run()
                        self.running = False

                # handle input based on active UI
                if self.current_passcode_input['visible']:  # process passcode-related input
                    if event.key == K_RETURN:
                        self.feedback_message = None
                        print(self.feedback_message)
                        self.check_passcodes()
                    elif event.key == K_BACKSPACE:
                        for input_box in self.passcode_inputs:
                            if input_box['active']:
                                input_box['text'] = ""
                                print(f"input_box['text']: {input_box['text']}")
                elif self.current_question['visible'] and not self.is_correct:  # process question-related input
                    if event.key == K_RETURN:
                        self.check_answer()
                    elif event.key == K_BACKSPACE:
                        self.input_text = self.input_text[:-1]

            elif event.type == TEXTINPUT:
                # Handle text input for both question input and passcode inputs
                if self.input_active and (self.current_question['visible']) and not self.is_correct:
                    if len(self.input_text) < 200:  # Increased from 30 to 200 characters
                        self.input_text += event.text
                elif hasattr(self, 'passcode_inputs') and self.current_passcode_input['visible']:  # edit
                    for input_box in self.passcode_inputs:
                        if input_box['active'] and len(input_box['text']) < input_box['limit']:
                            input_box['text'] = event.text  # Store the character
                            # Move to next box automatically
                            current_index = self.passcode_inputs.index(input_box)
                            if current_index < len(self.passcode_inputs) - 1:
                                input_box['active'] = False
                                self.passcode_inputs[current_index + 1]['active'] = True
                            break

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:  # left mouse click
                self.input_active = False
                mouse_pos = event.pos

                # Reset all passcode input activeness
                for input_box in self.passcode_inputs:
                    input_box['active'] = False

                    # Check if clicking on passcode input boxes
                    if self.current_passcode_input['visible']:
                        for input_box in self.passcode_inputs:
                            screen_rect = pygame.Rect(
                                self.current_passcode_input['position'][0] + input_box['rect'].x,
                                self.current_passcode_input['position'][1] + input_box['rect'].y,
                                input_box['rect'].width,
                                input_box['rect'].height
                            )
                            if screen_rect.collidepoint(mouse_pos):
                                input_box['active'] = True
                                break

                # Check if clicking on exclamation mark (door prompt)
                if self.door_message_visible:
                    exclamation_rect = pygame.Rect(
                        self.door_message_position[0] - self.door_message_radius,
                        self.door_message_position[1] - self.door_message_radius,
                        self.door_message_radius * 2,
                        self.door_message_radius * 2
                    )
                    if exclamation_rect.collidepoint(mouse_pos):
                        self.show_completion = True
                        self.show_completion_message()
                        continue

                # Check if clicking on question mark (hint prompt)
                if hasattr(self, 'hint_text_rect') and self.hint_text_rect and self.hint_text_rect.collidepoint(mouse_pos):
                    self.current_question['visible'] = False
                    self.current_passcode_input['visible'] = False
                    self.show_hints = True

                # First check if clicking on any UI elements when a question/passcode screen is visible
                if hasattr(self, 'current_question') and self.current_question['visible']:
                    # Check for passcode input boxes (new functionality)
                    if hasattr(self, 'passcode_inputs'):
                        for input_box in self.passcode_inputs:
                            # Convert input rect to screen coordinates
                            screen_rect = pygame.Rect(
                                self.current_question['position'][0] + input_box['rect'].x,
                                self.current_question['position'][1] + input_box['rect'].y,
                                input_box['rect'].width,
                                input_box['rect'].height
                            )

                            if screen_rect.collidepoint(mouse_pos):
                                input_box['active'] = True
                            else:
                                input_box['active'] = False

                    # Check original question input box
                    if hasattr(self, 'input_rect') and self.input_rect and self.input_rect.collidepoint(mouse_pos):
                        self.input_active = True
                else:
                    # Check if click is on a sticky note
                    for item_id, item_data in self.item_info.items():
                        for stickynote in item_data['stickynotes']:
                            if stickynote['rect'].collidepoint(mouse_pos):
                                char_center = pygame.Rect(self.char_x, self.char_y, self.char_width, self.char_height).center
                                stickynote_center = stickynote['rect'].center
                                distance = ((char_center[0] - stickynote_center[0]) ** 2 + (
                                        char_center[1] - stickynote_center[1]) ** 2) ** 0.5
                                interaction_radius = 130 * self.scale_factor

                                if distance <= interaction_radius:
                                    print(f"Clicked note near {item_data['type']} (ID: {item_id})")
                                    index = int(item_id[-1]) - 1
                                    question_id = self.question_ids[index]
                                    self.handle_stickynote_interaction(question_id)
                                    break  # Exit the loop once we've found and handled the clicked note

            elif event.type == MOUSEMOTION:
                # Force cursor update on mouse movement
                self.render()

    def draw_timer(self):
        """Render the countdown timer on screen"""
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        time_text = f"Time: {minutes:02d}:{seconds:02d}"

        timer_font = pygame.font.Font(None, int(28 * self.scale_factor))
        timer_surface = timer_font.render(time_text, True, (255, 255, 255))

        # Position in top-right corner with some padding
        timer_x = self.width - timer_surface.get_width() - 20
        timer_y = 20

        # Add background for better visibility
        bg_rect = pygame.Rect(
            timer_x - 10,
            timer_y - 5,
            timer_surface.get_width() + 20,
            timer_surface.get_height() + 10
        )
        pygame.draw.rect(self.screen, (50, 50, 50, 200), bg_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), bg_rect, 2)

        self.screen.blit(timer_surface, (timer_x, timer_y))

    def display_notes(self):
        try:
            self.cursor.execute("""
                SELECT Title, Content, Hint
                FROM Notes
                WHERE LevelID = ?
            """, self.level)
            notes_data = self.cursor.fetchall()

            # store notes
            if notes_data:
                self.note_title = f"Topic: {notes_data[0].Title}"
                self.note_content = notes_data[0].Content
                self.note_hint = notes_data[0].Hint

        except Exception as e:
            print(f"Error fetching notes: {e}")
            # Set default values in case of error
            self.note_title = "No notes available"
            self.note_content = ""
            self.note_hint = ""

        # notes surface
        notes_width = min(self.width - 100, 1200)
        notes_height = 750
        self.notes_surface = pygame.Surface((notes_width, notes_height), pygame.SRCALPHA)
        self.notes_surface.fill((50, 50, 50))
        self.notes_pos = ((self.width - notes_width) // 2, (self.height - notes_height) // 2)

        title_font = pygame.font.Font(None, 32)
        content_font = pygame.font.Font(None, 24)
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))

        # Render title
        title_surface = title_font.render(self.note_title, True, (255, 255, 255))
        self.notes_surface.blit(title_surface, (20, 20))

        y_offset = 70
        line_height = 30

        # Split content by newlines
        paragraphs = self.note_content.split('\\n')

        for paragraph in paragraphs:
            # Handle empty paragraphs (just add spacing)
            if not paragraph.strip():
                y_offset += line_height
                continue

            # Split long lines into multiple lines if needed
            words = paragraph.split(' ')
            current_line = ""

            for word in words:
                test_line = f"{current_line} {word}".strip()
                if content_font.size(test_line)[0] <= notes_width - 40:
                    current_line = test_line
                else:
                    # Render the current line
                    line_surface = content_font.render(current_line, True, (255, 255, 255))
                    self.notes_surface.blit(line_surface, (20, y_offset))
                    y_offset += line_height
                    current_line = word

            # Render the last line of the paragraph
            if current_line:
                line_surface = content_font.render(current_line, True, (255, 255, 255))
                self.notes_surface.blit(line_surface, (20, y_offset))
                y_offset += line_height

        # "Press [Tab] to close" text
        skip_text = other_font.render("Press [Enter] to skip", True, (200, 200, 0))
        self.notes_surface.blit(skip_text, (20, notes_height - 30))

    def is_completed_message(self):
        message_width = min(self.width - 70, 600)
        message_height = 150
        self.completed_surface = pygame.Surface((message_width, message_height), pygame.SRCALPHA)
        self.completed_surface.fill((50, 50, 50))
        self.completed_pos = ((self.width - message_width) // 2, (self.height - message_height) // 2)

        message_font = pygame.font.Font(None, 30)
        other_font = pygame.font.Font(None, 26)
        y_offset = 20

        # render message
        message_surface = message_font.render("Level already completed. Would you like to reattempt?", True, (255, 255, 255))
        message_x = (message_width - message_surface.get_width()) // 2
        self.completed_surface.blit(message_surface, (message_x, y_offset))

        # "Press [Enter]" text
        yes_text = other_font.render("Yes (Press [Enter])", True, (200, 200, 0))
        yes_x = (message_width - yes_text.get_width()) // 2
        self.completed_surface.blit(yes_text, (yes_x, y_offset + 50))

        # "Press [Q]" text
        no_text = other_font.render("No (Press [Q])", True, (200, 200, 0))
        no_x = (message_width - no_text.get_width()) // 2
        self.completed_surface.blit(no_text, (no_x, y_offset + 90))

    def get_all_passcodes(self):
        """Retrieve all passcodes from the database"""
        if not self.ensure_connection():
            return []

        passcodes = []
        for id in self.question_ids:
            try:
                self.cursor.execute("""
                    SELECT passcode
                    FROM QuestionDetails
                    WHERE QuestionID LIKE ?
                """, id)
                result = self.cursor.fetchone()
                passcodes.append((result, id))
                print("pass: ", passcodes)
            except Exception as e:
                print(f"Error fetching passcodes: {e}")
                return []
        return passcodes

    def display_hints(self):
        # hints surface
        hints_width = min(self.width - 100, 800)
        hints_height = 500
        self.hints_surface = pygame.Surface((hints_width, hints_height), pygame.SRCALPHA)
        self.hints_surface.fill((50, 50, 50))
        self.hints_pos = ((self.width - hints_width) // 2, (self.height - hints_height) // 2)

        title_font = pygame.font.Font(None, 36)
        hint_font = pygame.font.Font(None, 26)
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))

        # render title
        title_surface = title_font.render("Hints", True, (255, 255, 255))
        self.hints_surface.blit(title_surface, ((self.hints_surface.get_width() - title_surface.get_width()) // 2, 20))

        y_offset = 70
        line_height = 30

        # split content by newlines
        paragraphs = self.note_hint.split('\\n')

        for paragraph in paragraphs:
            if not paragraph.strip():
                y_offset += line_height
                continue

            # split long lines if needed
            words = paragraph.split(' ')
            current_line = ""

            for word in words:
                test_line = f"{current_line} {word}".strip()
                if hint_font.size(test_line)[0] <= hints_width - 40:
                    current_line = test_line
                else:
                    line_surface = hint_font.render(current_line, True, (255, 255, 255))
                    self.hints_surface.blit(line_surface, (20, y_offset))
                    y_offset += line_height
                    current_line = word

            if current_line:
                line_surface = hint_font.render(current_line, True, (255, 255, 255))
                self.hints_surface.blit(line_surface, (20, y_offset))
                y_offset += line_height

        # "Press [Tab] to close" text
        skip_text = other_font.render("Press [Tab] to close", True, (200, 200, 0))
        self.hints_surface.blit(skip_text, (20, hints_height - 30))

    def handle_stickynote_call(self):
        if self.current_question['visible'] or self.current_passcode_input['visible']:
            return

        # check distance
        for item_id, item_data in self.item_info.items():
            for stickynote in item_data['stickynotes']:
                char_center = pygame.Rect(self.char_x, self.char_y, self.char_width, self.char_height).center
                stickynote_center = stickynote['rect'].center
                distance = ((char_center[0] - stickynote_center[0]) ** 2 + (
                        char_center[1] - stickynote_center[1]) ** 2) ** 0.5
                interaction_radius = 130 * self.scale_factor

                if distance <= interaction_radius:
                    print(f"Clicked note near {item_data['type']} (ID: {item_id})")
                    index = int(item_id[-1]) - 1
                    question_id = self.question_ids[index]
                    self.handle_stickynote_interaction(question_id)
                    self.is_correct = False

    def handle_stickynote_interaction(self, question_id):
        # check if completed submission available
        print(f"\nDebug: Handling sticky note interaction for question_id: {question_id}")
        try:
            self.cursor.execute("""
                        SELECT s.status, q.passcode
                        FROM QuestionDetails q
                        LEFT JOIN Submissions s ON q.QuestionID = s.QuestionID AND s.TP_Number = ?
                        WHERE q.QuestionID = ?
                    """, self.tp_number, question_id)

            submission = self.cursor.fetchone()
            print(f"Debug: Submission query result: {submission}")
            
            if submission:
                status = submission[0] if submission[0] is not None else 0
                passcode = submission[1]
                print(f"Debug: Status: {status}, Passcode: {passcode}")

                if status == 1:
                    self.show_passcode(question_id, passcode)
                    self.passcode_visible = True
                else:
                    try:
                        print("Debug: Fetching question details...")
                        self.cursor.execute("""
                                        SELECT Question_text, correct_answer, MapsItemsID
                                        FROM QuestionDetails
                                        WHERE QuestionID = ?
                                    """, question_id)

                        row = self.cursor.fetchone()
                        print(f"Debug: Question details row: {row}")
                        
                        if row:
                            self.current_question_id = question_id
                            self.current_question_text = row[0]
                            self.current_correct_answer = row[1]  # Store the correct answer
                            self.current_item_id = row[2]  # Store the item ID for answer checking
                            print(f"Debug: Showing question with text: {self.current_question_text}")
                            self.show_question(self.current_question_text, self.current_item_id)
                        else:
                            print("Debug: No question details found")
                            self.show_question("This question appears to be blank.", self.current_item_id)
                    except Exception as e:
                        print(f"Error fetching note content: {e}")
                        self.show_question("You found a question!")

        except Exception as e:
            print(f"Error checking submissions: {e}")
            
    def show_question(self, text, item_id=None):
        """display question and input box"""
        print(f"\nDebug: Showing question with text: {text}")
        question_width = min(self.width - 40, 600)
        question_height = 200
        question_surface = pygame.Surface((question_width, question_height), pygame.SRCALPHA)
        question_surface.fill((50, 50, 50, 220))  # question background

        # render text
        ques_font = pygame.font.Font(None, int(32 * self.scale_factor))
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if ques_font.size(test_line)[0] <= question_width - 40:  # 20px padding each side
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        print(f"Debug: Split question into {len(lines)} lines: {lines}")

        # render lines
        y_offset = 20
        for line in lines:
            text_surf = ques_font.render(line, True, (255, 255, 255))
            question_surface.blit(text_surf, (20, y_offset))
            y_offset += 25

        # "Press [Tab] to close" text
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))
        close_text = other_font.render("Press [Tab] to close", True, (200, 200, 0))
        question_surface.blit(close_text, (20, 160))

        # input box
        input_width = question_width - 40
        input_height = 35
        input_x = 20
        input_y = y_offset + 20

        # Calculate input box position relative to screen
        question_x = (self.width - question_width) // 2
        question_y = (self.height - question_height) // 2

        # Store input box rect in screen coordinates for click detection
        self.input_rect = pygame.Rect(
            question_x + input_x,
            question_y + input_y,
            input_width,
            input_height
        )

        border_colour = (100, 100, 255) if self.input_active else (200, 200, 200)
        pygame.draw.rect(question_surface, border_colour, (input_x, input_y, input_width, input_height), 2)

        # submit instruction
        submit_text = other_font.render("Press [Enter] to submit", True, (200, 200, 0))
        question_surface.blit(submit_text, (20, 135))

        # Initialize input properties
        input_props = {
            'x': input_x,
            'y': input_y,
            'width': input_width,
            'height': input_height
        }

        # Store input box rect in screen coordinates for click detection
        self.input_rect = pygame.Rect(
            question_x + input_x,
            question_y + input_y,
            input_width,
            input_height
        )

        # Store question info
        self.current_question = {
            'surface': question_surface,
            'position': (question_x, question_y),
            'visible': True,
            'input_properties': input_props
        }

    def check_answer(self):
        """validate answer submitted"""
        if not hasattr(self, 'current_item_id'):
            return  # No active question

        print(f"Submitted: {self.input_text}")
        index = int(self.current_item_id[-1]) - 1
        question_id = self.question_ids[index]

        try:
            self.cursor.execute("""
                SELECT correct_answer, passcode
                FROM QuestionDetails
                WHERE MapsItemsID = ? AND QuestionID = ?
                """, self.current_item_id, question_id)

            self.is_correct = False
            row = self.cursor.fetchone()
            if row:
                correct_answer = row[0]
                passcode = row[1]
                user_answer = self.input_text.strip()
                self.is_correct = (user_answer == correct_answer)

                if self.is_correct:
                    print("Correct answer")
                    self.show_feedback(f"Correct! Reopen this note to get your passcode.", (0, 255, 0))
                else:
                    print("Incorrect answer")
                    self.show_feedback("Incorrect! Please try again.", (255, 0, 0))
            else:
                print("No correct answer found in database")
                self.show_feedback("Error validating answer.", (255, 165, 0))  # Orange for error

            # get SubmissionID
            self.cursor.execute("""
                SELECT MAX(CAST(SUBSTRING(SubmissionID, 4, LEN(SubmissionID)) AS INT))
                FROM Submissions
                WHERE SubmissionID LIKE 'SBM%'
                """)
            max_id = self.cursor.fetchone()[0] or 0
            next_id = f"SBM{max_id + 1:05d}"

            # record submission in database
            self.cursor.execute("""
                MERGE INTO Submissions AS target
                USING (VALUES (?, ?, ?, ?, ?)) AS source (SubmissionID, QuestionID, TP_Number, student_answer, status)
                ON target.TP_Number = source.TP_Number AND target.QuestionID = source.QuestionID
                WHEN MATCHED THEN
                    UPDATE SET status = source.status, student_answer = CAST(source.student_answer AS varchar(max))
                WHEN NOT MATCHED THEN
                    INSERT (SubmissionID, QuestionID, TP_Number, student_answer, status)
                    VALUES (source.SubmissionID, source.QuestionID, source.TP_Number, CAST(source.student_answer AS varchar(max)), source.status);
            """,
                                next_id,
                                self.current_question_id,
                                self.tp_number,
                                self.input_text,
                                1 if self.is_correct else 0)

            self.conn.commit()

        except Exception as e:
            print(f"Error checking answer: {e}")
            self.show_feedback("Error checking answer", (255, 165, 0))

        finally:
            # Reset input
            self.input_text = ""

    def show_feedback(self, message, colour):
        """Store feedback message to be displayed in render()"""
        self.feedback_message = message
        self.feedback_color = colour
        self.feedback_timestamp = pygame.time.get_ticks()  # Record when feedback was shown

    def show_passcode(self, question_id, passcode):
        """display only passcode if question completed"""
        # Get the item image if available
        item_img = None
        item_type = "Item"

        # Get MapsItemsID based on QuestionID
        self.cursor.execute("""
            SELECT MapsItemsID
            FROM QuestionDetails
            WHERE QuestionID = ?
        """, question_id)

        item_id_row = self.cursor.fetchone()
        if item_id_row:
            item_id = item_id_row[0]  # Extract the string value from the row

            if item_id and item_id in self.item_info:
                print(f"Item info for {item_id}: {self.item_info[item_id]}")
                # Find the item in our items list by matching position
                for i, pos in enumerate(self.item_positions):
                    item_rect = self.item_info[item_id].get('rect')
                    if item_rect and pos[0] == item_rect.x and pos[1] == item_rect.y:
                        item_img = self.items[i]
                        print(f"Found item image at index {i}")  # Debug
                        break

        passcode_width = min(self.width - 40, 400)
        passcode_height = 180 if item_img else 150
        passcode_surface = pygame.Surface((passcode_width, passcode_height), pygame.SRCALPHA)
        passcode_surface.fill((50, 50, 50, 220))

        # render passcode
        p_font = pygame.font.Font(None, 26)
        t_font = pygame.font.Font(None, 30)

        # Draw item image if available (scaled down)
        if item_img:
            # Scale down the image to fit (max 100px height)
            img_height = max(90, item_img.get_height())
            scale_factor = img_height / item_img.get_height()
            img_width = int(item_img.get_width() * scale_factor)
            scaled_img = pygame.transform.scale(item_img, (img_width, img_height))

            # Position image at top center
            img_x = (passcode_width - img_width) // 2
            passcode_surface.blit(scaled_img, (img_x, 10))

            passcode_text = p_font.render(f"Passcode: {passcode}", True, (0, 255, 0))
            passcode_surface.blit(passcode_text,
                                  ((passcode_width - passcode_text.get_width()) // 2, 100))

        else:
            item_text = t_font.render(f"Item: {item_type}", True, (255, 255, 255))
            passcode_surface.blit(item_text,
                                  ((passcode_width - item_text.get_width()) // 2, 20))

            passcode_text = p_font.render(f"Passcode: {passcode}", True, (0, 255, 0))
            passcode_surface.blit(passcode_text,
                                  ((passcode_width - passcode_text.get_width()) // 2, 70))


        # "Press [Tab] to close" text
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))
        close_text = other_font.render("Press [Tab] to close, then press [P] to input passcode", True, (200, 200, 0))
        passcode_surface.blit(close_text, ((passcode_width - close_text.get_width()) // 2, passcode_height - 35))

        self.current_passcode_input = {
            'surface': passcode_surface,
            'position': ((self.width - passcode_width) // 2, (self.height - passcode_height) // 2),
            'submit_rect': None,
            'visible': True
        }

    def show_passcode_inputs(self):
        """Show a screen with all passcode inputs"""
        # Preserve existing inputs if they exist
        existing_inputs = {}
        if hasattr(self, 'passcode_inputs'):
            for input_box in self.passcode_inputs:
                existing_inputs[input_box['question_id']] = input_box['text']

        # Clear and reset inputs while preserving values
        self.passcode_inputs = []

        surface_width = min(self.width - 100, 800)
        surface_height = 400
        passcode_surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
        passcode_surface.fill((50, 50, 50, 220))

        title_font = pygame.font.Font(None, 34)
        input_font = pygame.font.Font(None, 26)
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))

        # Title
        title_text = title_font.render("Enter All Passcodes:", True, (255, 255, 255))
        title_x = (surface_width - title_text.get_width()) // 2
        passcode_surface.blit(title_text, (title_x, 30))

        # Get all passcodes
        passcodes = self.get_all_passcodes()

        # Initialize display positions
        self.item_display_positions = []

        # Top row - Map items
        item_size = 50
        item_spacing = 70
        start_x = (surface_width - (len(passcodes) * (item_size + item_spacing) - item_spacing)) // 2
        y_pos = 120
        input_y_pos = y_pos + item_size + 30

        for i, (passcode, question_id) in enumerate(passcodes):
            # Get the MapsItemsID for this question
            self.cursor.execute("""
                SELECT MapsItemsID 
                FROM QuestionDetails 
                WHERE QuestionID = ?
            """, question_id)
            maps_items_id = self.cursor.fetchone()[0]

            # Find the item in our item_info
            if maps_items_id in self.item_info:
                item_data = self.item_info[maps_items_id]
                item_rect = item_data['rect']

                # Find the corresponding image in our items list
                for item_idx, pos in enumerate(self.item_positions):
                    if pos[0] == item_rect.x and pos[1] == item_rect.y:
                        item_img = self.items[item_idx]

                        # Scale the image to fit our display size
                        scale_factor = max(1.0, item_size / item_img.get_width(), item_size / item_img.get_height())
                        scaled_width = int(item_img.get_width() * scale_factor)
                        scaled_height = int(item_img.get_height() * scale_factor)
                        scaled_img = pygame.transform.scale(item_img, (scaled_width, scaled_height))

                        # Calculate position
                        x_pos = start_x + i * (item_size + item_spacing) + (item_size - scaled_width) // 2

                        # Draw the item
                        passcode_surface.blit(scaled_img, (x_pos, y_pos + (item_size - scaled_height) // 2))

                        # Store position for input box alignment
                        self.item_display_positions.append({
                            'x': x_pos + scaled_width // 2,
                            'y': y_pos + item_size + 10,
                            'question_id': question_id,
                            'passcode': passcode
                        })
                        break

        # Initialize passcode_inputs with preserved values
        for item_pos in self.item_display_positions:
            input_box_size = 30
            input_x = item_pos['x'] - input_box_size // 2

            # Use preserved value if available
            input_text = existing_inputs.get(item_pos['question_id'], "")

            self.passcode_inputs.append({
                'rect': pygame.Rect(input_x, input_y_pos, input_box_size, input_box_size),
                'text': input_text,
                'active': False,
                'correct_passcode': item_pos['passcode'],
                'question_id': item_pos['question_id'],
                'limit': 1
            })

        # "Press [Enter] to submit" text
        submit_text = other_font.render("Press [Enter] to submit", True, (200, 200, 0))
        passcode_surface.blit(submit_text, (20, surface_height - 70))

        # "Press [Tab] to close" text
        close_text = other_font.render("Press [Tab] to close", True, (200, 200, 0))
        passcode_surface.blit(close_text, (20, surface_height - 40))

        # Store as current passcode input
        self.current_passcode_input = {
            'surface': passcode_surface,
            'position': ((self.width - surface_width) // 2, (self.height - surface_height) // 2),
            'visible': True
        }

    def check_passcodes(self):
        """Validate all entered passcodes"""
        if not hasattr(self, 'passcode_inputs'):
            return

        passcode_count = 0
        correct_count = 0
        self.passcode_feedback = True
        reset = False

        for input_box in self.passcode_inputs:
            if not input_box['text']:
                self.show_feedback("Please fill in all passcodes", (255, 255, 255))
            else:
                try:
                    input_value = int(input_box['text'])
                    correct_passcode = int(input_box['correct_passcode'][0])
                    passcode_count += 1
                    if input_value != correct_passcode:
                        self.show_feedback("Not all passwords are correct. Please try again.", (255, 0, 0))
                        reset = True
                        break
                    else:
                        correct_count += 1
                        if correct_count == 6:
                            self.show_feedback("All passcodes correct! Door unlocked.", (0, 255, 0))
                            self.door_unlocked = True
                            self.current_passcode_input['visible'] = False
                except ValueError:
                    # If conversion to int fails
                    self.show_feedback("Hint: Passcodes are all numeric", (255, 255, 255))
                    reset = True
                    break

        if reset and self.passcode_inputs:
            for i, input_box in enumerate(self.passcode_inputs):
                input_box['text'] = ""
                input_box['active'] = (i == 0)

    def show_fail_message(self):
        """show "Time's Up" message if time_remaining = 0"""
        surface_width = min(self.width - 100, 500)
        surface_height = 120
        message_surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
        message_surface.fill((50, 50, 50, 220))

        title_font = pygame.font.Font(None, 38)
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))

        # Title
        title_text = title_font.render("Time's up! Game over.", True, (255, 0, 0))
        title_x = (surface_width - title_text.get_width()) // 2
        message_surface.blit(title_text, (title_x, 35))

        # "Press [Q] to return to Level Selection" text
        return_text = other_font.render("Press [Q] to return to Level Selection", True, (200, 200, 0))
        message_surface.blit(return_text, (20, surface_height - 30))

        self.fail_message = {
            'surface': message_surface,
            'position': ((self.width - surface_width) // 2, (self.height - surface_height) // 2),
            'visible': True
        }

    def show_completion_message(self):
        """Show level completion message when "!" clicked after passcodes submitted"""
        surface_width = min(self.width - 100, 500)
        surface_height = 200
        message_surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
        message_surface.fill((50, 50, 50, 220))

        title_font = pygame.font.Font(None, 38)
        other_font = pygame.font.Font(None, int(26 * self.scale_factor))

        # Title
        title_text = title_font.render("Level Completed!", True, (0, 255, 0))
        title_x = (surface_width - title_text.get_width()) // 2
        message_surface.blit(title_text, (title_x, 25))

        # "Press [Q] to return to Level Selection" text
        return_text = other_font.render("Press [Q] to return to Level Selection", True, (200, 200, 0))
        message_surface.blit(return_text, (20, surface_height - 30))

        self.completion_message = {
            'surface': message_surface,
            'position': ((self.width - surface_width) // 2, (self.height - surface_height) // 2),
            'visible': True
        }

    def update(self):
        """Update game state"""
        # Update timer once notes close
        if not self.show_notes and not self.is_completed:
            current_time = pygame.time.get_ticks()
            elapsed_seconds = (current_time - self.start_time) // 1000

            # Only decrement if a full second has passed
            if elapsed_seconds > self.last_second and not self.door_unlocked:
                self.last_second = elapsed_seconds
                if self.time_remaining > 0:
                    self.time_remaining -= 1
                else:
                    # Time's up - handle game over
                    self.time_remaining = 0
                    self.show_fail = True
                    self.show_fail_message()

        keys = pygame.key.get_pressed()

        # Only allow movement when no UI elements are visible
        if (not self.current_question['visible'] and not self.current_passcode_input['visible']
                and not self.show_completion and not self.show_fail):
            new_x, new_y = self.char_x, self.char_y

            # Calculate potential new positions first
            if keys[K_w] or keys[K_UP]:
                new_y -= self.speed
            if keys[K_s] or keys[K_DOWN]:
                new_y += self.speed
            if keys[K_a] or keys[K_LEFT]:
                new_x -= self.speed
            if keys[K_d] or keys[K_RIGHT]:
                new_x += self.speed

            # Check collision before actually moving
            if not self.check_collision(new_x, new_y):
                self.char_x, self.char_y = new_x, new_y

        # Keep character within bounds
        self.char_x = max(0, min(self.width - self.char_width, self.char_x))
        self.char_y = max(0, min(self.height - self.char_height, self.char_y))

        # Door interactions
        char_rect = pygame.Rect(self.char_x, self.char_y, self.char_width, self.char_height)
        current_time = pygame.time.get_ticks()
        self.active_door = None

        for door in self.doors:
            if char_rect.colliderect(door["floor_area"]):
                # Special handling for the exit door (last door in list)
                if door == self.doors[-1]:
                    continue  # Skip other interactions for exit door

                self.active_door = door
                if keys[K_f] and (current_time - self.last_tel_time > self.tel_cooldown):
                    self.char_x, self.char_y = door["destination"]
                    self.last_tel_time = current_time
                break
        else:
            self.active_door = None

    def render(self):
        # Add protection at start of render
        if not hasattr(self, 'items') or not self.items:
            print("ERROR: Items list is empty or missing!")
            # Fallback rendering or early return
            self.screen.fill((255, 0, 0))  # Red error screen
            pygame.display.flip()
            return

        """Render all game objects"""
        self.screen.blit(self.background, (0, 0))

        # Pre-calculate sticky note dimensions
        sticky_note_width = int(35 * self.scale_factor)
        sticky_note_height = int(34 * self.scale_factor)

        try:
            # First draw all sticky notes
            for item, pos in zip(self.items, self.item_positions):
                try:
                    if item.get_width() == sticky_note_width and item.get_height() == sticky_note_height:
                        self.screen.blit(item, pos)
                except Exception as e:
                    print(f"Error drawing sticky note at {pos}: {e}")

            question_id = ""

            # draw other items with submission checks
            for idx, (item, pos) in enumerate(zip(self.items, self.item_positions)):
                try:
                    # Skip sticky notes (already drawn)
                    if item.get_width() == sticky_note_width and item.get_height() == sticky_note_height:
                        continue

                    # Find corresponding item ID
                    item_id = None
                    for potential_id, item_data in self.item_info.items():
                        item_rect = item_data.get('rect')
                        if item_rect and item_rect.x == pos[0] and item_rect.y == pos[1]:
                            item_id = potential_id
                            index = int(item_id[-1]) - 1
                            question_id = self.question_ids[index]
                            break

                    if not item_id:
                        print(f"No matching item ID found for item at {pos}")
                        self.screen.blit(item, pos)
                        continue

                    # Check submission status
                    self.cursor.execute('''
                                    SELECT s.status
                                    FROM Submissions s
                                    INNER JOIN QuestionDetails q ON s.QuestionID = q.QuestionID
                                    WHERE s.TP_Number = ? AND q.MapsItemsID = ? AND s.QuestionID = ?
                                ''', (self.tp_number, item_id, question_id))

                    submission = self.cursor.fetchone()

                    # Draw if no submission or submission incorrect
                    if submission is None or submission[0] == 0:
                        self.screen.blit(item, pos)

                except Exception as e:
                    print(f"Error processing item at {pos}: {e}")
                    # Fallback: draw the item anyway
                    self.screen.blit(item, pos)

        except Exception as e:
            print(f"Critical error in render loop: {e}")
            # Fallback: draw all items without checks
            for item, pos in zip(self.items, self.item_positions):
                self.screen.blit(item, pos)

        # Draw character
        self.screen.blit(self.character, (self.char_x, self.char_y))

        # Draw notes and NPC
        if self.show_notes:
            self.display_notes()
            self.screen.blit(self.notes_surface, (self.notes_pos))
            self.screen.blit(self.npc, (self.npc_x, self.npc_y))

        # Draw completed message if available
        if self.is_completed and not self.show_notes:
            self.is_completed_message()
            self.screen.blit(self.completed_surface, (self.completed_pos))

        # Draw door instructions if available
        if self.active_door:
            door = self.active_door
            text_x = door["door_area"].x - int(45 * self.scale_factor)
            text_y = door["door_area"].y
            circle_radius = int(20 * self.scale_factor)
            circle_center = (text_x + circle_radius // 2, text_y + circle_radius // 2)
            pygame.draw.circle(self.screen, "Black", circle_center, circle_radius + 2)
            pygame.draw.circle(self.screen, "White", circle_center, circle_radius)
            self.screen.blit(self.hover_text, (text_x, text_y))

        # Draw sticky note instructions if available
        for item_id, item_data in self.item_info.items():
            for stickynote in item_data['stickynotes']:
                char_center = pygame.Rect(self.char_x, self.char_y, self.char_width, self.char_height).center
                stickynote_center = stickynote['rect'].center
                distance = ((char_center[0] - stickynote_center[0]) ** 2 + (
                        char_center[1] - stickynote_center[1]) ** 2) ** 0.5
                interaction_radius = 130 * self.scale_factor

                if distance <= interaction_radius:
                    note_x = stickynote['rect'].x - 30
                    note_y = stickynote['rect'].y - 5
                    n_circle_radius = int(20 * self.scale_factor)
                    n_circle_center = (note_x + n_circle_radius // 2, note_y + n_circle_radius // 2)
                    pygame.draw.circle(self.screen, "Black", n_circle_center, n_circle_radius + 2)
                    pygame.draw.circle(self.screen, "White", n_circle_center, n_circle_radius)
                    note_text = self.font.render("E", True, 'Black')
                    self.screen.blit(note_text, (note_x, note_y))

        # Draw "!" above closed door
        if self.door_message_visible and self.door_unlocked:
            exclamation_rect = pygame.Rect(
                self.door_message_position[0] - self.door_message_radius,
                self.door_message_position[1] - self.door_message_radius,
                self.door_message_radius * 2,
                self.door_message_radius * 2
            )

            pygame.draw.circle(self.screen, (255, 255, 255),
                               self.door_message_position,
                               self.door_message_radius)
            pygame.draw.circle(self.screen, 'black',
                               self.door_message_position,
                               self.door_message_radius, 2)
            text_rect = self.door_message_text_surface.get_rect(center=self.door_message_position)
            self.screen.blit(self.door_message_text_surface, text_rect)

            mouse_pos = pygame.mouse.get_pos()
            if exclamation_rect.collidepoint(mouse_pos):
                pygame.mouse.set_cursor(self.hover_cursor)

        # Draw "?" button for notes
        if not self.show_notes and not self.show_fail and not self.show_completion:
            pygame.draw.circle(self.screen, (255, 255, 255),
                               (self.width - 30, 65),
                               15)
            pygame.draw.circle(self.screen, 'black',
                               (self.width - 30, 65),
                               15, 2)

            hint_button_text_font = pygame.font.Font(None, 28)
            hint_button_text_surface = hint_button_text_font.render("?", True, 'black')
            self.hint_button_position = (self.width - 30, 65)
            self.hint_text_rect = hint_button_text_surface.get_rect(center=self.hint_button_position)
            self.screen.blit(hint_button_text_surface, self.hint_text_rect)

            mouse_pos = pygame.mouse.get_pos()
            if self.hint_text_rect.collidepoint(mouse_pos):
                pygame.mouse.set_cursor(self.hover_cursor)

        # Draw question if available
        if hasattr(self, 'current_question') and self.current_question['visible']:
            self.screen.blit(self.current_question['surface'], self.current_question['position'])

            # Only render input if input_properties exists and isn't None
            if (hasattr(self, 'current_question') and 'input_properties' in self.current_question and
                    self.current_question['input_properties'] is not None):
                input_props = self.current_question['input_properties']
                input_screen_x = self.current_question['position'][0] + input_props['x']
                input_screen_y = self.current_question['position'][1] + input_props['y']

                # Render the input text
                if hasattr(self, 'input_text'):
                    passcode_text_surface = self.input_font.render(self.input_text, True, (255, 255, 255))
                    self.screen.blit(passcode_text_surface, (input_screen_x + 10, input_screen_y + 10))

                    # Render cursor if active and blinking
                    if hasattr(self, 'input_active') and self.input_active and int(
                            pygame.time.get_ticks() / 600) % 2 == 0 and not self.is_correct:
                        cursor_x = input_screen_x + 10 + passcode_text_surface.get_width()
                        pygame.draw.line(self.screen, (255, 255, 255),
                                         (cursor_x, input_screen_y + 8),
                                         (cursor_x, input_screen_y + input_props['height'] - 8), 2)

        # Draw feedback if available
        if self.feedback_message:
            feedback_font = pygame.font.Font(None, 24)
            feedback_text = feedback_font.render(self.feedback_message, True, self.feedback_color)

            # Calculate dimensions with padding
            padding = 8
            text_width, text_height = feedback_text.get_size()
            surface_width = text_width + 2 * padding
            surface_height = text_height + 2 * padding

            # Create surface with correct dimensions
            feedback_surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
            feedback_surface.fill((50, 50, 50, 220))  # Semi-transparent background

            # Position the text centered on the surface
            text_x = (surface_width - text_width) // 2
            text_y = (surface_height - text_height) // 2
            feedback_surface.blit(feedback_text, (text_x, text_y))

            # Position the surface centered on screen
            if self.passcode_feedback:
                surface_rect = feedback_surface.get_rect(center=(self.width // 2, self.height // 2 - 240))
            else:
                surface_rect = feedback_surface.get_rect(center=(self.width // 2, self.height // 2 - 130))

            self.screen.blit(feedback_surface, surface_rect)

        # Draw passcode input screen if visible
        if self.current_passcode_input['visible']:
            # Draw the main passcode input surface
            self.screen.blit(self.current_passcode_input['surface'], self.current_passcode_input['position'])

            if not self.passcode_visible:
                # Draw each passcode input box
                for input_box in self.passcode_inputs:
                    # Calculate screen position of this input box
                    box_x = self.current_passcode_input['position'][0] + input_box['rect'].x
                    box_y = self.current_passcode_input['position'][1] + input_box['rect'].y
                    box_width = input_box['rect'].width
                    box_height = input_box['rect'].height

                    # Draw the input box border
                    border_color = (0, 255, 0) if input_box['active'] else (200, 200, 200)
                    pygame.draw.rect(self.screen, border_color,
                                     (box_x, box_y, box_width, box_height), 2)

                    # Draw the entered text (if any)
                    if input_box['text']:
                        text_surface = self.input_font.render(input_box['text'], True, (255, 255, 255))
                        text_x = box_x + (box_width - text_surface.get_width()) // 2
                        text_y = box_y + (box_height - text_surface.get_height()) // 2
                        self.screen.blit(text_surface, (text_x, text_y))

                    # Draw blinking cursor if active
                    if input_box['active'] and int(pygame.time.get_ticks() / 500) % 2 == 0:
                        cursor_x = box_x + box_width // 2
                        pygame.draw.line(self.screen, (255, 255, 255),
                                         (cursor_x, box_y + 5),
                                         (cursor_x, box_y + box_height - 5), 2)

        # draw hints surface
        if self.show_hints:
            self.display_hints()
            surf_pos = ((self.width - self.hints_surface.get_width()) // 2, (self.height - self.hints_surface.get_height()) // 2)
            self.screen.blit(self.hints_surface, surf_pos)

        # Draw timer (unless completion message showing)
        if not self.show_completion:
            self.draw_timer()

        # Draw completion message if available
        if self.show_completion:
            # Draw the completion message surface
            self.screen.blit(self.completion_message['surface'], self.completion_message['position'])

            # Draw the time remaining in the completion message
            minutes = self.time_remaining // 60
            seconds = self.time_remaining % 60
            time_text = f"Time Remaining: {minutes:02d}:{seconds:02d}"

            # Calculate position relative to the completion message surface
            time_font = pygame.font.Font(None, 28)
            time_surface = time_font.render(time_text, True, (255, 255, 255))

            # Position the time text below the "Level Completed" title
            time_x = self.completion_message['position'][0] + \
                     (self.completion_message['surface'].get_width() - time_surface.get_width()) // 2
            time_y = self.completion_message['position'][1] + 80

            self.screen.blit(time_surface, (time_x, time_y))

            # Draw points earned
            if self.time_remaining and self.time_remaining > 0:
                self.points = 50 + (0.5 * self.time_remaining)
            else:
                self.points = 50

            points_text = f"Points Earned: {int(self.points)}"
            points_surface = time_font.render(points_text, True, (255, 255, 255))
            points_x = self.completion_message['position'][0] + \
                       (self.completion_message['surface'].get_width() - points_surface.get_width()) // 2
            points_y = time_y + 40

            self.screen.blit(points_surface, (points_x, points_y))

        # Draw "Time's up" message if available
        if self.show_fail:
            self.screen.blit(self.fail_message['surface'], self.fail_message['position'])

        # Check for hover states
        mouse_pos = pygame.mouse.get_pos()
        cursor = self.default_cursor

        # Initialize input_rect if it doesn't exist
        if not hasattr(self, 'input_rect'):
            self.input_rect = None

        # Check if hovering over question input box
        if hasattr(self, 'current_question') and self.current_question['visible']:
            if self.input_rect is not None and self.input_rect.collidepoint(mouse_pos):
                cursor = self.text_cursor

        # Check if hovering over passcode input boxes
        if hasattr(self, 'passcode_inputs') and self.current_passcode_input['visible']:
            if hasattr(self, 'passcode_inputs'):
                for input_box in self.passcode_inputs:
                    screen_rect = pygame.Rect(
                        self.current_question['position'][0] + input_box['rect'].x,
                        self.current_question['position'][1] + input_box['rect'].y,
                        input_box['rect'].width,
                        input_box['rect'].height
                    )
                    if screen_rect.collidepoint(mouse_pos):
                        cursor = self.hover_cursor
                        break  # Found hover, no need to check others

                # Check if hovering over submit button
                if hasattr(self.current_passcode_input, 'submit_rect'):
                    submit_rect = pygame.Rect(
                        self.current_question['position'][0] + self.current_question['submit_rect'].x,
                        self.current_question['position'][1] + self.current_question['submit_rect'].y,
                        self.current_question['submit_rect'].width,
                        self.current_question['submit_rect'].height
                    )
                    if submit_rect.collidepoint(mouse_pos):
                        cursor = self.hover_cursor

        # Set the cursor
        pygame.mouse.set_cursor(cursor)
        pygame.display.flip()

    def run(self):
        """Main game loop"""
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.render()
                self.clock.tick(60)
        
        except Exception as e:
            print(f"Error in game loop: {e}")
            # Ensure database connection is closed even if there's an error
            if hasattr(self, 'conn') and self.conn:
                try:
                    self.conn.close()
                except:
                    pass
            if hasattr(self, 'cursor') and self.cursor:
                try:
                    self.cursor.close()
                except:
                    pass
        
        finally:
            # Always ensure database connections are closed
            if hasattr(self, 'conn') and self.conn:
                try:
                    self.conn.close()
                except:
                    pass
            if hasattr(self, 'cursor') and self.cursor:
                try:
                    self.cursor.close()
                except:
                    pass
            pygame.quit()
            sys.exit()