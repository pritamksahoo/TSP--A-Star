import socket 
from _thread import *
import threading 
import json
import time
from os import listdir
from os.path import isfile, join
import account as acc
import log_handling as logh
import error_detection_recovery as er

global_port = 12356

halt_process = False
deamon_processes = []
warning_phase = False
running_process = {}
error_detection_time = None


def cur_time():
	'''
	Return current time in terms of yyyy-mm-dd hh:mm:ss
	'''

	time_now = time.localtime()
	y, mo, d, h, mi, s = time_now.tm_year, time_now.tm_mon, time_now.tm_mday, time_now.tm_hour, time_now.tm_min, time_now.tm_sec

	timestamp = "{year}-{month}-{day} {hour}:{minute}:{second}".format(year=y, month=mo, day=d, hour=h, minute=mi, second=s)

	return timestamp


def check_server_status(pid, con):
	'''
	Check whether the server is running a background check on log consistency of the system
	'''

	global halt_process
	global warning_phase
	global deamon_processes
	global error_detection_time

	if halt_process:
		# Wait for background consistency check to finish
		while halt_process:
			pass

	if warning_phase:
		# There was log inconsistency in the system. It is recovered, so strat fresh
		message = json.dumps({
			"type": "RESTART",
			"message": "Deamon process detected!",
			"process": { k:v for k,v in enumerate(deamon_processes) },
			"timestamp": error_detection_time
		})

		running_process.pop(pid)

		# force logout for system to be start fresh
		acc.logout(pid, cur_time())
		if pid in deamon_processes:
			acc.block(client_pid)

		con.sendall(message.encode())

		return "ERROR"

	# There was no inconsistency
	return "OK"


def background_error_check(sckt):
	'''
	Runs every 60 secs to check log inconsistency
	'''

	while True:
		try:
			global deamon_processes
			global halt_process

			# From now all processes have to halt
			halt_process = True

			# Server waiting for all the processes to become IDLE
			idly = list(running_process.values())
			while "BUSY" in idly:
				idly = list(running_process.values())

			# All processes are now idle, so server check for any inconsistency
			status, deamon_processes = er.check_log_consistency()

			if not status:
				# System is inconsistent
				print(" -------------------------")
				print("| DEAMON PROCESS DETECTED |")
				print(" -------------------------")

				global warning_phase
				global error_detection_time

				# Indicates all processes have to abort
				warning_phase = True
				
				# Block all the processes causing inconsistency
				for pid in deamon_processes:
					acc.block(pid)

				all_process = acc.all_process()
				error_detection_time = cur_time()

				# Notify all the other process about deamon processes
				notification = "[ " + error_detection_time + " ] : Deamon process detected ! Processes - " + str(deamon_processes)

				for pid, status in all_process:
					if status != 'Y':
						logh.create_notification(pid, notification, 'N')

					logh.create_notification(pid, "[ " +  error_detection_time + " ] : Starting system recovery", 'N')

				# Recover from fault, backword error recovery method has been used
				er.backward_error_recovery(cur_time())

				for pid, status in all_process:
					logh.create_notification(pid, "[ " + cur_time() + " ] : System back to normal", 'N')

				halt_process = False

				# Waiting until all the processes which were active during inconsistency to become passive (logged out)
				while len(running_process) != 0:
					pass

				# System is safe now, server can accept new connections
				warning_phase = False

			else:
				print(" -----------------------------------------------")
				print("| Background Error Detection Complete. NO ERROR |")
				print(" -----------------------------------------------")

				er.create_checkpoint(cur_time())
				deamon_processes = []
				halt_process = False
				warning_phase = False

		except KeyboardInterrupt:
			pass
		except Exception as e:
			s_log = json.dumps({
				"TYPE": "ERROR",
				"ERROR_DOMAIN": "CHECK_CONSISTENCY",
				"TIMESTAMP": cur_time(),
				"ERROR_DESC": str(e)
			})
			logh.create_new_log(None, s_log, False, False, True)

			pass

		warning_phase = False
		halt_process = False

		# Wait 60 secs before next background check
		time.sleep(60.0)


