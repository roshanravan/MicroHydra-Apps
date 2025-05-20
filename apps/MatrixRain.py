# MatrixRain.py
#
# This application simulates the "Matrix digital rain" effect on an ST7789 display.
# It features falling streams of characters, with a leading bright character,
# and periodically displays an "ACCESS DENIED" message.
# It uses the ST7789 display driver library.

import machine
import lib.st7789fbuf as st7789fbuf
import random
import time

# --- Hardware Initialization ---

# Initialize SPI for display communication
# sck: Pin 36 (SCK/Clock)
# mosi: Pin 35 (MOSI/Data Out)
# baudrate: 40MHz (communication speed)
spi = machine.SPI(1, baudrate=40000000, sck=machine.Pin(36), mosi=machine.Pin(35))

# Initialize display driver
# ST7789 is the display controller
# spi: The SPI bus instance
# 135, 240: Display resolution (width, height)
# reset: Pin 33 (Reset pin for the display)
# cs: Pin 37 (Chip Select pin for the display)
# dc: Pin 34 (Data/Command pin for the display)
# backlight: Pin 38 (Controls the display backlight)
# rotation: 1 (Sets display rotation; 0=0, 1=90, 2=180, 3=270 degrees)
display = st7789fbuf.ST7789(
    spi,
    135,
    240,
    reset=machine.Pin(33),
    cs=machine.Pin(37),
    dc=machine.Pin(34),
    backlight=machine.Pin(38),
    rotation=1
)

# Initial fill of the display with black to clear any previous content
display.fill(0x0000) # 0x0000 is the color code for black

# --- Matrix Rain Configuration ---

# Screen dimensions derived from the display object
SCREEN_WIDTH = display.width
SCREEN_HEIGHT = display.height

# Character properties for the rain effect
CHAR_WIDTH = 8       # Width of each character in pixels (font dependent)
CHAR_HEIGHT = 12     # Height of each character in pixels (font dependent)
POSSIBLE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" # Characters to use in rain

