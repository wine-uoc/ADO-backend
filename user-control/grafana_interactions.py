"""Grafana interaction functions."""
import requests
from grafana_api.grafana_face import GrafanaFace
import os

# Login to the grafana api through the library

grafana_port = os.environ["MF_USER_CONTROL_GRAFANA_PORT"] #3001
grafana_admin_name = os.environ["MF_USER_CONTROL_GRAFANA_ADMIN_NAME"] #admin
grafana_admin_pass = os.environ["MF_USER_CONTROL_GRAFANA_ADMIN_PASS"] #admin
#grafana_port = 3001
#grafana_admin_name = "admin"
#grafana_admin_pass = "admin"
grafana_api = GrafanaFace(auth=(grafana_admin_name, grafana_admin_pass), host='mainflux-grafana', port=grafana_port)
host = 'http://'+ grafana_admin_name + ':' + grafana_admin_pass + '@mainflux-grafana:'+str(grafana_port)


def _generic_get(url_):
    url = host + url_
    headers = {"Content-Type": 'application/json'}
    response = requests.get(url, headers=headers)
    print(response.text)
    return response.json


# ORGANIZATIONS
def _organization_check(organization):  # checks if org exists or not in order to create it
    orgs = grafana_api.organizations.list_organization()
    for i in range(len(orgs)):
        if str(organization) in orgs[i]['name']:
            print("organization already created")
            return 1
    return 0


def _create_organization(organization):
    url = host + '/api/orgs'
    data = {
        "name": organization,
    }
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    print(response.text)


def _get_current_organization():
    url = host + '/api/org/'
    response = requests.get(url)
    organization_details = response.json()
    print(organization_details["name"])
    return str(organization_details["name"])


def _get_organization_id(organization_name):
    orgs = grafana_api.organizations.list_organization()
    print(orgs)
    for i in range(len(orgs)):
        if str(organization_name) in orgs[i]['name']:
            return orgs[i]['id']
    return 0  # there is no organization ID zero in grafana


def _change_current_organization_to(new_organization):
    org_id = _get_organization_id(new_organization)
    print('organization id ', org_id)
    url = host + '/api/user/using/' + str(org_id)
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, headers=headers)
    print(response.text)
    print("current organization is now ", new_organization)


def _delete_organization(org_name):
    org_id = _get_organization_id(org_name)
    if org_id != 0:
        print("deleting organization..", org_name)
        url = host + '/api/orgs/' + str(org_id)
        headers = {"Content-Type": 'application/json'}
        response = requests.delete(url, headers=headers)
        print(response.text)
    else:
        print("organization does not exist")


def update_preferences_org(dash_id):
    url = host + '/api/org/preferences'
    headers = {"Content-Type": 'application/json'}
    data = {
        "theme": "dark",
        "homeDashboardId": dash_id,
        "timezone": "browser"
    }
    response = requests.put(url, json=data, headers=headers)
    print(response.text)


# USERS
def _get_all_users_org():  # returns all users of the selected organization
    url = host + '/api/org/users'
    response = requests.get(url)
    user_list = response.json()
    for i in range(len(user_list)):
        print(user_list[i]['login'])
    return user_list


def _user_check(user_org, user):
    # switch to user_org
    _change_current_organization_to(user_org)
    user_list = _get_all_users_org()
    for i in range(len(user_list)):
        if user_list[i]['login'] == user:
            return user_list[i]['userId']
    return 0  # user not found


def _create_user(user):  # creates it and does not assign it to anything
    print("****************************************")
    url = host + '/api/admin/users'
    data = {
        "name": user["name"],
        "email": user["email"],
        "login": user["login"],
        "password": user["password"],
    }
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    print(response.text)


def _assign_user_to_organization(organization, user, role):
    org_id = _get_organization_id(organization)
    url = host + '/api/orgs/' + str(org_id) + '/users'
    data = {
        "loginOrEmail": user["login"],
        "role": str(role),

    }
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    print(response.text)


def _get_global_user_id(user_login):  # without switching to org
    url = host + '/api/users/lookup?loginOrEmail=' + str(user_login)
    headers = {"Content-Type": 'application/json'}
    response = requests.get(url, headers=headers)
    print(response.text)
    user_data = response.json()
    if 'id' not in user_data:  # user does not exists
        print("no such user")
        return 0
    else:
        print(user_data['id'])
        return user_data['id']


def _delete_user(user_login):
    print("deleting user .. ", user_login)
    user_id = _get_global_user_id(user_login)
    if user_id != 0:
        url = host + '/api/admin/users/' + str(user_id)
        headers = {"Content-Type": 'application/json'}
        response = requests.delete(url, headers=headers)
        print(response.text)


def _remove_user_from_org(user_login):
    print("removing user from current organization .. ", user_login)
    user_id = _get_global_user_id(user_login)
    if user_id != 0:
        url = host + '/api/org/users/' + str(user_id)
        headers = {"Content-Type": 'application/json'}
        response = requests.delete(url, headers=headers)
        print(response.text)


def _star_dashboard(dash_id):
    url = host + '/api/user/stars/dashboard/' + str(dash_id)
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, headers=headers)
    print(response.text)


