"""Module to use as interface with Grafana's API.

This module is intended to be used by the Grafana Provisioning scripts to
communicate with Grafana's API through HTTP requests. If you wish to use HTTPS
all you need to do is add an `s` to the string returned by the _apiUrl function,
note that this is not tested though.

Notes
=====
The default timeout for API requests is 5 seconds. This can be changed through
the global variable `timeout`.

Functions
=========
"""
import requests

timeout = 5  # Default timeout
head = {'Content-Type': 'application/json', 'Accept': 'application/json'}
methods = { 'get': requests.get,
            'post': requests.post,
            'put': requests.put,
            'delete': requests.delete,
            'patch': requests.patch}


def _apiUrl(api, user, password):
    """Return the url needed to make an API request with basic authentication.
    
    Parameters
    ==========
    api : `str`
        Suffix of the url. This should be the variable part of the API path that is
        required in the url, i.e. what comes after ``[...]/api/``.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    url : `str`
        The complete url to be used for API requests, including the credentials for
        basic authentication.
    
    Notes
    =====
    To use HTTPS you can change the string returned by this function at your own
    discretion, because a valid certificate was not available at the time of
    development, so this functionality has not been tested.
    """
    return 'http://{}:{}@localhost:3000/api/{}'.format(user, password, api)


def _req(requestFunction, api, user, password, jsn=None):
    """Make any kind of request to the Grafana API using basic authentication.
    
    Parameters
    ==========
    requestFunction : `requests`.{`get`, `post`, `put`, `delete`, `patch`}
        A requests function that can make an HTTP request with a certain method.
    api : `str`
        Suffix of the url. This should be the variable part of the API path that is
        required in the url, i.e. what comes after ``http://[...]/api/``.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    jsn : `dict`
        Contains the metadata that will be passed in JSON format with the API
        request. This should be data that Grafana is prepared to receive. Optional.
    
    Returns
    =======
    response : `requests.Response`
        Response object containig the data returned by Grafana, including JSON data
        as a string which can be converted to a dictionary with r.json(), and a
        status code.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: incomplete or wrong data passed with `jsn`, the `api`
        url or the `method` is wrong, invalid credentials (`user` and `password`),
        the user doesn't have permission to make this request or the server is not
        responding. Check the error messages for more information.
    
    See Also
    ========
    _apiUrl
    
    Notes
    =====
    Requests that return with a status code that represents an error are logged by
    Grafana to ``/var/log/messages``.
    """
    url = _apiUrl(api, user, password)
    if jsn is None:
        response = requestFunction(url, headers=head, timeout=timeout)
    else:
        response = requestFunction(url, json=jsn, headers=head, timeout=timeout)
    # We do not use response.raise_for_status() since it could print the url
    # (with the user and password) to stdout/stderr.
    if 400 <= response.status_code <= 599:
        raise APIError(user, password, response) from None
    return response


class APIError(requests.RequestException):
    """Represents that an error occurred when executing an API request.
    
    This exception should be raised when an API request returns with a status code
    in the 4XX or 5XX range. This mirrors the behavior of the default
    requests.HTTPError, except that it doesn't print the user and password
    contained in the url constituting the request (within the API, Grafana's admin
    can only authenticate using the default authentication method for all of the
    admin only functions, although this might change in the future).
    
    When raised with an HTTP ``response``, the exception prints out the status code
    returned, the method used for the request (e.g. POST), the url to which the
    request was made (without user and password) and the content of the response
    made by Grafana.
    
    Used together, these four items can give enough information to understand what
    request was being made and what went wrong with it.
    
    Parameters
    ----------
    user : `str`
        ``login`` of the user who was making the API request. To be erased from the
        url.
    password : `str`
        ``password`` of the user who was making the API request. To be erased from
        the url.
    response : `requests.Response`, optional
        Response to the API request containing error information. If ignored, the
        exception will not print an error message.
    """
    
    def __init__(self, user, password, response=None):
        self.response = response
        self.user = user
        self.password = password
    
    def __str__(self):
        """Return string representation of the error contained in the response.
        
        Returns
        =======
        errorMessage : `str`
            String to be printed out when the exception is raised. If the response is
            None this will be an empty string, or else it will be a concatenation of
            the following items:
            - ``code``: status code returned by the request (`int`).
            - ``method``: method type of the HTTP request (`str`).
            - ``url``: url of the request (`str`).
            - ``msg``: string representation of the JSON response returned by the
            request (`str`).
        """
        if self.response is not None:
            url = self.response.url.replace('{}:{}@'.format(self.user,self.password), '')
            msg = self.response.text
            code = self.response.status_code
            method = self.response.request.method
            return '{} | {} | {} | {}'.format(code, method, url, msg)
        else:
            return ''


