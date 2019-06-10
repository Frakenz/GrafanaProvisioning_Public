"""Creates files/symlinks to provision orgs, users, datasources and dashboards.

Input Files
===========
This script is meant to run it's main body on every Puppet execution. It will
process files provided by users which should be stored in folders inside the
``inputs`` directory. These folders represent Grafana organizations and should
come with three files and a directory inside them:

 1. ``org.yaml``
 2. ``accounts.yaml``
 3. ``datasources.yaml``
 4. ``dashboards/``

The specifications for these files are described on :ref:`input_structure`.

Organization
------------
The script will create a symlink to this file in the ``orgs/`` directory.

Accounts
--------
The script will create a symlink to this file in the ``accounts/`` directory.

Datasources
-----------
The script will create the final version of this file inside
`/etc/grafana/provisioning/datasources` which **will be read by grafana-server
when it starts**.

Dashboards
----------
The script will create a directory in the configured `dashboardsDir` where a
directory for each folder will be created, inside them the JSON files will be
copied, without the ID and UID of their dashboards. A YAML file will also be
created inside `/etc/grafana/provisioning/dashboards/` which will contain the
list of directories corresponding to this organization. The YAML file with the
folder structure **will be read by grafana-server when it starts**, the
dashboards inside them will be checked for changes inside the provided folders
with a time period configured by `updateIntervalSeconds`.

Notes
=====
Provisioning configurations are stored in ``config.yaml``.

Functions
=========
"""
import os
import copy
import glob
import json
import shutil
from datetime import datetime
import grafanaAPI as gapi
import yamlUtility as yutil


def getDirList(top):
    """Get list of first level directories at `top`, excluding hidden folders.
    
    Parameters
    ==========
    top : `str`
        Path of the directory which will be scanned.
    
    Returns
    =======
    dirs : `list` of `str`
        List containing the directories found in the first level of `top` excluding
        the ones that start with a period.
    
    See Also
    ========
    os.walk
    """
    return [d for d in next(os.walk(top))[1] if not d.startswith('.')]


def provisionOrg(orgInputDir, user, password, provisionedOrgs):
    """Makes sure that the organization in Grafana is provisioned.
    
    If the organization already exists, get the org's id from Grafana. Else, create
    the org in Grafana and the symlink to ``org.yaml`` inside ``orgs/``. Returns
    the org's id and name.
    
    Parameters
    ==========
    orgInputDir : `str`
        The directory where the inputs for this org are stored.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    provisionedOrgs : `dict`
        Dictionary containing all orgs in the provisioning configuration. Consists
        of one key per org, where the key is the org's name and the value True for
        all provisioned organizations. We use a dictionary instead of a list
        because it should be faster for searching if an org is provisioned.
    
    Returns
    =======
    orgId : `int`
        ``id`` of the organization inside Grafana.
    orgName: `str`
        Name of the Grafana organization.
    
    Raises
    ======
    ValueError
        Raised if there is more than one organization with the same name in the
        YAML configuration files or if ``org.yaml`` doesn't contain exactly one
        organization. We do not support this feature. Different organizations
        should come separately in different inputs.
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: the symlink in ``orgs/`` exists but the organization in
        Grafana doesn't (in this case delete the symlink manually), the org already
        exists in Grafana and the symlink doesn't, invalid credentials (`user` and
        `password`), the user doesn't have permission to make this request or the
        server is not responding. Check the error messages for more information.
    
    See Also
    ========
    grafanaAPI.getOrgId
    grafanaAPI.createOrg
    
    Notes
    =====
    The existance of the symlink should represent the state of the Grafana org: if
    the symlink doesn't exist then the org shouldn't exist either, and if the 
    symlink exists the org should as well. If the creation of the org is
    interrupted halfway through it will need to be deleted manually (or else we
    could be deleting already existing orgs).
    """
    # Get Org name
    file = '{}/org.yaml'.format(orgInputDir)
    orgDict = yutil.getYamlContent(file)
    numOrgs = len(orgDict)
    if numOrgs != 1:
        raise ValueError('There must be 1 org in the configuration file and {} were found. {}'
            .format(numOrgs, file))
    orgName = next(iter(orgDict))
    if orgName in provisionedOrgs:
        raise ValueError('Duplicate organization {} in the yaml configuration. {}/org.yaml'
            .format(orgName, orgInputDir))
    provisionedOrgs[orgName] = True
    
    # Check if org is provisioned (file or symlink exists in ./orgs)
    symlink = '{}/orgs/{}_org.yaml'.format(provisioningDir, orgName)
    if os.path.exists(symlink):
        # Get org's id
        orgId = gapi.getOrgId(orgName, user, password)
    else:
        # Add the symlink to org
        os.symlink(file, symlink)
        # Create org and get the id
        gadmin = yutil.getSuperAdminLogin()
        try:
            orgId = gapi.createOrg(orgName, gadmin, user, password)
        except Exception as exc:
            os.remove(symlink)
            print('The operation failed while creating or configuring the  organization "{}". If the org was '
                'created, you will need to delete it manually from Grafana. If your org already exists and '
                'doesn\'t need to be created by the provisioning script, you can create a symlink called "{}"'
                'that points to "{}"'.format(orgName, symlink, file))
            raise exc
    return orgId, orgName


