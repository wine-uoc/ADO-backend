from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import psycopg2
import paho.mqtt.client as mqtt
import time
import json
import os
import grafana_interactions as gr
import grafana_bootstrap
import jwt
from flask_mail import Message, Mail

app = Flask(__name__)
CORS(app)

#Obtain variables
postgres_user = os.environ["MF_USER_CONTROL_POSTGRES_USER"] 
postgres_password = os.environ["MF_USER_CONTROL_POSTGRES_PASSWORD"] 
postgres_host = os.environ["MF_USER_CONTROL_POSTGRES_HOST"] # mainflux-things-db
postgres_port = os.environ["MF_USER_CONTROL_POSTGRES_PORT"] #5432
postgres_db = os.environ["MF_USER_CONTROL_POSTGRES_DB"] #things
mqtt_broker_host = "mainflux-mqtt"
mqtt_port = 1883

http_protocol = os.environ["MF_AJAX_HTTP_PROTOCOL"] 
server_ip = os.environ["MF_AJAX_SERVER_IP"] 

# Email Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ['MF_USER_CONTROL_MAIL_USERNAME'] #"@gmail.com"
app.config['MAIL_PASSWORD'] = os.environ['MF_USER_CONTROL_MAIL_PASSWORD']
app.config['MAIL_DEFAULT_SENDER'] = ("ADO-RECOVERY", app.config['MAIL_USERNAME'])

mail = Mail()
mail.init_app(app)

connection = psycopg2.connect(user=postgres_user,
                                  password=postgres_password,
                                  host=postgres_host,
                                  port=postgres_port,
                                  database=postgres_db)

cursor = connection.cursor()

user_connection = psycopg2.connect(user=postgres_user,
                                  password=postgres_password,
                                  host="mainflux-users-db",
                                  port=postgres_port,
                                  database="users")

user_cursor = user_connection.cursor()

def query_db(publisher):
	postgreSQL_select_Query = "select things.* from things things where things.id='"+ str(publisher)+ "'"
	cursor.execute(postgreSQL_select_Query)
	things_records = cursor.fetchall() 
	thing_id =0
	thing_key=0
	if things_records is not None:
		for row in things_records:
			print("Entry = ", row, "\n")
			thing_id=row[0]
			thing_key=row[2]
		return thing_id,thing_key

def query_channels(channel):
	postgreSQL_select_Query = "select channels.* from channels where channels.id='"+ str(channel)+ " LIMIT 1'"
	cursor.execute(postgreSQL_select_Query)
	channels_records = cursor.fetchone() 
	user_email=None
	if channels_records is not None:
		for row in channels_records:
			print("Entry = ", row, "\n")
			user_email=row[1]
		return user_email

def return_channels_list():
	postgreSQL_select_Query = "select channels.* from channels"
	cursor.execute(postgreSQL_select_Query)
	channels_records = cursor.fetchall() 
	ch_list=[]
	if channels_records is not None:
		for row in channels_records:
			#print("Entry = ", row, "\n")
			ch=row[0]
			ch_list.append(ch)
		return ch_list

def query_db_passwd(email):
	postgreSQL_select_Query = "select users.* from users where users.email='"+ str(email)+ "'"
	user_cursor.execute(postgreSQL_select_Query)
	password_record = user_cursor.fetchall() 
	passwd= None
	if password_record is not None:
		for row in password_record:
			print("Entry = ", row, "\n")
			passwd=row[1]
	return passwd

def update_db_passwd(email, new_hash):
	#updates the password corresponding to this user with a new one as hash
	try:
		postgreSQL_update_Query = "update users set password='"+ str(new_hash)+ "' where users.email='"+ str(email)+ "'"
		user_cursor.execute(postgreSQL_update_Query)
		user_connection.commit()
		count= user_cursor.rowcount
		print(count, "Record updated successfully")
	except:
		user_cursor.execute("ROLLBACK")
		user_connection.commit()
	return count

def on_connect(client, userdata, flags, rc):
	if rc == 0:
		client.connected_flag=True               #Signal connection 
	else:
		client.connected_flag=False
                   #attach function to callback
@app.route('/control/SetSR///sensors/') #when there is no data in influxdb
def initialpage():
	msg = "Waiting for sensor to initialize" #to send its SR, confirming that is up
	return render_template('index.html', message=msg)

@app.route('/control/SetSR/<publisher>/<channel>/sensors/<sensor_name>')
def mainpage(publisher, channel, sensor_name):
	return render_template('index.html', message= "", device = publisher, channel = channel, sensor=sensor_name)


