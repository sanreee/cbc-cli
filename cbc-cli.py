import sys
import pprint
import json
import getpass
import argparse
import requests 
import re
import configparser
import concurrent.futures
import datetime
from time import sleep
from pykeepass import PyKeePass
from collections import OrderedDict
from urllib.parse import unquote
from menuhelpers import * 

header = "\
    ____             __                            __  _   _ _  _ \n\
   / __ \__  _______/ /___  ____  __   _   _____  / /_(_)_(_|_)(_)\n\
  / /_/ / / / / ___/ __/ / / / / / /  | | / / _ \/ __/ __ `/ _ |  \n\
 / ____/ /_/ (__  ) /_/ /_/ / /_/ /   | |/ /  __/ /_/ /_/ / __ |  \n\
/_/    \__, /____/\__/\__, /\__, /    |___/\___/\__/\__,_/_/ |_|  \n\
      /____/         /____//____/                                 \n"


class ParserClass(argparse.ArgumentParser):
  def error(self, message):
    sys.stderr.write('error: %s\n' % message)
    self.print_help()
    sys.exit(2)

class SmartFormatter(argparse.HelpFormatter):
  def _split_lines(self, text, width):
    if text.startswith('R|'):
      return text[2:].splitlines()
    return argparse.HelpFormatter._split_lines(self, text, width)
pp = pprint.PrettyPrinter(indent=4)

def parse_config():
    """
    parse the config file into globals
    :return:
    """
    global config
    try:
        config = configparser.ConfigParser()
        config.read('./config.ini', encoding='utf-8')
    except Exception as e:
        print(e)
        return None
    else:
        return config

config = parse_config()

parser = ParserClass(formatter_class=SmartFormatter)
parser.add_argument("instance", help="Instance name")

parser.add_argument("-a", help="Sweep mode. When declared, it goes through all instances in instances.txt", action='store_true')
parser.add_argument("-v", help="Verbose mode. Output all available fields as JSON", action='store_true')
parser.add_argument("-i", help="Interactive mode", action='store_true')
parser.add_argument("-e", help="Enriched mode. Fetch enriched events. Contains more post-processed data, including process links.", action='store_true')
parser.add_argument("-ho", help="Hostname to search", default="*", dest='device_name')
parser.add_argument("-st", help="Time window. y=year, w=week, d=day, h=hour, m=minute, s=second", default="4w", dest='timewindow')
parser.add_argument("-x", help="HTTPS proxy :: e.g. -x 127.0.0.1:8080 - sorry no http :)", default=None, dest='proxy')
parser.add_argument("-f", help="Feed search mode :: usage: -f feed.json :: cbfeeds format (github.com/carbonblack/cbfeeds)", default=None)
parser.add_argument("-w", help="Window search mode :: usage: -w 1440 :: Search events for timewindow of n-MINUTES around given process GUID")

args = parser.parse_args()
passwd = getpass.getpass(prompt='Password for KeePass database: ')
keepass_path = config.get('settings','keepass_path')
kp = PyKeePass(keepass_path, password=passwd)
instance = args.instance
timewindow = args.timewindow

global feedMode

colors = {
        'blue': '\033[94m',
        'pink': '\033[95m',
        'green': '\033[92m',
        }

if args.proxy:
  proxies = {
    "https": args.proxy
  }
else: 
  proxies = None

temp = None
sweepMode = False
verboseMode = False
enrichedMode = False

if args.a is True:
  sweepMode ^= True
if args.v is True:
  verboseMode ^= True
if args.e is True:
  enrichedMode ^= True

def colorize(string, color):
    if not color in colors: return string
    return colors[color] + string + '\033[0m'

def printBanner():
  print(colorize(header,'pink'))
  print(colorize('v0.0.4 by sanre','green'))

def clearPrompt():
   print("\x1B[2J")

