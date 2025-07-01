import time
import board
import neopixel
import math

NUM_PIXELS = 16  # Change this to 12 if using a 12-LED ring
PIXEL_PIN = board.GP9
BRIGHTNESS = 0.1

pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.GRB
)

class CountdownTimer:
    def __init__(self, total_seconds, active_color=(0, 255, 0), off_color=(0, 0, 0)):
        self.total_seconds = total_seconds
        self.active_color = active_color
        self.off_color = off_color
        self.red_color = (255, 0, 0)
        self.green_color = (0, 255, 0)
        self.start_time = None
        self.finished = False

        # Flash control
        self.flash_mode = False
        self.flash_color = self.red_color
        self.flash_speed = 5  # flashes per second
        self.flash_count_target = 50
        self.flash_count_done = 0
        self.flash_on = True
        self.last_flash_time = 0
        self.flash_interval = 1.0 / self.flash_speed

        self.clear()

    def start(self):
        self.start_time = time.monotonic()
        self.finished = False
        self.flash_mode = False
        self.flash_count_done = 0
        self.flash_on = True
        for i in range(NUM_PIXELS):
            pixels[i] = self.active_color
        pixels.show()

    def clear(self):
        self.start_time = None
        self.finished = False
        self.flash_mode = False
        self.flash_count_done = 0
        self.flash_on = True
        for i in range(NUM_PIXELS):
            pixels[i] = self.off_color
        pixels.show()

    def update(self):
        if self.flash_mode:
            self._handle_flash()
            return

        if self.start_time is None:
            return

        elapsed = time.monotonic() - self.start_time
        leds_to_turn_off = int((elapsed / self.total_seconds) * NUM_PIXELS)
        leds_to_turn_off = min(leds_to_turn_off, NUM_PIXELS)

        for i in range(NUM_PIXELS):
            if i < leds_to_turn_off:
                pixels[i] = self.red_color
            else:
                pixels[i] = self.active_color
        pixels.show()

        if leds_to_turn_off == NUM_PIXELS:
            self.finished = True
            self.game_lost()

    def start_flashing(self, color, flash_count=50, flash_speed=5):
        self.flash_mode = True
        self.flash_color = color
        self.flash_speed = flash_speed
        self.flash_count_target = flash_count
        self.flash_count_done = 0
        self.last_flash_time = time.monotonic()
        self.flash_interval = 1.0 / flash_speed
        self.flash_on = True

    def _handle_flash(self):
        now = time.monotonic()
        if now - self.last_flash_time >= self.flash_interval:
            self.last_flash_time = now
            self.flash_on = not self.flash_on
            self.flash_count_done += 1

            color = self.flash_color if self.flash_on else self.off_color
            for i in range(NUM_PIXELS):
                pixels[i] = color
            pixels.show()

        if self.flash_count_done >= self.flash_count_target * 2:  # on/off = 2 toggles per flash
            self.flash_mode = False
            self.clear()

    def game_won(self, flash_count=30, flash_speed=4):
        self.start_flashing(self.green_color, flash_count, flash_speed)

    def game_lost(self, flash_count=30, flash_speed=4):
        self.start_flashing(self.red_color, flash_count, flash_speed)

    def pulse(self, color=(255, 0, 0), speed=1.0):
        """Pulse all LEDs in a color (0-255 range) while idle."""
        if self.start_time is not None or self.flash_mode:
            return  # Don't pulse while active

        t = time.monotonic()
        brightness = (math.sin(t * speed * math.pi) + 1) / 2  # 0 → 1

        r = int(color[0] * brightness)
        g = int(color[1] * brightness)
        b = int(color[2] * brightness)

        for i in range(NUM_PIXELS):
            pixels[i] = (r, g, b)
        pixels.show()
