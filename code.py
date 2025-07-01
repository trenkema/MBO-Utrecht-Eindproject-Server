import board
import time
from server import Server
from button_led import Button, RGBLed
from led_ring import CountdownTimer

# Constants
TALK_PRESS_TIME_WINDOW = 3.0
RESET_PRESS_THRESHOLD = 8
START_PRESS_THRESHOLD = 3
TOTAL_TIME = 15
MAX_FLASH_TIME_WINLOSE = 10
MAX_FLASH_TIME_NORMAL = 5

# Setup
status_ring = CountdownTimer(total_seconds=TOTAL_TIME)
talk_button = Button(board.GP28)
talk_led = RGBLed([board.GP21, board.GP20, board.GP19])
talk_led.set_color((0, 0, 0))

buttons = [Button(getattr(board, f"GP{i}")) for i in range(8, -1, -1)]
buttons_rgb = []  # Fill with actual RGBLed instances in your real setup

correct_order = [5, 7, 8, 1, 2, 6, 3, 0, 4]
pressed_order = []

# States
game_started = game_over = game_completed = False
buttons_locked = True
show_button_flash = False
other_person_talking = False

talk_press_count = 0
first_press_time = None
talk_button_pressed = False
button_flash_start_time = None

# Colors
RED = (0, 65535, 65535)
GREEN = (65535, 0, 65535)
WHITE = (0, 0, 0)
OFF = (65535, 65535, 65535)
colors = [RED, GREEN, WHITE, OFF]

for led in buttons_rgb:
    led.set_color(OFF)

# --- Utility Functions ---
def reset_talk_press_state():
    global talk_press_count, first_press_time
    talk_press_count = 0
    first_press_time = None

def reset_game():
    global game_started, game_over, game_completed, buttons_locked
    global pressed_order, show_button_flash
    print("Resetting Game")
    server.send_command("RESET_GAME")
    game_started = game_over = game_completed = False
    buttons_locked = True
    pressed_order.clear()
    show_button_flash = False
    reset_talk_press_state()
    for led in buttons_rgb:
        led.set_color(OFF)
    status_ring.clear()

def start_game():
    global game_started, buttons_locked
    print("Starting Game")
    server.send_command("START_GAME")
    game_started = True
    buttons_locked = False
    status_ring.start()

def game_lost():
    global game_over, buttons_locked
    print("Game Lost")
    server.send_command("GAME_OVER")
    game_over = True
    buttons_locked = True
    pressed_order.clear()
    status_ring.game_lost()

def game_won():
    global game_completed, buttons_locked
    print("Game Won")
    server.send_command("GAME_WON")
    game_completed = True
    buttons_locked = True
    pressed_order.clear()
    status_ring.game_won()

# --- Server Setup ---
server = Server()
server.start_ap()
time.sleep(2)

while not server.conn:
    server.start_server()
    status_ring.pulse((0, 0, 255), speed=1)
    time.sleep(0.01)

status_ring.clear()

# --- Main Loop ---
while True:
    status_ring.update()
    talk_button.update()
    incoming = server.poll()

    if incoming == "TALKING" and not talk_button_pressed:
        other_person_talking = True
    elif incoming == "STOPPED_TALKING":
        other_person_talking = False

    if status_ring.finished and not game_over:
        game_lost()
        button_flash_start_time = time.monotonic()
        show_button_flash = True
        max_flash_time = MAX_FLASH_TIME_WINLOSE

    # Handle talk button press
    if talk_button.reverse_pressed():
        now = time.monotonic()
        talk_button_pressed = True
        server.send_command("TALKING")
        talk_led.set_color(GREEN if not other_person_talking else RED)

        if not first_press_time or (now - first_press_time) > TALK_PRESS_TIME_WINDOW:
            talk_press_count = 1
            first_press_time = now
        else:
            talk_press_count += 1

    if talk_button_pressed and not talk_button.is_pressed:
        talk_button_pressed = False
        server.send_command("STOPPED_TALKING")
        talk_led.set_color((0, 0, 0))
        print("Talk Button Released")

        elapsed = time.monotonic() - first_press_time if first_press_time else 0
        if elapsed <= TALK_PRESS_TIME_WINDOW:
            if talk_press_count >= RESET_PRESS_THRESHOLD and game_started:
                reset_game()
            elif not game_started and talk_press_count >= START_PRESS_THRESHOLD:
                time.sleep(0.5)
                start_game()
        reset_talk_press_state()

    if game_started:
        for i, btn in enumerate(buttons):
            if btn.pressed() and not buttons_locked and i not in pressed_order:
                pressed_order.append(i)
                buttons_rgb[i].set_color(WHITE)
                print(f"Button {i} pressed! Order: {pressed_order}")

        if len(pressed_order) == len(correct_order):
            buttons_locked = True
            if pressed_order == correct_order and not game_completed:
                game_won()
                max_flash_time = MAX_FLASH_TIME_WINLOSE
            else:
                print("Incorrect sequence!")
                max_flash_time = MAX_FLASH_TIME_NORMAL
            button_flash_start_time = time.monotonic()
            show_button_flash = True

    if show_button_flash:
        elapsed = time.monotonic() - button_flash_start_time
        flash_color = GREEN if game_completed else RED
        flash_state = (elapsed * 2) % 2 < 1
        color = flash_color if flash_state else OFF

        for led in buttons_rgb:
            led.set_color(color)

        if elapsed >= max_flash_time:
            if game_completed or game_over:
                reset_game()
            else:
                buttons_locked = False
                show_button_flash = False
                reset_talk_press_state()
                for led in buttons_rgb:
                    led.set_color(OFF)

    time.sleep(0.01)