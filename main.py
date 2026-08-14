import sys
import math
import struct
import random
import pygame

# ---------------------------------------------------------
# AUDIO PRE-INIT (Fixes audio issues on Android / PC)
# ---------------------------------------------------------
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 820, 680
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Anmol Games - Cashier Simulator Ultimate Edition")

# Color Palette
BACKGROUND = (25, 25, 40)
CARD_BG = (40, 42, 60)
TEXT_COLOR = (240, 240, 240)
GREEN = (76, 175, 80)
GREEN_HOVER = (102, 187, 106)
ACCENT = (0, 188, 212)
YELLOW = (255, 193, 7)
YELLOW_HOVER = (255, 213, 79)
RED = (244, 67, 54)
RED_HOVER = (239, 83, 80)
PURPLE = (156, 39, 176)
ORANGE = (255, 152, 0)

# Fonts
font_intro_title = pygame.font.SysFont("Arial", 54, bold=True)
font_intro_sub = pygame.font.SysFont("Arial", 20, bold=True)
font_menu_title = pygame.font.SysFont("Arial", 44, bold=True)
font_title = pygame.font.SysFont("Arial", 22, bold=True)
font_btn = pygame.font.SysFont("Arial", 15, bold=True)
font_main = pygame.font.SysFont("Arial", 17)
font_mono = pygame.font.SysFont("Courier", 15)
font_pause = pygame.font.SysFont("Arial", 40, bold=True)

# ---------------------------------------------------------
# EMBEDDED BACKEND / SERVER DATABASE LOGIC
# ---------------------------------------------------------
ITEMS_DATABASE = {
    "101": {"name": "Paracetamol", "price": 12.50},
    "102": {"name": "Gloves", "price": 5.00},
    "103": {"name": "Thermometer", "price": 25.00},
    "104": {"name": "Syrup", "price": 18.00}
}

ITEMS_LIST = [
    {"code": "101", "name": "Paracetamol"},
    {"code": "102", "name": "Gloves"},
    {"code": "103", "name": "Thermometer"},
    {"code": "104", "name": "Syrup"}
]

def api_scan(code):
    """Simulates API /scan endpoint locally"""
    if code in ITEMS_DATABASE:
        return {"status": 200, "item": ITEMS_DATABASE[code]}
    return {"status": 404, "error": "Item not found"}

def api_print(items):
    """Simulates API /print endpoint locally"""
    total = sum(ITEMS_DATABASE[c]["price"] for c in items if c in ITEMS_DATABASE)
    return {"status": 200, "printed_total": total}

# ---------------------------------------------------------
# SOUND SYNTHESIZER
# ---------------------------------------------------------
def generate_tone(tone_freq, duration, volume=0.5, wave_type="sine"):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    raw_bytes = bytearray()
    
    for i in range(num_samples):
        t = float(i) / sample_rate
        if wave_type == "sine":
            val = math.sin(2.0 * math.pi * tone_freq * t)
        elif wave_type == "square":
            val = 1.0 if math.sin(2.0 * math.pi * tone_freq * t) > 0 else -1.0
        
        fade = 1.0
        if i < 500: fade = i / 500.0
        if i > num_samples - 500: fade = (num_samples - i) / 500.0

        sample_val = int(32767 * volume * val * fade)
        raw_bytes.extend(struct.pack('<h', sample_val))
        
    return pygame.mixer.Sound(buffer=bytes(raw_bytes))

# Sound Effects
SOUND_SCAN = generate_tone(tone_freq=1200, duration=0.1, volume=0.5, wave_type="sine")
SOUND_ERROR = generate_tone(tone_freq=200, duration=0.25, volume=0.5, wave_type="square")
SOUND_PRINT = generate_tone(tone_freq=880, duration=0.1, volume=0.4, wave_type="sine")
SOUND_SUCCESS = generate_tone(tone_freq=1500, duration=0.15, volume=0.5, wave_type="sine")
SOUND_BELL = generate_tone(tone_freq=650, duration=0.2, volume=0.4, wave_type="sine")
SOUND_PAUSE = generate_tone(tone_freq=500, duration=0.15, volume=0.4, wave_type="sine")
SOUND_INTRO = generate_tone(tone_freq=440, duration=0.6, volume=0.4, wave_type="sine")
SOUND_ALARM = generate_tone(tone_freq=950, duration=0.3, volume=0.6, wave_type="square")
SOUND_COMBO = generate_tone(tone_freq=1800, duration=0.2, volume=0.5, wave_type="sine")

