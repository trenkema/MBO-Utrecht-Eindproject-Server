import digitalio

class Button:
    def __init__(self, pin):
        """
        Initialize the button on the given pin.
        Configures the pin as input with pull-up resistor enabled.
        Sets initial button state to 'not pressed' (True).
        """
        self.pin = pin
        self.button = digitalio.DigitalInOut(pin)
        self.button.direction = digitalio.Direction.INPUT
        self.button.pull = digitalio.Pull.UP  # Use pull-up resistor for button wiring
        self._prev_state = True  # Button not pressed (high because of pull-up)
        self.is_pressed = False  # Track whether button is currently pressed

    def pressed(self):
        """
        Detect a press event (transition from not pressed to pressed).
        Returns True only once per press.
        """
        current = self.button.value  # Read current pin value (True = released)
        was_pressed = self._prev_state and not current  # Detect HIGH to LOW transition
        self._prev_state = current  # Save current state for next call
        return was_pressed

    def update(self):
        """
        Update the current pressed state of the button.
        Sets is_pressed True while button held down, False otherwise.
        """
        current = self.button.value
        if self._prev_state and not current:
            # Button just pressed (HIGH to LOW)
            self.is_pressed = False  # This looks like a logic inversion; likely a bug or custom logic
        else:
            # Button is released or held, mark as pressed
            self.is_pressed = True

    def reverse_pressed(self):
        """
        Detect release event (transition from pressed to not pressed).
        Returns True once when button is released.
        """
        current = self.button.value  # True if button released
        # Detect LOW to HIGH transition (pressed to released)
        was_reverse_pressed = not self._prev_state and current
        self._prev_state = current
        return was_reverse_pressed


import digitalio

class RGBLed:
    def __init__(self, pins):
        """
        Initialize RGB LED using given pins.
        Supports both digital GPIO pins and PWM pins (e.g., from PCA9685).
        """
        self.leds = []
        for pin in pins:
            # Check if the pin is a PWM channel by checking for 'duty_cycle' attribute
            if hasattr(pin, "duty_cycle"):
                # Add PWM pin directly
                self.leds.append(pin)
            else:
                # Setup digital output pin (assumed common cathode LED)
                led = digitalio.DigitalInOut(pin)
                led.direction = digitalio.Direction.OUTPUT
                led.value = True  # Turn off LED initially (True for common cathode)
                self.leds.append(led)

    def set_color(self, color):
        """
        Set the RGB LED color by setting each LED pin's brightness or on/off.
        'color' is a tuple of values corresponding to each LED channel.
        """
        for led, val in zip(self.leds, color):
            if hasattr(led, "duty_cycle"):
                # For PWM pins, set brightness directly
                led.duty_cycle = val
            else:
                # For digital pins, treat 0 as ON (LED active low), anything else as OFF
                led.value = (val != 0)