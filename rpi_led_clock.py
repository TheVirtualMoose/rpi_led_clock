#!/usr/bin/env python3
import argparse
import datetime
import time
try:
    import RPi.GPIO as GPIO
    gpio_present = True
except ModuleNotFoundError:
    print("RPi.GPIO module not present, forcing a dry run")
    gpio_present = False


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


def gpio_setup(channel_list):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(channel_list, GPIO.OUT, initial=GPIO.HIGH)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Display time on a 7-segment LED clock")
    parser.add_argument("time", metavar="HHMM", type=str, nargs="?", help="Hour to display on the clock")
    parser.add_argument("--dry_run", action="store_true", help="If set, do a dry run and do not set any GPIO pins")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    if parse_arguments().time is not None:
        time_on_clock = datetime.datetime(100, 1, 1, int(args.time[0:2]), int(args.time[2:]), 00)
    else:
        time_on_clock = datetime.datetime.now()
    if args.dry_run or gpio_present is False:
        dry_run = True
    if not dry_run:
        gpio_setup(channels)
    x = LedClock(dry_run=dry_run)
    try:
        while True:
            x.display = time_on_clock.strftime("%H%M")
            x.update_display()
            time.sleep(60)
            time_on_clock = time_on_clock + datetime.timedelta(minutes=1)
    except KeyboardInterrupt:
        print("Received a keyboard interrupt, cleaning up GPIO")
    except:
        print("Received an unexpected interrupt, cleaning up GPIO")
    finally:
        GPIO.cleanup()
