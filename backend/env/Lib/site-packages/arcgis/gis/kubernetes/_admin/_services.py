try:
    import ujson as json
except ImportError:
    import json
from functools import lru_cache
from arcgis._impl.common._mixins import PropertyMap
from typing import Dict, Any, Optional, List

###########################################################################
class KubeService(object):
    """
    A service exposes GIS resources like maps, rasters, locators,
    geodatabases, and so forth through REST and SOAP interfaces. The type
    of the service is often dictated by the type of resources being
    published. In addition to accessing the underlying resource, a GIS
    service can expose additional capabilities called extensions (or server
    object extensions). Extensions are packages of custom functionality that
    can perform business logic or expose the service through additional
    formats or protocols.
    """

    _url = None
    _con = None
    _gis = None
    _properties = None

    def __init__(self, url, gis):
        self._url = url
        self._gis = gis
        self._con = gis._con

    # ----------------------------------------------------------------------
    def change_provier(self, provider: str) -> bool:
        """
        This operation is used to update an individual service to use either
        a dedicated or shared instance type. When a qualified service is
        published, the service is automatically set to use shared instances.

        When using this operation, services may populate other provider types
        as values for the provider parameter, such as ArcObjects and SDS.
        While these are valid provider types, this operation does not support
        changing the provider of such services to either ArcObjects11 or
        DMaps. Services with either ArcObjects or SDS as their provider will
        not be able to change their instance type.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        provider            Required String. Specifies the service instance as either a shared
                            (DMaps) or dedicated (ArcObjects11) instance type. These values are case-sensitive.

                            values: DMaps, ArcObjects11
        ===============     ====================================================================


        :return: boolean
        """
        lu = {"dmaps": "DMaps", "arcobjects11": "ArcObjects11"}
        provider = lu[provider.lower()]
        params = {"f": "json", "provider": provider}
        url = "{self._url}/changeProvider"
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    def delete(self) -> bool:
        """
        Removes the service from the hosting server

        :return: bool

        """
        url = f"{self._url}/delete"
        params = {"f": "json"}
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    @property
    def status(self) -> dict:
        """
        This resource provides the configured and current status of a GIS
        service. The configured status represents the state of the resource
        as you have configured it to be. For example, starting a service
        would set its configured status to be STARTED. However, it is
        possible that the configured state may not match the actual state
        of the resource. The realTimeState property represents the actual
        state of a service.
        """
        url = f"{self._url}/status"
        params = {"f": "json"}
        return self._con.get(url, params)

    # ----------------------------------------------------------------------
    def start(self) -> bool:
        """
        Starts the service

        :return: bool
        """

        url = f"{self._url}/start"
        params = {"f": "json"}
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def stop(self) -> bool:
        """
        Stops the service

        :return: bool
        """

        url = f"{self._url}/stop"
        params = {"f": "json"}
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def restart(self) -> bool:
        """
        Recycles the current service
        :return: Bool
        """
        self.stop()
        return self.start()

    # ----------------------------------------------------------------------
    @property
    def scaling(self) -> Dict[str, Any]:
        """
        This resource returns the scaling and resource allocation for a
        specific GIS service microservice. When used to update the service,
        it updates the scaling (replicas min and max) and resource allocation
        (cpuMin, cpuMax, memoryMin, memoryMax).

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        value               Required Dict[str, Any]. The service scaling properties.
        ===============     ====================================================================

        :return: Dict[str, Any]

        """
        url = f"{self._url}/scaling"
        params = {"f": "json"}
        return self._con.get(url, params)

    # ----------------------------------------------------------------------
    @scaling.setter
    def scaling(self, value: Dict[str, Any]):
        """
        See main ``scaling`` property docstring
        """
        url = f"{self._url}/scaling/edit"
        params = {
            "f": "json",
            "serviceScalingSpec": value,
        }
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    @property
    def properties(self) -> PropertyMap:
        """
        To edit a service, you need to submit the complete JSON representation of
        the service, which includes the updates to the service properties. Editing
        a service can cause the service to be restarted with updated properties.

        The edit settings of a service contains the following four sections:

        + Service Description Properties - Common properties that are shared by all services. These properties typically identify a specific service.
        + Service Framework Properties - Properties targets towards the framework that hosts the GIS service. They define the life cycle and load balancing of the service.
        + Service Type Properties - Properties targeted towards the core service type as seen by the server administrator. Since these properties are associated with a server object, they vary across the service types.
        + Extension Properties - Represent the extensions that are enabled on the service.

        :return: dict
        """
        if self._properties is None:
            url = self._url
            params = {"f": "json"}
            res = self._con.get(url, params)
            self._properties = PropertyMap(res)
        return self._properties

    # ----------------------------------------------------------------------
    @properties.setter
    def properties(self, properties: dict):
        """
        See main ``properties`` property docstring.
        """
        historic = dict(self.properties)
        historic.update(properties)
        params = {"f": "json", "service": historic}
        url = f"{self._url}/edit"
        res = self._con.post(url, params)
        self._properties = None
        if "status" in res and not res["status"] == "success":
            raise Exception(str(res))


