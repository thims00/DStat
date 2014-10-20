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
# - Incorporate better return status for help()
########################################################


import os
import sys
import time
import getopt
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
    ret = 0

    if msg != None:
        ret = 1
        print msg
        print

    print sys.argv[0] + " [OPTION] [data] - A simple statusbar generator for dwm."
    print """    -h,--help        - Print help and exit.
    -n,--no-color        - Do not include ANSI colors with the output.
    -s,--stdout          - Print the bars to stdout and exit.
    -m,--message=STRING  - Print a message in the status bar for N seconds. (Defaults to 4 Seconds)
    -i,--idle=NUM        - Define how long the specified message should idle before disappearing."""
    
    sys.exit(ret)


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


# Process our command line arguments
try:
    args, argv = getopt.getopt(sys.argv[1:], "hnsm:i:", ["help", "no-color", "stdout", "message=", "idle="])
except getopt.GetoptError:
    help("ERROR: Invalid argument supplied.")
    sys.exit(1)

for arg, data in args:
    if arg in ("-h", "--help"):
        help()

    elif arg in ("-n", "--no-color"):
        print("ERROR: No color, or code.")  

    elif arg in ("-s", "--stdout"):
        stdout = True

    elif arg in ("-m", "--message"):
        status_msg_bool = True
        status_msg = data

    elif arg in ("-i", "--idle"):
        try:
            msg_ghost_time = int(data)
        except ValueError:
            help("ERROR: The ", arg, " argument expects and integar as a value. Char provided.")

    else:
        help()


def main():
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
	        stats = status_msg
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


if __name__ == "__main__":
    main()
