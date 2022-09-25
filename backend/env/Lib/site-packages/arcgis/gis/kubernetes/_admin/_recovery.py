from arcgis.gis.kubernetes._admin._base import _BaseKube
from arcgis.gis import GIS
from typing import Dict, Any, Optional, List

###########################################################################
class BackupStore(_BaseKube):
    """ """

    _con = None
    _gis = None
    _url = None

    def __init__(self, url: str, gis: GIS) -> None:
        super()
        self._url = url
        self._gis = gis
        self._con = gis._con

    def delete(self) -> bool:
        """Unregisters a backup store from the deploayment"""
        url = f"{self._url}/unregister"
        params = {"f": "json"}
        return self._con.post(url, params).get("status", "failed") == "success"


###########################################################################
class Backup(_BaseKube):
    """ """

    _con = None
    _gis = None
    _url = None

    def __init__(self, url: str, gis: GIS) -> None:
        super()
        self._url = url
        self._gis = gis
        self._con = gis._con

    def delete(self) -> bool:
        """
        Removes the backup from the system

        :return: Boolean. True if successful else False.
        """
        url = "{self._url}/delete"
        params = {"f": "json"}
        return self._con.post(url, params).get("status") == "success"

    def restore(self, store_name: str, passcode: str) -> bool:
        """
        Restores the organization to the state it was in when the backup
        was created. Once completed, any existing content and data will be
        replaced with what was contained in the backup.


        ==================     ====================================================================
        **Argument**           **Description**
        ------------------     --------------------------------------------------------------------
        store_name             Required String. The name of the store the backup was copied to.
        ------------------     --------------------------------------------------------------------
        passcode               Required String. The passcode used to encrypted the backup. This
                               passcode must be the same as the one used when creating the backup.
        ==================     ====================================================================

        :return: Boolean. True if successful else False.

        """
        url = f"{self._url}/restore"
        params = {
            "f": "json",
            "storeName": store_name,
            "passcode": passcode,
        }
        return self._con.post(url, params).get("status") == "success"


###########################################################################
class RecoveryManager(_BaseKube):
    """
    Allows an administrator the ability to manage disaster recovery settings
    """

    _con = None
    _gis = None
    _url = None

    def __init__(self, url: str, gis: GIS) -> None:
        super()
        self._url = url
        self._gis = gis
        self._con = gis._con

    def register(
        self,
        name: str,
        credentials: Dict[str, str],
        root: str,
        storage_config: Dict[str, str],
        is_default: Optional[bool] = False,
    ) -> BackupStore:
        """
        This method registers a backup store.


        ==================     ====================================================================
        **Argument**           **Description**
        ------------------     --------------------------------------------------------------------
        name                   Required String. The unique name of the backup store.
        ------------------     --------------------------------------------------------------------
        credentials            Required Dict[str, str]. The credentials of the configuration store.
        ------------------     --------------------------------------------------------------------
        root                   Required String. The root directory of the store.
        ------------------     --------------------------------------------------------------------
        storage_config         Required Dictionary. A dictionary describing the storage
                               configuration for the backup store.
        ------------------     --------------------------------------------------------------------
        is_default             Optional Bool. Determines if the store will be the default backup
                               store.  The default is `False`.
        ==================     ====================================================================

        :return: BackupStore

        """
        try:
            url = f"{self._url}/stores/register"
            params = {
                "f": "json",
                "storeName": name,
                "credentials": credentials,
                "rootDirectory": root,
                "storageConfig": storage_config,
                "isDefault": is_default,
            }
            res = self._con.post(url, params)
            url = "{self._url}/stores/%s" % res["name"]
            return BackupStore(url=url, gis=self._gis)
        except Exception as e:
            raise e

    def backup(
        self,
        name: str,
        store_name: str,
        passcode: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a backup that can be restored in the event of data loss,
        data corruption, or deployment failures. Backups are stored in a
        designated backup store.

        ==================     ====================================================================
        **Argument**           **Description**
        ------------------     --------------------------------------------------------------------
        name                   Required String. The unique name of the backup.
        ------------------     --------------------------------------------------------------------
        store_name             Required String. The name of the backup store to save in.
        ------------------     --------------------------------------------------------------------
        passcode               Required String. A passcode that will be used to encrypt the content
                               of the backup. When restoring a backup, this passcode must be passed
                               in. The passcode must be at least eight characters in length.
        ------------------     --------------------------------------------------------------------
        description            Optional String. A description of the backup.
        ==================     ====================================================================

        :return: Dict[str, Any]
        """
        params = {
            "f": "json",
            "name": name,
            "storeName": store_name,
            "passcode": passcode,
            "description": description or "",
        }
        url = f"{self._url}/backuprestore/backup"
        return self._con.post(url, params)

    @property
    def backup_status(self) -> Dict[str, Any]:
        """
        This resource returns the status of a current, or previously
        executed, backup.

        :return: Dict[str, Any]

        """
        try:

            url = f"{self._url}/backuprestore/status"
            params = {"f": "json"}
            return self._con.get(url, params).get("status", {})
        except:
            return {}

    @property
    def backups(self) -> List[Backup]:
        """
        Returns the backups that have been created of an organization.

        :return: List[Backup]

        """
        try:
            url = f"{self._url}/backuprestore/backups"
            params = {"f": "json"}
            res = self._con.get(url, params)
            backups = []
            for bckup in res.get("backups", []):
                name = bckup["backupName"]
                url = f"{self._url}/backuprestore/backups/{name}"
                backups.append(Backup(url=url, gis=self._gis))
            return backups
        except:
            return []

    @property
    def stores(self) -> List[BackupStore]:
        """
        Returns the backup stores that are registered with your deployment.

        :return: List[BackupStore]
        """
        url = f"{self._url}/stores"
        params = {"f": "json"}
        res = self._con.get(url, params)
        stores = []
        for bs in res.get("backupStores", []):
            name = bs["name"]
            url = f"{self._url}/stores/{name}"
            stores.append(BackupStore(url=url, gis=self._gis))
        return stores

    @property
    def settings(self) -> Dict[str, Any]:
        """
        Gets/Sets the currently configured disaster recovery settings.

        ==================     ====================================================================
        **Argument**           **Description**
        ------------------     --------------------------------------------------------------------
        value                  Required Dict[str, Any]. Dictionary describing disaster recovery
                               settings.
        ==================     ====================================================================

        :return: Dict[str, Any]

        """
        url = f"{self._url}/settings"
        params = {"f": "json"}
        return self._con.get(url, params)

    # ----------------------------------------------------------------------
    @settings.setter
    def settings(self, value: Dict[str, Any]) -> None:
        """
        See main ``settings`` property docstring
        """
        url = f"{self._url}/settings/update"
        params = {
            "f": "json",
            "settings": value,
        }
        return self._con.post(url, params)