def request(method, api, user, password, jsn=None):
    """Make an api request with a string HTTP method, using basic authentication.
    
    Wrapper for internal _req function. This function receives an HTTP request
    method as a string and passes it onto _req as a function.
    
    Parameters
    ==========
    method : {'get', 'post', 'put', 'delete', 'patch'} (`str`)
        An HTTP request method as a string.
    api : `str`
        Suffix of the url. This should be the variable part of the API path that is
        required in the url, i.e. what comes after ``http://[...]/api/``.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    jsn : `dict`
        Contains the metadata that will be passed in JSON format with the API
        request. This should be data that Grafana is prepared to receive. Optional.
    
    Returns
    =======
    response : `requests.Response`
        Response object containig the data returned by Grafana, including JSON data
        as a string which can be converted to a dictionary with r.json(), and a
        status code.
    
    Raises
    ======
    ValueError
        Raised if the method passed does not correspond to one of the accepted
        parameters.
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: incomplete or wrong data passed with `jsn`, the `api`
        url or the `method` is wrong, invalid credentials (`user` and `password`),
        the user doesn't have permission to make this request or the server is not
        responding. Check the error messages for more information.
    
    See Also
    ========
    _apiUrl
    _req
    
    Notes
    =====
    This function makes the script importing this module free to call a request
    with an HTTP method as string instead of as a library function. This way we
    separate implementation details from functionality.
    
    The `methods` dictionary is defined globally so that it does not need to be
    created every time a request is made. It only contains the HTTP methods
    currently used by the scripts.
    """
    method = method.lower()
    if method in methods:
        return _req(methods[method], api, user, password, jsn)
    else:
        raise ValueError('The HTTP method requested does not exist or is not implemented.')


def removeFromOrg(orgId, userId, user, password):
    """Remove a user from a Grafana organization.
    
    Parameters
    ==========
    orgId : `int`
        Number corresponding to the organization's ``id`` in Grafana.
    userId : `int`
        ``id`` of the user that is being removed from the Grafana organization.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    r : `requests.Response`
        Response object containig the data returned by Grafana, including JSON data
        as a string which can be converted to a dictionary with r.json(), and a
        status code.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: invalid credentials (`user` and `password`), the user
        doesn't have permission to make this request or the server is not
        responding. Check the error messages for more information.
    
    See Also
    ========
    _req
    
    Notes
    =====
    This function is intended to be used when creating new accounts to remove them
    from the default organization, and when creating new organizations to remove
    the API account from them.
    """
    return _req(requests.delete, 'orgs/{}/users/{}'.format(orgId, userId), user, password)


def setUserRoleOrg(orgId, userId, login, newRole, user, password):
    """Add a user to an org, with a role. Or set the role for a user in an org.
    
    Parameters
    ==========
    orgId : `int`
        Number corresponding to the organization's ``id`` in Grafana.
    userId : `int`
        ``id`` of the user who is being assigned a role on the Grafana org.
    login : `str`
        Grafana username (``login``) of the user who is being assingned a role.
    newRole : {'Admin', 'Editor', 'Viewer'}
        The role to be assigned to the user inside the organization.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: invalid `newRole`, inexistant organization or user, 
        wrong `login` regarding the given `userId`, invalid credentials (`user` and
        `password`), the user doesn't have permission to make this request or the
        server is not responding. Check the error messages for more information.
    
    See Also
    ========
    _req
    
    Notes
    =====
    In the future, if needed login can be turned into an optional parameter and it
    can be fetched inside this function using `userId`. Currently the function
    assumes that the `login` corresponds to the correct `userId` in Grafana.
    Passing a `login` of a different user might produce unexpected behavior.
    """
    # Get list of orgs for user
    r = _req(requests.get, 'users/{}/orgs'.format(userId), user, password)
    userOrgs = r.json()
    
    # Get the role for the user in the org if it exists
    currentRole = next((uo['role'] for uo in userOrgs if uo['orgId'] == orgId), None)
    # If the account exists but it's not in the org, add them to the org with role
    newRole = newRole.capitalize()
    if currentRole is None:
        data = {'loginOrEmail':login, 'role':newRole}
        r = _req(requests.post, 'orgs/{}/users'.format(orgId), user, password, data)
        
        # Change context organization for user
        r = _req(requests.post, 'users/{}/using/{}'.format(userId, orgId), user, password)
        
    # If the user belongs to the org but the role has changed
    elif currentRole != newRole:
        data = {'role':newRole}
        r = _req(requests.patch, 'orgs/{}/users/{}'.format(orgId, userId), user, password, data)