def threaded_client(con, sckt, addr):
	'''
	Threaded function. Each thread is assigned to listen for one client and respond to them
	'''
	
	client_pid, warning = None, False
	global running_process

	while True:

		try:
			# Received data from client
			print("\n" + str(addr) + " : Waiting for next request")
			msg = con.recv(4096).decode()
			data = json.loads(msg)
			print(str(addr) + "Request received")

			# Cheking server status, whether to proceed or halt
			if halt_process:
				while halt_process:
					pass

			if client_pid is None:
				client_pid = data["pid"]
				running_process[client_pid] = "NONE"

			if warning_phase:
				message = json.dumps({
					"type": "RESTART",
					"message": "Deamon process detected!",
					"process": { k:v for k,v in enumerate(deamon_processes) },
					"timestamp": error_detection_time
				})

				running_process.pop(client_pid)

				acc.logout(client_pid, cur_time())
				if client_pid in deamon_processes:
					acc.block(client_pid)

				con.sendall(message.encode())
				break
			
			# End checking server status, now proceed
			running_process[client_pid] = "BUSY"

			# Handling request from client
			if not data: 
				print("\n[", addr, "] Disconnected\n")
				break

			else:
				type = data["type"]

				if type == "SIGN_UP" or type == "LOG_IN":
					# Account creation (or) log in
					pid, password = data["pid"], data["password"]
					client_pid = pid

					time_now = cur_time()
					# Calling the main function
					ret_data = acc.create_account(pid, password, addr, time_now) if type == "SIGN_UP" else acc.login(pid, password, addr, time_now)

					print(addr, ":", ret_data["message"])

					ret_data["type"] = type

					message = json.dumps(ret_data)
					# Sending response
					con.sendall(message.encode())

					# If Log in or account creation fails, abort
					if ret_data["status"] == 400 or type == "SIGN_UP":
						running_process.pop(client_pid)
						break

					else:
						# Successful login
						client_log = json.dumps({
							"TYPE": "LOGIN",
							"TIMESTAMP": cur_time(),
							"STATUS": "SUCCESS"
						})

						logh.create_new_log(client_pid, client_log)

						print(addr, " : Waitig for ACK from client")

						'''
						Waiting for data from client
						'''
						running_process[client_pid] = "IDLE"

						# Receiveng ack from client
						acknowledgement = json.loads(con.recv(4096).decode())
						state = check_server_status(client_pid, con)
						if state == "ERROR":
							break

						running_process[client_pid] = "BUSY"

						print("\nACK from", addr)
						# print(acknowledgement)

						if acknowledgement["type"] == "ACK":
							notifications = logh.retrieve_unread_notifications(pid)
							message = json.dumps({
								"type" : "UNREAD_NOTIFICATIONS",
								"message": { k:v for k,v in enumerate(notifications) },
							})

							con.sendall(message.encode())

						else:
							running_process.pop(client_pid)
							break

				elif type == "LOG_OUT":
					# Logging out of the system
					acc.logout(pid, cur_time())

					client_log = json.dumps({
						"TYPE": "LOGOUT",
						"TIMESTAMP": cur_time(),
						"STATUS": "SUCCESS"
					})

					logh.create_new_log(client_pid, client_log)

					message = json.dumps({
						"type": "LOG_OUT_ACK",
						"message": "You are logged out",
					})

					running_process.pop(client_pid)
					con.sendall(message.encode())
					break

				elif type == "TRANSACTION":
					# Transaction
					credit, amount = data["credit"], data["amount"]

					timestamp = cur_time()

					debit_log = {
						"TYPE": "DEBIT",
						"FROM": client_pid,
						"TO": credit,
						"AMOUNT": amount,
						"TIMESTAMP": timestamp
					}

					credit_log = json.dumps({
						"TYPE": "CREDIT",
						"FROM": credit,
						"TO": client_pid,
						"AMOUNT": amount,
						"TIMESTAMP": timestamp
					})

					debit_notification = "[ " + cur_time() + " ] : $" + str(amount) + " debited from your account and credited to " + credit
					
					credit_notification = "[ " + cur_time() + " ] : $" + str(amount) + " credited to your account, received from " + client_pid

					# Saving transaction history
					status = logh.create_new_log(credit, credit_log, False, False)

					if status:
						debit_log["STATUS"] = "SUCCESS"
						logh.create_new_log(client_pid, json.dumps(debit_log))

						# Notify sender and receiver about successfult transaction
						logh.create_notification(client_pid, debit_notification, 'N')
						logh.create_notification(credit, credit_notification, 'N')

						client_note = logh.send_notifications_to_clients(client_pid)
						
						if client_note is None or client_note[0] is None:
							pass
						else:
							message = json.dumps({
								"type": "TRANSACTION",
								"status": 200,
								"message": debit_notification,
							})
							con.sendall(message.encode())
						
					else:
						debit_log["STATUS"] = "FAIL"
						logh.create_new_log(client_pid, json.dumps(debit_log))

						message = json.dumps({
							"type": "TRANSACTION",
							"status": 400,
							"message": "[ " + cur_time() + " ] : Transaction Failed! Invalid credit account (or) Credit Account is blocked for malicious activity",
						})
						con.sendall(message.encode())

				elif type == "REQ_LOG":
					client_log = logh.fetch_client_log(client_pid)

					# Sending log data bytes by bytes to client
					for log in client_log:
						con.sendall(log)
						
						'''
						Waiting for data from client
						'''
						running_process[client_pid] = "IDLE"						
						d = con.recv(1024).decode()
						state = check_server_status(client_pid, con)
						if state == "ERROR":
							break

						running_process[client_pid] = "BUSY"

						# Sending next bytes of data
						if d == "NEXT":
							pass
						else:
							break

					con.sendall("END_OF_FILE".encode())

					client_log = json.dumps({
						"TYPE": "REQ_LOG",
						"TIMESTAMP": cur_time(),
						"STATUS": "SUCCESS"
					})

					# logh.create_new_log(client_pid, client_log)
					'''
					Waiting for data from client
					'''
					running_process[client_pid] = "IDLE"

					# Receive back the file from client
					d = con.recv(1024).decode()
					state = check_server_status(client_pid, con)
					if state == "ERROR":
						break

					running_process[client_pid] = "BUSY"

					if d == "READY":
						content = ""
						con.sendall("READY".encode())

						while True:
							'''
							Waiting for data from client
							'''
							running_process[client_pid] = "IDLE"

							data = con.recv(1024).decode()
							state = check_server_status(client_pid, con)
							if state == "ERROR":
								break

							running_process[client_pid] = "BUSY"

							if data == "END_OF_FILE":
								break
							else:
								content = content + data

							con.sendall("NEXT".encode())
						
						with open("./server/local_storage/client_log/" + str(client_pid) + "/log.txt", "w") as fw:
							fw.write(content)
						
						print("\nComplete transfer\n")
					
					logh.create_new_log(client_pid, client_log)
						
					message = json.dumps({
						"type": "REQ_LOG",
						"status": 200,
						"message": "[ " + cur_time() + " ] : Successful log file transfer"
					})
					con.sendall(message.encode())
					
				else:
					pass
			
			running_process[client_pid] = "IDLE"

		except KeyboardInterrupt:
			message = json.dumps({
				"type" : "FORCED_LOG_OUT",
			})
			# Account becomes passive
			acc.logout(client_pid, cur_time())
			client_log = json.dumps({
				"TYPE": "LOGOUT",
				"TIMESTAMP": cur_time(),
				"STATUS": "SUCCESS"
			})
			logh.create_new_log(client_pid, client_log)

			running_process.pop(client_pid)

			con.sendall(message.encode())
			sckt.close()
			break

		except Exception as e:
			# print(e)
			s_log = json.dumps({
				"TYPE": "ERROR",
				"ERROR_DOMAIN": "MAIN_THREAD",
				"TIMESTAMP": cur_time(),
				"ERROR_DESC": str(e)
			})
			create_new_log(None, s_log, False, False, True)

			message = json.dumps({
				"type" : "FORCED_LOG_OUT",
			})
			# Account becomes passive
			acc.logout(client_pid, cur_time())
			client_log = json.dumps({
				"TYPE": "LOGOUT",
				"TIMESTAMP": cur_time(),
				"STATUS": "SUCCESS"
			})
			logh.create_new_log(client_pid, client_log)

			running_process.pop(client_pid)

			con.sendall(message.encode())
			sckt.close()
			break

		running_process[client_pid] = "IDLE"


	print("### Connection with [", addr, "] Closed ###\n")
	con.close() 
  
  
if __name__ == '__main__': 
	host = "127.0.0.1" 

	# Creating socket for listening to clients
	sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
	sckt.bind((host, global_port))
	print("\n### Socket binded to port -", global_port, "###")

	# Threaded function to check error in background
	t = threading.Thread(target=background_error_check, args=(sckt, ))
	t.start()

	# Listen upto maximum 5 clients
	sckt.listen(5) 
	print("Socket is listening ...\n") 

	while True:
		try:
			# Accepting clients' connection
			con, addr = sckt.accept()
			print('\nConnected to :', addr[0], ':', addr[1]) 

			# Assigning a thread to an individual client
			t1 = threading.Thread(target=threaded_client, args=(con, sckt, addr, ))
			t1.start()

		except KeyboardInterrupt:
			sckt.close()
			break

		except Exception as e:
			sckt.close()
			break

	try:
		sckt.close() 
	except Exception as exp:
		pass