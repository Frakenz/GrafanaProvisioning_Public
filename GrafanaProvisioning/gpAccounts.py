"""Provisions non-default orgs and non-admin accounts in Grafana using the API.

This script is meant to run it's main body on every Puppet execution.

It will make sure that there are no duplicate organizations or accounts in the
YAML configuration files, and create them in Grafana in case they do not exist
yet. Each account will be created with its given username, password, name and
email. Each organization will be created with their given name, and all
accounts in their list will be added to that organization with their given
role. Note that accounts can belong to more than one organization, but must
only be declared once in the YAML files.

This script loads the basic info of all accounts and organizations into memory,
and makes many requests to the API, so it can be a bit slow. Further testing is
necessary to determine if, how and where it can be optimized.

Functions
=========
"""
import glob
import grafanaAPI as gapi
import yamlUtility as yutil

    
def loadProvisionedOrgs(orgsDir):
    """Load orgs from YAML config into dict indexed by name, storing user lists.
    
    Parameters
    ==========
    orgsDir : `str`
        Path to the directory where the orgs YAML files (symlinks) are stored.
    
    Returns
    =======
    provOrgs : `dict`
        Dictionary containing all orgs in the provisioning configuration. Consists
        of one key per org, where the key is the org's name and the value is a list
        with the accounts to be provisioned for the organization.
    
    Raises
    ======
    ValueError
        Raised if there is more than one organization with the same name in the
        YAML configuration files or if there isn't exactly one org in a given
        ``org.yaml`` file.
    yaml.YAMLError
        Raised if an org file does not contain a valid YAML format.
    PermissionError:
        Raised if the script does not have read permissions on an org file.
    
    See Also
    ========
    yamlUtility.getYamlContent
    """
    provOrgs = {}
    for orgFile in glob.glob('{}/[!_]*.yaml'.format(orgsDir)):
        orgDict = yutil.getYamlContent(orgFile)
        numOrgs = len(orgDict)
        if numOrgs != 1:
            raise ValueError('There must be 1 org in the configuration file and {} were found. {}'
                .format(numOrgs, orgFile))
        orgName = next(iter(orgDict))
        if orgName in provOrgs:
            raise ValueError('Duplicate organization {} in the yaml configuration. {}'
                .format(orgName, orgFile))
        # Save list of org's accounts
        provOrgs[orgName] = orgDict[orgName]
    return provOrgs


def getOrCreateUser(account, user, password):
    """Return a user's ID. If the account doesn't exist, create it.
    
    Query for accounts containing the login name inside their login, email or name.
    The default limit is 1000 results per page, it is not expected that a query
    will match more than 1000 results. This is done instead of getting a single
    user because this doesn't return a 404 code when the user isn't found.
    
    Parameters
    ==========
    account : `dict`
        Dictionary with the data that Grafana can receive for account creation with
        the API. This is the same data which is found on an org's ``accounts.yaml``
        file. Grafana 5.4.2 supports the following fields:
        - ``login``: Username of the new user (`str`).
        - ``password``: Password of the new user (`str`).
        - ``name``: Name of the new user (`str`).
        - ``email``: Email of the new user (`str`).
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    userId : `int`
        Grafana ``id`` of the user. Either of an existing account or a new one.
    
    Raises
    ======
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: Trying to create an account with an email already in
        use, invalid password or email, invalid credentials (`user` and
        `password`), the user doesn't have permission to make this request or the
        server is not responding. Check the error messages for more information.
    
    See Also
    ========
    grafanaAPI.request
    grafanaAPI.createAccount
    """
    login = account['login']
    r = gapi.request('get', 'users/search?query={}'.format(login), user, password)
    users = r.json()['users']
    # https://stackoverflow.com/questions/9979970/#comment12752199_9980160
    userId = next((user['id'] for user in users if user['login'] == login), None)
    # Check if user exists or else create it
    if userId is None:
        userId = gapi.createAccount(account, user, password)
    return userId


