# crits_ldap
A quick tool to add LDAP data as CRITS Target data. Includes two scripts:
* crits_ldap.py - Gathers data from LDAP and enters it into CRITS as target information
* ldap_query.py - A quick utility to run an arbitrary ldap query and output the results in JSON. I included this because it was easy to create along with the main project goal of getting LDAP data into CRITS.

This script will do the following:

1. Query LDAP for all users.
2. For each user, search the CRITS target for the email address of that user.
  1. If the user exists, update the existing information if necessary.
3. If the user is not found, add the LDAP information for the user as a Target in CRITS.

## Installation
1. Copy etc/logging.ini.example to etc/logging.ini
  1. Edit etc/logging.ini to include a logging path if you wish. By default it logs to ../log/ldap.log.
2. Copy etc/ldap.ini.example to etc/ldap.ini
  1. Edit ldap.ini and fill out all the fields with your LDAP information and CRITS mongo information
3. Install dependencies

### Dependencies
See requirements.txt for dependencies. Optionally, set up a python3 virtual environment for this tool. On Ubuntu 14.04, do the following to set up your venv:

```shell
pyvenv-3.4 --without-pip venv
source ./venv/bin/activate
wget https://pypi.python.org/packages/source/s/setuptools/setuptools-3.4.4.tar.gz
tar -zxvf setuptools-3.4.4.tar.gz
cd setuptools-3.4.4/
python setup.py install
cd ..
wget https://pypi.python.org/packages/source/p/pip/pip-1.5.6.tar.gz
tar -zxvf pip-1.5.6.tar.gz
cd pip-1.5.6/
python setup.py install
cd ../
rm -rf setuptools-3.4.4*
rm -rf pip-1.5.6*
```

Then install the dependencies with pip:
```shell
pip install -r requirements.txt
```

## Usage
It is recommended you test this script on a development instance of CRITS so you don't break anything accidentally. Usage is simple:
```shell
python crits_ldap.py
```

Optionally, you can set up a cron job to run it regularly.

## ldap_query Usage
ldap_query is a simple command on the analysis server to run a given LDAP query.

```shell
$ ldap_query -h
usage: ldap_query.py [-h] QUERY

positional arguments:
  QUERY       The LDAP query to run. Ex: cn=lolnate, mail=*

optional arguments:
  -h, --help  show this help message and exit
```

For example, find the user lolnate:
```shell
ldap_query "cn=lolnate"
```
It also accepts wildcards:

```shell
ldap_query "mail=*"
ldap_query "cn=a*"
```

The result is printed to the screen, so if it is a large result, you may want to write it to a file:
```shell
ldap_query "mail=*" > ldap.out
```

You can also pipe the result to jq for fancy formatting:
```shell
ldap_query "cn=lolnate" | jq '.'
```

## TODO
* Ensure this works on any LDAP server or ensure it is configurable.
* Add email distribution groups as target information
* Add additional LDAP information in the "notes" section of the Target in CRITS

