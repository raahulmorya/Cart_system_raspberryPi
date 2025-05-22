#!/usr/bin/env python3
import RPi.GPIO as GPIO
import subprocess
import time

# Configuration
BUTTON_PIN = 2        # Using GPIO2
SCRIPT = "/home/rahul/run_cart_system.sh"
DEBOUNCE_TIME = 0.3    # Seconds

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def run_script():
    print("Executing script...")
    subprocess.Popen([SCRIPT], shell=True)

def button_pressed(channel):
    # Debounce and check button is still pressed
    time.sleep(DEBOUNCE_TIME)
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:
        run_script()

# Add event detection
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, 
                     callback=button_pressed, 
                     bouncetime=300)

try:
    print("Button controller running. Press CTRL+C to exit.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()