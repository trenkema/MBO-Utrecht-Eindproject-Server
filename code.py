import board
import busio
import time
import digitalio
from server import Server
from button_led import Button, RGBLed
from led_ring import CountdownTimer
from adafruit_pca9685 import PCA9685

# Constants for button press timing and game settings
TALK_PRESS_TIME_WINDOW = 3.0  # Time window to count multiple talk button presses
RESET_PRESS_THRESHOLD = 8     # Number of presses required to reset game during play
START_PRESS_THRESHOLD = 3     # Number of presses required to start the game
TOTAL_TIME = 300              # Total countdown time in seconds
MAX_FLASH_TIME_WINLOSE = 10   # Max time to flash LEDs when game is won or lost
MAX_FLASH_TIME_NORMAL = 5     # Max time to flash LEDs for normal button feedback

# --- Hardware and Game Setup ---

# LED ring for showing countdown timer
status_ring = CountdownTimer(total_seconds=TOTAL_TIME)

# Talk button connected to GP28
talk_button = Button(board.GP28)

# RGB LED for talk button status (using three GPIO pins)
talk_led = RGBLed([board.GP13, board.GP14, board.GP15])
talk_led.set_color((0, 0, 0))  # Initially off

# --- I2C and PWM Setup for Buttons and RGB LEDs ---

# Initialize I2C bus for PWM driver boards
i2c = busio.I2C(board.GP11, board.GP10)  # SDA, SCL pins

# Two PCA9685 PWM driver boards at different addresses
pca1 = PCA9685(i2c, address=0x40)
pca2 = PCA9685(i2c, address=0x41)
pca1.frequency = 1000  # Set PWM frequency to 1kHz
pca2.frequency = 1000

# Combine all PWM channels from both boards into a single list
all_channels = list(pca1.channels) + list(pca2.channels)

# Initialize 9 physical buttons, connected to GPIO pins GP8 to GP0 (descending)
buttons = [Button(getattr(board, f"GP{i}")) for i in range(8, -1, -1)]

# Initialize corresponding RGB LEDs for each button using PWM channels
# Mapping channels in a way that order is (Blue, Red, Green) per LED
buttons_rgb = [
    RGBLed([all_channels[i*3 + 2], all_channels[i*3 + 0], all_channels[i*3 + 1]])
    for i in range(9)
]

# Define the correct button press sequence by their indices
correct_order = [6, 5, 4, 7, 0, 8, 2, 1, 3]

# Track the order buttons are pressed during gameplay
pressed_order = []

# --- Game State Variables ---

game_started = False      # True when game is active
game_over = False         # True if player lost
game_completed = False    # True if player won
buttons_locked = True     # Disable button inputs when True
show_button_flash = False # Whether to flash buttons as feedback
other_person_talking = False  # Flag for other player's talk button status

# Talk button press tracking variables
talk_press_count = 0      # Count of rapid presses
first_press_time = None   # Time when first press was detected
talk_button_pressed = False  # Current state of talk button pressed

# Button flash timing
button_flash_start_time = None

# Color definitions in PWM duty cycle scale (0-65535)
RED = (0, 65535, 65535)
GREEN = (65535, 0, 65535)
WHITE = (0, 0, 0)
OFF = (65535, 65535, 65535)
colors = [RED, GREEN, WHITE, OFF]

# Turn off all button RGB LEDs initially
for led in buttons_rgb:
    led.set_color(OFF)

# --- Utility Functions ---

def reset_talk_press_state():
    """
    Reset the count and timer tracking talk button presses.
    """
    global talk_press_count, first_press_time
    talk_press_count = 0
    first_press_time = None

def reset_game():
    """
    Reset game state to initial values and notify connected clients.
    Clears pressed buttons and updates LEDs.
    """
    global game_started, game_over, game_completed, buttons_locked
    global pressed_order, show_button_flash
    print("Resetting Game")
    server.send_command("RESET_GAME")
    game_started = False
    game_over = False
    game_completed = False
    buttons_locked = True
    pressed_order.clear()
    show_button_flash = False
    reset_talk_press_state()
    for led in buttons_rgb:
        led.set_color(OFF)
    status_ring.clear()

def start_game():
    """
    Begin the game: unlock buttons, start countdown, and notify clients.
    """
    global game_started, buttons_locked
    print("Starting Game")
    server.send_command("START_GAME")
    game_started = True
    buttons_locked = False
    status_ring.start()

def game_lost():
    """
    Handle game lost condition: lock buttons, clear presses,
    notify clients, and start lost animation.
    """
    global game_over, buttons_locked
    print("Game Lost")
    server.send_command("GAME_OVER")
    game_over = True
    buttons_locked = True
    pressed_order.clear()
    status_ring.game_lost()

