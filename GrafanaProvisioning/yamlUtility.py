"""Module to read from and write to our yaml configuration files.

This module is intended to be used by the Grafana provisioning scripts to read
information from certain yaml configuration files, and write to others. The 
functions getYamlContent and writeYamlContent are generic enough so that they 
can be used with any yaml file. It is implemented with pyyaml 3.13.

Functions
=========
"""
import yaml
import os


def getYamlContent(file):
    """Return YAML file translated to a Python data structure.
    
    Parameters
    ==========
    file : `str`
        Path of the YAML file whose content will be loaded.
    
    Returns
    =======
    yamlConfig : Usually `dict` or `list`
        Contents of the YAML configuration file translated to Python, can be any
        type of value or structure supported by YAML.
    
    Raises
    ======
    yaml.YAMLError
        Raised if the given file does not contain a valid YAML format.
    PermissionError:
        Raised if the module does not have read permissions on the given file.
    FileNotFoundError:
        Raised if the given file doesn't exist or if the file cannot be accessed by
        the module.
    
    Notes
    =====
    Since YAML files are data structures mainly composed of dictionaries and lists,
    the caller of this function must know what data structure to expect as a return
    value for a given file.
    """
    try:
        with open(file, 'r') as stream:
            try:
                yamlConfig = yaml.safe_load(stream)
                return yamlConfig
            except yaml.YAMLError as exc:
                print('There was an error when reading the YAML file, make sure that the file has a valid '
                    'yaml format.')
                raise exc from None
    except PermissionError as exc:
        print('Could not open {} because this user does not have permission to read the file.'.format(file))
        raise exc


def writeYamlContent(file, data):
    """Write contents of a Python data structure to a YAML file.
    
    Parameters
    ==========
    file : `str`
        Path of the YAML to which `data` will be written.
    data : Usually `dict` or `list`
        Python data structure to be written in `file`, can be any type of value or
        structure supported by YAML.
    
    Raises
    ======
    PermissionError:
        Raised if the module does not have write permissions on the given file or
        directory.
    """
    try:
        with open(file, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)
    except PermissionError as exc:
        print('Could not open {} because this user does not have permission to write to the file.'
            .format(file))


def loadConfig():
    """Return config.yaml as a Python data structure and set global timeout.
    
    This function loads the content of config.yaml into Python. These are settings
    for the Grafana provisioning scripts to use. It also sets the global value of
    ``to``, which is a timeout configuration used by ``req()``.
    
    Returns
    =======
    config : `dict`
        The contents of config.yaml as a Python dictionary. Contains routes to
        directories used by the provisioning scripts, and other settings such as
        timeout limit for API requets.
    
    Raises
    ======
    yaml.YAMLError
        Raised if the config file does not contain a valid YAML format.
    PermissionError:
        Raised if the module does not have read permissions on the config file.
    FileNotFoundError:
        Raised if the config file doesn't exist or if the file cannot be accessed
        by the module.
    
    See Also
    ========
    getYamlContent
    """
    # Get the absolute path to where this file is running from
    path = os.path.abspath(os.path.dirname(__file__))
    try:
        config = getYamlContent('{}/config.yaml'.format(path))
    except FileNotFoundError as exc:
        print('The file with the basic configuration for the provisioning is missing! This file should '
            'contain important information like the directories where different files are stored. Check the '
            'file structure in the documentation and default files.')
        raise exc
    
    return config


def getSuperAdminLogin():
    """Obtain the username of Grafana's Main admin account.
    
    Returns
    =======
    login : `str`
        Username of Grafana's Main admin account.
    
    Raises
    ======
    yaml.YAMLError
        Raised if the super admins file does not contain a valid YAML format.
    PermissionError:
        Raised if the module does not have read permissions on the super admins
        file.
    FileNotFoundError:
        Raised if the super admins file doesn't exist or if the file cannot be
        accessed by the module.
    
    See Also
    ========
    loadConfig
    getYamlContent
    """
    admins = getYamlContent('{}/admins/_superAdmins.yaml'.format(config['provisioningDir']))
    return admins['grafanaAdmin']['data']['login']


def getApiCredentials():
    """Return Grafana's main admin's username and password.
    
    From the information stored in /admins/_superAdmins.yaml, return the main
    admin's ``login`` and ``password``. This user should usually have id=1.
    
    Returns
    =======
    admLogin : `str`
        Username, or ``login``, of the main Grafana Admin account.
    admPasswd : `str`
        ``password`` of the main Grafana Admin account.
    
    Raises
    ======
    yaml.YAMLError
        Raised if the super admins file does not contain a valid YAML format.
    PermissionError:
        Raised if the module does not have read permissions on the super admins
        file.
    FileNotFoundError:
        Raised if the super admins file doesn't exist or if the file cannot be
        accessed by the module.
    
    See Also
    ========
    loadConfig
    getYamlContent
    """    
    # Get API user and password
    api = getYamlContent('{}/admins/_superAdmins.yaml'.format(config['provisioningDir']))['api']
    admLogin = api['login']
    admPasswd = api['password']
    
    return (admLogin, admPasswd)


config = loadConfig()
if 'provisioningDir' not in config:
    config['provisioningDir'] = os.path.abspath(os.path.dirname(__file__))
