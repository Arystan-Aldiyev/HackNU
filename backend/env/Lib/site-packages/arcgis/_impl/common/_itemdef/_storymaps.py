import os
import uuid
import copy
import shutil
import tempfile
from arcgis._impl.common._clone import CloneNode, _deep_get
from arcgis._impl.common._clone import (
    _search_org_for_existing_item,
    _share_item_with_groups,
)

try:
    import ujson as json
except ImportError:
    import json


class _StoryMapDefinition(CloneNode):
    """
    Represents the definition of a quick capture project within ArcGIS Online or Portal.
    """

    def __init__(
        self,
        target,
        info,
        data,
        sharing=None,
        thumbnail=None,
        portal_item=None,
        folder=None,
        item_extent=None,
        search_existing=True,
        owner=None,
        **kwargs,
    ):
        clone_mapping = kwargs.get("clone_mapping")
        super().__init__(target, clone_mapping, search_existing)
        self._preserve_item_id = kwargs.pop("preserve_item_id", False)
        self.info = info
        self._data = data
        self.resolved = False
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
        self.resources = kwargs.pop("resources", None)
        self._clone_mapping = clone_mapping
        self.clone_mapping = self._clone_mapping

    @property
    def data(self):
        """Gets the data of the item"""
        return copy.deepcopy(self._data)

    def _add_new_item(self, item_properties, data=None):
        """Add the new item to the portal"""
        thumbnail = self.thumbnail
        if not thumbnail and self.portal_item:
            temp_dir = os.path.join(self._temp_dir.name, self.info["id"])
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            thumbnail = self.portal_item.download_thumbnail(temp_dir)
        item_id = None
        if self._preserve_item_id and self.target._portal.is_arcgisonline:
            item_id = self.portal_item.itemid

        new_item = self.target.content.add(
            item_properties=item_properties,
            data=data,
            thumbnail=thumbnail,
            folder=self.folder,
            owner=self.owner,
            item_id=item_id,
        )
        if self.portal_item.url:
            if self.target._portal.is_arcgisonline:
                url = f"https://storymaps.arcgis.com/stories/{new_item.id}"
            else:
                url = f"{self.target._portal.url}/apps/storymaps/stories/{new_item.id}"
            new_item.update({"url": url})

        self.created_items.append(new_item)
        self._clone_resources(new_item)
        return new_item

    def _clone_resources(self, new_item):
        """Add the resources to the new item"""
        if self.portal_item:
            resources = self.portal_item.resources
            resource_list = resources.list()
            if len(resource_list) > 0:
                resources_dir = os.path.join(
                    self._temp_dir.name, self.info["id"], "resources"
                )
                if not os.path.exists(resources_dir):
                    os.makedirs(resources_dir)
                for resource in resource_list:
                    resource_name = resource["resource"]
                    folder_name = None
                    if len(resource_name.split("/")) == 2:
                        folder_name, resource_name = resource_name.split("/")
                    elif len(resource_name.split("/")) > 2:
                        folder_name = os.path.dirname(resource_name)
                        resource_name = os.path.basename(resource_name)
                    resource_path = resources.get(
                        resource["resource"], False, resources_dir, resource_name
                    )
                    new_item.resources.add(resource_path, folder_name, resource_name)

    def _get_item_properties(self, item_extent=None):
        """Get a dictionary of item properties used in create and update operations."""

        item_properties = {}
        for property_name in self._item_property_names:
            if property_name in self.info and self.info[property_name] is not None:
                item_properties[property_name] = self.info[property_name]

        type_keywords = item_properties["typeKeywords"]
        for keyword in list(type_keywords):
            if keyword.startswith("source-"):
                type_keywords.remove(keyword)

        tags = item_properties["tags"]
        type_keywords.append("source-{0}".format(self.info["id"]))
        item_properties["typeKeywords"] = ",".join(item_properties["typeKeywords"])
        item_properties["tags"] = ",".join(tags)

        item_properties.pop("url", None)
        extent = _deep_get(item_properties, "extent")
        if item_extent is not None and extent is not None and len(extent) > 0:
            item_properties["extent"] = "{0}, {1}, {2}, {3}".format(
                item_extent.xmin, item_extent.ymin, item_extent.xmax, item_extent.ymax
            )

        return item_properties

    def _get_item_data(self):
        temp_dir = os.path.join(self._temp_dir.name, self.info["id"])
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        data = self.data
        if not data and self.portal_item:
            data = self.portal_item.download(temp_dir)

        # The item's name will default to the name of the data, if it already exists in the folder we need to rename it to something unique
        name = os.path.basename(data)
        item = next(
            (
                item
                for item in self.target.users.get(self.owner).items(folder=self.folder)
                if item["name"] == name
            ),
            None,
        )
        if item:
            new_name = "{0}_{1}{2}".format(
                os.path.splitext(name)[0],
                str(uuid.uuid4()).replace("-", ""),
                os.path.splitext(name)[1],
            )
            new_path = os.path.join(temp_dir, new_name)
            os.rename(data, new_path)
            data = new_path

        return data

    def clone(self):
        """
        Clone the StoryMap v2.0 Item in the target organization.
        """
        new_item = None
        original_item = self.info
        if self._search_existing:
            new_item = _search_org_for_existing_item(self.target, self.portal_item)
        if not new_item:
            # Get the item properties from the original item to be applied when the new item is created
            item_properties = self._get_item_properties(self.item_extent)
            data = self.data
            web_maps = set(
                [
                    v["data"]["itemId"]
                    for k, v in data["resources"].items()
                    if v["type"].lower().find("webmap") > -1
                ]
            )
            express_maps = set(
                [
                    v["data"]["itemId"]
                    for k, v in data["resources"].items()
                    if v["type"].lower().find("expressmap") > -1
                ]
            )

            webmap_mapper = {}
            for wm in web_maps:
                webmap_to_copy = self.portal_item._gis.content.get(wm)
                cloned_webmaps = self.target.content.clone_items(
                    [webmap_to_copy], search_existing_items=False
                )  # Clones the WebMap
                webmap_mapper[webmap_to_copy.id] = [
                    i.id for i in cloned_webmaps if i.type == "Web Map"
                ]
                if len(webmap_mapper[webmap_to_copy.id]) == 1:
                    webmap_mapper[webmap_to_copy.id] = webmap_mapper[webmap_to_copy.id][
                        0
                    ]

            story_map_text = json.dumps(data)
            for k, v in webmap_mapper.items():
                story_map_text = story_map_text.replace(k, v)  # replace the IDs

            if story_map_text:
                item_properties["text"] = story_map_text
            # Add the new item
            new_item = self._add_new_item(item_properties)
            if self.resources:
                new_item.resources.add(self.resources, archive=True)
            new_item.update(
                {"url": new_item.url.replace(self.portal_item.id, new_item.id)}
            )
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", dir=tempfile.gettempdir(), delete=False
            ) as jsonfile:
                jsonfile.write(story_map_text)
                new_item.resources.add(file=jsonfile.name)
                type_keywords = [
                    tk for tk in new_item.typeKeywords if "smdraftresourceid:" not in tk
                ]
                type_keywords.append(
                    f"smdraftresourceid:{os.path.basename(jsonfile.name)}"
                )
                new_item.update({"typeKeywords": type_keywords})
            # express maps
            if len(express_maps) > 0:
                with tempfile.TemporaryDirectory() as d:
                    shutil.unpack_archive(filename=self.resources, extract_dir=d)
                    for expmap in express_maps:
                        express_draft = os.path.join(d, "draft_" + expmap)
                        express_pub = os.path.join(d, "pub_" + expmap)
                        if os.path.isfile(express_pub):
                            shutil.copy(express_pub, express_draft)
                            new_item.resources.add(express_draft)
            _share_item_with_groups(
                new_item, self.sharing, self._clone_mapping["Group IDs"]
            )

        self.resolved = True
        self._clone_mapping["Item IDs"][original_item["id"]] = new_item["id"]
        return new_item
