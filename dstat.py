#!/usr/bin/env python


import os
import psutil
import time


# Character width of progress bars
bar_width = 12
update_invl = 1

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


while True:
    cpu_perc = round(cpu_avg(psutil.cpu_percent(None, True)), 1)
    mem_perc = psutil.phymem_usage()[3]

    cpu_bar = mk_prog_bar(cpu_perc)
    mem_bar = mk_prog_bar(mem_perc)

    stats = "CPU " + str(cpu_perc) + cpu_bar + " "
    stats += "MEM " + str(mem_perc) + mem_bar

    
    ret = os.system("xsetroot -name '" + stats + "'")
    time.sleep(update_invl)
