from ._base import _BaseKube
from typing import Dict, Any, Optional

###########################################################################
class Mode(_BaseKube):
    _url = None

    @property
    def read_only(self) -> bool:
        """
        Returns if the site is in read only mode.

        :return: bool

        """
        return self.properties

    # ----------------------------------------------------------------------
    def update(
        self, read_only: bool, description: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Updates the site's mode to set it in read only

        ==================     ====================================================================
        **Argument**           **Description**
        ------------------     --------------------------------------------------------------------
        read_only              Required Boolean.  If True, the organization will be in read only mode.  False it is in write mode.
        ------------------     --------------------------------------------------------------------
        description            Optional String. The description of the action.
        ==================     ====================================================================

        :return: Boolean. True if successful else False.


        """
        url = f"{self._url}/update"
        params = {"isReadOnly": read_only}
        if description:

            params["message"] = description
        res = self._con.post(path=url, params=params)
        if "success" in res:
            return res["success"]
        return res
