#!/usr/bin/python

import logging
import select
import socket
import sys
import argparse
import rosapi

logging.basicConfig(level=logging.INFO)

exits = [{"text": "Ok", "code": 0}, {"text": "Warning", "code": 1}, {"text": "Critical", "code": 2}, {"text": "Unknown", "code": 3}]

parser = argparse.ArgumentParser(description='Check for monitoring Mikrotik Routerboards')
parser.add_argument('-H', help='Host address')
parser.add_argument('-p', help='ROS API Port', default=8728)
parser.add_argument('-m', help='Check type',default="resources")
parser.add_argument('-U', help='Username', default="admin")
parser.add_argument('-P', help='Password', default="")
args = parser.parse_args()

critical = 90
warning = 80

def gather_info(command):

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((args.H, args.p))
	api = rosapi.RosAPI(s)
	api.login(args.U, args.P)
	result = api.talk([command, "" ])
	return result

res = gather_info("/system/resource/print")[0][1]

values = {}

# Calculate memory
total = float(res['total-memory'])
free = float(res['free-memory'])
used = total - free
values['Memory Used'] = float(round(used / total * 100,2))

# Calculate HDD Space
total = float(res['total-hdd-space'])
free = float(res['free-hdd-space'])
used = total - free
values['HDD Used Space'] = int(round(used / total * 100,2))

# CPU is easy
values['CPU Load'] = int(res['cpu-load'])

info = "Routerboard " + res['board-name'] + " (" + res['architecture-name'] + ") RouterOS " + res['version']  + ", Uptime: " + res['uptime'] 
message = ""
perfdata = " | "
for metric in ["CPU Load", "HDD Used Space", "Memory Used"]:

	if values[metric] >= critical: 
		exit = exits[2]
		message += metric + " above critical threshold of " + str(critical) +"% "
	elif values[metric] >= warning: 
		exit = exits[1]
		message += metric + " above critical threshold of " + str(warning) + "% " 
	else: 
		exit = exits[0]
		message += metric + " is OK (" + str(values[metric]) + "%) "
	perfdata += metric.lower().replace(" ", "_") + "=" + str(values[metric]) + "%, "

print exit["text"] + ": " + message  + info + perfdata
sys.exit(exit["code"])