@app.route('/control/CAL///sensors/') #when there is no data in influxdb
def calinitialpage():
	return render_template('calibration-empty.html')

@app.route('/control/CAL/<publisher>/<channel>/sensors/<sensor_name>') #NGINX requires "control"
def calpage(publisher, channel, sensor_name):
	if sensor_name == "pH":
		return render_template('calibration-ph.html', message= "", device = publisher, channel = channel, sensor=sensor_name)
	elif sensor_name == "Conductivity1":
		return render_template('calibration-conductivity1.html', message= "", device = publisher, channel = channel, sensor=sensor_name)
	elif sensor_name == "Conductivity2":
		return render_template('calibration-conductivity2.html', message= "", device = publisher, channel = channel, sensor=sensor_name)
	elif sensor_name == "Oxygen":
		return render_template('calibration-do.html', message= "", device = publisher, channel = channel, sensor=sensor_name)
	elif sensor_name == "AirCO2":
		return render_template('calibration-airco2.html', message= "", device = publisher, channel = channel, sensor=sensor_name)




@app.route('/control/SendMessage/<selectedvalue>/<publisher>/<channel>/sensors/<sensor_name>')
def sendmessage(selectedvalue, publisher, channel, sensor_name):
	thing_id, thing_key= query_db(publisher)
	if (thing_id != 0 and thing_key != 0):
		mqtt.Client.connected_flag=False
		client = mqtt.Client()    
		client.username_pw_set(thing_id, thing_key)    #set username and password
		client.on_connect=on_connect
		try:
			client.connect(host=mqtt_broker_host, port=mqtt_port)
			client.loop_start()
			topic= "channels/" + str(channel) +  "/control/SR/" + str(thing_id)  #only this node will be subscribed to this particular topic
			timestamp = time.time()
			data = {"type": "SET_SR", "sensor":sensor_name, "v":selectedvalue, "u":"s", "t":timestamp}
			client.publish(topic,json.dumps(data)) 
			client.disconnect()
			client.loop_stop()
			return "OK"
		except:
			return "Connection to device failed, try again"
	else:
		return "Failed setting SR, try again"



@app.route('/control/calibration/Set/<db_to_use>/<target_device>/<channel>/sensors/<sensorname>')
def cal_sensor(db_to_use,target_device,channel,sensorname):

	print("sensor:", sensorname) 
	print("db:", db_to_use) 
	print("target dev:", target_device) 
	print("channel:", channel)
	thing_id, thing_key= query_db(target_device)
	if (thing_id != 0 and thing_key != 0):
		mqtt.Client.connected_flag=False
		client = mqtt.Client()    
		client.username_pw_set(thing_id, thing_key)    #set username and password
		client.on_connect=on_connect
		try:
			client.connect(host=mqtt_broker_host, port=mqtt_port)
			client.loop_start()
			topic= "channels/" + str(channel) +  "/control/CAL/" + str(thing_id)  #only this node will be subscribed to this particular topic
			timestamp = time.time()
			data = {"type": "CAL", "sensor":sensorname, "v":db_to_use, "t":timestamp}
			client.publish(topic,json.dumps(data)) 
			client.disconnect()
			client.loop_stop()
			return "OK"
		except:
			return "Connection to device failed, try again"
	else:
		return "Failed calibrating sensor, try again"	


