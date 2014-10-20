#!/usr/bin/env python

########################################################
# Dstat - A simple statusbar for DWM
# Ver: 0.4
# Author: Tomm Smith (root DOT packet AT gmail DOT come)
# Date: 7/20/2014
#
# TODO:
# - Add a feature to display if sleep is on. Support began 10/20/2014.
# - A function to display lock status, only when active.
# - bitmap support (dependant upon support of the WM).
########################################################


import os
import sys
import time
import psutil
import subprocess


## Settings
# Volume Info Display (Percentage or dB)
vol_perc = True
snd_dev_ident = 'Headphone'

# System defaults #
# Default idle time of messages passed through -m
msg_ghost_time = 6
sleepd_ctl_file='/var/run/sleepd.ctl'

# Internal mechanisms #
status_msg_bool = False

# Character width of progress bars
bar_width = 12
update_invl = 1
stdout = False


def cpu_avg(cpu_loads):
    sum = 0
    avg = 0

    for i in cpu_loads:
        sum += i

    avg = sum / len(cpu_loads)
    return avg


def get_volume():
    try:
        bsh = subprocess.Popen(["amixer", "get", snd_dev_ident], stdout=subprocess.PIPE, shell=False)
    except OSError:
        print "ERROR: amixer is not installed or not in the search path."
        return False

    output = bsh.communicate()
    
    # Could have False Positives
    if len(output[0]) == 0:
        print "ERROR: Invalid arguments were passed to amixer."
        return False


    ## Parse our stdout string and retrieve our volume dB and percentage.
    # Split by new line, replace all [,] brackets, splice and return the last Three elements
    tmp = output[0].split("\n")[-2]
    tmp0 = tmp.replace("[", "").replace("]", "")

    # [percentage, decibals, mute(on|off)
    vals = tmp0.split(" ")[-3:]

    if vol_perc == True:
        output = vals[0]
    else:
        output = vals[1]

    if vals[2] == 'off':
        output = "Muted"

    return output


def help(msg=None):
    if msg != None:
        print msg
        print

    print sys.argv[0] + " [data]- A simple statusbar generator for dwm."
    print """    -h,--help     - Print help and exit.
    -n,--no-color - Do not include ANSI colors with the output.
    -s,--stdout   - Print the bars to stdout and exit.
    -m,--message  - Print a message in the status bar for N seconds. (Defaults to 4 Seconds)
    -i,--idle     - Define how long the specified message should idle before disappearing."""
    
    sys.exit(1)


def mk_prog_bar(perc_val):
    bar_str = ""
    delim = 100.0 / bar_width
    stp_cnt = 0

    for i in range(0, bar_width):
        if stp_cnt <  perc_val and perc_val != 0:
            bar_str += "|"
        else:
            bar_str += " "

        stp_cnt += delim

    bar_str = "[" + bar_str + "]"
    return bar_str


def sleep_enabled():
    # Ensure that sleepd has a ctl file
    try:
        os.stat(sleepd_ctl_file)
    except OSError:
        print("ERROR: Sleepd does not exist. Is sleepd installed?\nNOTICE: Sleepd support disabled.")

    sleepd_fd = open(sleep_ctl_file, 4)
    if data[0:1] == 1:
        return False
    else :
        return True


# Deal with our command line arguments
arg_stp = 1
for arg in sys.argv[1:]:
    if arg == "-h" or arg == "--help":
        help()

    elif arg == "-n" or arg == "--no-color":
        print("ERROR: No color, or code")

    elif arg == "-s" or arg == "--stdout":
        stdout = True 

    # Deal with the arguments that require values
    elif arg == "-m" or arg == "--message" or \
         arg == "-i" or arg == "--idle":

        try:
            sys.argv[arg_stp + 1]
        except IndexError:
            help("ERROR: You did not provide enough data for the specified argument.")    
            sys.exit(1)
    
        # Deal with our arguments requiring extra data
        if arg == "-m" or arg == "--message":
            status_msg_bool = True
            status_msg = str(sys.argv[arg_stp + 1])

        elif arg == "-i" or arg == "--idle":
           # Make this cleaner?
            try:
                msg_ghost_time = sys.argv[arg_step + 1]
            except IndexError:
                print("ERROR: Provided criteria must be an integar. String provided.")
                sys.exit(1)
        
    else:
        help()
    
    arg_stp += 1
   

# Main loop
while True:
    cpu_perc = round(cpu_avg(psutil.cpu_percent(None, True)), 1)
    mem_perc = psutil.phymem_usage()[3]

    cpu_bar = mk_prog_bar(cpu_perc)
    mem_bar = mk_prog_bar(mem_perc)

    volume = get_volume()

    stats = "Volume: " + str(volume) + " "
    stats += "CPU " + str(cpu_perc) + cpu_bar + " "
    stats += "MEM " + str(mem_perc) + mem_bar
  
    if status_msg_bool:
        print(status_msg)
        time.sleep(msg_ghost_time)

    if stdout == True:
        print(stats)
        sys.exit(0)

    else:
        ret = os.system("xsetroot -name '" + stats + "'")
        if ret > 0:
            print("ERROR: Binary 'xsetroot' is not installed.")
            sys.exit(255)

    time.sleep(update_invl)
