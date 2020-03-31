from pprint import pprint
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import socket

# check if port open
def port_checker(ip, port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.settimeout(5)
   try:
      s.connect((ip, int(port)))
      s.shutdown(2)
      return True
   except:
      return False

# Based on the Apache Libcloud API https://libcloud.apache.org/index.html

# Prerequisites :
# - install libcloud with command "pip3 install apache-libcloud"
# - setup GCE to get an API key with https://libcloud.readthedocs.io/en/stable/compute/drivers/gce.html#connecting-to-google-compute-engine

ComputeEngine = get_driver(Provider.GCE)
# driver = ComputeEngine('your_service_account_email', 'path_to_key_file', project='your_project_id')
driver = ComputeEngine('test-integration-api-cyberwatc@quickstart-1579112015773.iam.gserviceaccount.com', 'quickstart-1579112015773-a50695cb060a.json', project='quickstart-1579112015773')
nodes = driver.list_nodes()

for node in nodes:
#    if node.state == 'running':
    if node.state != 'terminated':
        print(node.name)
        print(node.public_ips)
        print(node.image)
        # Infos for groups
        # Region / Zone
        print(node.extra['zone'].name)
        # Custom labels defined on the node
        print(node.extra['labels'])
        
        # If instance is running, try to connect
        if node.state == 'running':
            node_ip = node.public_ips[0]
            if port_checker(node_ip, 22):
                print('SSH')
            elif port_checker(node_ip, 5985):
                print('WinRM')
            else:
                print('No port to connect')
