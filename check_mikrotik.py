#!/usr/bin/python

import logging
import select
import socket
import sys
import argparse
import rosapi

logging.basicConfig(level=logging.INFO)

exits = [{"text": "Ok", "code": 0}, {"text": "Warning", "code": 1}, {"text": "Critical", "code": 2}, {"text": "Unknown", "code": 3}]
exit = exits[3]

parser = argparse.ArgumentParser(description='Check for monitoring Mikrotik Routerboards')
parser.add_argument('-H', help='Host address')
parser.add_argument('-p', help='ROS API Port', default=8728)
parser.add_argument('-t', help='Check type',default="resources")
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
	result = api.talk([command])
	return result

if args.t == "resources": 

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
	values['HDD Used Space'] = float(round(used / total * 100,2))

	# CPU is easy
	values['CPU Load'] = float(res['cpu-load'])

	info = "Routerboard " + res['board-name'] + " (" + res['architecture-name'] + ") RouterOS " + res['version']  + ", Uptime: " + res['uptime'] 
	message = ""
	perfdata = " | "
	for metric in values:

		if values[metric] >= critical: 
			exit = exits[2]
			message += metric + "is " + str(values[metric]) + " - above critical threshold of " + str(critical) +"% "
		elif values[metric] >= warning: 
			exit = exits[1]
			message += metric + "is " + str(values[metric]) + " - above critical threshold of " + str(warning) + "% " 
		else: 
			exit = exits[0]
			message += metric + " is OK (" + str(values[metric]) + "%) "
		perfdata += "'" + metric + "'" + "=" + str(values[metric]) + "%;" + str(warning) + ";" + str(critical) + ";; " 
	print(exit["text"] + ": " + message  + info + perfdata)

elif args.t == "wireless_signal":
	message = ""
	perfdata = " | "
	res = gather_info("/interface/wireless/registration-table/print")
	del res[-1] #remove !done last element 
	client = dict()
	for reg in res: 
		client[reg[1]["mac-address"]] = dict()
		if "signal-strength-ch0" in reg[1].keys(): 
			client[reg[1]["mac-address"]]["Signal Chain 0"] = int(reg[1]["signal-strength-ch0"])
		if "signal-strength-ch1" in reg[1].keys():
			client[reg[1]["mac-address"]]["Signal Chain 1"] = int(reg[1]["signal-strength-ch1"])
		if "signal-to-noise" in reg[1].keys():
			client[reg[1]["mac-address"]]["Signal to Noise"] = int(reg[1]["signal-to-noise"])
		if "rx-ccq" in reg[1].keys():
			client[reg[1]["mac-address"]]["RX CCQ"] = int(reg[1]["rx-ccq"])
		if "tx-ccq" in reg[1].keys():
			client[reg[1]["mac-address"]]["TX CCQ"] = int(reg[1]["tx-ccq"])
		if "rx-rate" in reg[1].keys(): 
			client[reg[1]["mac-address"]]["RX Rate"] = reg[1]["rx-rate"]
		if "tx-rate" in reg[1].keys():
			client[reg[1]["mac-address"]]["TX Rate"] = reg[1]["tx-rate"]
	
	message = "Found " + str(len(client)) + " wireless clients\n"

	for c in client: 
		message += "Wireless client: " + c + " - "
		for metric in client[c]: 
			message += metric + ": " + str(client[c][metric]) + "; "
			if type(client[c][metric]) == int: 
				perfdata += "'" + c + " " + metric + "'=" + str(abs(client[c][metric])) + ";" + str(warning) + ";" + str(critical) + ";; "
		message += "\n"
	print message + perfdata
	exit = exits[0]

sys.exit(exit["code"])