# ---------------------------------------------------------
# GAME STATE & VARIABLES
# ---------------------------------------------------------
game_state = "INTRO"
intro_timer = 0
intro_sound_played = False

score = 0.0
input_text = ""
scanned_cart = []
scanned_cart_names = []
status_message = "Type Item Code & Press ENTER to Scan."

is_paused = False

# Upgrades Shop State
upgrades = {
    "laser_v2": False,      # Price $50
    "fast_printer": False,  # Price $75
    "coffee_boost": False   # Price $40
}

# Combo System
combo_multiplier = 1
combo_timer = 0

# Thief Event
is_thief = False
thief_caught = False

# Patience Meter
patience = 100.0

customer_x = -700
target_customer_x = 30
laser_timer = 0
printing_anim = False
receipt_height = 0
floating_text = ""
float_y = 0
float_alpha = 0

# UI Buttons Rectangles
menu_start_btn = pygame.Rect(WIDTH // 2 - 130, 310, 260, 50)
menu_shop_btn = pygame.Rect(WIDTH // 2 - 130, 380, 260, 50)
shop_back_btn = pygame.Rect(30, 20, 100, 35)

buy_laser_btn = pygame.Rect(520, 160, 120, 40)
buy_printer_btn = pygame.Rect(520, 230, 120, 40)
buy_coffee_btn = pygame.Rect(520, 300, 120, 40)

# In-Game Top Buttons
ingame_alarm_btn = pygame.Rect(380, 15, 110, 32)
ingame_pause_btn = pygame.Rect(505, 15, 80, 32)
ingame_menu_btn = pygame.Rect(595, 15, 80, 32)
ingame_quit_btn = pygame.Rect(685, 15, 85, 32)

def fetch_new_customer():
    global is_thief, thief_caught, patience
    patience = 100.0
    thief_caught = False
    
    # 20% Chance for Thief Event
    is_thief = random.random() < 0.20

    if is_thief:
        text = "🚨 [SUSPICIOUS CUSTOMER]: Scanning fake item codes..."
    else:
        num_items = random.randint(1, 3)
        requested = random.sample(ITEMS_LIST, num_items)
        names = [item["name"] for item in requested]
        
        if len(names) == 1:
            text = f"Hello! I need {names[0]}."
        elif len(names) == 2:
            text = f"Hello! I need {names[0]} and {names[1]}."
        else:
            text = f"Hello! I need {names[0]}, {names[1]}, and {names[2]}."
        
    SOUND_BELL.play()
    return text

target_text = fetch_new_customer()

running = True
clock = pygame.time.Clock()

while running:
    mouse_pos = pygame.mouse.get_pos()
    screen.fill(BACKGROUND)

    # =========================================================
    # STATE 0: ANIMATED INTRO (SPLASH SCREEN)
    # =========================================================
    if game_state == "INTRO":
        if not intro_sound_played:
            SOUND_INTRO.play()
            intro_sound_played = True

        intro_timer += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                game_state = "MENU"

        if intro_timer < 40:
            alpha = int((intro_timer / 40) * 255)
        elif intro_timer < 140:
            alpha = 255
        elif intro_timer <= 180:
            alpha = int(((180 - intro_timer) / 40) * 255)
        else:
            game_state = "MENU"
            alpha = 0

        title_surf = font_intro_title.render("🎮 ANMOL GAMES", True, ACCENT)
        sub_surf = font_intro_sub.render("P R E S E N T S", True, YELLOW)
        skip_surf = font_main.render("Press any key to skip...", True, (120, 120, 150))

        alpha_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alpha_surf.fill((0, 0, 0, 0))

        pulse_y = math.sin(intro_timer * 0.08) * 4

        title_surf.set_alpha(max(0, alpha))
        sub_surf.set_alpha(max(0, alpha))
        skip_surf.set_alpha(min(max(0, alpha), 150))

        alpha_surf.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 50))
        alpha_surf.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, HEIGHT // 2 + 20 + pulse_y))
        alpha_surf.blit(skip_surf, (WIDTH // 2 - skip_surf.get_width() // 2, HEIGHT - 50))

        screen.blit(alpha_surf, (0, 0))

    # =========================================================
    # STATE 1: MAIN MENU
    # =========================================================
    elif game_state == "MENU":
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if menu_start_btn.collidepoint(mouse_pos):
                    SOUND_SUCCESS.play()
                    game_state = "PLAYING"
                elif menu_shop_btn.collidepoint(mouse_pos):
                    SOUND_BELL.play()
                    game_state = "SHOP"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    SOUND_SUCCESS.play()
                    game_state = "PLAYING"

        m_title = font_menu_title.render("🎮 ANMOL GAMES", True, ACCENT)
        m_sub = font_main.render("Pharmacy Cashier Simulator (Ultimate Edition)", True, TEXT_COLOR)
        screen.blit(m_title, (WIDTH // 2 - m_title.get_width() // 2, 140))
        screen.blit(m_sub, (WIDTH // 2 - m_sub.get_width() // 2, 210))

        # Start Game Button
        s_color = GREEN_HOVER if menu_start_btn.collidepoint(mouse_pos) else GREEN
        pygame.draw.rect(screen, s_color, menu_start_btn, border_radius=10)
        st_txt = font_title.render("▶ START GAME", True, (255, 255, 255))
        screen.blit(st_txt, (menu_start_btn.centerx - st_txt.get_width() // 2, menu_start_btn.centery - st_txt.get_height() // 2))

        # Upgrade Shop Button
        sh_color = YELLOW_HOVER if menu_shop_btn.collidepoint(mouse_pos) else YELLOW
        pygame.draw.rect(screen, sh_color, menu_shop_btn, border_radius=10)
        sh_txt = font_title.render("🛒 UPGRADE SHOP", True, (20, 20, 30))
        screen.blit(sh_txt, (menu_shop_btn.centerx - sh_txt.get_width() // 2, menu_shop_btn.centery - sh_txt.get_height() // 2))

    # =========================================================
    # STATE 2: UPGRADE SHOP
    # =========================================================
    elif game_state == "SHOP":
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if shop_back_btn.collidepoint(mouse_pos):
                    game_state = "MENU"
                elif buy_laser_btn.collidepoint(mouse_pos) and not upgrades["laser_v2"]:
                    if score >= 50:
                        score -= 50
                        upgrades["laser_v2"] = True
                        SOUND_SUCCESS.play()
                    else: SOUND_ERROR.play()
                elif buy_printer_btn.collidepoint(mouse_pos) and not upgrades["fast_printer"]:
                    if score >= 75:
                        score -= 75
                        upgrades["fast_printer"] = True
                        SOUND_SUCCESS.play()
                    else: SOUND_ERROR.play()
                elif buy_coffee_btn.collidepoint(mouse_pos) and not upgrades["coffee_boost"]:
                    if score >= 40:
                        score -= 40
                        upgrades["coffee_boost"] = True
                        SOUND_SUCCESS.play()
                    else: SOUND_ERROR.play()

        # Header
        pygame.draw.rect(screen, CARD_BG, shop_back_btn, border_radius=6)
        screen.blit(font_btn.render("⬅ Back", True, TEXT_COLOR), (48, 28))
        screen.blit(font_menu_title.render("🛒 CASHIER SHOP", True, YELLOW), (WIDTH // 2 - 150, 40))
        screen.blit(font_title.render(f"Balance: ${score:.2f}", True, GREEN), (620, 45))

        # Items List
        items = [
            ("⚡ Neon Laser Scanner v2", "$50.00", "Neon laser & double combo timer!", upgrades["laser_v2"], buy_laser_btn, 160),
            ("🖨️ Auto Fast Printer", "$75.00", "Prints receipts 3x faster!", upgrades["fast_printer"], buy_printer_btn, 230),
            ("☕ Energy Drink (Coffee)", "$40.00", "Customer patience decays 50% slower!", upgrades["coffee_boost"], buy_coffee_btn, 300),
        ]

        for title, cost, desc, owned, rect, y in items:
            pygame.draw.rect(screen, CARD_BG, (100, y, 620, 55), border_radius=8)
            screen.blit(font_title.render(title, True, ACCENT), (115, y + 8))
            screen.blit(font_main.render(desc, True, (180, 180, 200)), (115, y + 30))
            
            if owned:
                pygame.draw.rect(screen, (60, 60, 80), rect, border_radius=6)
                screen.blit(font_btn.render("OWNED", True, GREEN), (rect.centerx - 22, rect.centery - 8))
            else:
                btn_c = GREEN_HOVER if rect.collidepoint(mouse_pos) else GREEN
                pygame.draw.rect(screen, btn_c, rect, border_radius=6)
                screen.blit(font_btn.render(f"BUY {cost}", True, (255, 255, 255)), (rect.centerx - 35, rect.centery - 8))

    # =========================================================
    # STATE 3: PLAYING GAME
    # =========================================================
    elif game_state == "PLAYING":
        
        # ---------------------------------------------------------
        # EVENTS HANDLING
        # ---------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Police Alarm Click
                if ingame_alarm_btn.collidepoint(mouse_pos):
                    if is_thief and not thief_caught:
                        SOUND_ALARM.play()
                        thief_caught = True
                        score += 25.0
                        status_message = "🚨 THIEF CAUGHT! +$25.00 Police Reward!"
                        floating_text = "+$25.00"
                        float_y = 180
                        float_alpha = 255
                        target_text = fetch_new_customer()
                        customer_x = -700
                    else:
                        status_message = "False Alarm! Fine -$5.00"
                        score = max(0, score - 5.0)
                        SOUND_ERROR.play()

                # Pause Button
                elif ingame_pause_btn.collidepoint(mouse_pos):
                    is_paused = not is_paused
                    SOUND_PAUSE.play()
                    status_message = "Game Paused." if is_paused else "Game Resumed!"
                elif ingame_menu_btn.collidepoint(mouse_pos):
                    game_state = "MENU"
                elif ingame_quit_btn.collidepoint(mouse_pos):
                    running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q: running = False
                elif event.key == pygame.K_m: game_state = "MENU"
                elif event.key == pygame.K_p:
                    is_paused = not is_paused
                    SOUND_PAUSE.play()
                elif event.key == pygame.K_a:
                    # Press A for Alarm Shortcut
                    if is_thief and not thief_caught:
                        SOUND_ALARM.play()
                        thief_caught = True
                        score += 25.0
                        status_message = "🚨 THIEF CAUGHT! +$25.00 Reward!"
                        floating_text = "+$25.00"
                        float_y = 180
                        float_alpha = 255
                        target_text = fetch_new_customer()
                        customer_x = -700

                elif not is_paused and not printing_anim:
                    if event.key == pygame.K_RETURN:
                        code_entered = input_text.strip()
                        if is_thief:
                            status_message = "🚨 DON'T SCAN THIEF ITEMS! Click ALARM or Press 'A'!"
                            SOUND_ERROR.play()
                        else:
                            res = api_scan(code_entered)
                            if res["status"] == 200:
                                item_data = res["item"]
                                scanned_cart.append(code_entered)
                                scanned_cart_names.append(f"{item_data['name']} (${item_data['price']})")
                                status_message = f"Scanned: {item_data['name']}"
                                laser_timer = 10
                                
                                # Combo increment
                                combo_multiplier = min(3, combo_multiplier + 1)
                                combo_timer = 300 if upgrades["laser_v2"] else 180
                                
                                SOUND_SCAN.play()
                                if combo_multiplier > 1: SOUND_COMBO.play()
                            else:
                                status_message = f"Invalid Code '{code_entered}'!"
                                combo_multiplier = 1
                                SOUND_ERROR.play()
                        input_text = ""

                    elif event.key == pygame.K_SPACE:
                        if len(scanned_cart) > 0:
                            printing_anim = True
                            receipt_height = 0
                            status_message = "Printing Receipt..."
                        else:
                            status_message = "Cart empty! Scan items first."
                            SOUND_ERROR.play()

                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        if event.unicode.isalnum() and len(input_text) < 5:
                            input_text += event.unicode

        # ---------------------------------------------------------
        # ANIMATIONS & GAME MECHANICS
        # ---------------------------------------------------------
        if not is_paused:
            customer_x += (target_customer_x - customer_x) * 0.1

            # Patience Decay Logic
            decay_rate = 0.08 if upgrades["coffee_boost"] else 0.15
            patience -= decay_rate
            if patience <= 0:
                patience = 100.0
                score = max(0, score - 10.0)
                status_message = "😡 Customer got angry & left! Fine -$10.00"
                SOUND_ERROR.play()
                scanned_cart = []
                scanned_cart_names = []
                target_text = fetch_new_customer()
                customer_x = -700

            # Combo Decay Logic
            if combo_timer > 0:
                combo_timer -= 1
            else:
                combo_multiplier = 1

            if laser_timer > 0: laser_timer -= 1

            # Print Logic
            if printing_anim:
                speed = 20 if upgrades["fast_printer"] else 8
                receipt_height += speed
                if receipt_height % 20 == 0: SOUND_PRINT.play()
                    
                if receipt_height >= 120:
                    printing_anim = False
                    res = api_print(scanned_cart)
                    base_earned = res["printed_total"]
                    
                    # Fast service bonus tip
                    tip = 5.0 if patience > 60 else 0.0
                    earned = (base_earned * combo_multiplier) + tip
                    score += earned
                    
                    floating_text = f"+${earned:.2f}" + (f" (x{combo_multiplier} Combo!)" if combo_multiplier > 1 else "")
                    float_y = 180
                    float_alpha = 255
                    status_message = f"SUCCESS! Earned +${earned:.2f}" + (f" (Includes $5 Tip!)" if tip > 0 else "")
                    SOUND_SUCCESS.play()

                    scanned_cart = []
                    scanned_cart_names = []
                    target_text = fetch_new_customer()
                    customer_x = -700

            if float_alpha > 0:
                float_y -= 1.5
                float_alpha -= 4

        # ---------------------------------------------------------
        # DRAW GAMEPLAY UI
        # ---------------------------------------------------------
        # Top Header
        screen.blit(font_title.render("🎮 Anmol Games", True, ACCENT), (30, 18))
        screen.blit(font_title.render(f"Earnings: ${score:.2f}", True, GREEN), (200, 18))

        if combo_multiplier > 1:
            screen.blit(font_title.render(f"🔥 {combo_multiplier}x COMBO!", True, ORANGE), (330, 18))

        # --- TOP BUTTONS ---
        # Alarm Button
        al_c = RED_HOVER if ingame_alarm_btn.collidepoint(mouse_pos) else RED
        pygame.draw.rect(screen, al_c, ingame_alarm_btn, border_radius=6)
        screen.blit(font_btn.render("🚨 ALARM (A)", True, (255, 255, 255)), (ingame_alarm_btn.centerx - 42, ingame_alarm_btn.centery - 8))

        # Pause Button
        p_c = YELLOW_HOVER if ingame_pause_btn.collidepoint(mouse_pos) else YELLOW
        pygame.draw.rect(screen, p_c, ingame_pause_btn, border_radius=6)
        p_str = "▶ Play" if is_paused else "⏸ Pause"
        screen.blit(font_btn.render(p_str, True, (20, 20, 30)), (ingame_pause_btn.centerx - 28, ingame_pause_btn.centery - 8))

        # Menu Button
        m_c = ACCENT if ingame_menu_btn.collidepoint(mouse_pos) else CARD_BG
        pygame.draw.rect(screen, m_c, ingame_menu_btn, border_radius=6)
        pygame.draw.rect(screen, ACCENT, ingame_menu_btn, 1, border_radius=6)
        screen.blit(font_btn.render("🏠 Menu", True, TEXT_COLOR), (ingame_menu_btn.centerx - 28, ingame_menu_btn.centery - 8))

        # Quit Button
        q_c = RED_HOVER if ingame_quit_btn.collidepoint(mouse_pos) else RED
        pygame.draw.rect(screen, q_c, ingame_quit_btn, border_radius=6)
        screen.blit(font_btn.render("❌ Quit", True, (255, 255, 255)), (ingame_quit_btn.centerx - 22, ingame_quit_btn.centery - 8))

        # Cheat Sheet
        pygame.draw.rect(screen, CARD_BG, (30, 60, 760, 42), border_radius=8)
        screen.blit(font_main.render("Codes -> 101: Paracetamol | 102: Gloves | 103: Thermometer | 104: Syrup", True, YELLOW), (45, 71))

        # Customer Card & Patience Bar
        card_color = (80, 30, 30) if is_thief else CARD_BG
        pygame.draw.rect(screen, card_color, (int(customer_x), 115, 760, 85), border_radius=8)
        screen.blit(font_main.render("👤 Customer:", True, ACCENT if not is_thief else RED), (int(customer_x) + 15, 122))
        screen.blit(font_main.render(f'"{target_text}"', True, TEXT_COLOR), (int(customer_x) + 15, 148))

        # Patience Bar
        p_color = GREEN if patience > 60 else (YELLOW if patience > 30 else RED)
        pygame.draw.rect(screen, (20, 20, 30), (int(customer_x) + 15, 175, 730, 10), border_radius=4)
        pygame.draw.rect(screen, p_color, (int(customer_x) + 15, 175, int(730 * (patience / 100.0)), 10), border_radius=4)

        # Floating Text Animation
        if float_alpha > 0:
            f_surf = font_title.render(floating_text, True, GREEN)
            f_surf.set_alpha(int(float_alpha))
            screen.blit(f_surf, (480, int(float_y)))

        # Code Input Box
        screen.blit(font_main.render("Type Code & Press ENTER:", True, TEXT_COLOR), (30, 215))
        pygame.draw.rect(screen, (20, 20, 30), (30, 245, 250, 45), border_radius=5)
        
        laser_color = (0, 255, 200) if upgrades["laser_v2"] else RED
        if laser_timer > 0 and not is_paused:
            pygame.draw.rect(screen, laser_color, (30, 245, 250, 45), 3, border_radius=5)
            pygame.draw.line(screen, laser_color, (30, 267), (280, 267), 4)
        else:
            pygame.draw.rect(screen, ACCENT, (30, 245, 250, 45), 2, border_radius=5)

        screen.blit(font_title.render(input_text, True, YELLOW), (45, 253))

        # Scanned Cart
        pygame.draw.rect(screen, CARD_BG, (320, 215, 470, 260), border_radius=8)
        screen.blit(font_main.render("🛒 Scanned Items (API Cart):", True, TEXT_COLOR), (335, 225))

        y_offset = 255
        if len(scanned_cart_names) == 0:
            screen.blit(font_mono.render("[ No items scanned ]", True, (120, 120, 140)), (335, y_offset))
        else:
            for name in scanned_cart_names:
                screen.blit(font_mono.render(f"- {name}", True, GREEN), (335, y_offset))
                y_offset += 24

        # POS Thermal Slot
        pygame.draw.rect(screen, (15, 15, 25), (30, 310, 250, 165), border_radius=8)
        screen.blit(font_main.render("🖨️ POS Thermal Printer", True, ACCENT), (45, 320))
        pygame.draw.rect(screen, (200, 200, 200), (50, 350, 210, 6))

        if receipt_height > 0:
            pygame.draw.rect(screen, (255, 255, 255), (60, 356, 190, receipt_height))
            for line_y in range(365, 356 + receipt_height - 5, 15):
                pygame.draw.line(screen, (180, 180, 180), (70, line_y), (230, line_y), 2)

        # Controls & Status Bar
        pygame.draw.rect(screen, (20, 20, 35), (30, 495, 760, 45), border_radius=5)
        screen.blit(font_main.render("[ENTER] Scan | [SPACE] Print | [A] Alarm | [P] Pause | [M] Menu", True, YELLOW), (45, 507))
        screen.blit(font_main.render(status_message, True, TEXT_COLOR), (30, 560))

        # PAUSE OVERLAY
        if is_paused:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(190)
            overlay.fill((10, 10, 20))
            screen.blit(overlay, (0, 0))

            pygame.draw.rect(screen, CARD_BG, (210, 230, 400, 170), border_radius=12)
            pygame.draw.rect(screen, ACCENT, (210, 230, 400, 170), 3, border_radius=12)

            pause_txt = font_pause.render("⏸️ GAME PAUSED", True, YELLOW)
            screen.blit(pause_txt, (WIDTH // 2 - pause_txt.get_width() // 2, 270))
            screen.blit(font_main.render("Press 'P' or Click 'Play' to Resume", True, TEXT_COLOR), (WIDTH // 2 - 130, 340))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()