###########################################################################
class ServicesManager(object):
    """
    The `ServicesManager` acts as the root folder and container for all
    sub-folders and GIS services for your deployment. You can create a
    new sub-folder by using the Create Folder operation as well as a new
    GIS service by using the Create Service method.
    """

    _gis = None
    _url = None
    _folder = None
    _types = None
    _properties = None

    def __init__(self, url: str, gis: "GIS"):
        self._url = url
        self._gis = gis
        self._con = gis._con

    # ----------------------------------------------------------------------
    @property
    def services_properties(self):
        """
        This resource is used to provide default settings for new services
        when they are published to the server. You can use the update
        operation to change the default settings. However, updating the
        default properties for services won't change the properties of any
        pre-existing services in your organization. To update these services,
        you must edit the individual service's properties.
        """
        return self._con.get(self._url + "/properties", {"f": "json"})

    # ----------------------------------------------------------------------
    @services_properties.setter
    def services_properties(self, properties: dict):
        """
        See main ``service_properties`` docstring
        """
        res = self._con.post(
            self._url + "/properties", {"f": "json", "properties": properties}
        )
        if res["status"] != "success":
            raise Exception(res)

    # ----------------------------------------------------------------------
    @property
    def properties(self) -> dict:
        """
        The proeprties of the manager.

        :return: dict
        """
        url = self._url
        params = {"f": "json"}
        self._properties = self._con.get(url, params)
        return self._properties

    # ----------------------------------------------------------------------
    @property
    def folder(self):
        """returns the current folder"""
        return self._folder or "/"

    # ----------------------------------------------------------------------
    @folder.setter
    def folder(self, folder: str):
        """get/set the current folder"""
        if folder is None:
            self._folder = "/"
        elif folder in self.folders:
            self._folder = folder
        else:
            raise Exception("Folder does not exist.")

    # ----------------------------------------------------------------------
    def list(self, folder: str = None) -> list:
        """lists the services in the current folder"""
        services = []
        if folder is None and self.folder != "/":
            folder = self.folder
        else:
            folder = None
        if folder:
            url = f"{self._url}/{folder}"
        else:
            url = self._url
        res = self._con.get(url, {"f": "json"})
        if "services" in res:
            return [
                KubeService(
                    url=f"{url}/{service['serviceName']}.{service['type']}",
                    gis=self._gis,
                )
                for service in res["services"]
            ]
        return []

    # ----------------------------------------------------------------------
    @property
    def folders(self) -> list:
        """
        returns a list of folder names

        :return: List[str]

        """
        return self.properties.get("folders", [])

    # ----------------------------------------------------------------------
    @property
    def types(self) -> dict:
        """
        This resource provides metadata about all service types and extensions that can be enabled.

        :return: Dict

        """
        if self._types is None:
            self._types = self._con.get(f"{self._url}/types", {"f": "json"})
        return self._types

    # ----------------------------------------------------------------------
    @property
    def extensions(self) -> dict:
        """
        Returns a collection of all the custom server object extensions that have been uploaded
        and registered with the deployment. A .soe file is a container of one or more server object
        extensions.

        :return: Dict
        """
        return self._con.get(f"{self._url}/types/extensions", {"f": "json"})

    # ----------------------------------------------------------------------
    @property
    def providers(self) -> dict:
        """
        returns the supported provider types for the GIS services in your organization.
        """
        return self._con.get(f"{self._url}/types/providers", {"f": "json"})

    # ----------------------------------------------------------------------
    def exists(
        self, *, service_name: str = None, folder: str = None, service_type: str = None
    ) -> dict:
        """
        This operation checks if a folder or service exists on the server.

        :return: dict
        """
        params = {
            "f": "json",
            "folderName": folder,
            "serviceName": service_name,
            "type": service_type,
        }
        for key in list(params.keys()):
            if params[key] is None:
                del params[key]

        url = f"{self._url}/exists"
        res = self._con.post(url, params)
        return res

    # ----------------------------------------------------------------------
    def can_create(
        self,
        service_type: str,
        *,
        folder: str = None,
        service: dict = None,
        options: dict = None,
    ) -> bool:
        """
        Checks if a service can be generated. It is recommended that the user
        check if the service can be created before calling `create_service`.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        service_type        Required String.  The type of service to create.
        ---------------     --------------------------------------------------------------------
        folder              Optional String. The location to create the service in.  If the `folder`
                            if set on the `ServicesManager`, the `folder` parameter will override
                            the save location. The folder must exist before calling this method.
        ---------------     --------------------------------------------------------------------
        service             Optional Dict. The service configuration in JSON format.
        ---------------     --------------------------------------------------------------------
        options             Optional Dict. Provides additional information about the service, such as whether it is a hosted service.
        ===============     ====================================================================

        """
        url = f"{self._url}/canCreateService"
        params = {
            "f": "json",
            "folderName": folder,
            "serviceType": service_type,
            "service": service,
            "options": options,
        }
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    def create_service(
        self, service_json: dict = None, input_upload_id: str = None, folder: str = None
    ) -> bool:
        """
        Creates a new GIS service in a folder (either the root or a sub-folder) by
        submitting a JSON representation of the service to this operation.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        service_json        Required dict. The JSON representation of the service being created.
        ---------------     --------------------------------------------------------------------
        folder              Optional String. The location to create the service in.  If the `folder`
                            if set on the `ServicesManager`, the `folder` parameter will override
                            the save location. The folder must exist before calling this method.
        ===============     ====================================================================

        :return: Bool

        """
        if isinstance(service_json, dict):
            service_json = json.dumps(service_json)

        if folder:
            url = f"{self._url}/{folder}/createService"
        elif folder is None and (self.folder or self.folder != "/"):
            url = f"{self._url}/{self.folder}/createService"
        else:
            url = f"{self._url}/createService"
        params = {"f": "json", "serviceJson": service_json}
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    def create_folder(self, folder: str) -> bool:
        """
        Creates a folder on the hosting server

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        folder              Required string. Name of the folder.
        ===============     ====================================================================

        :return: boolean
        """
        url = self._url + "/createFolder"
        params = {"f": "json", "folderName": folder}
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        return res

    # ----------------------------------------------------------------------
    def _delete_folder(self, folder: str) -> bool:
        """
        Removes a folder on the hosting server

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        folder              Required string. Name of the folder.
        ===============     ====================================================================

        :return: boolean
        """
        params = {"f": "json"}
        if folder in self.folders:
            u_url = self._url + "/%s/deleteFolder" % folder
            res = self._con.post(path=u_url, postdata=params, try_json=False)
            return not folder in self.folders
            # if 'status' in res:
            #    return res['status'] == 'success'
            # return res
        else:
            return False

    # ----------------------------------------------------------------------
    def refresh_auto_deployment(self) -> bool:
        """
        This operation auto-deploys the System or Utility services if they failed to be deployed
        during site creation. This operation should only be performed if either the System or
        Utility service fails to be created with the site.

        :return: Boolean

        """
        url = f"{self._url}/refreshAutodeployedServices"
        params = {"f": "json"}
        res = self._con.post(url, params)
        if "status" in res:
            return res["status"] == "success"
        else:
            return res

    # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