def provisionDatasources(orgId, orgName, dSrcYaml):
    """Create datasources config, which is read by grafana-server when it starts.
    
    Loads the configuration provided in ``org.yaml``, adds the corresponding
    orgId and sets ``editable = false`` to each datasource. Also removes the
    ``deleteDatasources`` field.
    
    Parameters
    ==========
    orgId : `int`
        ID of the org in Grafana to which the datasources will be provisioned.
    orgName : `str`
        Name of the org in Grafana to which the datasources will be provisioned.
    dSrcYaml : `dict`
        Contains the data required by Grafana to provision datasources. The two
        required keys are:
        
        - apiVersion: Version of the input ``datasources.yaml`` file (`int`).
        - datasources: List of datasources, with all the necessary configurations
            except for `orgId` and ``editable``, which are added here.
    
    Raises
    ======
    PermissionError:
        Raised if the script does not have write permissions to
        ``/etc/grafana/provisioning/datasources/```orgName```_datasources.yaml``
    
    See Also
    ========
    yamlUtility.writeYamlContent
    """
    # We don't want this functionality so we remove it
    if 'deleteDatasources' in dSrcYaml:
        del dSrcYaml['deleteDatasources']
    
    # Add parameters
    datasources = dSrcYaml['datasources']
    for dSrc in datasources:
        dSrc['orgId'] = orgId
        dSrc['editable'] = False
    
    # Provision datasources to Grafana's installation folder
    yutil.writeYamlContent('/etc/grafana/provisioning/datasources/{}_datasources.yaml'
        .format(orgName), dSrcYaml)


def copyDashboardWithoutIds(source, dest):
    """Load source JSON file, delete ID and UID, and save the dashboard at dest.
    
    Parameters
    ==========
    source : `str`
        Path to input JSON file containing a dashboard.
    dest : `str`
        Path to output JSON file, the dashboard to be provisioned at dashboardsDir.
    
    Raises
    ======
    FileNotFoundError:
        Raised if `source` does not exist or it cannot be accessed by the script.
    PermissionError:
        Raised if the script does not have permission to read from `source` or to
        write to `dest`.
    JSONDecodeError:
        Raised if `source` does not contain a valid JSON format.
    """
    try:
        with open(source, 'r', encoding='utf-8') as dashboard:
            data = json.load(dashboard)
    except json.JSONDecodeError as exc:
        print('The dashboard at {} does not contain a valid JSON format.'.format(source))
        raise exc from None
    data.pop('id', None)
    data.pop('uid', None)
    with open(dest, 'w', encoding='utf-8') as dashboard:
        json.dump(data, dashboard, indent=2)


def needsProvisioning(inputFile, currentFile):
    """Check if source is newer than dest.
    
    Parameters
    ==========
    inputFile : `str`
        File in the input folder.
    currentFile : `str`
        File created by this script for provisioning Grafana.
    
    Returns
    =======
    inputIsNewer : `bool`
        True if input file is newer than current provisioning file, else False.
    """
    # time since last modification of file (float)
    inputModified = datetime.utcfromtimestamp(os.path.getmtime(inputFile))
    currentModified = datetime.utcfromtimestamp(os.path.getmtime(currentFile))
    
    return inputModified > currentModified


