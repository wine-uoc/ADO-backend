# user_control
Grafana to RPI user settings
This service is a python script (app.py) that collects the environment variables passed in the docker-compose file for accessing things and users postgres databases and connects to the mqtt broker. It also holds the credentials for the ado gmail account that sends notifications to the user on alerts.

The purpose of this service is to implement the grafana commands for setting the sampling rate @app.route('/control/SetSR/<publisher>/<channel>/sensors/<sensor_name>'), setting the alarm thresholds @app.route('/control/SetAlarm/<channel>/sensors/<sensorname>/<organization>/<dashboard_name>/<user_login>') and for calibration @app.route('/control/CAL/<publisher>/<channel>/sensors/<sensor_name>') #NGINX requires "control".

This service has also the role of resetting the user password if the user has forgotten it @app.route('/control/RenewAccountPassword/<token>/<identifier>', methods=['GET', 'POST']) and of bootstrapping the grafana dashboards on user registration using the flask app of the raspberry @app.route('/control/grafana', methods=['GET', 'POST']).


## Build image

"docker build -t user_control:latest ."
