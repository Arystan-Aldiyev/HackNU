from arcgis.gis import Item
from arcgis._impl.common._clone import CloneNode, _ItemDefinition, _TextItemDefinition


class BaseCloneDefinition(CloneNode):
    """
    The base cloning module that allows users to extend the cloning API to
    meet there cloning workflows.
    """

    def clone(self) -> Item:
        """
        Override the clone operation in order performs the cloning logic
        """
        raise NotImplementedError("clone is not implemented")


class BaseCloneItemDefinition(_ItemDefinition):
    """
    Represents the definition of an item within ArcGIS Online or Portal.
    """

    def clone(self) -> Item:
        """
        Override the clone operation in order performs the cloning logic
        """
        raise NotImplementedError("clone is not implemented")


class BaseCloneTextItemDefinition(_TextItemDefinition):
    """
    Represents the definition of a text based item within ArcGIS Online or Portal.
    """

    def clone(self) -> Item:
        """
        Override the clone operation in order performs the cloning logic
        """
        raise NotImplementedError("clone is not implemented")