@app.route('/control/SetAlarm/<channel>/sensors/<sensorname>/<organization>/<dashboard_name>/<user_login>')
def alarmpage(channel, sensorname, organization, dashboard_name, user_login):
#TBD: USER_LOGIN--> USER_EMAIL. to check in channels table the existing link between channel and user
	# for now: just check that channel is valid, or exists
	if sensorname == "Temperature-S":
		pan_order = 2 #panel order in Alertes dashboard
	elif sensorname == "AirCO2":
		pan_order = 3
	elif sensorname == "WaterLevel":
		pan_order = 4
	elif sensorname == "Oxygen":
		pan_order = 5
	elif sensorname == "AtmosphericTemp":
		pan_order = 6
	elif sensorname == "Conductivity2":
		pan_order = 7
	elif sensorname == "Conductivity1":
		pan_order = 8
	elif sensorname == "Turbidity":
		pan_order = 9
	elif sensorname == "pH":
		pan_order = 10
	elif sensorname == "Humidity":
		pan_order = 11
	elif sensorname == "Temperature-D":
		pan_order = 12
	else:
		message = "Invalid sensor name" #will appear in div
		return render_template('alarm.html', message= message, sensor=sensorname, min_val="None", max_val = "None" , channel=channel,
			 organization=organization, dashboard_name=dashboard_name, user_login=user_login)
	#try:
	#	start_time = time.time()
	#	user_email = query_channels(channel)
	#	print("--- %s seconds query_channels ---" % (time.time() - start_time))
	#except:
	#	message = "Db Query error"
	#	return render_template('alarm.html', message= message, sensor=sensorname, min_val = "None", max_val= "None", channel=channel,
	#		 organization=organization, dashboard_name=dashboard_name, user_login=user_login)
	user_email = None
	if user_email is None: #so channel exists
		try:
			start_time =  time.time()
			#will extract the json definition of this particular dashboard
			#this fc already switches organization
			print("Obtaining dashboard json")  
			data=gr._get_dashboard_json(dashboard_name, organization) #collapsed has to be True for all rows!
			crt_min = data['dashboard']['panels'][pan_order]['panels'][0]['alert']['conditions'][0]['evaluator']['params'][0]
			crt_max = data['dashboard']['panels'][pan_order]['panels'][0]['alert']['conditions'][0]['evaluator']['params'][1]
			print("--- %s seconds _get_dashboard_json---" % (time.time() - start_time))
			return render_template('alarm.html', message= "", sensor=sensorname, min_val=crt_min, max_val = crt_max, channel=channel,
			 organization=organization, dashboard_name=dashboard_name, user_login=user_login)
		except:
			message = "Something went wrong when querying the alarm"
			return render_template('alarm.html', message= message, sensor=sensorname, min_val="None", max_val = "None" , channel=channel,
			 organization=organization, dashboard_name=dashboard_name, user_login=user_login)
	else:
		message = "Invalid channel"
		return render_template('alarm.html', message= message, sensor=sensorname, min_val="None", max_val = "None", channel=channel,
			 organization=organization, dashboard_name=dashboard_name, user_login=user_login)
	

@app.route('/control/UpdateAlarmDashboard/<channel>/sensors/<sensorname>/<organization>/<dashboard_name>/<user_login>/<set_min_value>/<set_max_value>')
def Set_Alarm(channel, sensorname, organization, dashboard_name, user_login, set_min_value, set_max_value):
	#TBD: USER_LOGIN--> USER_EMAIL. to check in channels table the existing link between channel and user
	# for now: just check that channel is valid, or exists

	print("sensor:", sensorname) 
	print("organization:", organization)
	print("dashboard_name:", dashboard_name)
	print("user_login:", user_login)
	print("set_min_value:", set_min_value)
	print("set_max_value:", set_max_value)


	if sensorname == "Temperature-S":
		pan_order = 2 #panel order in Alertes dashboard
	elif sensorname == "AirCO2":
		pan_order = 3
	elif sensorname == "WaterLevel":
		pan_order = 4
	elif sensorname == "Oxygen":
		pan_order = 5
	elif sensorname == "AtmosphericTemp":
		pan_order = 6
	elif sensorname == "Conductivity2":
		pan_order = 7
	elif sensorname == "Conductivity1":
		pan_order = 8
	elif sensorname == "Turbidity":
		pan_order = 9
	elif sensorname == "pH":
		pan_order = 10
	elif sensorname == "Humidity":
		pan_order = 11
	elif sensorname == "Temperature-D":
		pan_order = 12
	else:
		return "Invalid sensor name" #will appear in div
		
	#try:
	#	start_time = time.time()
	#	user_email = query_channels(channel)
	#	print("--- %s seconds query_channels set alarm---" % (time.time() - start_time))
	#except:
	#	return  "Db Query error"
		
	user_email = None
	if user_email is None: #so channel exists
		try:
			#will extract the json definition of this particular dashboard
			#this fc already switches organization
			start_time =  time.time()
			print("Obtaining dashboard json")  
			data=gr._get_dashboard_json(dashboard_name, organization) #collapsed has to be True for all rows!

			print("--- %s seconds obtain dash ---" % (time.time() - start_time))
			start_time = time.time()
			data['dashboard']['panels'][pan_order]['panels'][0]['alert']['conditions'][0]['evaluator']['params'][0]= float(set_min_value)
			data['dashboard']['panels'][pan_order]['panels'][0]['alert']['conditions'][0]['evaluator']['params'][1]= float(set_max_value)

			#also change the position of the critical red line
			data['dashboard']['panels'][pan_order]['panels'][0]['thresholds'][0]['value']= float(set_min_value)
			data['dashboard']['panels'][pan_order]['panels'][0]['thresholds'][1]['value']= float(set_max_value)

			#also change the yaxes min and max values which are set to [0,40] by default. +/- 10% of the interval
			interval = float(set_max_value) - float(set_min_value)
			data['dashboard']['panels'][pan_order]['panels'][0]['yaxes'][0]['min']= float(set_min_value) - interval/10
			data['dashboard']['panels'][pan_order]['panels'][0]['yaxes'][0]['max']= float(set_max_value) + interval/10

			
			print("Uploading dashboard json")

			status, uid = gr._update_existing_dashboard(data)
			print("--- %s seconds update dash---" % (time.time() - start_time))
			#todo:
			# html file for setting alarms
			# upload code to github and dockerhub and mainflux docker
			if status == "success":
				print("the alarm was correctly set")
				return "OK"
			else:
				print("unable to set alarm", str(status))
				return "Unable to set alarm"
		except Exception as e:
			print(str(e))
			return "Something went wrong when querying the alarm"
	else:
		return "Invalid channel"
	

