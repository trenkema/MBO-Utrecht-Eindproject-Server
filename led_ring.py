import time
import board
import neopixel
import math

# Number of LEDs in the NeoPixel ring
NUM_PIXELS = 12  # Adjust if using a different LED count
PIXEL_PIN = board.GP28  # GPIO pin connected to NeoPixel data line
BRIGHTNESS = 0.1  # Overall brightness of the LED ring (0.0 to 1.0)

# Initialize the NeoPixel strip with the specified pin, number of LEDs, and settings
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,  # Manual control over when LEDs update
    pixel_order=neopixel.GRB  # LED color channel order
)

class CountdownTimer:
    def __init__(self, total_seconds, active_color=(0, 255, 0), off_color=(0, 0, 0)):
        """
        Initialize countdown timer with total duration in seconds.
        active_color: LED color while time remains (default green).
        off_color: LED color when turned off (default black/off).
        """
        self.total_seconds = total_seconds
        self.active_color = active_color
        self.off_color = off_color

        # Predefined colors for game lost and won states
        self.red_color = (255, 0, 0)
        self.green_color = (0, 255, 0)

        self.start_time = None  # Will store start time when countdown begins
        self.finished = False  # Indicates if countdown completed

        # Flashing animation controls
        self.flash_mode = False
        self.flash_color = self.red_color
        self.flash_speed = 5  # Flashes per second
        self.flash_count_target = 50  # Total number of flashes
        self.flash_count_done = 0
        self.flash_on = True  # Flash currently ON or OFF
        self.last_flash_time = 0  # Time at last flash toggle
        self.flash_interval = 1.0 / self.flash_speed  # Time between flash toggles

        self.clear()  # Initialize LEDs to off_color

    def start(self):
        """
        Start the countdown timer by recording the current time.
        Set all LEDs to the active color.
        """
        self.start_time = time.monotonic()
        self.finished = False
        self.flash_mode = False
        self.flash_count_done = 0
        self.flash_on = True
        for i in range(NUM_PIXELS):
            pixels[i] = self.active_color
        pixels.show()

    def clear(self):
        """
        Reset the countdown timer and turn off all LEDs.
        """
        self.start_time = None
        self.finished = False
        self.flash_mode = False
        self.flash_count_done = 0
        self.flash_on = True
        for i in range(NUM_PIXELS):
            pixels[i] = self.off_color
        pixels.show()

    def update(self):
        """
        Update the countdown LED ring based on elapsed time.
        Turns LEDs off progressively as time passes.
        If in flash mode, delegates to flash handler.
        """
        if self.flash_mode:
            self._handle_flash()
            return

        if self.start_time is None:
            # Timer not started, do nothing
            return

        elapsed = time.monotonic() - self.start_time
        # Calculate how many LEDs should be turned off based on elapsed time
        leds_to_turn_off = int((elapsed / self.total_seconds) * NUM_PIXELS)
        leds_to_turn_off = min(leds_to_turn_off, NUM_PIXELS)

        # Set LED colors: red for time elapsed, active_color for remaining time
        for i in range(NUM_PIXELS):
            if i < leds_to_turn_off:
                pixels[i] = self.red_color
            else:
                pixels[i] = self.active_color
        pixels.show()

        # If all LEDs are off, countdown is finished and game is lost
        if leds_to_turn_off == NUM_PIXELS:
            self.finished = True
            self.game_lost()

    def start_flashing(self, color, flash_count=50, flash_speed=5):
        """
        Begin flashing all LEDs in specified color.
        flash_count: total number of flashes (on + off counts as 2).
        flash_speed: flashes per second.
        """
        self.flash_mode = True
        self.flash_color = color
        self.flash_speed = flash_speed
        self.flash_count_target = flash_count
        self.flash_count_done = 0
        self.last_flash_time = time.monotonic()
        self.flash_interval = 1.0 / flash_speed
        self.flash_on = True

    def _handle_flash(self):
        """
        Internal method to handle the flashing animation logic.
        Toggles LEDs on/off at the specified speed and counts flashes.
        Stops flashing when target count reached and clears LEDs.
        """
        now = time.monotonic()
        if now - self.last_flash_time >= self.flash_interval:
            self.last_flash_time = now
            self.flash_on = not self.flash_on  # Toggle flash state
            self.flash_count_done += 1

            # Set LEDs to flash color or off color based on flash state
            color = self.flash_color if self.flash_on else self.off_color
            for i in range(NUM_PIXELS):
                pixels[i] = color
            pixels.show()

        # Stop flashing after completing the target number of flashes (on + off)
        if self.flash_count_done >= self.flash_count_target * 2:
            self.flash_mode = False
            self.clear()

    def game_won(self, flash_count=30, flash_speed=4):
        """
        Trigger green flashing animation to indicate game won.
        """
        self.start_flashing(self.green_color, flash_count, flash_speed)

    def game_lost(self, flash_count=30, flash_speed=4):
        """
        Trigger red flashing animation to indicate game lost.
        """
        self.start_flashing(self.red_color, flash_count, flash_speed)

    def pulse(self, color=(255, 0, 0), speed=1.0):
        """
        Idle animation that pulses all LEDs smoothly in given color.
        Does not run while countdown active or flashing.
        color: RGB tuple with values 0-255.
        speed: speed of pulsing (cycles per second).
        """
        # Only pulse if timer not started and not in flash mode
        if self.start_time is not None or self.flash_mode:
            return

        t = time.monotonic()
        # Calculate brightness with sine wave oscillation between 0 and 1
        brightness = (math.sin(t * speed * math.pi) + 1) / 2

        # Scale the input color by brightness for smooth pulsing effect
        r = int(color[0] * brightness)
        g = int(color[1] * brightness)
        b = int(color[2] * brightness)

        # Update all LEDs to the pulsing color
        for i in range(NUM_PIXELS):
            pixels[i] = (r, g, b)
        pixels.show()