def readInstances():
  wl = open("instances.txt","r")
  content = wl.readlines()
  #print(content)      # DEBUG print
  wl.close()
  return content

def doTheNeedful(q, sweepMode):
  if sweepMode == True:
    # Load instances
    instances = readInstances()
    args = ((q, instance, timewindow) for instance in instances)
    # Multithread through instances, gotta go fast
    if enrichedMode == True:
      with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for result in executor.map(lambda p: enrichedSearch(*p), args):
          if q != "MAGIC":
            pass
          else:
            print(result)
            return(result)
    else:
      with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for result in executor.map(lambda p: processSearch(*p), args):
          if q != "MAGIC":
            pass
          else:
            print(result)
            return(result)
  else:
    if enrichedMode == True: 
      return(enrichedSearch(q, instance,timewindow))
    else: 
      return(processSearch(q, instance,timewindow))

  input(colorize('Press enter to continue.', 'blue'))
  clearPrompt()
  mainMenu()

def windowSearch(sweepMode):
  window = args.w
  proc_guid = str(input("GUID> "))
  # 3A769AKMWN-003e2b21-00000434-00000000-1d7523d77de90e6
  if re.match("^[{]?([0-9a-zA-Z]{8}|[0-9a-zA-Z]{9}|[0-9a-zA-Z]{10}|[0-9a-zA-Z]{11}|[0-9a-zA-Z]{12})-([0-9a-fA-F]{8}-){3}[0-9a-fA-F]{15}[}]?$", proc_guid):
    # first get the process document for the GUID and parse it's timestamp
    q = f"process_guid:{proc_guid}"
    proc_document = doTheNeedful(q, sweepMode)
    if proc_document['results'][0]:
      process_start_time = proc_document['results'][0]['process_start_time']
      print(f"Original timestamp: {process_start_time}")
      print(colorize("Event found for GUID, fetching results for the window", 'pink'))
      proc_device = proc_document['results'][0]['device_name']
      if "\\" in proc_device: 
        proc_device = proc_device.split("\\")[1]
      args.device_name = proc_device
      process_start_time = datetime.datetime.strptime(process_start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
      earliest_ts = datetime.datetime.strftime(process_start_time - datetime.timedelta(minutes=int(window)), "%Y-%m-%dT%H:%M:%S.%fZ")
      latest_ts = datetime.datetime.strftime(process_start_time + datetime.timedelta(minutes=int(window)), "%Y-%m-%dT%H:%M:%S.%fZ")
      q = f"process_start_time:[{earliest_ts} TO {latest_ts}]"
      doTheNeedful(q, sweepMode)

  else:
    print("ERROR: Does not look like a GUID, exiting...")
    exit()

def feedSearch(sweepMode):
  socfeed = open(args.f, "r", encoding="ascii")
  socfeed = socfeed.read()
  socfeed = json.loads(socfeed)
  translated_queries = []
  
  for i in socfeed['reports']:
    report = ['title', 'query', 'description']
    title = i['title']
    ioc_queries = i['iocs']['query']
    description = "description_placeholder"
    for query in ioc_queries:
      q = unquote(query['search_query']).split("q=")[1]
      
    if q != "":
      report[0] = title
      report[1] = q
      report[2] = description
      translated_queries.append(report)
  
  #print(translated_queries)

  # For now, just go through the queries
  # In future, add also the title and description in the output
  for report in translated_queries:
    print(report[0])
    doTheNeedful(report[1], sweepMode)  

def freeSearch(sweepMode):
  clearPrompt()
  printBanner()
  print(colorize('All instances mode: '+str(sweepMode),'blue'))
  freesearch = input("CBC> ")
  q = freesearch
  doTheNeedful(q,sweepMode)

# MAIN MENU
def mainMenu(sweepMode=sweepMode):
  while True:
    clearPrompt()
    printBanner()
    print(colorize('All instances mode: '+str(sweepMode),'blue'))
    for item in menu_main:
      print("\033[32m[{0}]\033[m {1}".format(list(menu_main.keys()).index(item),item))
    try:
      opt = int(input("CBC> "))
      if int(opt) < 0 : raise ValueError
      for i, (a,b) in enumerate(menu_main.items()):
        if i == opt:
          if b == "menu_general"        : initMenu(menu_general, sweepMode)
          elif b == "menu_discovery"    : initMenu(menu_discovery, sweepMode)
          elif b == "menu_execution"    : initMenu(menu_execution, sweepMode)
          elif b == "menu_persistence"  : initMenu(menu_persistence, sweepMode)
          elif b == "menu_creds"        : initMenu(menu_creds, sweepMode)
          elif b == "menu_lateral"      : initMenu(menu_lateral, sweepMode)
          elif b == "menu_evasion"      : initMenu(menu_evasion, sweepMode)
          elif b == "menu_powershell"   : initMenu(menu_powershell, sweepMode)
          elif b == "menu_emotet"       : initMenu(menu_emotet, sweepMode)
          elif b == "menu_lolbins"      : initMenu(menu_lolbins, sweepMode)
          elif b == "menu_hafnium"      : initMenu(menu_hafnium, sweepMode)
          elif b == "free_search"       : freeSearch(sweepMode)
          elif b == "toggle_sweep"      : sweepMode^=True
    except (ValueError, IndexError):
      pass

# MENU HANDLER
def initMenu(b, sweepMode, temp=temp):
  while True:
    if (temp is None):
      temp = b
    elif type(b) == dict: mainMenu()
    else:
      clearPrompt()
      printBanner()
      print(colorize('All instances mode: '+str(sweepMode),'blue'))
      for item in temp:
        print("\033[32m[{0}]\033[m {1}".format(list(temp.keys()).index(item),item))
      try:
        opt = int(input("CBC> "))
        if int(opt) < 0 : raise ValueError
        for i, (a,b) in enumerate(b.items()):
          if i == opt:
            if b == "back" : mainMenu()
            else:
              doTheNeedful(b,sweepMode)
      except (ValueError, IndexError):
        pass

def processSearch(q, instance, timewindow):
  job_id = None
  device_name = args.device_name
  if instance != "" and timewindow != "":
    try:
      print(instance.strip())
      entry = kp.find_entries(title=instance.strip(), first=True)
      apikey = entry.password
      cbdurl = entry.url
      orgkey = entry.notes
    except Exception as e:
        print(e)

    headers = {'X-Auth-Token': apikey, 'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*'}

    job_data = {
        "fields": ["*", "process_start_time", "process_cmdline","process_internal_name","netconn_domain", "process_product_name", "crossproc_target", "crossproc_api","netconn_domain", "netconn_ipv4", "netconn_ipv6", "netconn_port", "netconn_inbound", "event_id", "childproc_name", "childproc_cmdline", "event_attack_stage", "ttp", "parent_name", "scriptload_hash", "scriptload_name", "scriptload_count", "fileless_scriptload_cmdline", "fileless_scriptload_cmdline_length", "fileless_scriptload_hash", "filemod_name"],
        "query": "device_name:{0} AND ({1})".format(device_name, q), 
        "rows": 500,
        "sort": [
            {
                "field": "device_timestamp",
                "order": "asc"
            }
        ],
        "time_range": {
            "window": "-{0}".format(timewindow)
        }
    }

    job_response = requests.post("{0}api/investigate/v2/orgs/{1}/processes/search_jobs".format(cbdurl,orgkey),headers=headers,data=json.dumps(job_data), verify=True, proxies=proxies)
    print(proxies)

    try:
      job_id = json.loads(job_response.text)['job_id']
    except UnboundLocalError:
      #print(e)
      pass
    except KeyError:
      pass

    if job_id:
      for retry in range(0,12):
        job_result = requests.get("{0}api/investigate/v2/orgs/{1}/processes/search_jobs/{2}/results".format(cbdurl,orgkey,job_id),headers=headers, verify=True, proxies=proxies) # This query schema fetches 10 rows of results by default, max is 10k. End results most likely need to be paginated.
        job_result_done = json.loads(job_result.text)
        contacted = job_result_done['contacted']
        completed = job_result_done['completed']
        num_found = job_result_done['num_found']
        num_available = job_result_done['num_available']
        #print(job_result_done)
        #print(retry)
        if (completed < contacted) and (retry <= 10):
          #print(job_result_done)
          print("instance: {0}, num_available: {1}, num_found: {2}, completed: {3}, contacted: {4}, retry: {5}/10".format(instance.strip(), num_available, num_found, completed, contacted, retry))
          #print(retry)
          sleep(1)
        elif retry > 10: 
          # Handle the pagination of results
          rows = 0
          print("instance: {0}, num_available: {1}, num_found: {2}, completed: {3}, contacted: {4}".format(instance.strip(), num_available, num_found, completed, contacted))
          while rows < num_available:
            job_result = requests.get("{0}api/investigate/v2/orgs/{1}/processes/search_jobs/{2}/results?start={3}&rows=500".format(cbdurl,orgkey,job_id,rows),headers=headers, verify=True, proxies=proxies) # This query schema fetches 500 rows at a time. Go through the results until pages run out.
            job_result_done = json.loads(job_result.text)
            for result in job_result_done['results']:
              result['instance'] = instance.strip()
              process_guid = result['process_guid']
              device_id = result['device_id']
              try:
                event_id = result['event_id']
                result['link_process'] = '{0}cb/investigate/events/events?query=event_id%3A{1}'.format(cbdurl,event_id)
                link_process = result['link_process']
              except Exception as e: 
                #print(e)
                event_id = "N/A"
                event_id = "N/A"
                result['link_process'] = "N/A"
                link_process = "N/A"
                try:
                  process_guid = result['process_guid']
                  result['link_process'] = '{0}cb/investigate/events/events?query=device_id%3A{1}%20process_guid%3A{2}'.format(cbdurl, device_id, process_guid)
                  link_process = result['link_process']
                except:
                  pass
                pass
              
              process_start_time = result['process_start_time']
              device_name = result['device_name']
              try:
                process_username = result['process_username']
              except:
                process_username = "N/A"
                pass
              try:
                process_cmdline = result['process_cmdline']
              except Exception as e:
                process_cmdline = "N/A"
                pass
            print("num_available: {0}".format(num_available))
            print("rows: {0}".format(rows))
            rows += 500
            if verboseMode == True:
              pprint.pprint(job_result_done)
              return(job_result_done)
              break
            else:
              for result in job_result_done['results']:
                process_start_time = result['process_start_time']
                device_name = result['device_name']
                try:
                  process_username = result['process_username']
                except:
                  process_username = "N/A"
                  pass
                try:
                  process_cmdline = result['process_cmdline']
                except Exception as e:
                  process_cmdline = "N/A"
                  pass
                link_process = result['link_process']
                print("{0} {1} {2} {3} {4} \n\033[1;30;40m{5}\033[m".format(process_start_time, instance.strip(), device_name, process_username, process_cmdline, link_process))
              return(job_result_done)
              break

    else: 
      print("No events found")

def enrichedSearch(q, instance, timewindow):
  job_id = None
  device_name = args.device_name
  if instance != "" and timewindow != "":
    try:
      print(instance.strip())
      entry = kp.find_entries(title=instance.strip(), first=True)
      apikey = entry.password
      cbdurl = entry.url
      orgkey = entry.notes
    except Exception as e:
        print(e)

    headers = {'X-Auth-Token': apikey, 'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*'}

    job_data = {
        "fields": ["*", "process_start_time", "process_cmdline","process_internal_name","netconn_domain", "process_product_name", "crossproc_target", "crossproc_api","netconn_domain", "netconn_ipv4", "netconn_ipv6", "netconn_port", "netconn_inbound", "event_id", "childproc_name", "childproc_cmdline", "event_attack_stage", "ttp", "parent_name", "scriptload_hash", "scriptload_name", "scriptload_count", "fileless_scriptload_cmdline", "fileless_scriptload_cmdline_length", "fileless_scriptload_hash"],
        "query": "device_name:{0} AND ({1})".format(device_name, q), 
        "rows": 500,
        "sort": [
            {
                "field": "device_timestamp",
                "order": "asc"
            }
        ],
        "time_range": {
            "window": "-{0}".format(timewindow)
        }
    }

    job_response = requests.post("{0}api/investigate/v1/orgs/{1}/enriched_events/aggregation_jobs/device_id".format(cbdurl,orgkey),headers=headers,data=json.dumps(job_data), verify=True, proxies=proxies)

    try:
      job_id = json.loads(job_response.text)['job_id']
    except UnboundLocalError:
      #print(e)
      pass
    except KeyError:
      pass
    if job_id:
      for retry in range(0,12):
        job_result = requests.get("{0}api/investigate/v1/orgs/{1}/enriched_events/aggregation_jobs/{2}/results".format(cbdurl,orgkey,job_id),headers=headers, verify=True, proxies=proxies) # This query schema fetches 10 rows of results by default, max is 10k. End results most likely need to be paginated.
        job_result_done = json.loads(job_result.text)
        contacted = job_result_done['contacted']
        completed = job_result_done['completed']
        num_found = job_result_done['num_found']
        num_available = job_result_done['num_available']

        if (completed < contacted) and (retry <= 10):
          print("instance: {0}, num_available: {1}, num_found: {2}, completed: {3}, contacted: {4}, retry: {5}/10".format(instance.strip(), num_available, num_found, completed, contacted, retry))
          sleep(1)
        elif retry > 10: 
          # Handle the pagination of results
          rows = 0
          print("instance: {0}, num_available: {1}, num_found: {2}, completed: {3}, contacted: {4}".format(instance.strip(), num_available, num_found, completed, contacted))
          while rows < num_available:
            job_result = requests.get("{0}api/investigate/v1/orgs/{1}/enriched_events/aggregation_jobs/{2}/results?start={3}&rows=500".format(cbdurl,orgkey,job_id,rows),headers=headers, verify=True, proxies=proxies) # This query schema fetches 500 rows at a time. Go through the results until pages run out.
            job_result_done = json.loads(job_result.text)
            for result in job_result_done['results']:
              result['instance'] = instance.strip()
              process_guid = result['process_guid']
              device_id = result['device_id']
              event_id = result['event_id']
              result['link_process'] = '{0}cb/investigate/events/events?query=event_id%3A{1}'.format(cbdurl,event_id)
              process_start_time = result['process_start_time']
              device_name = result['device_name']
              process_username = result['process_username']
              process_cmdline = result['process_cmdline']
              link_process = result['link_process']
            print("num_available: {0}".format(num_available))
            print("rows: {0}".format(rows))
            rows += 500
            if verboseMode == True:
              pprint.pprint(job_result_done)
              return(job_result_done)
              break
            else:
              for result in job_result_done['results']:
                process_start_time = result['process_start_time']
                device_name = result['device_name']
                process_username = result['process_username']
                process_cmdline = result['process_cmdline']
                link_process = result['link_process']
                print("{0} {1} {2} {3} {4} \n\033[1;30;40m{5}\033[m".format(process_start_time, instance.strip(), device_name, process_username, process_cmdline, link_process))
              return(job_result_done)
              break

    else: 
      print("No events found")

if args.i == True:
  mainMenu(sweepMode)
elif args.f:
  feedSearch(sweepMode)
elif args.w:
  windowSearch(sweepMode)
else: freeSearch(sweepMode)
