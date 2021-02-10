# Information
CLI-tool for VMware Carbon Black Cloud REST API. Main purpose of this tool is to be able to conduct searches on multiple instances, using saved or custom queries.


# Configuration

**API credentials**
The credentials are stored in KeePass-database in following format:
title = instance name
password = [API Secret Key]/[API ID]
url = [dashboard url]
notes = [Org key]

Example:
title = instance-1
password = ABCDEFGHIJKLMNOPQRSTUVWX/12345678
url = https://example.com/
notes = ABCDEFGH

Ref. https://developer.carbonblack.com/reference/carbon-black-cloud/authentication/

If you want to use the `-a` switch on this tool to sweep all instances with the query you need to create file `instances.txt` which contains the instance names, in the same directory as `cbc-cli.py`.

The KeePass-database location can be configured in file `config.ini`. Sample content:

```
[settings]
keepass_path=/home/foo/cbc-api.kdbx
```

# Usage
```
usage: cbc-cli.py [-h] [-a] [-v] [-i] [-ho DEVICE_NAME] [-st TIMEWINDOW]
                  instance

positional arguments:
  instance         Instance name

optional arguments:
  -h, --help       show this help message and exit
  -a               Sweep mode. When declared, it goes through all instances in
                   instances.txt
  -v               Verbose mode. Output all available fields as JSON
  -i               Interactive mode
  -ho DEVICE_NAME  Hostname to search
  -st TIMEWINDOW   Time window. y=year, w=week, d=day, h=hour, m=minute,
                   s=second
```


## Examples

**Do a free query on all instances**
    
    python3 cbc-cli.py instance-2 -st 4w -a

**Interactive mode, note that you can use -a switch to sweep all instances, otherwise it will reset back to False after a search if manually switched to 'All instances mode' in interactive mode.** 
    
    python3 cbc-cli.py instance-2 -st 2h -i -a


**Verbose mode**

    python3 cbc-cli.py instance-2 -st 1y -v

```
    ____             __                            __  _   _ _  _ 
   / __ \__  _______/ /___  ____  __   _   _____  / /_(_)_(_|_)(_)
  / /_/ / / / / ___/ __/ / / / / / /  | | / / _ \/ __/ __ `/ _ |  
 / ____/ /_/ (__  ) /_/ /_/ / /_/ /   | |/ /  __/ /_/ /_/ / __ |  
/_/    \__, /____/\__/\__, /\__, /    |___/\___/\__/\__,_/_/ |_|  
      /____/         /____//____/                                 

v0.0.1 by sanre
All instances mode: True
[0] General
[1] Discovery
[2] Execution
[3] Persistence
[4] Credential Access
[5] Lateral Movement
[6] Defense evasion
[7] Powershell
[8] Emotet
[9] LOLBINS
[10] Free search
[11] Toggle sweep mode (all instances or only the current)
CBC> 

```

**NOTE for lazy people like myself:**
I recommend using `rlwrap` or similar readline wrapper to have command history and completion within CLI.. :)
https://linux.die.net/man/1/rlwrap

