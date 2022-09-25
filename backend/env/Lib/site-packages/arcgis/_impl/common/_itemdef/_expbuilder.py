import os
import uuid
import copy
import shutil
import tempfile
from arcgis._impl.common._clone import CloneNode, _deep_get, _ItemDefinition


class _WebExperience(_ItemDefinition):
    """Clones an Web Expereince Item"""

    def __init__(
        self,
        target,
        clone_mapping,
        info,
        data=None,
        sharing=None,
        thumbnail=None,
        portal_item=None,
        folder=None,
        item_extent=None,
        search_existing=True,
        owner=None,
        **kwargs,
    ):
        super().__init__(target, clone_mapping, search_existing)
        self.info = info
        self._preserve_item_id = kwargs.pop("preserve_item_id", False)
        self._data = data
        self.sharing = sharing
        if not self.sharing:
            self.sharing = {"access": "private", "groups": []}
        self.thumbnail = thumbnail
        self._item_property_names = [
            "title",
            "type",
            "description",
            "snippet",
            "tags",
            "culture",
            "accessInformation",
            "licenseInfo",
            "typeKeywords",
            "extent",
            "url",
            "properties",
        ]
        self.portal_item = portal_item
        self.folder = folder
        self.owner = owner
        self.item_extent = item_extent
        self.created_items = []

    def _add_new_item(self, item_properties, data=None):
        """Add the new item to the portal"""
        thumbnail = self.thumbnail
        if not thumbnail and self.portal_item:
            temp_dir = os.path.join(self._temp_dir.name, self.info["id"])
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            thumbnail = self.portal_item.download_thumbnail(temp_dir)
        item_id = None
        if self._preserve_item_id and self.target._portal.is_arcgisonline == False:
            item_id = self.portal_item.itemid
        item_properties["text"] = data
        new_item = self.target.content.add(
            item_properties=item_properties,
            thumbnail=thumbnail,
            folder=self.folder,
            owner=self.owner,
            item_id=item_id,
        )
        self.created_items.append(new_item)
        self._clone_resources(new_item)
        return new_item
