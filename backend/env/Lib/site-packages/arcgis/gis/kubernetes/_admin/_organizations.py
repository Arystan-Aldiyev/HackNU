import json
from collections import OrderedDict
from urllib.request import HTTPError
from arcgis.gis._impl._con import Connection
from arcgis.gis import GIS
from arcgis._impl.common._mixins import PropertyMap
from typing import Dict, Any, Optional, List

###########################################################################
class KubeEnterpriseGroups:
    """
    This resource is an umbrella for operations that inventory your
    organization's groups, such as retrieving a list of users within a
    specific group or listing which groups a specific user is assigned to.
    The groups resource returns the total number of enterprise groups in
    the system.
    """

    # ----------------------------------------------------------------------
    def __init__(self, url: str, gis: "GIS"):
        self._url = url
        self._gis = gis
        self._con = gis._con

    # ----------------------------------------------------------------------
    def __str__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    @property
    def properties(self) -> dict:
        """
        returns the properties for the Organization

        :return: dict
        """
        if self._properties is None:
            self._properties = self._con.get(self._url, {"f": "json"})
        return self._properties

    # ----------------------------------------------------------------------
    def search(self, query: str = "", max_count: int = 1000) -> dict:
        """
        Searches users in the configured enterprise user store.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        query                           Optional String. Text to narrow down the user search.
        ---------------------------     --------------------------------------------------------------------
        max_count                       Optional Integer.  The maximum number of recrods that the client will accept.
        ===========================     ====================================================================

        """
        url = f"{self._url}/searchEnterpriseGroups"
        params = {"f": "json", "filter": query, "maxCount": max_count}
        return self._gis._portal.con.post(url, params)

    # ----------------------------------------------------------------------
    def find_within_groups(self, name: str, query: str = None, max_count: int = 1000):
        """
        This operation returns a list of users that are currently assigned to the enterprise group within the enterprise user and group stores.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        name                            Required String. The name of the group.
        ---------------------------     --------------------------------------------------------------------
        query                           Optional String. Text to narrow down the user search.
        ---------------------------     --------------------------------------------------------------------
        max_count                       Optional Integer.  The maximum number of recrods that the client will accept.
        ===========================     ====================================================================
        """
        if query is None:
            query = ""
        url = f"{self._url}/getUsersWithinEnterpriseGroup"
        params = {
            "f": "json",
            "groupName": name,
            "filter": query,
            "maxCount": max_count,
        }
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def get_user_groups(
        self, username: str, query: str = None, max_count: int = 1000
    ) -> dict:
        """
        This operation searches groups in the configured role store. You can narrow down the search using the `query` parameter.


        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        username                        Required String. The username to examine.
        ---------------------------     --------------------------------------------------------------------
        query                           Optional String. Text to narrow down the user search.
        ---------------------------     --------------------------------------------------------------------
        max_count                       Optional Integer.  The maximum number of recrods that the client will accept.
        ===========================     ====================================================================

        :returns: dict

        """
        if query is None:
            query = ""

        url = f"{self._url}/getEnterpriseGroupsForUser"
        params = {
            "f": "json",
            "username": username,
            "filter": query,
            "maxCount": max_count,
        }
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def refresh_membership(self, groups: List[str]) -> bool:
        """
        This operation iterates over every enterprise account configured in
        your organization and determines whether the user account is part
        of the input enterprise group. If there are any changes in
        membership, the database and indexes are updated for each group.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        groups                          Required List[str]. The name of the groups to refresh.
        ===========================     ====================================================================

        :returns: bool
        """
        assert isinstance(groups, (list, tuple))
        groups = ",".join(groups)
        url = f"{self._url}/refreshMembership"
        params = {"groups": groups, "f": "json"}
        return self._con.post(url, params).get("status", False)


###########################################################################
class KubeOrgSecurity(object):
    """
    Allows the for the management of the security of the settings.
    """

    _con = None
    _gis = None
    _url = None
    _properties = None
    # ----------------------------------------------------------------------
    def __init__(self, url: str, gis: "GIS") -> "KubeOrgSecurity":
        self._url = url
        self._gis = gis
        self._con = gis._con

    # ----------------------------------------------------------------------
    def __str__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    @property
    def properties(self) -> dict:
        """
        returns the properties for the Organization

        :return: dict
        """
        if self._properties is None:
            self._properties = self._con.get(self._url, {"f": "json"})
        return self._properties

    @property
    def enterprise_user(self):
        """Allows users to manage and work with enterprise users"""
        url = f"{self._url}/users"
        return KubeEnterpriseUser(url, gis=self._gis)

    @property
    def enterprise_groups(self):
        """Allows users to manage and work with enterprise groups"""
        url = f"{self._url}/groups"
        return KubeEnterpriseGroups(url, gis=self._gis)