def provisionDashboards(orgName, grafanaFolders, orgInputDir, dashboardsDir):
    """Maintain the correct dashboards inside the folders in dashboardsDir.
    
    Copy dashboards to dashboardsDir without ID and UID when they need to be
    copied. Delete dashboards from dashboardsDir which do not exist in the input.
    
    Parameters
    ==========
    orgName : `str`
        Name of the org in Grafana to which the dashboards will be provisioned.
    grafanaFolders : `list` of `str`
        List containing the names of the folders that are going to be provisioned.
        Just the folder names, not full paths.
    orgInputDir : `str`
        The directory where the inputs for the given org are stored.
    dashboardsDir : `str`
        The directory where Grafana will look for provisioned dashboards.
    
    Raises
    ======
    FileNotFoundError:
        Raised if one or more of the parameters conforms a path that doesn't exist.
    PermissionError:
        Raised if the script does not have permission to read dashboards from the
        input, or to write to dashboards in the dashboardsDir.
    JSONDecodeError:
        Raised if an input dashboard does not contain a valid JSON format.
    """
    for folder in grafanaFolders:
        srcDbs = glob.glob('{}/dashboards/{}/*.json'.format(orgInputDir, folder))
        
        destDir ='{}/{}/{}'.format(dashboardsDir, orgName, folder)
        destDbs = glob.glob('{}/*.json'.format(destDir))
        
        shortSrcDbs = [os.path.basename(dashboard) for dashboard in srcDbs]
        shortDestDbs = [os.path.basename(dashboard) for dashboard in destDbs]
        
        for d in range(len(shortSrcDbs)):
            if shortSrcDbs[d] in shortDestDbs:
                i = shortDestDbs.index(shortSrcDbs[d])
                if needsProvisioning(srcDbs[d], destDbs[i]):
                    copyDashboardWithoutIds(srcDbs[d], destDbs[i])
            else:
                copyDashboardWithoutIds(srcDbs[d], '{}/{}'.format(destDir, shortSrcDbs[d]))
        
        # Remove deleted files from provisioning
        for old in range(len(destDbs)):
            if not shortDestDbs[old] in shortSrcDbs:
                os.remove(destDbs[old])


def provisionFolders(orgId, orgName, grafanaFolders, orgInputDir, dashboardsDir):
    """Create folder structure in dashboardsDir and configure each folder route.
    
    Uses ``dashboardRoutesTemplate.yaml`` as a template to create the folder
    routes.
    
    Parameters
    ==========
    orgId : `int`
        ID of the org in Grafana to which the dashboards will be provisioned.
    orgName : `str`
        Name of the org in Grafana to which the dashboards will be provisioned.
    grafanaFolders : `list` of `str`
        List containing the names of the folders that are going to be provisioned.
        Just the folder names, not full paths.
    orgInputDir : `str`
        The directory where the inputs for the given org are stored.
    dashboardsDir : `str`
        The directory where Grafana will look for provisioned dashboards.
    
    Raises
    ======
    yaml.YAMLError
        Raised if the template contains an invalid YAML format.
    PermissionError:
        Raised if the script does not have read permissions on the template, or
        if it doesn't have write permissions to the configured ``dashboardsDir`` or
        ``/etc/grafana/provisioning/dashboards/``
    FileNotFoundError:
        Raised if the template doesn't exist or it can't be accessed by the script.
    
    See Also
    ========
    yamlUtility.getYamlContent
    yamlUtility.writeYamlContent
    os.makedirs
    os.symlink
    
    Notes
    =====
    The folder configuration is read by grafana-server when it starts. The
    dashboards in the folders will be checked periodically for updates by Grafana.
    """
    path = os.path.abspath(os.path.dirname(__file__))
    routeYaml = yutil.getYamlContent('{}/dbRoutesTemplate.yaml'.format(path))
    
    # Create org directory
    orgDashboardsPath = '{}/{}'.format(dashboardsDir, orgName)
    os.makedirs(orgDashboardsPath, exist_ok=True)
    
    # Delete removed folders and their contents
    existingFolders = getDirList(orgDashboardsPath)
    diff = set(existingFolders) - set(grafanaFolders)
    for oldFolder in diff:
        shutil.rmtree('{}/{}'.format(orgDashboardsPath, oldFolder))
    
    providerTemplate = routeYaml['providers'][0]
    routeYaml['providers'] = []
    for i in range(len(grafanaFolders)):
        provider = copy.deepcopy(providerTemplate)
        # Route to where the dashboards are going to be stored
        folderPath = '{}/{}'.format(orgDashboardsPath, grafanaFolders[i])
        provider['options']['path'] = folderPath
        
        provider['updateIntervalSeconds'] = yutil.config['updateIntervalSeconds']
        provider['orgId'] = orgId
        provider['folder'] = grafanaFolders[i]
        provider['name'] = '{}_{}'.format(orgName, grafanaFolders[i])
        
        routeYaml['providers'].append(provider)
        
        # Create directory for this Grafana Folder
        if not os.path.isdir(folderPath):
            os.mkdir(folderPath)
    
    yutil.writeYamlContent('/etc/grafana/provisioning/dashboards/{}_dashboardRoutes.yaml'
        .format(orgName), routeYaml)


