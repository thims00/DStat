#!/usr/bin/python2.7

########################################################
# Dstat - A simple statusbar for dwm.
# Ver: 0.7
# Author: Tomm Smith (root DOT packet AT gmail DOT come)
# Date: 7/20/2014
# Notes: In Jesus' name are you healed.
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


## Defaults ##
# Volume Info Display (Percentage or dB)
vol_perc = True
snd_dev_ident = 'Headphone'
update_clk = 0.7
# Default time to display a message
msg_ghost_time = 5
bar_width = 12
# Military time?
time_frmt = True

## Control Files ##
# Strip /path/info/, and .py from our basename
basename = sys.argv[0].split('/')[-1][0:-3]

run_file='/tmp/%s.pid' % basename
sock_file='/tmp/%s' % basename
sleepd_ctl_file='/var/run/sleepd.ctl'
xtrlock_pid='/tmp/xtrlock.pid'

## Internal control ##
client = False
stdout = False
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


def get_music(dsply_str=""):
    """ get_music()
    """
    None


def get_byte(fd):
    """ get_byte(fd)

    A function to receive a "byte" from the listening port, process it, and 
    return the received data. Base 64 decoding is done within.

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
  
    try:
        data = base64.b64decode(encd_data)
    except TypeError:
        return False

    # Error handling here!
    try:
        expl = data.split(':')
        data = {'COMMAND' : expl[0], 
                'DELAY'   : expl[1],
                'DATA'    : expl[2]}
    except IndexError:
        return False
    
    return data


def get_volume():
    """ get_volume()
        
    Get the state/value of the volume.

    Arguments: None

    Return: Status/percentage string of current volume value upon success,
            False upon error.
    """
    try:
        bsh = subprocess.Popen(["amixer", "get", snd_dev_ident], stdout=subprocess.PIPE, shell=False)
    except OSError:
        print("ERROR: amixer is not installed or not in the search path.")
        return False

    output = bsh.communicate()
    
    # Could have False Positives
    if len(output[0]) == 0:
        print("ERROR: Invalid arguments were passed to amixer.")
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

    return str(output)


def help(msg=None):
    ret = 0

    if msg != None:
        ret = 1
        print(msg)
        print

    print(sys.argv[0] + " [OPTION] [data] - A simple statusbar generator for dwm.")
    print("""    -h,--help            - Print help and exit.
    -n,--no-color        - Do not include ANSI colors with the output.
    -s,--stdout          - Print the bars to stdout and exit.
    -m,--message=STRING  - Print a message in the status bar for N seconds. (Defaults to 4 Seconds)
    -i,--idle=NUM        - Define how long the specified message should idle before disappearing.
    -d,--die             - Send a sigterm to the server.""")
    
    sys.exit(ret)


def is_running(pid_file):
    """ is_running(pid_file)

    Check if the process under the PID found in pid_file is running.

    Return: PID upon success, False upon all else.
    """
    try:
        fd = os.open(pid_file, 0)
        buf = os.read(fd, 1024)
        os.close(fd)
        
        if len(buf) == 0 or buf == '\n':
            return False
        else:
            pid = int(buf.strip("\n"))

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


def read(r_file, svrty_lvl=None, bytes=1024):
    """ read(file, svrty_lvl=None, bytes=1024)

    Read file and return the data or return false and raise appropriate error 
    based upon the level of svrty_lvl.

    Arguments: @arg str file      - The file to read
               @arg str svrty_lvl - The level of severity if an issue is raised. 
                                    One of:
                                        None  - Do nothing and return False
                                        Warn  - Raise error to stdout and return
                                                False
                                        Error - Raise error and die
               @arg int bytes     - Amount of bytes to read in. Default: 1024

    Return: String of data upon success, False and exception "raised" upon failure.
    """
    err_msg = "No Error"
    try:
        fd = os.open(r_file, os.R_OK)
        data = os.read(fd, bytes)
        os.close(fd)
    except OSError as err:
        err_msg = "[Errno %d] %s" % (err.errno, err.strerror)
        
        if svrty_lvl.lower() == 'error':
            print("ERROR: %s: %s" % (err_msg, r_file))
            cleanup()
            sys.exit(1)
        elif svrty_lvl.lower() == 'warn':
            print("WARNING: %s: %s" % (err_msg, r_file))
            return False
        else:
            return False
    else:
        return data


def send_byte(fd, data):
    """ send_byte(fd, data)

    Send data specified in "data" to file pointed to by fd. The variable "data"
    should be a tuple indexed by the protocol defined in the header 
    documentation. This function will include the base 64 encoding before 
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
    """ sleep_enabled()

    Check whether or not sleepd is running and return the state.

    Arguments: None

    Return: True upon sleep being enabled, 
            False upon disabled,
            and None, warning/error raised upon other situation.
    """
    # Ensure that sleepd has a ctl file
    try:
        os.stat(sleepd_ctl_file)
    except OSError as err:
        if err.errno == 2:
            print("WARNING: Sleepd status file %s does not exist. Is sleepd \
                    installed?\n Sleepd support disabled.", sleepd_ctl_file)
            None
        else:
            print("ERROR: [errno %d] %s" % (err.errno, err.strerror))
            sys.exit(1)
    else:
        fd = os.open(sleepd_ctl_file, os.R_OK)
        val = os.read(fd, 1024)
        os.close(fd)
        if int(val) == 1:
            return False
        else :
            return True