def loadProvisionedUsers(accountsDir, user, password):
    """Load users from YAML config, create them if the don't exist, get their IDs.
    
    Parameters
    ==========
    accountsDir : `str`
        Path to the directory where the accounts YAML files (symlinks) are stored.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    existingUsers : `dict`
        Dictionary containing all the Grafana users in the provisioning 
        configuration. Consists of one key per user, where the key is the user's
        username and the value is the user's ID in Grafana.
    
    Raises
    ======
    ValueError
        Raised if there is more than one user with the same username in the YAML
        configuration files. This could happen if two orgs are trying to provision
        the same user, in this case only one of them should provision the user in
        the ``accounts.yaml`` file, but both of them should have the user in their
        ``org.yaml`` file.
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: email already in use, invalid password or email,
        invalid credentials (`user` and `password`), the user doesn't have
        permission to make this request or the server is not responding. Check the
        error messages for more information.
    yaml.YAMLError
        Raised if an accounts file does not contain a valid YAML format.
    PermissionError:
        Raised if the script does not have read permissions on an accounts file.
    
    See Also
    ========
    getOrCreateUser
    yamlUtility.getYamlContent
    """
    existingUsers = {}
    # Don't open the files that start with '_'
    # https://stackoverflow.com/a/36295481
    for accountsFile in glob.glob('{}/[!_]*.yaml'.format(accountsDir)):
        accountsList = yutil.getYamlContent(accountsFile)
        
        if accountsList is not None:
            for account in accountsList:
                login = account['login']
                if login in existingUsers:
                    raise ValueError('Duplicate user {} in the yaml configuration. {}'.format(login, accountsFile))
                existingUsers[login] = getOrCreateUser(account, user, password)
    return existingUsers


def reviewOrgUsers(orgId, provOrgUserList, existingUsers, user, password):
    """Make sure each user for the given org belongs to it with the correct role.
    
    For the given org, go through each user in the list and make sure they are in
    the org and have the correct role. Assumes the users exists.
    
    Parameters
    ==========
    orgId : `int`
        ID of the organization to review users for.
    provOrgUserList : `list` of `dict` of `str`
        List of the users for each org. This is equivalent to the structure found
        in the ``org.yaml`` input files. Each dict has two keys:
        - login: Username of the account belonging to the org (`str`).
        - role: Role that the account has in this organization (`str`).
    existingUsers : `dict`
        Dictionary containing all the Grafana users in the provisioning 
        configuration. Consists of one key per user, where the key is the user's
        username and the value is the user's ID in Grafana.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Raises
    ======
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: invalid `role`, inexistant organization or user, wrong
        `login` regarding the given `userId`, invalid credentials (`user` and
        `password`), the user doesn't have permission to make this request or the
        server is not responding. Check the error messages for more information.
    
    See Also
    ========
    grafanaAPI.setUserRoleOrg
    
    Notes
    =====
    If an account is configured in an ``org.yaml`` file but it is not found in any
    ``accounts.yaml`` file, a warning message will be printed and the program will
    continue normally.
    
    If an account is found more than once in an ``org.yaml`` file, only the first
    time it appears on the file will be considered for provisioning and a warning
    message will be printed. The program will continue normally.
    """
    members = {}
    for user in provOrgUserList:
        login = user['login']
        if login not in existingUsers:
            print('Warning: Org number {} is trying to invite user "{}" but the user\'s account was not '
                'found in the configuration files.'.format(orgId, login))
            continue
        if login in members:
            print('Warning: configuration for user "{}" was found more than once on org number {}. Only '
                'the first instance is valid.'.format(login, orgId))
            continue
        userId = existingUsers[login]
        
        gapi.setUserRoleOrg(orgId, userId, login, user['role'], admLogin, admPasswd)
        
        members[login] = True