# Raindrop properties
# NUM_DROPS: Defines how many raindrops will be active on screen.
# Calculated based on screen width and character width to achieve a certain density.
# Division by 2 provides a less dense rain.
NUM_DROPS = (SCREEN_WIDTH // CHAR_WIDTH) // 2

# Colors used in the animation (16-bit RGB565 format)
HEAD_COLOR = 0xFFFF  # White color for the leading character of a raindrop
TAIL_COLOR = 0x03E0  # Green color for the tail characters of a raindrop
RED_COLOR = 0xF800   # Red color, used for "ACCESS DENIED" background

# --- RainDrop Class Definition ---
class RainDrop:
    """
    Represents a single stream of falling characters (a raindrop).
    """
    def __init__(self, x):
        """
        Initializes a RainDrop object.
        Args:
            x (int): The initial x-coordinate (column) for this raindrop.
        """
        self.x = x  # x-coordinate of the drop (left edge of the characters)
        self.reset() # Initialize other properties

    def reset(self):
        """
        Resets the raindrop to a new starting position and appearance.
        This is called when a drop goes off-screen or at initialization.
        """
        # y-coordinate: Start randomly above the visible screen area
        self.y = random.randint(-SCREEN_HEIGHT, 0)
        # length: Number of characters in this drop's tail
        self.length = random.randint(5, 15)
        # speed: How many pixels the drop moves down per frame
        self.speed = random.randint(1, 3)
        # chars: List of characters that make up this drop
        self.chars = [random.choice(POSSIBLE_CHARS) for _ in range(self.length)]

# --- Initialize Raindrops ---
drops = [] # List to store all RainDrop objects
for i in range(NUM_DROPS):
    # Distribute drops horizontally across the screen.
    # Multiply by (CHAR_WIDTH * 2) for wider spacing between drops.
    drop_x = i * (CHAR_WIDTH * 2)
    # Ensure the drop's x-coordinate is within screen boundaries
    if drop_x < SCREEN_WIDTH - CHAR_WIDTH:
        drops.append(RainDrop(drop_x))
    else:
        # If screen is too narrow for ideal spacing, place remaining drops
        # at the last possible valid column to avoid overflow.
        # This calculation ensures they don't go off the right edge.
        last_possible_x = SCREEN_WIDTH - CHAR_WIDTH
        offset_for_remaining = (NUM_DROPS - i) * CHAR_WIDTH 
        calculated_x = last_possible_x - offset_for_remaining
        drops.append(RainDrop(max(0, calculated_x))) # Ensure x is not negative

# --- Animation Functions ---

def update_drops(drops_list):
    """
    Updates the position of each raindrop in the provided list.
    If a drop moves off the bottom of the screen, it is reset.
    Args:
        drops_list (list): A list of RainDrop objects.
    """
    for drop in drops_list:
        drop.y += drop.speed # Move drop downwards
        # Check if the entire drop (including its tail) has passed the bottom edge
        if drop.y - (drop.length * CHAR_HEIGHT) > SCREEN_HEIGHT:
            drop.reset() # Reset the drop to a new starting position and look

def draw_drops(drops_list):
    """
    Draws all raindrops onto the display.
    The head character is drawn in HEAD_COLOR, and tail characters in TAIL_COLOR.
    Args:
        drops_list (list): A list of RainDrop objects.
    """
    for drop in drops_list:
        for i in range(drop.length):
            # Calculate the y-coordinate for the current character in the drop
            # (0 is the head, so y is reduced for characters further up the tail)
            char_y = drop.y - (i * CHAR_HEIGHT)
            
            # Determine color: head is bright, tail is dimmer
            if i == 0:  # Head character (first in the stream)
                color = HEAD_COLOR
            else:       # Tail character
                color = TAIL_COLOR
            
            # Draw the character only if it's within the vertical and horizontal screen bounds
            if 0 <= char_y < SCREEN_HEIGHT and 0 <= drop.x < SCREEN_WIDTH:
                # display.text expects a single character, so access drop.chars[i][0]
                # (though each element in drop.chars is already a single char)
                display.text(drop.chars[i], drop.x, char_y, color)

def show_access_denied():
    """
    Displays an "ACCESS DENIED" message with a flashing effect.
    This function takes control of the display temporarily.
    """
    display.fill(RED_COLOR)  # Set background to red

    message = "ACCESS DENIED"
    # Use default font properties for text centering (8x8 pixels per char)
    text_width = len(message) * 8  # Total width of the message text
    text_height = 8                # Height of the message text

    # Calculate coordinates to center the text on the screen
    text_x = (SCREEN_WIDTH - text_width) // 2
    text_y = (SCREEN_HEIGHT - text_height) // 2

    # Flashing effect: show and hide text multiple times
    for _ in range(3): # Flash 3 times
        display.text(message, text_x, text_y, HEAD_COLOR) # Draw text in white
        display.show() # Update the display
        time.sleep(0.2) # Pause for visibility
        display.fill(RED_COLOR) # Clear text by filling screen with red again
        display.show() # Update the display
        time.sleep(0.2) # Pause
    
    # Display the final "ACCESS DENIED" message steadily
    display.text(message, text_x, text_y, HEAD_COLOR) # Draw text in white
    display.show() # Update the display
    time.sleep(2) # Hold the message for 2 seconds

def show_system_scan():
    """
    Displays a "SYSTEM SCANNING..." visual effect with a progress bar.
    This function takes control of the display temporarily.
    """
    display.fill(0x0000) # Clear display to black

    # --- Display "SYSTEM SCANNING..." text ---
    scan_text = "SYSTEM SCANNING..."
    text_width_scan = len(scan_text) * 8
    text_x_scan = (SCREEN_WIDTH - text_width_scan) // 2
    text_y_scan = 10 # Position at the top
    display.text(scan_text, text_x_scan, text_y_scan, HEAD_COLOR) # White text

    # --- Progress Bar Properties ---
    bar_width = int(SCREEN_WIDTH * 0.8) # 80% of screen width
    bar_height = 20
    bar_x = (SCREEN_WIDTH - bar_width) // 2
    bar_y = SCREEN_HEIGHT // 2 # Centered vertically
    bar_border_color = 0x001F  # Blue
    bar_fill_color = 0x07FF    # Light Blue (Cyan-ish)
    
    # Draw progress bar outline
    display.rect(bar_x, bar_y, bar_width, bar_height, bar_border_color)
    display.show() # Show outline and text before animation

    # --- Animate Progress Bar Filling ---
    animation_steps = bar_width // 4 # Fill in 4-pixel increments
    for i in range(animation_steps + 1):
        fill_w = i * 4
        if fill_w > bar_width: # Ensure fill doesn't exceed bar width
            fill_w = bar_width
        display.fill_rect(bar_x + 1, bar_y + 1, fill_w -2 , bar_height - 2, bar_fill_color) # Inset fill slightly
        display.show()
        time.sleep(0.02) # Animation smoothness

    # --- Display "SCAN COMPLETE" ---
    # Clear "SYSTEM SCANNING..." text by drawing a black rectangle over it
    display.fill_rect(text_x_scan, text_y_scan, text_width_scan, 8, 0x0000) 

    complete_text = "SCAN COMPLETE"
    text_width_complete = len(complete_text) * 8
    text_x_complete = (SCREEN_WIDTH - text_width_complete) // 2
    # Position "SCAN COMPLETE" below the progress bar or inside if space allows
    text_y_complete = bar_y + bar_height + 5 
    if text_y_complete + 8 > SCREEN_HEIGHT: # If too low, put inside bar
        text_y_complete = bar_y + (bar_height - 8) // 2

    display.text(complete_text, text_x_complete, text_y_complete, HEAD_COLOR) # White text
    display.show()
    time.sleep(2) # Hold "SCAN COMPLETE" message for 2 seconds

# --- Main Application Loop ---

# Define the sequence of visual modes
modes = ["matrix_rain", "access_denied", "system_scan"]
current_mode_index = 0  # Start with "matrix_rain"
last_mode_switch = time.ticks_ms()  # Timestamp of the last mode switch
mode_switch_interval = 15000        # Switch mode every 15 seconds (in milliseconds)

while True:
    current_time = time.ticks_ms() # Get current time for interval check

    # Check if it's time to switch to the next mode
    if time.ticks_diff(current_time, last_mode_switch) > mode_switch_interval:
        current_mode_index = (current_mode_index + 1) % len(modes) # Cycle through modes
        last_mode_switch = current_time # Reset the timer for the new mode's duration
        display.fill(0x0000) # Clear screen before switching to a new mode to avoid visual artifacts

    current_mode = modes[current_mode_index] # Get the current mode string

    # Execute behavior based on the current mode
    if current_mode == "matrix_rain":
        update_drops(drops)      # Update raindrop positions
        display.fill(0x0000)   # Clear screen to black for rain effect
        draw_drops(drops)        # Draw the raindrops
        display.show()           # Update the physical display
        time.sleep(0.05)         # Control animation speed for matrix rain (approx 20 FPS)
    
    elif current_mode == "access_denied":
        show_access_denied()     # This function handles its own display, timing, and sleep
        # After show_access_denied completes, immediately switch to the next mode
        # and reset the timer to ensure the new mode runs for its full duration.
        last_mode_switch = time.ticks_ms() 
        current_mode_index = (current_mode_index + 1) % len(modes)
        # No display.show() or time.sleep() here, as show_access_denied handles it.
        # The loop will then continue, potentially starting a new mode immediately
        # or continuing matrix_rain if it's next and the interval hasn't passed.
        # To ensure the next mode starts cleanly:
        display.fill(0x0000) # Clear screen after special effect

    elif current_mode == "system_scan":
        show_system_scan()       # This function handles its own display, timing, and sleep
        # Similar to access_denied, reset timer and advance mode after completion.
        last_mode_switch = time.ticks_ms()
        current_mode_index = (current_mode_index + 1) % len(modes)
        display.fill(0x0000) # Clear screen after special effect
        # No display.show() or time.sleep() here.

    # Note: If the mode is not "matrix_rain", display.show() is handled by the
    # specific mode function (show_access_denied, show_system_scan).
    # The main loop's time.sleep(0.05) is primarily for the "matrix_rain" mode.
    # If other modes have finished, the loop will quickly iterate, check time,
    # and potentially switch modes or restart matrix_rain.