def statusbar_str():
    """ statusbar_str()

    The primary function that ties the business logic together.

    Return: A formatted str of the statusbar information 
    """
    sbar_str = ""

    # Show Locked Indiciator
    if is_running(xtrlock_pid):
        sbar_str += "[Locked] | "

    # Deal with sleepd
    ret = sleep_enabled()
    if ret:
        sbar_str += "Sleep: Enabled | "
    elif ret == None:
        sbar_str += "Sleep: NA | "
    else:
        sbar_str += "Sleep: Disabled | "

    # Volume status / information
    volume = get_volume()

    # CPU and memory information and bar
    cpu_perc = round(cpu_avg(psutil.cpu_percent(None, True)), 1)
    mem_perc = psutil.phymem_usage()[3]

    cpu_bar = mk_prog_bar(cpu_perc)
    mem_bar = mk_prog_bar(mem_perc)
    
    sbar_str += "Volume: %s | " % str_padding(volume, 4)
    sbar_str += "CPU %s%s | " % (str_padding(cpu_perc, 4), cpu_bar)
    sbar_str += "MEM %s%s | " % (str_padding(mem_perc, 4), mem_bar)

    sbar_str += "%s" % time_str(time_frmt)
  
    return sbar_str


def str_padding(data, width):
    """ str_padding(data, width)

    Pad the provided string with whitespace to ensure it fills the defined
    width of "width".

    Arguments: @arg str data   - The string to be padded.
               @arg int width  - The width to ensure the str is padded to.

    Return: The appropriate padded string upon success, False otherwise.
    """
    data = str(data)
    if len(data) >= width:
        return data
    else:
        stps = width - len(data)
        for i in range(stps):
            data += " "

        return data


def time_str(mltry=True):
    """ time_str(mltry)

    Return the current time in the style defined by mltry.
    Defaults to military time.

    Arguments: @arg bool mltry - True for military time, False for civillian.

    Return: String of current time upon success.
    """
    months = { 1 : 'JAN',
               2 : 'FEB',
               3 : 'MAR',
               4 : 'APR',
               5 : 'MAY',
               6 : 'JUN',
               7 : 'JUL',
               8 : 'AUG',
               9 : 'SEP',
              10 : 'OCT',
              11 : 'NOV',
              12 : 'DEC'}
    t = time.localtime()

    if mltry:
        time_str = "%02d:%02d:%02d %02d %s %d" % (t.tm_hour, t.tm_min, t.tm_sec,
                        t.tm_mday, months[t.tm_mon], t.tm_year)
    else:
        hour = t.tm_hour - 12
        time_str = "%d:%d:%d %d/%d/%d" % (hour, t.tm_min, t.tm_sec,
                        t.tm_mon, t.tm_mday, t.tm_year)

    return time_str
    

def touch_pid(pid_loca):
    """ touch_pid(pid_loca)

    Touch the PID file and concatenate our PID into it.

    Return: True upon success, False upon any failure.
    """
    pid = os.getpid()
    fd = os.open(pid_loca, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
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
            rlist, wlist, xlist = select.select([sock], [], [], 0)
            
            if rlist:
                pkt = get_byte(rlist[0])
                
                if not pkt:
                    print("WARNING: There was an issue receiving the packet from the client. Ignored.")
                    continue
                   
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
                    print("WARNING: Malformed packet received from client. Ignoring.")
                    

            statusbar = statusbar_str()
            xsetroot(statusbar)
            time.sleep(update_clk)

        cleanup()
