import os, logging, logging.handlers, requests
from flask import Flask, render_template, request
from ncclient import manager
from ncclient.xml_ import *
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from collections import namedtuple
from bs4 import BeautifulSoup

# Flask app settings
app = Flask(__name__)
app.secret_key = 'super secret key'

# Credentials of device
user = 'root'
password = 'Password'

# Creates a list of all devices in the host file
inventory_file_name = 'hosts'
data_loader = DataLoader()
inventory = InventoryManager(loader = data_loader,
                             sources=[inventory_file_name])
deviceList=inventory.get_groups_dict()['all']

# Example logfile list
logList=[["This is a test log","16/03/2018"], ["This is the second test log", "16/03/2018"]]


### Web API ###
# 127.0.0.1:5000/
@app.route('/')
def index():
    # Returns a template where the user inputs MAC, SN and chooses a config
    return render_template('index.html', deviceList=deviceList, logList=logList)

@app.route('/addLog', methods=['POST'])
def addLog():
    pass

# 127.0.0.1:5000/deploy
@app.route('/deploy', methods=['POST', 'GET'])
def deploy():
    if request.method == 'POST':
        # Gets the inputs from the forms of '/'
        deploy = request.form.to_dict()
        deviceIP = deploy['Device']
        deviceHostname = deploy['Hostname']

        if deploy['Method'] == 'ansi':
            ansibleRun(deviceHostname, user, password, deviceIP)
        elif deploy['Method'] == 'api':
            apiRun(deviceHostname, user, password, deviceIP)

        return render_template('index.html', deviceList=deviceList, logList=logList)
        # return send_from_directory(directory=uploads, filename=filename)

# 127.0.0.1:5000/execute
@app.route('/execute', methods=['POST', 'GET'])
def execute():
    if request.method == 'POST':
        # Gets the inputs from the forms of '/'
        execute = request.form.to_dict()
        deviceIP = execute['Device']

        # SRX REST API connection information
        headers = {'content-type': 'application/xml'}
        # authuser = srxuser
        # authpwd = srxpass
        # Create the Junos RPC string to add the source IP to the configuration

        # Assemble the REST call for the SRX
        # srxaddr = srxmgtip
        url = "http://" + deviceIP + ":" + "3000" + "/rpc/get-software-information"
        try:
            q = requests.get(url,
                              headers=headers,
                              auth=(user, password))
            soup = BeautifulSoup(q.text, "lxml")
            hostName = soup.find('host-name').string
            model = soup.find('product-model').string
            version = soup.find('junos-version').string


        except Exception as e:
            print ("Error: ", e)
            # Create the logger object
            jsa_logger = logging.getLogger('jsaLogger')
            # Send the message as log level WARNING
            jsa_logger.setLevel(logging.WARNING)
            # Define the SyslogHandler and assign - log to localhost
            handler = logging.handlers.SysLogHandler(address=('127.0.0.1', 514))
            jsa_logger.addHandler(handler)
            # Write the error message to JSA - will show as a local system message
            # with a low level category of Stored however event name will be
            # different depending on the error message
            jsa_logger.warning("CUSTOM_ACTION_SCRIPT {0}".format(e))


        return render_template('index.html', deviceList=deviceList, logList=logList, hostName=hostName, model=model, version=version)
        # return send_from_directory(directory=uploads, filename=filename)

def ansibleRun(deviceHostname, user, password, deviceIP):
    try:
        loader = DataLoader()

        # Path to playbook
        playbook_path = 'all.yaml'
        # Pathe to inventory
        inventory = InventoryManager(loader=loader, sources='hosts')
        passwords = {}
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        # Dict of extra vars used
        variable_manager.extra_vars = {'device':deviceIP, 'device_hostname':deviceHostname, 'user':user, 'pass':password}
        # Ansible options
        Options = namedtuple('Options', ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection','module_path', 'forks', 'remote_user', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user', 'verbosity', 'check','diff'])
        options = Options(listtags=False, listtasks=False, listhosts=False, syntax=False, connection='ssh', module_path=None, forks=100, remote_user=None, private_key_file=None, ssh_common_args=None, ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=False, become_method=None, become_user=None, verbosity=None, check=False, diff=False)

        # Creates the playbook object
        pbex = PlaybookExecutor(playbooks=[playbook_path], inventory=inventory, variable_manager=variable_manager, loader=loader, options=options, passwords=passwords)

        # Runs the playbook
        results = pbex.run()
    except Exception as e:
        print(e)


def apiRun(deviceHostname, user, password, deviceIP):
    # SRX REST API connection information
    headers = {'content-type': 'application/xml'}
    # authuser = srxuser
    # authpwd = srxpass
    # Create the Junos RPC string to add the source IP to the configuration
    payload = ("<lock-configuration/><load-configuration><configuration>"
               "<system>"
               "<host-name>"+deviceHostname+"</host-name>"
               "</system>"
               "</configuration></load-configuration><commit/>"
               "<unlock-configuration/>")

    # Assemble the REST call for the SRX
    # srxaddr = srxmgtip
    url = "http://" + deviceIP + ":" + "3000" + "/rpc"

    # Connect to SRX and update the configuration with the source IP
    try:
        requests.post(url,
                      headers=headers,
                      auth=(user, password),
                      data=payload)

    except Exception as e:
        print ("Error: ", e)
        # Create the logger object
        jsa_logger = logging.getLogger('jsaLogger')
        # Send the message as log level WARNING
        jsa_logger.setLevel(logging.WARNING)
        # Define the SyslogHandler and assign - log to localhost
        handler = logging.handlers.SysLogHandler(address=('127.0.0.1', 514))
        jsa_logger.addHandler(handler)
        # Write the error message to JSA - will show as a local system message
        # with a low level category of Stored however event name will be
        # different depending on the error message
        jsa_logger.warning("CUSTOM_ACTION_SCRIPT {0}".format(e))


if __name__ == '__main__':
    app.run(debug=True)
