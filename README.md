Grafana Provisioning
====================

This project was made to help provision Grafana server organizations, user accounts, folders, dashboards and datasources. You can store different organization's datasources and accounts in yaml files and export their Grafana dashboards, place them inside the inputs folder to have them automatically loaded into Grafana. Running the scripts more than once should overwrite dashboards and datasources, but not existing accounts or organizations (if they are not found, they will be created).

The provisioning script was designed to be compatible with Puppet and to be ran once every hour.

Documentation includes [setup and server configuration](Documentation/readme.rst) and also [instructions and sample files](Documentation/inputStructure.rst). The Documentation directory includes the files to generate the docs again using Sphinx, you can find an html version and an unpolished latex/pdf version inside the [build folder](Documentation/_build).

The source code and configuration files are found in the [GrafanaProvisioning](GrafanaProvisioning/) directory.

Requirements
============
To be used on CentOS 7 with Grafana 5.4.2 or greater. Grafana is expected to be installed on ``/etc/grafana``.

The scripts are written for Python3.6 and require the PyYAML and Requests libraries. Instructions on how to obtain them can be found in the Server Configuration docs.

About
=====
This project was developed for the IT Department of the LSST Project and AURA by the intern José Moreno Hanshing under the supervision of Andrés Villalobos Rivera, during Jan-Feb 2019 in the city of La Serena.
You can use install, use and build upon this project for your own personal projects or your organization's purposes free of charge, but you may not profit from distributing this software.
Contact me at jmoreno.hanshing@gmail.com
