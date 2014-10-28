#!/usr/bin/env python

########################################################
# Dstat - A simple statusbar for dwm.
# Ver: 0.4
# Author: Tomm Smith (root DOT packet AT gmail DOT come)
# Date: 7/20/2014
########################################################
#
# IPC Protocol Definition And Notes
# ---------------------------------
# The IPC protocol is fairly simple, it comprises of two commands
# and 3 fields. 
#
# COMMANDS:
#           MSG - Display the specified message in the <DATA> field.
#           DIE - The kill signal for the "daemon".
#
# FIELDS: <COMMAND>:<DELAY>:<DATA>
#           char COMMAND - One of the above listed commands.
#           int  DELAY   - The time period to show a message for before 
#                          returning to main data.
#           char DATA    - The information that corresponds to the command.


import os
import sys
import time
import stat
import getopt
import base64
import psutil
import subprocess
import select


# Volume Info Display (Percentage or dB)
vol_perc = True
snd_dev_ident = 'Headphone'

## Defaults
update_clk = 0.5
msg_ghost_time = 6
stdout = False
update_invl = 1
bar_width = 12

# Strip ./, and .py from our basename
bname = sys.argv[0]
if bname[0] == '.' and bname[1] == '/':
    basename = bname[2:-3]
else:
    basename = bname[0:-3]

sleepd_ctl_file='/var/run/sleepd.ctl'
run_file='/tmp/%s.pid' % basename
sock_file='/tmp/%s' % basename

# Internal control
client = False
die = False
status_msg_bool = False

   
def cleanup():
    """ cleanup()

    Clean up the running environment, sweep the floor, and return.

    Return: True upon success.
    """
    try:
        os.stat(run_file)
    except OSError as err:
        if err.errno == 2:
            pass
        else:
            print("WARNING: %s: Could not delete PID file." % err.strerror)
            pass
    else:
        os.unlink(run_file)

    try:
        os.stat(sock_file)
    except OSError as err:
        if err.errno == 2:
            pass
        else:
            print("WARNING: %s: Could not delete FIFO file." % err.strerror)
            pass
    else:
        os.unlink(sock_file)

    xsetroot("")
    return True


def cpu_avg(cpu_loads):
    sum = 0
    avg = 0

    for i in cpu_loads:
        sum += i

    avg = sum / len(cpu_loads)
    return avg


