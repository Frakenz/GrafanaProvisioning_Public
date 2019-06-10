##################################
Provisioning Grafana Organizations
##################################
Introduction
============
Grafana Basic Concepts
----------------------
This is a summary of what you need to know to understand this page. For more
details, you can read
`Grafana's Basic Concepts <docs.grafana.org/guides/basic_concepts/>`__.

Grafana works with internal ``organizations`` which function as user groups in
which users can add, view and generally manage their dashboards. Users have
their own ``account`` each, which have permissions depending on what that user
will use that account for. Accounts can be members of an organization in which
they can have three roles: `Admin`, `Editor` and `Viewer`; they can also be
members of more than one organization although it is usually not the case.

``Dashboards`` are pages where you can add ``panels``, which are types of
graphs, tables and other utilities. All dashboards must belong to an
organization. ``Datasources`` are Grafana's way of naming and configuring how
it connects to different databases available, they must be declared on each
organization and dashboards must gather data from datasources declared in the
same organization which they belong to.

What Provisioning Your Organization Means
-----------------------------------------
When you provision something to Grafana, you must provide access to your
``Input Files`` in an online repository. The server will download your files
every time it detects there are changes and will then update your Grafana
Organization.

Once your files are provisioned, your own Grafana organization will be created
where your dashboards will be displayed categorized in as many Grafana Folders
as you choose, your datasources will be added, and the accounts you specify
will belong to it. If the accounts are new they will be created for you, and if
they already exist they will just be added to the organization.

The advantage of having all of this done automatically is that we can easily
recover from losing a server or other mishaps. User mistakes can be avoided:

- If someone deletes a dashboard or folder on accident, it will be
  automatically restored.
- Datasources cannot be edited directly through the web client, they must be
  edited in the provisioning configuration.
- Dashboards can only be temporarily edited by editors. Users can't save over
  provisioned dashboards, but they can save new ones if their permissions allow
  them to.

You can add new dashboards, datasources and users to your organization. But you
can rest knowing that the basic configuration will always be there.

.. _input_structure:

Input Structure
===============
The script which processes the input files is `gpInputs.py`, it is meant to run
on every Puppet execution. It will process files provided by users which should
be stored in folders inside the `inputs/` directory. These folders represent
Grafana organizations and should come with three files and a directory inside
them:

::

   My Org's Repo/
   ├── org.yaml
   ├── accounts.yaml
   ├── datasources.yaml
   └── dashboards/
       ├── Your Grafana Folder/
       │   ├── DashboardsGoHere.json
       │   └── My Dashboard.json
       └── YourOtherGrafanaFolder/
           └── DashboardsGoHereToo.json

The specifications of each file are explained below. You should also
:download:`download the example files <./_static/SampleInputGrafana.zip>` and
modify them to fit your own requirements.
After you are done, upload them to an online repository and make them available
to the server admin so that they can add your organization to the provisioning
configuration. You can later add new folders, dashboards and users to the files
in your repository and the server will update them automatically.

Organization
------------
The `org.yaml` file should contain a hash with only one key, which should be
the organization's name. As the value of that key, there should be a list of
hashes, each with two keys:

   - login : `str`
      Username of a provisioned account inside an `accounts.yaml` file. This
      account could be configured inside a different organization.
   - role : {``Admin``, ``Editor``, ``Viewer``}
      The role that the user will have inside this organization

Organization names must be unique in each Grafana server. Check with a server
admin if your name for a new organization is available.

Accounts
--------
The `accounts.yaml` file should contain new accounts that need to be created
and maintained with the provisioning of this organization. The structure is a
list of hashes, each with four string keys, some of which must be unique inside
this Grafana installation:

   - login : Username of the new account (``unique``).
   - password : Password of the new account.
   - name : Name of the user.
   - email : Email associated with the new account (``unique``).

Datasources
-----------
The `datasources.yaml` file should contain a list of datasources to configure
according to what Grafana `requires for different database engines
<http://docs.grafana.org/administration/provisioning/#datasources>`_
to provision them, minus the fields ``orgId`` and ``editable`` since they will
be added by this script. If the file comes with settings for
``deleteDatasources`` this field will not be added to the provisioned file.

Note that if you have more than one datasource in your organization, it is
important that only one of them has the ``isDefault: true`` setting.

Folders and Dashboards
----------------------
The `dashboards/` directory must contain one directory for each Grafana
Folder that will need to be provisioned for this organization. The Grafana
Folders will take the name of these directories and will contain the dashboards
stored inside them. You must place your JSON files with Grafana Dashboards in 
these directories.

The dashboards must be already configured to use their corresponding
datasources and with the correct time range because they will be displayed
exactly as they are provided.

Exporting Dashboards
++++++++++++++++++++

You can create your own dashboards in Grafana and then export them to your
repository. To export a dashboard:

1. Open your dashboard in Grafana.
2. Depending on the Grafana version there are two ways to export dashboards: if
   you can't see the checkbox on the first one, you should use the second one.
   
 - The simple way:
 
   a. Click the `Share dashboard` button.
   b. Go to the `Export` tab.
   c. **Uncheck** `Export for sharing externally`.
   d. Save to file.
    
 - The long way. This method can be used for any Grafana version:
 
   a. Click on `Settings`.
   b. Go to the `View JSON` or `JSON Model` tab at the bottom.
   c. Click inside the JSON code.
   d. Press ``ctrl + a`` to select all of the JSON text.
   e. Copy the entire JSON.
   f. Open a text editor like `Notepad`.
   g. Paste the JSON into the editor.
   h. Save the file as a ``.json``. The file name is not important but
      should be descriptive. For example ``temperature.json``.

Program Behavior with Input Files
=================================
What the Input Files Do
-----------------------
org.yaml
++++++++
- Create a new organization with the configured name if it doesn't exist.
- Add configured users to organization, with given roles.
- Report an error if the organization name is already configured in another set
  of input files.

accounts.yaml
+++++++++++++
- Create configured accounts that don't exist.
- Report an error if a configured account is already provisioned by another
  organization.

datasources.yaml
++++++++++++++++
- Add the configured datasources to the organization.
- Remove previously provisioned datasources that were removed from the
  configuration.

dashboards/
+++++++++++
- Detects folders inside it and provisions a Grafana Folder with the contained
  dashboards for each one.
- Restore provisioned folders and dashboards that have been deleted.

What the Input Files Can't Do
-----------------------------
org.yaml
++++++++
- Change the name of an organization. If you change it the server will just
  create a new organization with the provisioning configuration and stop
  provisioning the old one.
- Add accounts to an organization, which are not part of any organization's
  provisioning files.

accounts.yaml
+++++++++++++
- Edit an existing account

dashboards/
+++++++++++
- Delete Grafana Folders and dashboards that have been removed from the
  configuration. You must remove these Folders or dashboards manually through
  the web client with an `Editor` or `Admin` account to delete them from
  Grafana's database.
- Provision dashboards with given UIDs. IDs and UIDs will be removed before
  provisioning and Grafana will assign new ones.