class KubeEnterpriseUser:
    """
    The `KubeEnterpriseUser` resource houses operations used to manage
    members in your organization.
    """

    _url = None
    _gis = None

    def __init__(self, url, gis):
        self._url = url
        self._gis = gis

    def search(self, query: str = "", max_count: int = 1000) -> dict:
        """
        Searches users in the configured enterprise user store.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        query                           Optional String. Text to narrow down the user search.
        ---------------------------     --------------------------------------------------------------------
        max_count                       Optional Integer.  The maximum number of recrods that the client will accept.
        ===========================     ====================================================================

        """
        url = f"{self._url}/searchEnterpriseUsers"
        params = {"f": "json", "filter": query, "maxCount": max_count}
        return self._gis._portal.con.post(url, params)

    def create_user(
        self,
        username,
        password,
        first_name,
        last_name,
        email,
        role="org_user",
        level=2,
        provider="arcgis",
        idp_username=None,
        description=None,
        user_license=None,
    ):
        """
        This operation is used to pre-create built-in or enterprise
        accounts within the portal. The provider parameter is used to
        indicate the type of user account.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        username                        Required string. The name of the user account
        ---------------------------     --------------------------------------------------------------------
        password                        Required string. The password of the user account
        ---------------------------     --------------------------------------------------------------------
        first_name                      Required string. The first name for the account
        ---------------------------     --------------------------------------------------------------------
        last_name                       Required string. The last name for the account
        ---------------------------     --------------------------------------------------------------------
        email                           Required string. The email for the account
        ---------------------------     --------------------------------------------------------------------
        role                            Optional string. The role for the user account. The default value is
                                        org_user.
                                        Values org_admin | org_publisher | org_user | org_editor (Data Editor) | viewer
        ---------------------------     --------------------------------------------------------------------
        level                           Optional integer. The account level to assign the user.
                                        Values 1 or 2
        ---------------------------     --------------------------------------------------------------------
        provider                        Optional string. The provider for the account. The default value is
                                        arcgis. Values arcgis | enterprise
        ---------------------------     --------------------------------------------------------------------
        idp_username                    Optional string. The name of the user as stored by the enterprise
                                        user store. This parameter is only required if the provider
                                        parameter is enterprise.
        ---------------------------     --------------------------------------------------------------------
        description                     Optional string. A user description
        ---------------------------     --------------------------------------------------------------------
        user_license	                Optional string. The user type for the account. (10.7+)

                                        Values: creator, editor, advanced (GIS Advanced),
                                                basic (GIS Basic), standard (GIS Standard), viewer,
                                                fieldworker

        ===========================     ====================================================================

        :return: boolean

        """
        role_lu = {
            "editor": "iBBBBBBBBBBBBBBB",
            "viewer": "iAAAAAAAAAAAAAAA",
            "org_editor": "iBBBBBBBBBBBBBBB",
            "org_viewer": "iAAAAAAAAAAAAAAA",
        }
        user_license_lu = {
            "creator": "creatorUT",
            "editor": "editorUT",
            "advanced": "GISProfessionalAdvUT",
            "basic": "GISProfessionalBasicUT",
            "standard": "GISProfessionalStdUT",
            "viewer": "viewerUT",
            "fieldworker": "fieldWorkerUT",
        }
        if user_license.lower() in user_license_lu:
            user_license = user_license_lu[user_license.lower()]
        if role.lower() in role_lu:
            role = role_lu[role.lower()]

        url = "%s/createUser" % self._url
        params = {
            "f": "json",
            "username": username,
            "password": password,
            "firstname": first_name,
            "lastname": last_name,
            "email": email,
            "role": role,
            "level": level,
            "provider": provider,
        }
        if idp_username:
            params["idpUsername"] = idp_username
        if description:
            params["description"] = description
        if user_license:
            params["userLicenseTypeId"] = user_license
        res = self._gis._portal.con.post(path=url, postdata=params)
        return res["status"] == "success"

    def get_enterprise_user(self, username):
        """gets the enterprise user"""
        url = f"{self._url}/getEnterpriseUser"
        params = {"f": "json", "username": username}
        return self._gis._portal.con.post(url, params)

    def refresh_membership(self, users):
        """refreshes the user membership"""
        url = f"{self._url}/refreshMembership"
        params = {"f": "json", "users": users}
        return self._gis._portal.con.post(url, params)


