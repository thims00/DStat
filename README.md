# DStatus - A "simple" notification statusbar for dwm

### Requirements
##### System Binaries
* dwm (http://dwm.suckless.org | a window manager supporting setting the statusbar through the Parent X Window Title.)
* sleepd (debpkg: https://packages.debian.org/source/sid/sleepd) 
* xtrlock (debpkg: https://packages.debian.org/source/wheezy/xtrlock)
* amixer  (debpkg: https://packages.debian.org/source/wheezy/alsa-utils)




### Supporting wrappers (Run file incorporation)
* The following wrappers must be in the users search path.

##### sleepd Wrapper:
```bash
#!/bin/bash

sleepctl status | grep -i "enabled" &> /dev/null
ret=$?

# Toggle the state of sleepd
if [ $ret == 0 ] ;then
  sleepctl off 
else
  sleepctl on
fi
```


##### xtrlock Wrapper:
```bash
#!/bin/bash

# run_file must correspond with dstat.py
run_file="/tmp/xtrlock.pid"
dstat="/home/user/.bin/dstat.py"

if [ ! -e "$run_file" ] ;then
  touch "$run_file"
  $dstat -m "Computer Locked"
  
  if [ $? -gt 0 ] ;then
    $dstat -m "ERROR: $0 could not create run file $run_file"
  fi

elif [ -w "$run_file" ] ;then
  :
else
  echo "ERROR: File is most likely not writable."
fi

# Start xtrlock, lose focus, and store the PID to the run file.
xtrlock &
pid="$!"
if [ -w "$run_file" ] ;then
  echo "$pid" > "$run_file"
fi

# Block execution and give xtrlock focus
wait 

if [ -w "$run_file" ] ;then
  rm "$run_file" 
fi

exit 0
```
