"""Script used to import not monitored servers from GCE into Cyberwatch and delete terminated GCE servers"""

# Based on the Apache Libcloud API https://libcloud.apache.org/index.html

# Prerequisites :
# - install libcloud with command "pip3 install apache-libcloud"
# - setup GCE to get an API key with https://libcloud.readthedocs.io/en/stable/compute/drivers/gce.html#connecting-to-google-compute-engine
# - SSH key file of servers to import named "id_rsa" 
# - Set WINRM password in script if it's not set in Cyberwatch

import argparse
import os
import sys
import socket

from configparser import ConfigParser
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from cbw_api_toolbox.cbw_api import CBWApi

SSH_KEY_SERVERS = open(os.path.expanduser('id_rsa')).read()
# If WINRM password is set in Cyberwatch comment the next line and line 82
WINRM_PASSWORD_SERVERS = "password"

def connect_api():
    '''Connect to the API and test connection'''
    conf = ConfigParser()
    conf.read(os.path.join(os.path.abspath(
        os.path.dirname(__file__)), '..', 'api.conf'))
    global API  # pylint: disable=global-variable-undefined
    API = CBWApi(conf.get('cyberwatch', 'url'), conf.get(
        'cyberwatch', 'api_key'), conf.get('cyberwatch', 'secret_key'))

    API.ping()


def retrieve_gce_servers():
    '''Retrieve GCE servers with apache-libcloud'''
    compute_engine = get_driver(Provider.GCE)
    # driver = compute_engine('your_service_account_email', 'path_to_gce_key_file', project='your_project_id')
    driver = compute_engine('', '', project='')
    return driver.list_nodes()


def port_checker(ip, port):
    '''Check if a specific port is open on an ip address'''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except:
        return False


def check_add_server(servers, gce_servers):
    '''Find GCE servers not monitored in Cyberwatch to import'''
    to_add = []
    for gce_server in gce_servers:
        gce_server_ip = gce_server.public_ips[0]
        if gce_server.state == 'running':
            if not any(server.address == gce_server_ip for server in servers):
                info = {}
                # Check for server groups
                groups = "GCE_crawling, " + gce_server.extra['zone'].name
                if gce_server.extra['labels'] is not None:
                    if "group" in gce_server.extra['labels']:
                        groups += ", " + gce_server.extra['labels']["group"]
                # Add server information
                info.update({"login": "maxime", "address": gce_server_ip,
                             "node_id": "2", "server_groups": groups})
                # Check port and add connection type
                if port_checker(gce_server_ip, 22):
                    info.update({"type": "CbwRam::RemoteAccess::Ssh::WithKey", "port": 22,
                                 "key": SSH_KEY_SERVERS})
                    to_add.append(info)
                elif port_checker(gce_server_ip, 5985):
                    info.update({"type": "CbwRam::RemoteAccess::WinRm::WithNegotiate",
                                 "port": 5985})
                    # Comment next line if WINRM password is set in Cyberwatch
                    info.update({"password": WINRM_PASSWORD_SERVERS})
                    to_add.append(info)
                else:
                    print('No port to connect for ' + gce_server_ip)
    return to_add


def check_delete_server(gce_servers):
    '''Find not imported GCE servers to delete'''
    to_delete = []
    servers = API.servers()
    for server in servers:
        if not any(gce_server.public_ips[0] == server.remote_ip for gce_server in gce_servers):
            for group in server.groups:
                if group.name == "GCE_crawling":
                    to_delete.append(server)

    return to_delete


def display_and_import(to_import_list, importing=False):
    '''Display to_import servers then import them'''

    print('\n\n================= Total of {} GCE servers to import (import={}) ================='.format(len(to_import_list),
                                                                                                         importing))
    for to_add_server in to_import_list:
        print('{} --- {} --- {}'.format(to_add_server["address"],
                                        to_add_server["server_groups"], to_add_server["type"]))
        if importing is True:
            API.create_remote_access(to_add_server)


def display_and_delete(to_delete_list, delete=False):
    '''Display to_delete servers then delete them'''
    print('\n\n================= Total of {} servers on Cyberwatch to delete (delete={}) ================='.format(len(to_delete_list),
                                                                                                                   delete))
    for server in to_delete_list:
        print('{} --- {} --- {}'.format(server.remote_ip, server.hostname, server.id))
        if delete is True:
            API.delete_remote_access(server.id)


def launch_script(parsed_args):
    '''Launch script'''
    connect_api()
    servers = API.remote_accesses()
    gce_servers = retrieve_gce_servers()

    if parsed_args.import_only:
        to_add = check_add_server(servers, gce_servers)
        display_and_import(to_add, True)
    elif parsed_args.delete_only:
        to_delete = check_delete_server(gce_servers)
        display_and_delete(to_delete, True)
    elif parsed_args.all:
        to_add = check_add_server(servers, gce_servers)
        to_delete = check_delete_server(gce_servers)
        display_and_import(to_add, True)
        display_and_delete(to_delete, True)
    else:
        print("Read-only")
        to_add = check_add_server(servers, gce_servers)
        to_delete = check_delete_server(gce_servers)
        display_and_import(to_add, False)
        display_and_delete(to_delete, False)

def main(args=None):
    '''Main function'''
    if not args:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description='Script using Cyberwatch API to import not monitored GCE servers and delete terminated GCE servers in Cyberwatch.\nBy default this script is run in read-only mode.')

    parser.add_argument(
        '-io', '--import_only',
        help='Only import not monitored GCE servers into Cyberwatch',
        action='store_true')

    parser.add_argument(
        '-do', '--delete_only',
        help='Only delete terminated GCE servers from Cyberwatch.',
        action='store_true')

    parser.add_argument(
        '-a', '--all',
        help='Import GCE servers into Cyberwatch and delete terminated GCE servers from Cyberwatch.',
        action='store_true')

    args = parser.parse_args(args)
    launch_script(args)


if __name__ == '__main__':
    main()