###########################################################################
class KubeOrganization:
    """
    A single organization within your deployment, allowing you to manage
    and update it's licensing and security information, as well as manage
    it's federated servers.
    """

    _con = None
    _gis = None
    _url = None
    _properties = None
    _security = None
    _federation = None
    _license = None
    # ----------------------------------------------------------------------
    def __init__(self, url, gis: "GIS", **kwargs):
        """class initializer"""
        self._gis = gis
        self._url = url
        self._con = gis._con
        self._properties = None
        self._json_dict = None

    # ----------------------------------------------------------------------
    def _init(self):
        """loads the properties into the class"""
        params = {"f": "json"}
        try:
            result = self._con.get(path=self._url, params=params)
            if isinstance(result, dict):
                self._json_dict = result
                self._properties = PropertyMap(result)
            else:
                self._json_dict = {}
                self._properties = PropertyMap({})
        except HTTPError as err:
            raise RuntimeError(err)
        except:
            self._json_dict = {}
            self._properties = PropertyMap({})

    # ----------------------------------------------------------------------
    def __str__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        returns the object properties
        """
        if self._properties is None:
            self._init()
        return self._properties

    # ----------------------------------------------------------------------
    @property
    def org_property(self) -> dict:
        """
        This operation lists and sets properties specific to an organization that
        can be modified to control your deployment.

        :Returns: dict

        """
        url = f"{self._url}/properties"
        params = {"f": "json"}
        res = self._con.get(url, params)
        return res

    # ----------------------------------------------------------------------
    @org_property.setter
    def org_property(self, value: dict):
        """
        This operation lists and sets properties specific to an organization that
        can be modified to control your deployment.

        :Returns: dict
        """
        url = f"{self._url}/properties/update"
        params = {"f": "json"}
        res = self._con.get(url, params)
        if res.get("status") == False:
            raise Exception(res)

    # ----------------------------------------------------------------------
    @property
    def url(self):
        """gets/sets the service url"""
        return self._url

    # ----------------------------------------------------------------------
    def _refresh(self):
        """reloads all the properties of a given service"""
        self._init()

    # ----------------------------------------------------------------------
    @property
    def security(self):
        if self._security is None:
            self._security = KubeOrgSecurity(url=f"{self._url}/security", gis=self._gis)
        return self._security

    # ----------------------------------------------------------------------
    @property
    def license(self) -> "KubeOrgLicense":
        """
        The Licenses resource returns high-level licensing details.

        :return: KubeOrgLicense
        """
        if self._license is None:
            url = url = f"{self._url}/license"
            self._license = KubeOrgLicense(url, self._gis)
        return self._license

    # ----------------------------------------------------------------------
    @property
    def federation(self) -> "KubeOrgFederations":
        """
        Returns manager to work with server federation.

        :return: KubeOrgFederations
        """
        if self._federation is None:
            url = self._url + "/federation"
            self._federation = KubeOrgFederations(url, self._gis)
        return self._federation


###########################################################################
class KubeOrgFederations:
    """
    Provides access to the federation of ArcGIS Server and the ability to
    federate them with the organization.
    """

    _con = None
    _gis = None
    _url = None
    _properties = None
    # ----------------------------------------------------------------------
    def __init__(self, url: str, gis: "GIS") -> "KubeOrgFederations":
        self._url = url
        self._gis = gis
        self._con = gis._con

    # ----------------------------------------------------------------------
    def __str__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    @property
    def properties(self) -> dict:
        """
        returns the properties for the Kubernetes License Organization

        :return: dict
        """
        if self._properties is None:
            self._properties = self._con.get(self._url, {"f": "json"})
        return self._properties

    @property
    def servers(self):
        """
        This resource returns detailed information about the ArcGIS Servers
        federated with ArcGIS on Kubernetes. Information such as the ID and
        name of the server, ArcGIS Web Adaptor URL, administration URL, and
        role of the server.
        """
        url = f"{self._url}/servers"
        params = {"f": "json"}
        return self._con.get(path=url, params=params)

    def federate(self, url: str, admin_url: str, username: str, password: str) -> bool:
        """
        This operation federates either a GIS Server or ArcGIS Image Server
        with an organization. The federate operation performs a validation
        check to determine whether the provided service and
        dministrative URLs are accessible. If the resulting validation check
        fails, a warning is returned. A SEVERE log type is also returned in
        the organization's logs. After federation, administrators will be
        unable to set a server role for the federated server.


        :returns: bool

        """
        params = {
            "f": "json",
            "url": url,
            "adminUrl": admin_url,
            "username": username,
            "password": password,
        }
        url = f"{self._url}/servers/federate"
        return self._con.post(url, params).get("status", "failed") == "success"

    def validate(self) -> dict:
        """
        The validate operation performs validation checks against all
        federated GIS Server and ArcGIS Image Server types within your
        organization, including the hosting server that is built in with an
        ArcGIS Enterprise on Kubernetes deployment. On completion, this
        operation returns status and accessibility information for all
        organization servers. This response also includes any failure
        messages from failed validation checks.

        :returns: dict
        """
        url = f"{self._url}/servers/validate"
        params = {"f": "json"}

        return self._con.get(url, params)


###########################################################################
class KubeOrgLicense:
    """
    The Licenses resource returns high-level licensing details, such as the
    total number of registered members that can be added, the current
    number of members in the organization, the Enterprise portal version,
    and license manager information. This API endpoint also provides access
    to various operations that allow you to manage your portal licenses for
    your organization.

    """

    _con = None
    _gis = None
    _url = None
    _properties = None
    # ---------------------------------------------------------------------
    def __init__(self, url: str, gis: "GIS") -> "KubeOrgLicense":
        """
        initializer
        """
        self._url = url
        self._gis = gis
        self._con = gis._con
        self._properties = None

    # ----------------------------------------------------------------------
    def __str__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    @property
    def properties(self) -> dict:
        """
        returns the properties for the Kubernetes License Organization

        :return: dict
        """
        if self._properties is None:
            self._properties = self._con.get(self._url, {"f": "json"})
        return self._properties

    # ----------------------------------------------------------------------
    def update_license_manager(self, config: dict) -> bool:
        """
        This operation allows you to change the license server connection
        information for your portal, as well as register a backup license
        manager for high availability. After changing the license manager
        properties, Portal for ArcGIS automatically restarts to register
        changes and set up connections with the backup license manager.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        config                          Required Dict. The JSON representation of the license server
                                        connection information.
        ===========================     ====================================================================

        :return: Boolean

        """

        url = self._url + "/updateLicenseManager"
        params = {"f": "json", "licenseManagerInfo": json.dumps(config)}
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    def import_license(self, license_file: str):
        """
        Applies a new license file to a specific organization, which contains the portal's user type and add-on licenses.

        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        license_file                    Required String. The kubernetes license file.
        ===========================     ====================================================================

        :return: Boolean

        """
        params = {"f": "json"}
        url = self._url + "/importLicense"
        file = {"file": license_file}
        res = self._con.post(url, params, files=file)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    def validate(self, file, list_ut=False):
        """
        The `validate` operation is used to validate an input license file.
        Only valid license files can be imported into the Enterprise
        portal. If the provided file is valid, the operation will return
        user type, app bundle, and app information from the license file.
        If the file is invalid, the operation will fail and return an error
        message.


        ===========================     ====================================================================
        **Argument**                    **Description**
        ---------------------------     --------------------------------------------------------------------
        file                            Required String. The kubernetes license file.
        ---------------------------     --------------------------------------------------------------------
        list_ut                         Optional Boolean. Returns a list of user types that are compatible
                                        with the Administrator role. This identifies the user type(s) that
                                        can be assigned to the Initial Administrator Account when creating
                                        a portal.
        ===========================     ====================================================================

        :return: Dict

        """
        file = {"file": file}
        params = {"f": "json", "listAdministratorUserTypes": list_ut}
        url = "%s/validateLicense" % self._url
        res = self._con.post(url, params, files=file)
        return res


###########################################################################
class KubeOrganizations:
    """
    Allows for the management of organizations within the ArcGIS Enterprise
    on Kubernetes deployment.
    """

    _con = None
    _gis = None
    _url = None
    _properties = None
    # ----------------------------------------------------------------------
    def __init__(
        self, url: str, gis: "GIS", initialize: bool = True
    ) -> "KubeOrganizations":
        """
        Kubernetes Organization
        """
        self._url = url
        self._gis = gis
        self._con = gis._con

        if initialize:
            self._init(gis)

    # ----------------------------------------------------------------------
    def _init(self, connection=None):
        """loads the properties into the class"""

        params = {"f": "json"}
        try:
            result = self._con.get(self._url, params)
            if isinstance(result, dict):
                self._json_dict = result
                self._properties = PropertyMap(result)
            else:
                self._json_dict = {}
                self._properties = PropertyMap({})
        except HTTPError as err:
            raise RuntimeError(err)
        except:
            self._json_dict = {}
            self._properties = PropertyMap({})

    # ----------------------------------------------------------------------
    def __str__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "<%s at %s>" % (type(self).__name__, self._url)

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        returns the object properties
        """
        if self._properties is None:
            self._init()
        return self._properties

    # ----------------------------------------------------------------------
    @property
    def url(self):
        """gets/sets the service url"""
        return self._url

    # ----------------------------------------------------------------------
    def _refresh(self):
        """reloads all the properties of a given service"""
        self._init()

    # ----------------------------------------------------------------------
    @property
    def orgs(self) -> tuple:
        """
        Returns a list of registered organizations with the Kubernetes deployment

        :return: tuple
        """
        return tuple(
            [
                KubeOrganization(url=f"{self._url}/{org}", gis=self._gis)
                for org in self.properties["organizations"]
            ]
        )
