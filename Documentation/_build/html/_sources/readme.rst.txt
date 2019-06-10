####################
Server Configuration
####################
To be used on CentOS 7 with Grafana 5.4.2 or greater. Grafana is expected to be
installed on ``/etc/grafana``.

.. _configuration:

Configuration
=============
The project will be stored and ran in a directory in the server. This is called
the ``main directory`` and will be set on :ref:`installation <r4>`. All
relative paths in this document are relative to the ``main directory``.

General Configuration
---------------------
The `config.yaml` file contains the following settings, which are all required:

- `dashboardsDir`:
   Base directory where Grafana provisioned dashboards will be
   stored. The provisioning project will create subfolders and symlinks inside
   to organize Grafana organizations and their provisioned folders.
- `provisioningDir`:
   `*` ``main directory``, where the project's files reside.
- `timeout`:
   Maximum time in seconds to wait for API requests when not receiving
   a reply. Will end the program execution if reached.
- `updateIntervalSeconds`:
   How often Grafana will scan for changed dashboards.
   Once a folder is provisioned, if the need arises to change this it must be
   done so manually in a YAML file inside Grafana's installation directory.

`*` This functionality has been made optional because now the program detects
its directory automatically. Since there was not enough time to test this
thoroughly, the option to set it manually is still available. Only set this if
you are seeing file not found errors pointing to the wrong directory.

Grafana Admin Accounts
----------------------
This project provisions two Grafana Admin accounts. To set their account
details like login name and password, you need to configure them in
``admins/_superAdmins.yaml``.

``grafanaAdmin`` refers to the configuration of Grafana's Main admin account,
which is the default account that is created when you install Grafana (id=1).

``api`` refers to the account that will be used by this script to make API
calls to the Grafana server and provision organizations, accounts, datasources,
folders and dashboards.

Default Organization
--------------------
The project treats the first organization (id=1) as a special case. You can
configure its name as well as the default accounts that will be part of it in
``admins/_kiosk.yaml``.

To add dashboards to this organization, you will need to add an input directory
in ``inputs/`` :ref:`just like with any other organization <input_structure>`,
the `org.yaml` file must contain a hash with a key as the name of the org, but
the list of other accounts that can be in it *can* be blank.

In the same way, the accounts that this organization provisions are set in
``admins/_kioskAccounts.yaml``. If you create input for this organization, you
still need have 

Installation
============
Note: *Some steps require previous steps to have been completed before being
executed. The syntax* ``rn`` *on one step means that this step requires step*
``n`` *to have been completed,* ``r1`` *on step 2 means that step 2 requires
step 1 to complete. Similarly,* ``r6, r8`` *on step 9 means that step 9
requires both step 6* **and** *step 8 to complete.*

For the following examples, the ``main directory`` will be `/etc/grafana/lsst`.

Dependencies
------------
.. _r1:

1. Install EPEL repository::

    yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm -y

.. _r2:

2. :ref:`r1 <r1>` Install Python 3.6 with the requests and pyyaml libraries::

    yum install python36 python36-requests.noarch -y
    python36 -m ensurepip
    pip3.6 install --upgrade pip
    pip3.6 install pyyaml

.. _r3:

3. Install Grafana plugins, this requires Grafana v5.3.0 or newer. You need to
   restart Grafana for new plugins to be recognized::

    grafana-cli plugins install yesoreyeram-boomtable-panel

Provisioning Setup
------------------
.. _r4:

4. Place the project in a secure directory::

    mv GrafanaProvisioning /etc/grafana/lsst

.. _r5:

5. :ref:`r4 <r4>` Configure the directories the project will use. See
   :ref:`configuration` for more details::
   
    vim /etc/grafana/lsst/config.yaml
   
   5.1. Configure the directory where the project resides in as \
   `provisioningDir` inside `config.yaml` which is in the ``main directory``::
   
    provisioningDir: /etc/grafana/lsst
   
   5.2. Set `dashboardsDir` to another secure directory, where Grafana will \
   look for dashboards::
   
    dashboardsDir: /var/lib/grafana/dashboards

Provisioning
------------
If any of the scripts close because of an error, do not continue with the
following steps.

.. _r6:

6. :ref:`r2 <r2>`, :ref:`r5 <r5>` Run `gpSetup.py`::

    python36 /etc/grafana/lsst/gpSetup.py

.. _r7:

7. :ref:`r6 <r6>` Configure firewall rules to use Grafana (open port 3000).

.. _r8:

8. :ref:`r4 <r4>` For each organization/use case/department for which you wish
   to provision Grafana, add a directory with the correct
   :ref:`input_structure` inside the `inputs/` directory.

.. _r9:

9. :ref:`r6 <r6>`, :ref:`r8 <r8>` Run `gpInputs.py`::

    python36 /etc/grafana/lsst/gpInputs.py

.. _r10:

10. :ref:`r9 <r9>` Run `gpAccounts.py`::

     python36 /etc/grafana/lsst/gpAccounts.py

.. _r11:

11. :ref:`r3 <r3>`, :ref:`r9 <r9>` Restart ``grafana-server``. See
    :ref:`restart` to understand when Grafana should be restarted::
    
     systemctl restart grafana-server.service

.. _restart:

Criteria to Restart Grafana
===========================
Grafana does not need to be restarted on every Puppet execution. You only need
to restart grafana-server if any of the following cases has happened since the
last Puppet execution:

