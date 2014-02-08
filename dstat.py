#!/usr/bin/env python


import os
import sys
import psutil
import time




# Character width of progress bars
bar_width = 12
update_invl = 1
stdout = False

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


def cpu_avg(cpu_loads):
    sum = 0
    avg = 0

    for i in cpu_loads:
        sum += i

    avg = sum / len(cpu_loads)
    return avg


def help():
    print sys.argv[0] + " - A simple statusbar generator for dwm."
    print """    -h,--help     - Print help and exit.
    -n,--no-color - Do not include ANSI colors with the output.
    -s,--stdout   - Print the bars to stdout and exit."""
    
    sys.exit(1)




# Deal with our command line arguments
for arg in sys.argv[1:]:
    if arg == "-h" or arg == "--help":
        help()

    elif arg == "-n" or arg == "--no-color":
        print "no color, or code"

    elif arg == "-s" or arg == "--stdout":
        stdout = True 
    
    else:
        help()


while True:
    cpu_perc = round(cpu_avg(psutil.cpu_percent(None, True)), 1)
    mem_perc = psutil.phymem_usage()[3]

    cpu_bar = mk_prog_bar(cpu_perc)
    mem_bar = mk_prog_bar(mem_perc)

    stats = "CPU " + str(cpu_perc) + cpu_bar + " "
    stats += "MEM " + str(mem_perc) + mem_bar

   
    if stdout == True:
        print(stats)
        ret = 0
        sys.exit(0)

    else:
        ret = os.system("xsetroot -name '" + stats + "'")
        if ret > 0:
            print("ERROR: Binary 'xsetroot' is not installed.")
            sys.exit(255)

    time.sleep(update_invl)
