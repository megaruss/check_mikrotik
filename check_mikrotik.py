#!/usr/bin/python

import logging
import select
import socket
import sys
import argparse
import rosapi

logging.basicConfig(level=logging.INFO)

exits = [{"text": "Ok", "code": 0}, {"text": "args.w", "code": 1}, {"text": "Critical", "code": 2}, {"text": "Unknown", "code": 3}]
exit = exits[3]

parser = argparse.ArgumentParser(description='Check for monitoring Mikrotik Routerboards')
parser.add_argument('-H', help='mikrotik router address')
parser.add_argument('-p', help='routeros api port', default=8728)
parser.add_argument('-t', help='check type',default="resources")
parser.add_argument('-U', help='username', default="admin")
parser.add_argument('-P', help='password', default="")
parser.add_argument('-w', help='warning threshold', type=float, default=80)
parser.add_argument('-c', help='critical threshold', type=float, default=95)
parser.add_argument('-n', help='nominal value', type=float)
args = parser.parse_args()


values = {}
message = ""
perfdata = " | "


def gather_info(command):

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((args.H, args.p))
	api = rosapi.RosAPI(s)
	api.login(args.U, args.P)
	result = api.talk([command])
	return result

if args.t == "resources": 

	res = gather_info("/system/resource/print")[0][1]

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
	for metric in values:

		if values[metric] >= args.c: 
			exit = exits[2]
			message += metric + " is " + str(values[metric]) + " - above critical threshold of " + str(args.c) +"% "
		elif values[metric] >= args.w: 
			exit = exits[1]
			message += metric + " is " + str(values[metric]) + " - above warning threshold of " + str(args.w) + "% " 
		else: 
			exit = exits[0]
			message += metric + " is OK (" + str(values[metric]) + "%) "
		perfdata += "'" + metric + "'" + "=" + str(values[metric]) + "%;" + str(args.w) + ";" + str(args.c) + ";; " 
	print(exit["text"] + ": " + message  + info + perfdata)

elif args.t == "wireless_signal":
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
	perfdata += " | 'Wireless Clients'=" + str(len(client)) + " "
	for c in client: 
		message += "Wireless client: " + c + " - "
		for metric in client[c]: 
			message += metric + ": " + str(client[c][metric]) + "; "
			if type(client[c][metric]) == int: 
				perfdata += "'" + c + " " + metric + "'=" + str(abs(client[c][metric])) + ";" + str(args.w) + ";" + str(args.c) + ";; "
		message += "\n"
	print message + perfdata
	exit = exits[0]

elif args.t == "temperature":
	res = gather_info("/system/health/print")
	if 'temperature' not in res[0][1].keys():
		print "Temperature monitoring not supported on this routerboard"
		exit = exits[3]
	else: 
		temp = float(res[0][1]['temperature'])
		if temp >= args.c: 
			exit = exits[2]
			message += "CRITICAL: System temperature is " + str(temp) + "deg - above critical threshold of " + str(args.c)
		elif temp >= args.w: 
			exit = exits[1]
			message += "WARNING: System temperature is " + str(temp) + "deg - above warning threshold of " + str(args.w) 
		else: 
			exit = exits[0]
			message += "System temperature is OK - " + str(temp) + "deg"
		
		perfdata += "'System Temp'=" + str(temp)
		print message + perfdata


elif args.t == "voltage" and args.n:
	res = gather_info("/system/health/print")
	if 'voltage' not in res[0][1].keys():
		print "Voltage monitoring not supported on this routerboard"
		exit = exits[3]
	else: 
		volts = float(res[0][1]['voltage'])

		if (args.n - args.w) <= volts <= (args.n + args.w): 
			message = "OK: Supply voltage is " + str(volts) + "V - within warning range of " + str(args.n -  args.w) + " and " + str(args.n + args.w) 
			exit = exits[0]
		elif (args.n - args.c) <= volts <= (args.n + args.c): 
			message = "WARNING: Supply voltage is " + str(volts) + "V - outside warning range " + str(args.n -  args.w) + " and " + str(args.n + args.w) 
			exit = exits[1]
		else: 
			message = "CRITICAL: Supply voltage is " + str(volts) + "V - outside critical range " + str(args.n -  args.c) + " and " + str(args.n + args.c) 
			exit = exits[2]

		perfdata += "'System Voltage'=" + str(volts)
		print message + perfdata

else:
	print "UNKNOWN: - please specify -t and all sub options, ie: -n"

sys.exit(exit["code"])