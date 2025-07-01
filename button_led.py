import digitalio

class Button:
    def __init__(self, pin):
        self.pin = pin
        self.button = digitalio.DigitalInOut(pin)
        self.button.direction = digitalio.Direction.INPUT
        self.button.pull = digitalio.Pull.UP  # Use PULL_UP if your button wiring requires it
        self._prev_state = True  # True means not pressed (pull-up)
        self.is_pressed = False

    def pressed(self):
        current = self.button.value
        was_pressed = self._prev_state and not current
        self._prev_state = current
        return was_pressed

    def update(self):
        current = self.button.value
        if self._prev_state and not current:
            self.is_pressed = False
        else:
            self.is_pressed = True

    def reverse_pressed(self):
        current = self.button.value  # True if released (open)
        was_reverse_pressed = not self._prev_state and current  # Detect LOW -> HIGH transition
        self._prev_state = current
        return was_reverse_pressed

import digitalio

class RGBLed:
    def __init__(self, pins):
        self.leds = []
        for pin in pins:
            # Check if pin is a PCA9685 channel (has 'duty_cycle' attribute)
            if hasattr(pin, "duty_cycle"):
                self.leds.append(pin)
            else:
                led = digitalio.DigitalInOut(pin)
                led.direction = digitalio.Direction.OUTPUT
                led.value = True  # Off for common cathode
                self.leds.append(led)

    def set_color(self, color):
        for led, val in zip(self.leds, color):
            if hasattr(led, "duty_cycle"):
                led.duty_cycle = val  # Use PWM value directly
            else:
                led.value = (val != 0)  # For GPIO: 0=on, anything else=off