def game_won():
    """
    Handle game won condition: lock buttons, clear presses,
    notify clients, and start won animation.
    """
    global game_completed, buttons_locked
    print("Game Won")
    server.send_command("GAME_WON")
    game_completed = True
    buttons_locked = True
    pressed_order.clear()
    status_ring.game_won()

# --- Server Setup ---

server = Server()
server.start_ap()  # Start Wi-Fi access point for clients to connect
time.sleep(2)      # Allow time for AP to initialize

# Wait until a client connects to the server
while not server.conn:
    server.start_server()            # Start TCP server for communication
    status_ring.pulse((0, 0, 255), speed=1)  # Pulse blue LED ring while waiting
    time.sleep(0.01)

status_ring.clear()  # Clear ring once connected

# --- Main Loop ---

while True:
    status_ring.update()  # Update countdown timer LEDs
    talk_button.update()  # Poll talk button hardware state
    incoming = server.poll()  # Check for incoming messages from client

    # Update talk status based on incoming messages
    if incoming == "TALKING" and not talk_button_pressed:
        other_person_talking = True
    elif incoming == "STOPPED_TALKING":
        other_person_talking = False

    # If countdown finished and game not yet flagged as over, trigger loss
    if status_ring.finished and not game_over:
        game_lost()
        button_flash_start_time = time.monotonic()
        show_button_flash = True
        max_flash_time = MAX_FLASH_TIME_WINLOSE

    # Handle talk button press events (detect press release)
    if talk_button.reverse_pressed():
        now = time.monotonic()
        talk_button_pressed = True
        server.send_command("TALKING")
        # Green LED if other person not talking, else red LED
        talk_led.set_color((0, 65535, 0) if not other_person_talking else (65535, 0, 0))

        # Count presses within the press time window
        if not first_press_time or (now - first_press_time) > TALK_PRESS_TIME_WINDOW:
            talk_press_count = 1
            first_press_time = now
        else:
            talk_press_count += 1

    # Detect when talk button is released
    if talk_button_pressed and not talk_button.is_pressed:
        talk_button_pressed = False
        server.send_command("STOPPED_TALKING")
        talk_led.set_color((0, 0, 0))  # Turn off talk LED
        print("Talk Button Released")

        elapsed = time.monotonic() - first_press_time if first_press_time else 0
        # Check if presses are within the time window and trigger start/reset
        if elapsed <= TALK_PRESS_TIME_WINDOW:
            print(f"Button Pressed: {talk_press_count}")
            if talk_press_count >= RESET_PRESS_THRESHOLD and game_started:
                time.sleep(0.5)
                reset_game()
            elif not game_started and talk_press_count >= START_PRESS_THRESHOLD:
                time.sleep(0.5)
                start_game()

    # If game is running, check physical buttons for presses
    if game_started:
        for i, btn in enumerate(buttons):
            # Register new presses if buttons not locked and button not already pressed
            if btn.pressed() and not buttons_locked and i not in pressed_order:
                pressed_order.append(i)
                buttons_rgb[i].set_color(WHITE)  # Light up the pressed button LED
                print(f"Button {i} pressed! Order: {pressed_order}")

        # Once all buttons are pressed, check correctness of sequence
        if len(pressed_order) == len(correct_order):
            buttons_locked = True  # Lock buttons to prevent further input

            if pressed_order == correct_order and not game_completed:
                game_won()
                max_flash_time = MAX_FLASH_TIME_WINLOSE
            else:
                print("Incorrect sequence!")
                max_flash_time = MAX_FLASH_TIME_NORMAL
                pressed_order = []  # Reset pressed order on failure

            button_flash_start_time = time.monotonic()
            show_button_flash = True

    # Handle flashing feedback of buttons after game end or sequence entry
    if show_button_flash:
        elapsed = time.monotonic() - button_flash_start_time
        flash_color = GREEN if game_completed else RED
        # Toggle flashing on and off every 0.5 seconds
        flash_state = (elapsed * 2) % 2 < 1
        color = flash_color if flash_state else OFF

        # Update all buttons' LEDs with flashing color
        for led in buttons_rgb:
            led.set_color(color)

        # After max flash time, either reset game or clear flash and unlock buttons
        if elapsed >= max_flash_time:
            if game_completed or game_over:
                reset_game()
            else:
                buttons_locked = False
                show_button_flash = False
                reset_talk_press_state()
                for led in buttons_rgb:
                    led.set_color(OFF)

    time.sleep(0.01)  # Short delay to reduce CPU load