def reviewExistingOrgs(grafOrgs, provOrgs, existingUsers, user, password):
    """Loop through all existing orgs and make sure their accounts are provisioned.
    
    Loop through all of Grafana's existing orgs and make sure that the ones which
    belong to the provisioning have their provisioned accounts associated to them,
    with the correct role. Remove the org from the `provOrgs` dictionary after
    finishing to be able to create and review the remaining ones later.
    
    Parameters
    ==========
    grafOrgs : `list` of `dict`
        List returned by Grafana containing all of its existing organizations.
    provOrgs : `dict`
        Dictionary containing all orgs in the provisioning configuration. Consists
        of one key per org, where the key is the org's name and the value is a list
        with the accounts to be provisioned for the organization.
    existingUsers : `dict`
        Dictionary containing all the Grafana users in the provisioning 
        configuration. Consists of one key per user, where the key is the user's
        username and the value is the user's ID in Grafana.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Raises
    ======
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: wrong parameters, invalid `role`, inexistant user,
        invalid credentials (`user` and `password`), the user doesn't have 
        permission to make this request or the server is not responding. Check the
        error messages for more information.
    
    See Also
    ========
    reviewOrgUsers
    grafanaAPI.setUserRoleOrg
    """
    for org in grafOrgs:
        orgName = org['name']
        if orgName in provOrgs:
            reviewOrgUsers(org['id'], provOrgs[orgName], existingUsers, user, password)
            del provOrgs[orgName]


def createAndReviewOrgs(provOrgs, existingUsers, user, password):
    """Loop through non existing orgs, create them and provision their accounts.
    
    Parameters
    ==========
    provOrgs : `dict`
        Dictionary containing all orgs in the provisioning configuration that have
        not been created yet. Consists of one key per org, where the key is the
        org's name and the value is a list with the accounts to be provisioned for
        the organization.
    existingUsers : `dict`
        Dictionary containing all the Grafana users in the provisioning 
        configuration. Consists of one key per user, where the key is the user's
        username and the value is the user's ID in Grafana.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Raises
    ======
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: wrong parameters, invalid `role`, inexistant user,
        invalid credentials (`user` and `password`), the user doesn't have 
        permission to make this request or the server is not responding. Check the
        error messages for more information.
    
    See Also
    ========
    reviewExistingOrgs
    reviewOrgUsers
    grafanaAPI.createOrg
    
    Notes
    =====
    Relies on deleting the existing orgs from provOrgs
    """
    # This shouldn't do anything unless an org is manually deleted from
    # Grafana, because orgs are created when processing new input
    gadmin = yutil.getSuperAdminLogin()
    for orgName in provOrgs:
        orgId = gapi.createOrg(orgName, gadmin, user, password)
        reviewOrgUsers(orgId, provOrgs[orgName], existingUsers, user, password)
    

if __name__ == '__main__':
    gapi.timeout = yutil.config['timeout']
    provisioningDir = yutil.config['provisioningDir']
    adminsDir = '{}/admins'.format(provisioningDir)
    accountsDir = '{}/accounts'.format(provisioningDir)
    orgsDir = '{}/orgs'.format(provisioningDir)
    
    # Get API user and password
    api = yutil.getYamlContent('{}/_superAdmins.yaml'.format(adminsDir))['api']
    admLogin = api['login']
    admPasswd = api['password']
    
    provOrgs = loadProvisionedOrgs(orgsDir)
    existingUsers = loadProvisionedUsers(accountsDir, admLogin, admPasswd)
    
    # Get all the orgs in Grafana
    r = gapi.request('get', 'orgs', admLogin, admPasswd)
    grafOrgs = r.json()
    
    reviewExistingOrgs(grafOrgs, provOrgs, existingUsers, admLogin, admPasswd)
    createAndReviewOrgs(provOrgs, existingUsers, admLogin, admPasswd)
    
    # Review users for the first organization (Kiosk)
    kiosk = yutil.getYamlContent('{}/_kiosk.yaml'.format(adminsDir))
    reviewOrgUsers(1, kiosk['Kiosk'], existingUsers, admLogin, admPasswd)