def get_byte(fd):
    """ get_byte(fd)

    A function to receive a "byte" from the listening port, process it, and 
    return the received data.

    @arg object fd - A file descriptor to use for obtaining the information.

    Return: Upon success, a dictionary of the data as expressed below:
        dict = {'COMMAND' : value, 'DELAY' : value, 'DATA' : value}

        Otherwise, False.
    """
    try:
        encd_data = os.read(fd, 1024)
    except OSError as err:
        print("WARNING: [Errno %d] %s" % (err.errno, err.strerror))
        return False
   
    data = base64.b64decode(encd_data)

    expl = data.split(':')
    data = {'COMMAND' : expl[0], 
            'DELAY'   : expl[1],
            'DATA'    : expl[2]}
    
    return data


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
    -i,--idle=NUM        - Define how long the specified message should idle before disappearing.
    -d,--die             - Send a sigterm to the server."""
    
    sys.exit(ret)


def is_running(pid_file):
    """ is_running(pid_file)

    Check if the process under the PID found in pid_file is running.

    Return: PID upon success, False upon all else.
    """
    try:
        fd = os.open(pid_file, 0)
        pid = int(os.read(fd, 1024))
        os.close(fd)
    except OSError as err:
        if err.errno == 2:
            return False
        else:
            print("ERROR: [errno %d] %s" % (err.errno, err.strerror))
            cleanup()
            sys.exit(1)
    else:
        if psutil.pid_exists(pid):
            return True
        else:
            return False
        
 
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


def poll_fifo(fd):
    """ poll_fifo(fd)

    Poll our FIFO descriptor for information and deal with the action 
    appropriately. 

    Arguments:

    Return: Data string upon success, False upon failure.
    """
    try:
        data = os.read(fd, 1024)

    except OSError as err:
        print("OSError: [%d]: %s" % (err.errno, err.strerror))
        return False

    else:
        if len(data) == 0:
            return False
        else:
            return data


def send_byte(fd, data):
    """ send_byte(fd, data)

    Send data specified in "data" to file pointed to by fd. The variable "data"
    should be a tuple indexed by the protocol defined in the header 
    documentation. This function will include the base 16 encoding before 
    sending the data.

    Arguments: @arg fd  fd   - A valid file descriptor for an open file.
               @arg str data - The data to be sent to the server in a dictionary 
                               in the following structure.
                               Dict = {'COMMAND' : 'CMDDATA',
                                       'DELAY'   : 10,
                                       'MSG'     : 'Hello World'}

    Return: True upon success, false upon failure.
    """
    tmp = "%s:%s:%s" % (str(data['COMMAND']), str(data['DELAY']), 
                        str(data['MSG']))
    encd_str = base64.b64encode(tmp)

    try:
        os.write(fd, encd_str)
    except OSError as err:
        print("ERROR: [Errno %d] %s" % (err.errno, err.strerror))
        return False

    return True


def setup(sock_file, server_bool=True):
    """ setup(sock_file, server_bool=True) 
    
    Setup the operating environment and ensure that all expected properties 
    of the environment are established properly and accessible. 

    Arguments: @arg str  sock_file - The location of the FIFO file.
               @arg bool server_bool - Is this a server environment?

    Return: A file descriptor to the active FIFO upon success.
            If this script returns, all is well. All issues raised
            will sys.exit() internally.
    """
    # Setup our PID file
    if server_bool:
        try:
           os.stat(run_file)
            
        except OSError as err: # run_file creation and errors
            if err.errno == 2: # File doesn't exist
                touch_pid(run_file)

            else:
                print("OSError: [Errno %d] %s: %s" % \
                        (err.errno, err.strerror, run_file)) 
                sys.exit(1)
    
        else: # run_file exists
            if is_running(run_file):
                print("ERROR: Instance of %s is already running." % basename)
                print("  Was it closed cleanly?")
                print("  See: \"ps aux | grep  %s.py\" Also: %s" % (basename, 
                            run_file))
                sys.exit(1)
            else:
                os.unlink(run_file)
                touch_pid(run_file)


    # If client environment, ensure server is running and fifo exists
    if not server_bool and not is_running(run_file):
            print("Server is not running. Try starting it...")
            sys.exit(1)
    
    # Ensure our FIFO file exists
    try:
        ss = os.stat(sock_file)
    
    except OSError as err: 
        if err.errno == 2: # sock_file doesn't exist
            os.mkfifo(sock_file)

        else: # other error
            print("OSError: [%d] %s: %s" % (err.errno, err.strerror, sock_file))
            sys.exit(1)

    else:
        # If our sock file is not a FIFO, blindly remove it
        # and create the desired FIFO.
        # TODO: Make this more polite.
        if not stat.S_ISFIFO(ss.st_mode):
            os.unlink(sock_file)
            os.mkfifo(sock_file)

    # Open our FIFO for polling
    try:
        fifo = os.open(sock_file, os.O_RDWR | os.O_NONBLOCK)
    except OSError as err:
        print("OSError: [Errno %d] %s" % (os.errno, os.strerror))
        cleanup()
        sys.exit(1)

    return fifo


def sleep_enabled():
    # Ensure that sleepd has a ctl file
    try:
        os.stat(sleepd_ctl_file)
    except OSError:
        print("ERROR: Sleepd does not exist. Is sleepd installed?\nNOTICE: \
                Sleepd support disabled.")

    sleepd_fd = open(sleep_ctl_file, 4)
    if data[0:1] == 1:
        return False
    else :
        return True


def statusbar_str():
    """ bld_stsbar()

    The primary function that ties the business logic together.

    Return: A formatted str of the statusbar information 
    """
    cpu_perc = round(cpu_avg(psutil.cpu_percent(None, True)), 1)
    mem_perc = psutil.phymem_usage()[3]
    
    cpu_bar = mk_prog_bar(cpu_perc)
    mem_bar = mk_prog_bar(mem_perc)
    
    volume = get_volume()
    
    sbar_str = "Volume: " + str(volume) + " "
    sbar_str += "CPU " + str(cpu_perc) + cpu_bar + " "
    sbar_str += "MEM " + str(mem_perc) + mem_bar
  
    return sbar_str


def touch_pid(pid_loca):
    """ touch_pid(pid_loca)

    Touch the PID file and add concatenate our PID into it.

    Return: True upon success, False upon any failure.
    """
    pid = os.getpid()
    fd = os.open(pid_loca, os.O_RDWR | os.O_CREAT)
    os.write(fd, "%d\n" % pid)
    os.close(fd)

    return True


def xsetroot(text):
    """ xsetroot(text)

    Set the title of the root window and return true.

    Arguments: @arg str text - The text to set as the root window's title.

    Return: True
    """
    os.system("xsetroot -name '%s'" % text)
    return True




# Main loop
if __name__ == "__main__":
    # Process our command line arguments
    try:
        args, argv = getopt.getopt(sys.argv[1:], "hnsm:i:d", \
                                    ["help", "no-color",    \
                                    "stdout", "message=",   \
                                    "idle=", "die"])
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
            client = True
            status_msg = data
    
        elif arg in ("-i", "--idle"):
            client = True
            try:
                msg_ghost_time = int(data)
            except ValueError:
                help("ERROR: The -h flag expects an integar as a value. \
                        Char provided.")
                sys.exit(1)

        elif arg in ("-d", "--die"):
            client = True
            die = True

        else:
            help()


    # Handle the client requests
    if client:
        sock = setup(sock_file, False)
        if sock:
            if die:
                byte = {'COMMAND' : 'DIE',
                        'DELAY'   : 'NULL',
                        'MSG'     : 'NULL'}
                send_byte(sock, byte)
                print("Sent DIE signal to server.")
                sys.exit(0)

            elif status_msg:
                byte = {'COMMAND' : 'MSG',
                        'DELAY'   : msg_ghost_time,
                        'MSG'     : status_msg}
                    
                if not send_byte(sock, byte):
                    print("ERROR: Could not contact the server. Is it running?")

        else:
            print("ERROR: Server is not running. Start the server and try again.")
            cleanup()
            sys.exit(1)


    # Main server loop
    else:
        sock = setup(sock_file)

        rlist = []
        wlist = []
        xlist = []

        while True: 
            rlist, wlist, xlist = select.select([sock], [], [], 0.1)
            
            if rlist:
                pkt = get_byte(rlist[0])

                # Process our command received
                if pkt['COMMAND'] == 'MSG':
                    try:
                       int(pkt['DELAY'])
                    except ValueError:
                        None
                    else:
                        msg_ghost_time = pkt['DELAY']
        
                    os.system("xsetroot -name '%s'" % pkt['DATA'])
                    time.sleep(float(msg_ghost_time))
                    continue

                elif pkt['COMMAND'] == 'DIE':
                    cleanup()
                    print("Caught SIGTERM from client.\nDieing...")
                    sys.exit(0)
                
                else:
                    print("WARNING: Malformed packet received from client. \
                            Ignoring.")
                    

            statusbar = statusbar_str()
            xsetroot(statusbar)
            time.sleep(update_clk)

        cleanup()