@app.route('/control/RenewAccountPassword/<token>/<identifier>', methods=['GET', 'POST'])
def RenewAccountPassword(token, identifier):
	#change mainflux password for this user
	#this function will be called only if rpi-flaskapp reset has a validated user via email with tokens
	#token is generated with the rpi db channel id for this user
	print("reading passed data")
	try:
		new_pass = request.get_json()['change'] #hashed password
		print(new_pass)
	except Exception as e:
		print(str(e))
	status= "failed"
	channel_list=return_channels_list() #returns all mainflux channels
	#print(channel_list)
	matching = [s for s in channel_list if identifier in s]
	for key in matching:
		try:
			email = jwt.decode(token, key=key)['reset_password']
			print(email)
			if email == query_channels(key):
				print("found user, modifying password")
				count=update_db_passwd(email, new_pass)
				if count:
					status = "success"
		except Exception as e:
			print(str(e))
	
	answer = {'status': status}
	return json.dumps(answer)

@app.route('/control/grafana', methods=['GET', 'POST'])
def BootstrapGrafana():
	global http_protocol, server_ip

	#this function is called by the rpi-flaskapp to instantiate grafana for a new user
	#user email and password are carried in json, exactly as in mainflux account creation
	#it should return success/failed
	try:
		email = request.get_json()['email']
		password = request.get_json()['password']
		name = request.get_json()['name']
		organization =  request.get_json()['organization']
		channel_id = request.get_json()['channel_id']
	except Exception as e:
		print(str(e))
	
	status=grafana_bootstrap.bootstrap(name, organization, email, password, channel_id, http_protocol, server_ip)
	answer = {'status': status}
	return json.dumps(answer)

@app.route('/control/grafana/dash_update', methods=['GET', 'POST'])
def UpdateDashboardGrafana():
	global http_protocol, server_ip
	#this function is called by the rpi-flaskapp to update the user dashboard to the last version
	#(if its the case)
	try:
		organization =  request.get_json()['organization']
	except Exception as e:
		print(str(e))
	
	status=grafana_bootstrap.updateDashboard(organization, http_protocol, server_ip)
	answer = {'status': status}
	return json.dumps(answer)

@app.route('/control/resetpassword/sendmail', methods=['GET', 'POST'])
def SendResetEmail():
	#this function is called by the rpi-flaskapp to update the send password reset email
	try:
		email = request.get_json()['email'] 
		token = request.get_json()['token']
		name = request.get_json()['name']
		node_name = request.get_json()['node_name']
	except Exception as e:
		print("Error when retrieving variables:", str(e))
	status= "failed"
	pageURL="https://"+ str(node_name)+ ".local/password_reset_code/"+str(token)
	try:
		msg = Message()
		msg.subject = "Reset your ADO-node password"
		msg.recipients = [email] #converts to list
		msg.html = render_template('reset-email.html', name=name, pageURL=pageURL)
		mail.send(msg)
		status = "success"
	except Exception as e:
		print("Error when sending email: ",str(e))

	answer = {'status': status}
	return json.dumps(answer)

@app.route('/control/calibration/Check/<target_device>/<channel>/sensors/<sensorname>')
def cal_check(target_device, channel, sensorname):
	return "OK"#"to be implemented"


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000)
