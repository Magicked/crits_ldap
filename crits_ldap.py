#!/usr/bin/env python3
# crits_ldap.py
# This connects to an LDAP server and pulls data about all users.
# Then, it either updates existing targets in CRITS or creates a new entry.

import json
import sys
import datetime
import logging
import logging.config

from configparser import ConfigParser
from ldap3 import Server, Connection, SIMPLE, SYNC, ASYNC, SUBTREE, ALL,
    ALL_ATTRIBUTES
from pymongo import MongoClient

try:
    config = ConfigParser()
    config.read('etc/ldap.ini')
except ImportError:
    raise SystemExit('ldap.ini was not found or was not accessible.')

try:
    logging.config.fileConfig('etc/logging.ini')
    log = logging.getLogger("ldap")
except Exception as e:
    raise SystemExit("unable to load logging configuration file {0}: {1}"
        .format('logging.ini', str(e)))

# load ldap settings from configuration file
ldap_server = config.get('ldap', 'ldap_server')
ldap_bind_user = config.get('ldap', 'ldap_bind_user')
ldap_bind_password = config.get('ldap', 'ldap_bind_password')
ldap_base_dn = config.get('ldap', 'ldap_base_dn')
crits_user = config.get('crits', 'user')
crits_server = config.get('crits', 'server')
TARGET_SCHEMA_VERSION = 3

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

            log.debug("running ldap query for ({0})".format(query))
            c.search(ldap_base_dn, '({0})'.format(query), SUBTREE, attributes =
                ALL_ATTRIBUTES, paged_criticality=True, paged_size=100)

            cookie = c.result['controls']['1.2.840.113556.1.4.319']['value']
                ['cookie']
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
                cookie = c.result['controls']['1.2.840.113556.1.4.319']
                    ['value']['cookie']

                response = json.loads(c.response_to_json())
                if len(response['entries']) < 1:
                    return None

                for entry in response['entries']:
                    response_entries.append(entry)

            return response_entries

    except Exception as e:
        log.warning("unable to perform ldap query: {0}".format(str(e)))
        return response_entries


def add_results_to_crits(entries):
    """Adds LDAP data to CRITS targets.

    Args:
        entries: dict with all the entry data from LDAP
    """
    client = MongoClient(crits_server, 27017)
    db = client.crits
    targets = db.targets
    for result in entries:
        firstname = ''
        lastname = ''
        if 'givenName' in result['attributes']:
            firstname = result['attributes']['givenName']
        if 'sn' in result['attributes']:
            lastname = result['attributes']['sn']
        department = ''
        if 'department' in result['attributes']:
            department = result['attributes']['department']
        orgid = ''
        if 'cn' in result['attributes']:
            orgid = result['attributes']['cn']
        company = ''
        if 'company' in result['attributes']:
            company = result['attributes']['company']
        title = ''
        if 'title' in result['attributes']:
            title = result['attributes']['title']
        mail = ''
        if 'mail' in result['attributes']:
            mail = result['attributes']['mail']
        tmpmail = str.strip(mail)
        if tmpmail == '':
            continue
        mongo_result = targets.find_one( { 'email_address' : mail.lower() } )
        if mongo_result:
            log.debug('Found id of {} for the target {}'.format(
                mongo_result['_id'], mail))
            modified = datetime.datetime.now()
            data = {
                'firstname' : firstname,
                'lastname' : lastname,
                'division' : company,
                'department' : department,
                'organization_id' : orgid,
                'title' : title,
                'modified' : modified
            }
            # The user is already in crits, do we need to
            # update any information?
            update_information = False
            for key in data.keys():
                if key == 'modified':
                    continue
                if key in mongo_result:
                    if mongo_result[key] != data[key]:
                        update_information = True
                else:
                    update_information = True

            if update_information:
                update_result = targets.update_one( { 'email_address' :
                    mail.lower() }, { '$set' : data } )
                log.info("Records matched: {}, modified: {}, email_address: {}"
                    .format(update_result.matched_count,
                    update_result.modified_count, mail.lower()))
        else:
            # The user is not in CRITS, let's add the information
            created = datetime.datetime.now()
            data = {
                "status" : "New",
                "created" : created,
                "modified" : created,
                "schema_version" : TARGET_SCHEMA_VERSION,
                "actions" : [ ],
                "tickets" : [ ],
                "bucket_list" : [ ],
                "campaign" : [ ],
                "locations" : [ ],
                "objects" : [ ],
                "relationships" : [ ],
                "releasability" : [ ],
                "screenshots" : [ ],
                "sectors" : [ ],
                "email_address" : mail.lower(),
                "email_count" : 0,
                'firstname' : firstname,
                'lastname' : lastname,
                'division' : company,
                'department' : department,
                'organization_id' : orgid,
                'title' : title,
                'note' : ''
                }
            insert_result = targets.insert_one( data )
            if insert_result:
                log.info("Record inserted: {}".format(
                    insert_result.inserted_id ))
            else:
                log.error("Insert failed for {}".format(mail.lower()))

log.info('Beginning LDAP update.')
# Before we do anything, we need to connect to the crits server and make sure
# the schema version is the same for our target collection
client = MongoClient(crits_server, 27017)
db = client.crits
targets = db.targets

tmp_target = targets.find_one()
if 'schema_version' not in tmp_target:
    log.error("schema_version not found in target result.")
    sys.exit(1)
if tmp_target['schema_version'] != TARGET_SCHEMA_VERSION:
    log.error("schema_version has changed (found {}, expected {}). Check "
        "CRITS target table.".format(tmp_target['schema_version'],
        TARGET_SCHEMA_VERSION))
    sys.exit(1)

log.info('Running LDAP query.')
results = ldap_paged_query("mail=*")
if results is not None:
    add_results_to_crits(results)
else:
    log.info("No results returned from LDAP")

log.info('LDAP update complete.')