- If a Grafana plugin has been installed.
- If one of the ``datasources.yaml`` files inside any organization's input
  folder has changed.
- If the contents of the first level inside one of the ``dashboards/``
  directories in any organization's input has changed.

The last two are hard to track with Puppet, so instead a file called
``restart.txt`` is created, which contains the string "restart". If Puppet
finds this file it can schedule grafana-server for restarting and delete the
file.

FAQ
===
Can I make permanent links to my dashboards?
--------------------------------------------
While Grafana uses and allows a unique id (uid) for their dashboards making it
easy to link them over the web, we do not allow persistent UIDs on provisioned
dashboards. This is to avoid conflicting UIDs, since if two dashboards are
provisioned with the same uid, the second one will overwrite the first one and
remove the latter from the database. It is possible to write a script that
manages a local file with taken UIDs corresponding to specific files, but this
has not been implemented in this version of this project.

Grafana will generates random UIDs for dashboards which do not have them on
startup. Sometimes when Grafana is :ref:`restarted <restart>`, the uid of
provisioned dashboards will change. This means that you *can* have direct links
to your dashboards, but it is not guaranteed that they will work in the long
term.

As per Grafana's
`documentation: <http://docs.grafana.org/administration/provisioning/#reusable-dashboard-urls>`_

 "**Note.** Provisioning allows you to overwrite existing dashboards which
 leads to problems if you re-use settings that are supposed to be unique. Be
 careful not to re-use the same ``title`` multiple times within a folder or
 ``uid`` within the same installation as this will cause weird behaviors."

What software and versions does this project use?
-------------------------------------------------
- CentOS 7
- Grafana v5.4.2 (commit: d812109)
- Boom Table Plugin (Grafana) v0.4.6
- EPEL 7-11
- Python 3.6.6-1.el7
- python36-requests 2.12.5-2.el7
- pyyaml 3.13

Recommendations
===============
Grafana Settings
----------------
Grafana's default settings can be found on::

   /usr/share/grafana/conf/defaults.ini

They need to be changed directly through Puppet, as it is the one which manages
Grafana's deployment.

DNS
+++
Sometimes clicking a link in Grafana will redirect users to ``localhost``. This
likely due to the misconfigured DNS setting in Grafana. It is intended to be
set to what the address in the browser will use as a DNS.
`Reference <http://docs.grafana.org/installation/configuration/#domain>`__::

   [server]
      domain: 10.0.0.252:3000

Viewers Can Edit
++++++++++++++++
It is worth considering activating this option. When set to ``true``, viewers
are allowed to edit/inspect dashboard settings in the browser, but not to save
the dashboard. This would allow users to easily create and export new
dashboards.
`Reference <http://docs.grafana.org/installation/configuration/#viewers-can-edit>`__::

   [users]
      viewers_can_edit: true

Grafana Internal Database
-------------------------
Grafana uses an internal database to manage users, dashboards, organizations
and other data. By default this database is SQLite, which has limitations which
include concurrent queries. If the system ever grows to a scale where the
platform becomes unstable or unreliable, you may want to consider switching
this database to MySQL or PostgreSQL.

Time Related Issues
-------------------
There are a few settings that influence how you see data in Grafana depending
on the frequency that the data is collected, and how it is saved and queried.

Datasource Minimum Time Interval
++++++++++++++++++++++++++++++++
When configuring your datasources, you should set the minimum time interval to
the frequency that you are collecting data. If you set an smaller interval, you
will see empty graphs when you zoom in too much in Grafana and are using
dynamic time intervals.

When provisioning,
`Grafana accepts setting <http://docs.grafana.org/administration/provisioning/#json-data>`__
``timeInterval`` for Prometheus, Elasticsearch, InfluxDB, MySQL, PostgreSQL and
MSSQL datasources::

   jsonData:
      timeInterval: 1m

InfluxDB Row Limit
++++++++++++++++++
For this database, a setting can be configured to limit the size of a query's
response through HTTP. This can cause confusing behavior in Grafana when
zooming out too much. InfluxDB is set to respond with a maximum of 10,000 rows
to prevent server overload::

   [http]
      max-row-limit = 10000

This means that in a graph, Grafana will plot up to
10,000 points regardless of how many lines are drawn. When the query exceeds
this limit Grafana will just display the incomplete graph, but if you open the
query inspector you will find ``partial: true`` in the metadata inside certain
objects.

To avoid this you can group by larger time intervals in your query, which will
produce a smaller amount of results. Additionally, you can create a variable
with different time intervals and use it in your query like::

   GROUP BY time($var)

so that you can change it when you zoom out.

`Related Jira ticket <https://jira.lsstcorp.org/browse/IT-978>`__

Telegraf Precision
++++++++++++++++++
When the system clock shifts over time and is readjusted by chronyd, Telegraf's
internal clock is unaffected. This results in Telegraf saving measurements to
with shifted timestamps. Additionally, when Grafana queries InfluxDB for these
shifted measurements between time ranges and groups them by time, there is a
significant chance that some results will not be returned because the
measurement will correspond to a time after the specified time range.

To avoid this, you can set the precision in Telegraf to the interval that you
are gathering data, so that timestamps are automatically rounded to the nearest
interval. This is not perfect, but it can alleviate the problem::

   [agent]
      precision = "1m"

| `Related Jira ticket <https://jira.lsstcorp.org/browse/IT-986>`__
| `Bug report <https://github.com/influxdata/telegraf/issues/5335>`__
