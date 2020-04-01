"""Script used to delete duplicates and computers in initialization
To use the script, please install"""
# faire dexcription

# Based on the Apache Libcloud API https://libcloud.apache.org/index.html

# Prerequisites :
# - install libcloud with command "pip3 install apache-libcloud"
# - setup GCE to get an API key with https://libcloud.readthedocs.io/en/stable/compute/drivers/gce.html#connecting-to-google-compute-engine


import argparse
import os
import sys
import socket

from pprint import pprint
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from configparser import ConfigParser
from cbw_api_toolbox.cbw_api import CBWApi


def connect_api():
    '''Connect ot the API'''
    conf = ConfigParser()
    conf.read(os.path.join(os.path.abspath(
        os.path.dirname(__file__)), '.', 'api.conf'))
    global API  # pylint: disable=global-variable-undefined
    API = CBWApi(conf.get('cyberwatch', 'url'), conf.get(
        'cyberwatch', 'api_key'), conf.get('cyberwatch', 'secret_key'))

    API.ping()


key = open(os.path.expanduser('id_rsa_demo')).read()
winrm_password = "password"


def port_checker(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except:
        return False


def check_add_server(servers, GCE_servers):
    '''Find GCE servers not imported in Cyberwatch'''
    to_add = []

    for GCE_server in GCE_servers:
        GCE_server_ip = GCE_server.public_ips[0]
        if GCE_server.state == 'running':
            if not any(server.address == GCE_server_ip for server in servers):
                INFO = {}
                # Check for groups
                groups = "GCE_crawling, " + GCE_server.extra['zone'].name
                if GCE_server.extra['labels'] != None:
                    if "group" in GCE_server.extra['labels']:
                        groups += ", " + GCE_server.extra['labels']["group"]
                # Add server information
                INFO.update({"login": "maxime", "address": GCE_server_ip,
                             "node_id": "2", "server_groups": groups})
                # Check and add connection type
                if port_checker(GCE_server_ip, 22):
                    INFO.update(
                        {"type": "CbwRam::RemoteAccess::Ssh::WithKey", "port": 22, "key": key})
                    to_add.append(INFO)
                elif port_checker(GCE_server_ip, 5985):
                    INFO.update({"type": "CbwRam::RemoteAccess::WinRm::WithNegotiate",
                                 "password": winrm_password, "port": 5985})
                    to_add.append(INFO)
                else:
                    print('No port to connect for ' + GCE_server_ip)
    return to_add


def check_delete_server(GCE_servers):
    '''Find not imported GCE servers'''
    to_delete = []
    servers = API.servers()
    for server in servers:
        if not any(GCE_server.public_ips[0] == server.remote_ip for GCE_server in GCE_servers):
            for group in server.groups:
                if group.name == "GCE_crawling":
                    to_delete.append(server)

    return to_delete



def display_and_import(to_add_list, importing=False):
    '''Display to_import servers then import them'''

    print('\n\n================= Total of {} GCE servers to import (import={}) ================='.format(len(to_add_list),
                                                                                                importing))
    for to_add_server in to_add_list:
        print('{} --- {} --- {}'.format(to_add_server["address"],
                                        to_add_server["server_groups"], to_add_server["type"]))
        if importing is True:
            API.create_remote_access(to_add_server)


def display_and_delete(to_delete_list, delete=False):
    '''Display to_delete servers then delete them'''
    print('\n\n================= Total of {} servers on Cyberwatch to delete (delete={}) ================='.format(len(to_delete_list),
                                                                                                delete))
    for server in to_delete_list:
        print('{} --- {} --- {}'.format(server.hostname, server.remote_ip, server.id))
        if delete is True:
            API.delete_remote_access(server.id)


def launch_script(parsed_args):
    '''Launch script'''
    connect_api()
    servers = API.remote_accesses()

    ComputeEngine = get_driver(Provider.GCE)
    # driver = ComputeEngine('your_service_account_email', 'path_to_key_file', project='your_project_id')
    driver = ComputeEngine('******',
                           'quickstart-1579112015773-a50695cb060a.json', project='quickstart-1579112015773')
    GCE_servers = driver.list_nodes()

    if parsed_args.import_only:
        to_add = check_add_server(servers, GCE_servers)
        display_and_import(to_add, True)
    elif parsed_args.delete_only:
        to_delete = check_delete_server(GCE_servers)
        display_and_delete(to_delete, True)
    elif parsed_args.all:
        to_add = check_add_server(servers, GCE_servers)
        to_delete = check_delete_server(GCE_servers)
        display_and_import(to_add, True)
        display_and_delete(to_delete, True)
    else:
        print("Read-only")
        to_add = check_add_server(servers, GCE_servers)
        to_delete = check_delete_server(GCE_servers)
        display_and_import(to_add, False)
        display_and_delete(to_delete, False)


def main(args=None):
    '''Main function'''
    if not args:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description='Script using Cyberwatch API to import not monitored GCE servers and delete terminated GCE servers.\nBy default this script is run in read-only mode.')
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
