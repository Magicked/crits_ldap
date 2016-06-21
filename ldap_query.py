#!/usr/bin/env python3
# ldap_query.py
# This is a quick utility to run an arbitrary query on an LDAP server and
# output the results in JSON

import json
import argparse

from configparser import ConfigParser
from ldap3 import Server, Connection, SIMPLE, SYNC, ASYNC, SUBTREE, ALL, ALL_ATTRIBUTES

try:
    config = ConfigParser()
    config.read('etc/ldap.ini')
except ImportError:
    raise SystemExit('ldap.ini was not found or was not accessible.')

# load ldap settings from configuration file
ldap_server = config.get('ldap', 'ldap_server')
ldap_bind_user = config.get('ldap', 'ldap_bind_user')
ldap_bind_password = config.get('ldap', 'ldap_bind_password')
ldap_base_dn = config.get('ldap', 'ldap_base_dn')

def ldap_paged_query(query):
    response_entries = []

    try:
        server = Server(ldap_server, port = 389, get_info = ALL)
        with Connection(
            server,
            client_strategy = SYNC,
            user=ldap_bind_user,
            password=ldap_bind_password,
            authentication=SIMPLE,
            check_names=True) as c:

            c.search(ldap_base_dn, '({0})'.format(query), SUBTREE, attributes =
                    ALL_ATTRIBUTES, paged_criticality=True, paged_size=100)

            cookie = c.result['controls']['1.2.840.113556.1.4.319']\
                    ['value']['cookie']
            # a little hack to move the result into json
            response = json.loads(c.response_to_json())

            if len(response['entries']) < 1:
                return None

            for entry in response['entries']:
                response_entries.append(entry)

            while cookie:
                c.search(ldap_base_dn, '({0})'.format(query), SUBTREE,
                         attributes = ALL_ATTRIBUTES, paged_criticality=True,
                         paged_size=100, paged_cookie=cookie)
                # a little hack to move the result into json
                cookie = c.result['controls']['1.2.840.113556.1.4.319']\
                        ['value']['cookie']

                response = json.loads(c.response_to_json())
                if len(response['entries']) < 1:
                    return None

                for entry in response['entries']:
                    response_entries.append(entry)

            return response_entries

    except Exception as e:
        print("unable to perform ldap query: {0}".format(str(e)))
        return response_entries

argparser = argparse.ArgumentParser()
argparser.add_argument('QUERY', action='store', help='The LDAP query to run.'
                       ' Ex: cn=userid, mail=*')
args = argparser.parse_args()

results = ldap_paged_query(args.QUERY)
if results is not None:
    print( json.dumps(results) )
else:
    print("No results returned from LDAP")