def createAccount(accountData, user, password):
    """Create a Grafana user account.
    
    Parameters
    ==========
    accountData : `dict`
        Dictionary with the data that Grafana can receive for account creation with
        the API. Grafana 5.4.2 supports the following fields:
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
        Grafana ``id`` of the newly created user.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: The user already exists, email already in use, invalid
        password or email, invalid credentials (`user` and `password`), the user
        doesn't have permission to make this request or the server is not 
        responding. Check the error messages for more information.
    
    See Also
    ========
    _req
    removeFromOrg
    """
    try:
        r1 = _req(requests.post, 'admin/users', user, password, accountData)
    except APIError as exc:
        print('Failed to create user account: {}'.format(accountData['login']))
        raise exc
    
    # Remove user from default org
    userId = r1.json()['id']
    removeFromOrg(1, userId, user, password)
    
    return userId


def createGrafanaAdmin(accountData, user, password):
    """Create an account with Grafana Admin privileges.
    
    Parameters
    ==========
    accountData : `dict`
        Dictionary with the data that Grafana can receive for account creation with
        the API. Grafana 5.4.2 supports the following fields:
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
        Grafana ``id`` of the newly created user.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: The user already exists, email already in use, invalid
        password or email, invalid credentials (`user` and `password`), the user
        doesn't have permission to make this request or the server is not 
        responding. Check the error messages for more information.
    
    See Also
    ========
    createAccount
    _req
    """
    userId = createAccount(accountData, user, password)
    data = {'isGrafanaAdmin': True}
    r = _req(requests.put, 'admin/users/{}/permissions'.format(userId), user, password, data)


def getExistingUserId(login, user, password):
    """Get the Grafana ``id`` of a user that already exists
    
    Parameters
    ==========
    login : `str`
        Grafana (``login``) of the user for whom the ``id`` is being retrieved.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    id : `int`
        Grafana ``id`` of the existing user.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: user doesn't exist, invalid credentials (`user` and
        `password`), the user doesn't have permission to make this request or the
        server is not responding. Check the error messages for more information.
    
    See Also
    ========
    _req
    
    Notes
    =====
    If the user doesn't exist and there is another user with an email that is equal
    to this user's login name, that user will be retrieved instead.
    """
    r = _req(requests.get, 'users/lookup?loginOrEmail={}'.format(login), user, password)
    return r.json()['id']


def createOrg(orgName, mainAdmin, user, password):
    """Create a new Grafana organization.
    
    Parameters
    ==========
    orgName : `str`
        Name of the Grafana organization to be created.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    orgId : `int`
        Number corresponding to the new organization's ``id`` in Grafana.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: an organization with that name already exists, invalid
        credentials (`user` and `password`), the user doesn't have permission to
        make this request or the server is not responding. Check the error messages
        for more information.
    
    See Also
    ========
    _req
    setUserRoleOrg
    getExistingUserId
    removeFromOrg
    """
    # Create the org and get the ID
    data = {'name':orgName}
    r = _req(requests.post, 'orgs', user, password, data)
    orgId = r.json()['orgId']
    
    # Add main admin to org
    setUserRoleOrg(orgId, 1, mainAdmin, 'Admin', user, password)
    
    # Remove API user from org
    apiId = getExistingUserId(user, user, password)
    removeFromOrg(orgId, apiId, user, password)
    
    return orgId


def getOrgId(orgName, user, password):
    """Obtain the ``id`` of a Grafana organization using its name.
    
    Parameters
    ==========
    orgName : `str`
        Name of the Grafana organization for which the ``id`` will be retrieved.
    user : `str`
        ``login`` of the Grafana account that is making the API request.
    password : `str`
        ``password`` of the Grafana account that is making the API request.
    
    Returns
    =======
    orgId : `int`
        Number corresponding to the organization's ``id`` in Grafana.
    
    Raises
    ======
    APIError
        Raised if the request replies with a status code in the 4XX or 5XX range.
        The causes include: an organization with that name doesn't exist, invalid
        credentials (`user` and `password`), the user doesn't have permission to
        make this request or the server is not responding. Check the error messages
        for more information.
    
    See Also
    ========
    _req
    """
    r = _req(requests.get, 'orgs/name/{}'.format(orgName), user, password)
    orgId = r.json()['id']
    return orgId
