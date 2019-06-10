"""Configures Grafana Admin accounts and default org for a fresh installation.

This script is meant to run it's main body only on a fresh installation of
Grafana. Still, it is designed to be able to be ran with every Puppet execution
with the help of the file ``lastInitialization.txt`` which will be stored in
the same directory where this is ran from. When this script completes
successfully, it will write the timestamp of when it initialized Grafana.

This script will load configurations stored in ``admins/_kiosk.yaml`` and 
``admins/_superAdmins.yaml``. It changes the ``password`` and account name
(``login``) for the default account (which has ``super admin`` privileges).
It will then create another account, which will be used by the script from now
on to make requests to Grafana's API. With that account, the name of the
default organization will be changed.

Notes
=====
Since Grafana's API can be accessed over the network through the same port by
which the web client is accessed, it is ``IMPORTANT`` that this script is ran
before opening Grafana's port (default is 3000) on the firewall.

Functions
=========
"""
import os
from datetime import datetime
import grafanaAPI as gapi
import yamlUtility as yutil


def changeAdminPassword(newPasswd, user, password):
    """Change Grafana Admin's password.
    
    Parameters
    ==========
    newPasswd : `str`
        New password for the Admin account
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    See Also
    ========
    grafanaAPI
    renameAdminUser
    
    Notes
    =====
    It can be acceptable for the request to fail, if the execution of this script
    was interrupted before and it is still necessary to complete the final steps.
    
    When testing, changing the username and password did not kick the logged in 
    user from the website.
    """
    data = {'password': newPasswd}
    try:
        r = gapi.request('put', 'admin/users/1/password', user, password, data)
    except gapi.APIError:
        print('Warning: Failed to change default admin password. If the script failed in a previous '
            'execution then it can still be necessary to execute the rest of the script. If this is the '
            'first time you are running this script then there might be a connection problem with Grafana'
            ' or it might already be provisioned.')


def renameAdminUser(data, user, password):
    """Change Grafana admin's username.
    
    Parameters
    ==========
    data: `dict`
        Contains the fields accepted by Grafana API's ``User Update``:
         - login: Change the username of the account (`str`).
         - name: Change the name of the account (`str`).
         - email: Change the email of the account (`str`).
         - theme: Change the theme of the account {``light``, ``dark``}.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    See Also
    ========
    grafanaAPI
    changeAdminPassword
    
    Notes
    =====
    It can be acceptable for the request to fail, if the execution of this script
    was interrupted before and it is still necessary to complete the final steps.
    
    When testing, changing the username and password did not kick the logged in 
    user from the website.
    """
    try:
        r = gapi.request('put', 'users/1', user, password, data)
    except gapi.APIError:
        print('Warning: Failed to change default admin username. If the script failed in a previous '
            'execution then it can still be necessary to execute the rest of the script. If this is the '
            'first time you are running this script then there might be a connection problem with Grafana'
            ' or it might already be provisioned.')


def renameKioskOrg(user, password):
    """Rename the default organization (id=1) to what is in ``admins/_kiosk.yaml``.
    
    Parameters
    ==========
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Raises
    ======
    FileNotFoundError
        Raised if ``admins/_kiosk.yaml`` can't be found by this script. The file
        must contain the name of the default organization and a list of users which
        will be registered to it.
    ValueError
        Raised if 0 or more than 1 organizations exist in ``admins/_kiosk.yaml``.
        The number of organizations in this file must be exactly 1.
    grafanaAPI.APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: The first organization does not exist, invalid 
        credentials (`user` and `password`), the user doesn't have permission to
        make this request or the server is not responding. Check the error messages
        for more information.
    
    See Also
    ========
    grafanaAPI.request
    
    Notes
    =====
    Affects the current context organization for the user.
    """
    try:
        kiosk = yutil.getYamlContent('{}/_kiosk.yaml'.format(adminsDir))
    except FileNotFoundError as exc:
        print('Error: The file "{}/_kiosk.yaml" is missing. Make sure that the directory is set correctly'
            ' in "config.yaml" and that the file has the correct name. It must contain information about '
            'the account(s) that are provisioned for the first organization. You can change the name of '
            'the org in the key of the hash, but the filename shouldn\'t be changed.'.format(adminsDir))
        raise exc
        
    if len(kiosk) != 1:
        raise ValueError('{}/_kiosk.yaml must contain 1 organization.'.format(adminsDir))
    orgName = next(iter(kiosk))
    
    data = {'name':orgName}
    try:
        r = gapi.request('put', 'orgs/1', user, password, data)
    except gapi.APIError as exc:
        print('Error: There was an error when trying to change the default organization\'s name. Check '
            'the requests\' output below to see Grafana\'s response. There might be a problem with '
            ' Grafana, the API\'s account might be misconfigured or organization 1 might not exist.')
        raise exc


_path = os.path.abspath(os.path.dirname(__file__))
_lastInitialization = '{}/lastInitialization.txt'.format(_path)
if __name__ == '__main__' and (not os.path.exists(_lastInitialization)
        or os.path.getsize(_lastInitialization) == 0):
    gapi.timeout = yutil.config['timeout']
    adminsDir = '{}/admins'.format(yutil.config['provisioningDir'])
    
    try:
        supers = yutil.getYamlContent('{}/_superAdmins.yaml'.format(adminsDir))
    except FileNotFoundError as exc:
        print('The file "{}/_superAdmins.yaml" is missing! Make sure that the directory is set correctly in '
            '"config.yaml" and that the file has the correct name. It must contain information for the two '
            'Grafana Admin accounts, the main one (id=1) and the API account which the provisioning script '
            'should use. See the structure in the documentation and default files.'.format(adminsDir))
        raise exc
    
    grafAdmin = supers['grafanaAdmin']
    admLogin = 'admin'
    admPasswd = 'admin'
    
    changeAdminPassword(grafAdmin['password'], admLogin, admPasswd)
    admPasswd = grafAdmin['password']
    
    renameAdminUser(grafAdmin['data'], admLogin, admPasswd)
    admLogin = grafAdmin['data']['login']
    
    api = supers['api']
    gapi.createGrafanaAdmin(api, admLogin, admPasswd)
    
    renameKioskOrg(api['login'], api['password'])
    
    with open('{}/lastInitialization.txt'.format(_path),
            'w') as provisioned:
        provisioned.write(datetime.now().isoformat('T', 'seconds'))
