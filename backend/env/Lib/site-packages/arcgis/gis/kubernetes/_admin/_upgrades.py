from arcgis.gis.kubernetes._admin._base import _BaseKube
from arcgis.gis import GIS
from typing import Dict, Any, Optional, List


class UpgradeManager(_BaseKube):
    _url = None
    _gis = None
    _con = None
    _properties = None

    def __init__(self, url: str, gis: GIS):
        self._gis = gis
        self._con = gis._con
        self._url = url

    @property
    def version(self) -> Dict[str, Any]:
        """
        Returns the Current Version of the software
        """
        url = f"{self._url}/currentVersion"
        params = {
            "f": "json",
        }
        return self._con.get(url, params)

    @property
    def history(self) -> Dict[str, Any]:
        """
        Returns the transaction history for all upgrade and rollback jobs.

        :return: Dict[str, Any]
        """
        url = f"{self._url}/history"
        params = {
            "f": "json",
        }
        return self._con.get(url, params)

    @property
    def installed_updates(self) -> List[Dict[str, Any]]:
        """
        Returns a cumulative list of patches and releases that are installed in the deployment

        :return: List[Dict[str, Any]]
        """
        url = f"{self._url}/installed"
        params = {
            "f": "json",
        }
        return self._con.get(url, params).get("updates", [])

    @property
    def rollback_options(self) -> List[Dict[str, Any]]:
        """
        Returns a list of possible rollback options for the site, depending
        on the patch that is installed. The ID for the specific rollback
        version is passed as input for the `rollback` operation.

        :return: List[Dict[str, Any]]
        """
        url = f"{self._url}/checkRollback"
        params = {
            "f": "json",
        }
        return self._con.post(url, params).get("updates", [])

    def rollback(
        self, version: Dict[str, Any], settings: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        This operation uninstalls a patch, removing the updates and fixes
        that had been applied to specific containers, and restoring the
        deployment to a previous, user-specified version of the software.
        The rollback operation cannot be performed for release-based
        updates.

        ==================     ====================================================================
        **Argument**           **Description**
        ------------------     --------------------------------------------------------------------
        version                Required Dict[str, str]. The version of the deployment the operation
                               will rollback towards. This value can be retrieved from the
                               `rollback_options`.
        ------------------     --------------------------------------------------------------------
        settings               Optional Dict[str, str]. A configuration for patch settings.
                               This is only available at 10.9.1+.
        ==================     ====================================================================

        :return: Dict[str, Any]


        """
        url = f"{self._url}/rollback"
        params = {
            "f": "json",
            "versionManifest": version,
            "rollbackSettings": settings or {},
        }
        return self._con.post(url, params)

    def available(self) -> Dict[str, List]:
        """
        This operation returns the version manifest, a cumulative list of
        release and patch versions that have been made available to an
        ArcGIS Enterprise organization.

        :return: Dict[str, List]
        """
        url = f"{self._url}/available"
        params = {
            "f": "json",
        }
        return self._con.post(url, params)
