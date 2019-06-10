#!/bin/bash

sudo grafana-cli plugins install yesoreyeram-boomtable-panel
sudo grafana-cli plugins install grafana-clock-panel
sudo service grafana-server restart

# Install python and requests library
sudo yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm -y
sudo yum install python36 python36-requests.noarch -y

# Install pyyaml
sudo python36 -m ensurepip
# Using "python36 -m pip" as an alternative to using pip3.6 since the latter wasn't working with sudo
sudo python36 -m pip install --upgrade pip
sudo python36 -m pip install pyyaml

# git clone https://github.com/Frakenz/GrafanaProvisioning.git