def update_preferences_user(dash_id):
    url = host + '/api/user/preferences'
    headers = {"Content-Type": 'application/json'}
    data = {
        "theme": "dark",
        "homeDashboardId": dash_id,
        "timezone": "browser"
    }
    response = requests.put(url, json=data, headers=headers)
    print(response.text)


# DATASOURCES
def _create_datasource(name, database):
    global grafana_admin_name, grafana_admin_pass
    # https://community.influxdata.com/t/cannot-connect-to-influx-datasource-from-grafana/8048/2
    url = host + '/api/datasources'
    data = {
        "name": name,
        "type": "influxdb",
        "url": "http://influxdb:8086",
        "access": "proxy",  # direct, proxy
        "password": grafana_admin_pass,
        "user": grafana_admin_name,
        "database": database,
        "isDefault": True,
        "jsonData": {"httpMode": "GET"}
    }
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    print(response.text)
    return response.json()["datasource"]["id"]


def _delete_datasource(datasource_name):
    url = host + '/api/datasources/name/' + str(datasource_name)
    headers = {"Content-Type": 'application/json'}
    response = requests.delete(url, headers=headers)
    print(response.text)


def add_persmission_datasource(data_source_id, user_id):
    url = host + '/api/datasources/' + str(data_source_id) + '/permissions'
    data = {
        "userId": user_id,
        "permission": 1
    }
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    print(response.text)


def _get_all_datasource():
    url = host + '/api/datasources'
    headers = {"Content-Type": 'application/json'}
    response = requests.get(url, headers=headers)
    print(response.text)


# DASHBOARDS
def _create_dashboard(dash_json):
    url = host + '/api/dashboards/db'
    headers = {"Content-Type": 'application/json'}
    data = {}
    data["dashboard"] = dash_json
    data["folderId"] = 0
    data["overwrite"] = True
    response = requests.post(url, json=data, headers=headers)
    print(response.text)
    return response.json()["id"]

def _update_existing_dashboard(dash_json):
    url = host + '/api/dashboards/db'
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=dash_json, headers=headers)
    print(response.text)
    return response.json()['status'], response.json()["uid"]

def _create_dashboard_old(name):
    url = host + '/api/dashboards/db'
    headers = {"Content-Type": 'application/json'}
    data = {
        "dashboard": {
            "id": None,  # for new dashboard
            "uid": None,
            "title": name,
            "tags": ["templated"],
            "timezone": "browser",
            "schemaVersion": 16,
            "version": 0,
        },
        "folderId": 0,
        "overwrite": False  # new dashboard
    }
    response = requests.post(url, json=data, headers=headers)
    print(response.text)


def _update_dashboard(dash_json, name, uid):
    # future versions: add time intervals too
    url = host + '/api/dashboards/db'
    headers = {"Content-Type": 'application/json'}

    dash_json['title'] = name
    dash_json['uid'] = uid
    dash_json["refresh"] = "5s"  # default refresh rate
    data = {}
    data["dashboard"] = dash_json
    data["folderId"] = 0
    data["overwrite"] = True

    response = requests.post(url, json=data, headers=headers)
    print(response.text)


def _get_dashboard_uid(dash_title):
    url = host + '/api/search?folderIds=0&query=&starred=false'
    headers = {"Content-Type": 'application/json'}
    response = requests.get(url, headers=headers)
    # print (response.text)
    dash_list = response.json()
    for i in range(len(dash_list)):
        if dash_list[i]['title'] == dash_title:
            return dash_list[i]['uid']
    return 0  # user not found


def _get_dashboard_json(dash_title, org):
    _change_current_organization_to(org)
    dash_uid = _get_dashboard_uid(dash_title)
    if dash_uid != 0:
        url = host + '/api/dashboards/uid/' + str(dash_uid)
        headers = {"Content-Type": 'application/json'}
        response = requests.get(url, headers=headers)
        data = response.json()
        #print("************************************")
        #print(data['dashboard']['panels'])
        print('OK')
        return data
    else:
        print("get dash json not working")
        return None


def _delete_dashboard(dash_title):
    dash_uid = _get_dashboard_uid(dash_title)
    if dash_uid != 0:
        print("deleting dashboard ...", dash_title)
        url = host + '/api/dashboards/uid/' + str(dash_uid)
        headers = {"Content-Type": 'application/json'}
        response = requests.delete(url, headers=headers)
        print(response.text)
    else:
        print("dashboard does not exist")


# NOTIFICATIONS
def _get_notification_channels():
    """GET /api/alert-notifications
    HTTP / 1.1
    Accept: application / json
    Content - Type: application / json
    Authorization: Bearer eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk
    """
    url = host + '/api/alert-notifications'
    headers = {"Content-Type": 'application/json'}
    response = requests.get(url, headers=headers)
    print(response.text)


def _create_notification_channels(data):
    """GET /api/alert-notifications
    HTTP / 1.1
    Accept: application / json
    Content - Type: application / json
    Authorization: Bearer eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk
    """
    url = host + '/api/alert-notifications'
    headers = {"Content-Type": 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    print(response.text)
