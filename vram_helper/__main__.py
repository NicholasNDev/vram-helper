"""
Simple python script that sends warnings about VRAM usage.
Uses notify-send by default

MAX_VRAM_USAGE is maximal acceptable VRAM usage,
if GPU exceeds this limit warning will be displayed,
then for every +THRESHOLD Mib it will display another warning

VRAM_TOTAL is your gpu VRAM capacity. Make sure to update this variable
"""

import subprocess
import re
import time
import sys
import argparse

# max acceptable VRAM usage in megabytes
MAX_VRAM_USAGE = 3800

# Maximum allowed VRAM usage threshold in megabytes
THRESHOLD = 100

#max available VRAM
VRAM_TOTAL = 2048

#max acceptable temperature in degrees Celcius
MAX_TEMP = 80

#time between updates in seconds
WAITTIME = 2

#controls the minimum priority of log messages:
#  -0 to display all logs
#  -1 to display only warnings
#  -2 to display only errors
VERBOSITY_LEVEL = 0

#enable automatic configuration
AUTODETECT = True


def log_mess(message, layer = 0):
    """
    prints messages in log format
    """
    if VERBOSITY_LEVEL > 0:
        return
    print(" " * 2 * layer + f"\033[92m[LOG]\033[0m {message}")


def log_warn(message, layer = 0):
    """
    prints messages in warning format
    """
    if VERBOSITY_LEVEL > 1:
        return
    print(" " * 2 * layer + f"\033[33m[WARN]\033[0m {message}")


def log_err(message, layer = 0):
    """
    prints messages in error format
    """
    print(" " * 2 * layer + f"\033[91m[ERR]\033[0m {message}")


def update_variables():
    """
    automatically updates variables based on gathered info
    """
    log_mess("Attempting to autodetect necessary info...")
    try:
        output = subprocess.check_output(["nvidia-smi",
                                          "--query-gpu=name",
                                          "--format=csv,noheader"])
        log_mess(f"Detected GPU: {output.decode('utf-8').strip()}", 1)

        output = subprocess.check_output(["nvidia-smi",
                                          "--query-gpu=memory.total",
                                          "--format=csv,noheader,nounits"])

        global VRAM_TOTAL # pylint: disable=global-statement
        VRAM_TOTAL = int(output.decode("utf-8").strip())
        log_mess(f"Detected {VRAM_TOTAL}Mib of VRAM available.", 1)

        global MAX_VRAM_USAGE # pylint: disable=global-statement
        MAX_VRAM_USAGE = VRAM_TOTAL * .9
        log_mess(f"MAX_VRAM_USAGE set to {VRAM_TOTAL * .9}", 1)

        log_mess(f"Script will update every {WAITTIME}s", 1)

        log_mess(f"Max acceptable temperature is set to {MAX_TEMP}°C", 1)

    except subprocess.CalledProcessError as e:
        log_err(f"Failed to gather necessary info due to following errors: {e}", 1)

    except FileNotFoundError:
        log_err("Failed to gather necessary info, make sure that nvidia drivers are installed!", 1)
        sys.exit()


def get_vram_usage():
    """
    returns main GPU VRAM usage in megabytes
    """
    try:
        output = subprocess.check_output(["nvidia-smi",
                                          "--query-gpu=memory.used",
                                          "--format=csv,noheader,nounits"])
        return int(re.search(r'\d+', output.decode('utf-8')).group())
    except subprocess.CalledProcessError as e:
        log_err(f"Failed to get VRAM usage! {e}")
        sys.exit()

    except FileNotFoundError:
        log_err("Failed to get VRAM usage! " +
                "'nvidia-smi' command not found. " +
                "Please make sure NVIDIA drivers are installed.")
        sys.exit()

def get_temp():
    """
    returns GPU temperature in degrees celcius
    """
    try:
        output = subprocess.check_output(["nvidia-smi",
                                          "--query-gpu=temperature.gpu",
                                          "--format=csv,noheader,nounits"])
        return int(re.search(r'\d+', output.decode('utf-8')).group())
    except subprocess.CalledProcessError as e:
        log_err(f"Failed to get GPU temperature! {e}")
        sys.exit()

    except FileNotFoundError:
        log_err("Failed to get GPU temperature! " +
                "'nvidia-smi' command not found. " +
                "Please make sure NVIDIA drivers are installed.")
        sys.exit()



def send_vram_warning(message):
    """
    prints VRAM usage warning using notify-send (change your this as needed)
    """
    try:
        print("Warning! " + message)
        subprocess.run(["notify-send", "--urgency=critical" ,"Warning!", message], check=True)
    except subprocess.CalledProcessError as e:
        log_err(f"Error: {e}")


def start_monitoring():
    """
    the main program loop,
    monitors vram usage in real time and sends warnings if it exceeds certain limit
    """
    last_warning_vram = MAX_VRAM_USAGE - 20
    while True:
        vram_usage = get_vram_usage()
        gpu_temp = get_temp()
        if vram_usage is not None:
            if vram_usage < last_warning_vram - THRESHOLD and last_warning_vram >= MAX_VRAM_USAGE:
                last_warning_vram -= THRESHOLD
            log_mess(f"VRAM Usage: {vram_usage} MiB, temp: {gpu_temp}°C")
            if vram_usage > last_warning_vram + THRESHOLD:
                last_warning_vram += THRESHOLD
                send_vram_warning("VRAM usage critical! " +
                        f"{vram_usage}/{VRAM_TOTAL}Mib, " +
                        f"({(int)((vram_usage / VRAM_TOTAL) * 100)}%)")
        time.sleep(WAITTIME)

def main():
    """
    init function
    """
    global AUTODETECT # pylint: disable=global-statement

    parser = argparse.ArgumentParser("python3 vram_helper.py")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--noauto', dest='auto', action='store_false',
                       help='Disable automatic detection mode')
    parser.set_defaults(auto=True)
    args = parser.parse_args()

    AUTODETECT = args.auto

    if AUTODETECT:
        update_variables()
    else:
        log_warn("Program will not attempt to gather any information, " +
        "make sure that information provided in the script is correct!")
    start_monitoring()

if __name__ == "__main__":
    main()
