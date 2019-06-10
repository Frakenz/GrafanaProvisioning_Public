#! /bin/bash

sudo mv GrafanaProvisioning/ /etc/grafana/lsst

sudo python36 /etc/grafana/lsst/gpSetup.py
sudo python36 /etc/grafana/lsst/gpInputs.py
sudo python36 /etc/grafana/lsst/gpAccounts.py

sudo chown -hHR grafana:grafana /etc/grafana/
sudo chown -hHR grafana:grafana /var/lib/grafana/

sudo service grafana-server restart