if __name__ == '__main__':
    gapi.timeout = yutil.config['timeout']
    provisioningDir = yutil.config['provisioningDir']
    inputsDir = '{}/inputs'.format(provisioningDir)
    dashboardsDir = yutil.config['dashboardsDir']
    
    user, password = yutil.getApiCredentials()
    
    # Get folder names, these are inputs from different organizations
    dirs = getDirList(inputsDir)
    
    # Loop through organizations
    provisionedOrgs = {}
    for org in dirs:
        orgInputDir = '{}/{}'.format(inputsDir, org)
        
        orgId, orgName = provisionOrg(orgInputDir, user, password, provisionedOrgs)
        
        # Make symlink for account file
        symlink = '{}/accounts/{}_accounts.yaml'.format(provisioningDir, orgName)
        if not os.path.exists(symlink):
            # If the symlink exists but is broken, remove it to add the new one
            if os.path.lexists(symlink):
                os.remove(symlink)
            os.symlink('{}/accounts.yaml'.format(orgInputDir), symlink)
        
        # Check if there is something new to provision
        stateFile = '{}/.state.yaml'.format(orgInputDir)
        if os.path.exists(stateFile):
            state = yutil.getYamlContent(stateFile)
        else:
            state = {}
        
        # Datasources
        dSrcFile = '{}/{}'.format(orgInputDir, 'datasources.yaml')
        dSrcYaml = yutil.getYamlContent(dSrcFile)
        modified = False
        now = datetime.now()
        if 'datasourcesDate' in state:
            # time since last modification of file (float)
            lastModified = datetime.utcfromtimestamp(os.path.getmtime(dSrcFile))
            lastProvisioned = datetime.strptime(state['datasourcesDate'], '%Y-%m-%dT%H:%M:%S')
            if lastModified > lastProvisioned:
                provisionDatasources(orgId, orgName, dSrcYaml)
                state['datasourcesDate'] = now.isoformat('T', 'seconds')
                modified = True
        else:
            provisionDatasources(orgId, orgName, dSrcYaml)
            state['datasourcesDate'] = now.isoformat('T', 'seconds')
            modified = True
        
        # Dashboards
        grafanaFolders = getDirList('{}/dashboards'.format(orgInputDir))
        grafanaFolders.sort()
        if 'dashboardFolders' in state:
            # We sort them both to not depend on implementation details,
            # but they seem to come sorted from the beginning
            state['dashboardFolders'].sort()
            if state['dashboardFolders'] != grafanaFolders:
                provisionFolders(orgId, orgName, grafanaFolders, orgInputDir, dashboardsDir)
                state['dashboardFolders'] = grafanaFolders
                modified = True
        else:
            provisionFolders(orgId, orgName, grafanaFolders, orgInputDir, dashboardsDir)
            state['dashboardFolders'] = grafanaFolders
            modified = True
            
        provisionDashboards(orgName, grafanaFolders, orgInputDir, dashboardsDir)
        
        if modified:
            yutil.writeYamlContent(stateFile, state)
            
            ignorePath = '{}/.gitignore'.format(orgInputDir)
            if not os.path.exists(ignorePath):
                with open(ignorePath, 'w') as ignore:
                    ignore.write('.state.yaml\n')
            
            # Tell Puppet to restart Grafana.
            with open('{}/restart.txt'.format(provisioningDir), 'w') as restart:
                restart.write('restart\n')
