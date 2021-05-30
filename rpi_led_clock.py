#!/usr/bin/env python3
import argparse
import datetime
import time
import threading
import sys

try:
    import RPi.GPIO as GPIO

    gpio_present = True
except ModuleNotFoundError:
    print("RPi.GPIO module not present, forcing a dry run")
    gpio_present = False
from flask import Flask, request, render_template

app = Flask(__name__)
# Channels in use that need to be set as output.
channels = list(range(0, 28))

# Pins corresponding to each segment per digit TODO: Actually map the pins
pins_per_segment = {
    0: (0, 1, 2, 3, 4, 5, 6),
    1: (7, 8, 9, 10, 11, 12, 13),
    2: (14, 15, 16, 17, 18, 19, 20),
    3: (21, 22, 23, 24, 25, 26, 27),
}

# Pin controlling the colon between hour and minute digits - not used at the moment
# colon = 29

# Segments:
# 0 - top, 1 - upper right, 2 - upper left, 3 - bottom right, 4 - bottom left, 5 - bottom, 6 - crossbar

# Segments used for each digit; 0, 1 = off, on.
digits = {
    "0": (1, 1, 1, 1, 1, 1, 0),  # 0
    "1": (0, 1, 1, 0, 0, 0, 0),  # 1
    "2": (1, 1, 0, 1, 1, 0, 1),  # 2
    "3": (1, 1, 1, 1, 0, 0, 1),  # 3
    "4": (0, 1, 1, 0, 0, 1, 1),  # 4
    "5": (1, 0, 1, 1, 0, 1, 1),  # 5
    "6": (1, 0, 1, 1, 1, 1, 1),  # 6
    "7": (1, 1, 1, 0, 0, 0, 0),  # 7
    "8": (1, 1, 1, 1, 1, 1, 1),  # 8
    "9": (1, 1, 1, 1, 0, 1, 1),  # 9
    " ": (0, 0, 0, 0, 0, 0, 0),  # blank display
}


class LedClock:
    def __init__(self, dry_run=0):
        self.display = ""
        self.dry_run = dry_run

    def set_segment(self, segment, digit_position, state):
        if self.dry_run:
            print(f"Setting pin # {pins_per_segment[digit_position][segment]} to {state == 0}")
            print(f"Segment {segment} is now {'down' if (state == 0) else 'up'}")
        else:
            # We disable a segment by setting a GPIO pin to HIGH state
            GPIO.output(pins_per_segment[digit_position][segment], state == 0)

    def set_digit(self, digit, digit_position):
        for segment in range(0, 7):
            self.set_segment(segment, digit_position, digits[digit][segment])

    def update_display(self):
        for i in range(0, 4):
            self.set_digit(self.display[i], i)

    def blank_display(self):
        print("Blanking display and stopping updates until a new time is input")
        self.display = "    "
        self.update_display()


class TubeClock(LedClock):
    def __init__(self, dry_run=0):
        super().__init__(dry_run)
        self.digit_mapping = {
            0: (None, 0, 1),
            1: (2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
            2: (12, 13, 14, 15, 16, 17),
            3: (18, 19, 20, 21, 22, 23, 24, 25, 26, 27)
        }

    def set_digit(self, digit, digit_position):
        if self.dry_run:
            for i in self.digit_mapping[digit_position]:
                if i is None:
                    print(
                        f"Digit {self.digit_mapping[digit_position].index(i)} at position {digit_position} not "
                        f"enabled, skipping")
                elif str(self.digit_mapping[digit_position].index(i)) != digit:
                    print(f"Setting GPIO pin {i} to GPIO.HIGH")
                elif str(self.digit_mapping[digit_position].index(i)) == digit:
                    print(f"Setting GPIO pin {i} to GPIO.LOW")
        else:
            for i in self.digit_mapping[digit_position]:
                if i is None:
                    continue
                elif str(self.digit_mapping[digit_position].index(i)) != digit:
                    GPIO.output(self.digit_mapping[digit_position][digit], GPIO.HIGH)
                elif str(self.digit_mapping[digit_position].index(i)) == digit:
                    GPIO.output(self.digit_mapping[digit_position][digit], GPIO.LOW)


def gpio_setup(channel_list):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(channel_list, GPIO.OUT, initial=GPIO.HIGH)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Display time on a 7-segment LED clock")
    parser.add_argument("time", metavar="HHMM", type=str, nargs="?", help="Hour to display on the clock")
    parser.add_argument("--dry_run", action="store_true", help="If set, do a dry run and do not set any GPIO pins")
    parser.add_argument("--type", action="store", type=str, nargs="?", default="tube",
                        help='Type of clock. Allowed values "tube" (default) and "led"')
    return parser.parse_args()


@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # TODO Input validation
        global time_input
        time_input = request.form["time"]
        global update_needed
        update_needed = True
    return render_template('index.html')


def start_display(new_time):
    global time_input
    global update_needed
    global blank_requested
    update_needed = False
    blank_requested = False
    display_blanked = False
    while True:
        if update_needed:
            new_time = datetime.datetime(100, 1, 1, int(time_input[0:2]), int(time_input[2:]), 00)
            update_needed = False
            display_blanked = False
        if new_time.strftime("%H%M") != x.display and not blank_requested:
            x.display = new_time.strftime("%H%M")
            x.update_display()
            print(f"setting display to {new_time.strftime('%H%M')}")
        if blank_requested and not display_blanked:
            x.blank_display()
            display_blanked = True
        time.sleep(1)
        new_time = new_time + datetime.timedelta(seconds=1)


if __name__ == '__main__':
    args = parse_arguments()
    if parse_arguments().time is not None:
        starting_time = datetime.datetime(100, 1, 1, int(args.time[0:2]), int(args.time[2:]), 00)
    else:
        starting_time = datetime.datetime.now()
    if args.dry_run or gpio_present is False:
        dry_run = True
    else:
        dry_run = False
    try:
        if not dry_run:
            gpio_setup(channels)
        if args.type == "tube":
            x = TubeClock(dry_run=dry_run)
        elif args.type == "led":
            x = LedClock(dry_run=dry_run)
        else:
            print("Unknown clock type, aborting")
            sys.exit(1)
        display_thread = threading.Thread(target=start_display, args=(starting_time,), daemon=True)
        display_thread.start()
        app.run(host="0.0.0.0", port=1080)
    except KeyboardInterrupt:
        print("Received a keyboard interrupt, cleaning up GPIO")
    finally:
        if not dry_run:
            GPIO.cleanup()
