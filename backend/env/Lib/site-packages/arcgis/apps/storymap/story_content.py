from __future__ import annotations
from enum import Enum
from typing import Optional, Union
import uuid
from arcgis.auth.tools import LazyLoader

arcgis = LazyLoader("arcgis")
urllib3 = LazyLoader("urllib3")
requests = LazyLoader("requests")
mimetypes = LazyLoader("mimetypes")
os = LazyLoader("os")
_Image = LazyLoader("PIL.Image")
_io = LazyLoader("io")
_parse = LazyLoader("urllib.parse")


class TextStyles(Enum):
    """
    Represents the Supported Text Styles Type Enumerations.
    Example: Text(text="foo", style=TextStyles.HEADING)
    """

    PARAGRAPH = "paragraph"
    LARGEPARAGRAPH = "large-paragraph"
    BULLETLIST = "bullet-list"
    NUMBERLIST = "numbered-list"
    HEADING = "h2"
    SUBHEADING = "h3"
    QUOTE = "quote"


###############################################################################################################
class Image(object):
    """
    Class representing an ``image`` from a url or file.

    .. warning::
        Image must be smaller than 10 MB to avoid having issues when saving or publishing.

    ==================      ====================================================================
    **Argument**            **Description**
    ------------------      --------------------------------------------------------------------
    path                    Required String. The file path to the image that will be added.
    ==================      ====================================================================
    """

    def __init__(self, path: Optional[str] = None, **kwargs):
        self._story = kwargs.pop("story", None)
        self._type = "image"
        # Keep track if URL since different representation style in story dictionary
        self._url = False
        self.node = kwargs.pop("node_id", None)
        # If node exists in story, then create from resources and node dictionary provided.
        # If node doesn't already exist, create a new instance.
        existing = self._check_node()
        if existing is True:
            # Get the resource node id
            self.resource_node = self._story._properties["nodes"][self.node]["data"][
                "image"
            ]
            if (
                self._story._properties["resources"][self.resource_node]["data"][
                    "provider"
                ]
                == "uri"
            ):
                # Indicate that the image comes from a url
                self._url = True
            if self._url is True:
                # Path differs whether from file path or url originally
                self._path = self._story._properties["resources"][self.resource_node][
                    "data"
                ]["src"]
            else:
                self._path = self._story._properties["resources"][self.resource_node][
                    "data"
                ]["resourceId"]
        elif existing is False:
            # Create a new instance of Image
            self._path = path
            self.node = "n-" + uuid.uuid4().hex[0:6]
            self.resource_node = "r-" + uuid.uuid4().hex[0:6]

            # Determine if url or file path
            if _parse.urlparse(self._path).scheme == "https":
                self._url = True

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties for the Image.

        :return:
            A dictionary depicting the node dictionary and resource
            dictionary for the image.
            If nothing is returned, make sure your content has been added
            to the story.
        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
                "resource_dict": self._story._properties["resources"][
                    self.resource_node
                ],
            }

    # ----------------------------------------------------------------------
    @property
    def image(self):
        """
        Get/Set the image property.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        image               String. The new image path or url for the Image.
        ==================  ========================================

        :return:
            The image that is being used.
        """
        if self._check_node() is True:
            if self._url is False:
                return self._story._properties["resources"][self.resource_node]["data"][
                    "resourceId"
                ]
            else:
                return self._story._properties["resources"][self.resource_node]["data"][
                    "src"
                ]

    # ----------------------------------------------------------------------
    @image.setter
    def image(self, path):
        if self._check_node() is True:
            self._update_image(path)
            return self.image

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the image.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Image.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if self._check_node() is True:
            if isinstance(caption, str):
                self._story._properties["nodes"][self.node]["data"]["caption"] = caption
            return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the image.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Image.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
            return self.alt_text

    # ----------------------------------------------------------------------
    @property
    def display(self):
        """
        Get/Set display for image.

        ``Values: "small" | "wide" | "full" | "float"``
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["config"]["size"]

    # ----------------------------------------------------------------------
    @display.setter
    def display(self, display):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["config"]["size"] = display
            return self.display

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful.
        """
        return self._story._delete(self.node, self.resource_node)

    # ----------------------------------------------------------------------
    def _add_image(self, caption=None, alt_text=None, display=None, story=None):
        # Assign the story
        self._story = story
        # Make an add resource call if not url
        if self._url is False:
            self._story._add_resource(self._path)

        # Create image nodes. This is similar for file path and url
        self._story._properties["nodes"][self.node] = {
            "type": "image",
            "data": {
                "image": self.resource_node,
                "caption": "" if caption is None else caption,
                "alt": "" if alt_text is None else alt_text,
            },
            "config": {"size": "" if display is None else display},
        }

        # Create resource node. Different if file path or url
        if self._url is False:
            # Get image properties and create the resourceId that corresponds to the resource added
            im = _Image.open(self._path)
            w, h = im.size
            self._story._properties["resources"][self.resource_node] = {
                "type": "image",
                "data": {
                    "resourceId": os.path.basename(os.path.normpath(self._path)),
                    "provider": "item-resource",
                    "height": h,
                    "width": w,
                },
            }
        else:
            # Get image properties and assign the image src
            data = requests.get(self._path).content
            im = _Image.open(_io.BytesIO(data))
            w, h = im.size
            self._story._properties["resources"][self.resource_node] = {
                "type": "image",
                "data": {
                    "src": self._path,
                    "provider": "uri",
                    "height": h,
                    "width": w,
                },
            }

    # ----------------------------------------------------------------------
    def _update_image(self, new_image):
        # Check if new_image is url or path
        if _parse.urlparse(new_image).scheme == "https":
            # New image is a Url
            # Update the height and width for the image
            data = requests.get(new_image).content
            im = _Image.open(_io.BytesIO(data))
            w, h = im.size
            self._story._properties["resources"][self.resource_node]["data"][
                "height"
            ] = h
            self._story._properties["resources"][self.resource_node]["data"][
                "width"
            ] = w

            # Update resource dictionary
            # Do not need to make a resource
            self._story._properties["resources"][self.resource_node]["data"][
                "src"
            ] = new_image
            # Delete if the image was previously a file path
            if (
                "resouceId"
                in self._story._properties["resources"][self.resource_node]["data"]
            ):
                del self._story._properties["resources"][self.resource_node]["data"][
                    "resourceId"
                ]
            # Update provider
            self._story._properties["resources"][self.resource_node]["data"][
                "provider"
            ] = "uri"
        else:
            # Update the height and width for the image
            im = _Image.open(new_image)
            w, h = im.size
            self._story._properties["resources"][self.resource_node]["data"][
                "height"
            ] = h
            self._story._properties["resources"][self.resource_node]["data"][
                "width"
            ] = w

            # Update resource dictionary
            resource_id = self._story._properties["resources"][self.resource_node][
                "data"
            ]["resourceId"]
            # Update where file path is held
            self._story._properties["resources"][self.resource_node]["data"][
                "resourceId"
            ] = os.path.basename(os.path.normpath(new_image))
            # Delete path if item was previously a url
            if (
                "src"
                in self._story._properties["resources"][self.resource_node]["data"]
            ):
                del self._story._properties["resources"][self.resource_node]["data"][
                    "src"
                ]
            # Update provider
            self._story._properties["resources"][self.resource_node]["data"][
                "provider"
            ] = "item-resource"
            # Update the resource by removing old and adding new
            self._story._remove_resource(resource_id)
            self._story._add_resource(new_image)
        # Set new path
        self._path = new_image

    # ----------------------------------------------------------------------
    def _check_node(self):
        # Node is not in the story if no story or node id is present
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Video(object):
    """
    Class representing a ``video`` from a url or file

    ==================      ====================================================================
    **Argument**            **Description**
    ------------------      --------------------------------------------------------------------
    path                    Required String. The file path or embed url to the video that will
                            be added.

                            .. note::
                                URL must be an embed url.
                                Example: "https://www.youtube.com/embed/G6b7Kgvd0iA"

    ==================      ====================================================================
    """

    def __init__(self, path: Optional[str] = None, **kwargs):
        # Get properties if provided
        self._story = kwargs.pop("story", None)
        self._type = "video"
        # Hold whether video is url, this will impact the dictionary structure
        self._url = False
        self.node = kwargs.pop("node_id", None)
        # Check if node already in story, else create new instance
        existing = self._check_node()
        if existing is True:
            # If node is type video then video came from file path
            if self._story._properties["nodes"][self.node]["type"] == "video":
                self.resource_node = self._story._properties["nodes"][self.node][
                    "data"
                ]["video"]
                self._path = self._story._properties["resources"][self.resource_node][
                    "data"
                ]["resourceId"]
            else:
                # Node is of embedType: video and video came from url
                self.resource_node = None
                self._path = self._story._properties["nodes"][self.node]["data"]["url"]
                self._url = True
        else:
            # Create new instance of Video
            self._path = path
            self.node = "n-" + uuid.uuid4().hex[0:6]
            if _parse.urlparse(path).scheme == "https":
                self._url = True
                self.resource_node = None
            else:
                self.resource_node = "r-" + uuid.uuid4().hex[0:6]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties for the Video.

        :return:
            A dictionary depicting the node dictionary and resource
            dictionary for the video.
            If nothing is returned, make sure the content is part of the story.

        .. note::
            To change various properties of the Video use the other property setters.
        """
        if self._check_node() is True:
            vid_dict = {
                "node_dict": self._story._properties["nodes"][self.node],
            }
            if self.resource_node:
                vid_dict["resource_dict"] = (
                    self._story._properties["resources"][self.resource_node],
                )
            return vid_dict

    # ----------------------------------------------------------------------
    @property
    def video(self):
        """
        Get/Set the video property.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        video               String. The new video path for the Video.
        ==================  ========================================

        :return:
            The video that is being used.
        """
        if self._check_node() is True:
            if self.resource_node:
                # If resouce node exists it means the video comes from a file path
                return self._story._properties["resources"][self.resource_node]["data"][
                    "resourceId"
                ]
            else:
                # No resource node means the video is of type embed and embedType: video
                return self._story._properties["nodes"][self.node]["data"]["url"]

    # ----------------------------------------------------------------------
    @video.setter
    def video(self, path):
        if self._check_node() is True:
            self._update_video(path)
            return self.video

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the video.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Video.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if self._check_node() is True:
            if isinstance(caption, str):
                self._story._properties["nodes"][self.node]["data"]["caption"] = caption
            return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the video.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Video.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
            return self.alt_text

    # ----------------------------------------------------------------------
    @property
    def display(self):
        """
        Get/Set display for the video.

        ``Values: "small" | "wide" | "full" | "float"``

        .. note::
            Cannot change display when video is created from a url
        """
        if self._check_node() is True:
            if self._url is True:
                return self._story._properties["nodes"][self.node]["data"]["display"]
            else:
                return self._story._properties["nodes"][self.node]["config"]["size"]

    # ----------------------------------------------------------------------
    @display.setter
    def display(self, display):
        if self._check_node() is True:
            if self._url is True:
                self._story._properties["nodes"][self.node]["data"]["display"] = display
        return self.display

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful
        """
        return self._story._delete(self.node, self.resource_node)

    # ----------------------------------------------------------------------
    def _add_video(
        self,
        caption=None,
        alt_text=None,
        display=None,
        story=None,
        node_id=None,
        resource_node=None,
    ):
        # Add the story to the node
        self._story = story
        if node_id:
            # If node already exists (updating node)
            self.node = node_id
        if resource_node:
            # If node already exists (updating node)
            self.resource_node = resource_node
        if self._url is False:
            # Make an add resource call since it is a file path
            self._story._add_resource(self._path)

            # Create video nodes for file path
            self._story._properties["nodes"][self.node] = {
                "type": "video",
                "data": {
                    "video": self.resource_node,
                    "caption": "" if caption is None else caption,
                    "alt": "" if alt_text is None else alt_text,
                },
                "config": {
                    "size": display,
                },
            }

            # Create resource node for file path
            self._story._properties["resources"][self.resource_node] = {
                "type": "video",
                "data": {
                    "resourceId": os.path.basename(os.path.normpath(self._path)),
                    "provider": "item-resource",
                },
            }
        else:
            # Path is a url so node will be type embed and embedType: video
            # No resource call or resource node is made
            self._story._properties["nodes"][self.node] = {
                "type": "embed",
                "data": {
                    "url": self._path,
                    "embedType": "video",
                    "caption": "" if caption is None else caption,
                    "alt": "" if alt_text is None else alt_text,
                    "display": "inline",
                    "aspectRatio": 1.778,
                    "addedAsEmbedCode": True,
                },
            }

    # ----------------------------------------------------------------------
    def _update_video(self, new_video):
        # Node structure depends if new_video is file path or url
        # Changes are made and add video call is done since easier than restructuring
        self._path = new_video
        if self.resource_node:
            # If resource node present, remove resource from item.
            resource_id = self._story._properties["resources"][self.resource_node][
                "data"
            ]["resourceId"]
            self._story._remove_resource(resource_id)
            # Remove the resource node since should not exist for url. Will be added back if file path
            del self._story._properties["resources"][self.resource_node]
        if _parse.urlparse(new_video).scheme == "https":
            # New video is a url
            self._url = True
            self.resource_node = None
            # Update the node by making add video call with correct parameters
            self._add_video(
                caption=self.caption,
                alt_text=self.alt_text,
                story=self._story,
                node_id=self.node,
            )
        else:
            # If the node was not a file path before, need to create resource id
            if self.resource_node is None:
                self.resource_node = "r-" + uuid.uuid4().hex[0:6]
            # display depends on self._url so get it before
            display = self.display
            self._url = False
            # Update the node by making add video call with correct parameters
            self._add_video(
                caption=self.caption,
                alt_text=self.alt_text,
                display=display,
                story=self._story,
                node_id=self.node,
                resource_node=self.resource_node,
            )

    # ----------------------------------------------------------------------
    def _check_node(self):
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Audio(object):
    """
    This class represents content that is of type ``audio``. It can be created from
    a file path and added to the story.

    ==================      ====================================================================
    **Argument**            **Description**
    ------------------      --------------------------------------------------------------------
    path                    Required String. The file path to the audio that will be added.
    ==================      ====================================================================

    """

    def __init__(self, path: Optional[str] = None, **kwargs):
        if _parse.urlparse(path).scheme == "https":
            # Audio cannot be added by Url at this time.
            raise ValueError(
                "To add an audio from an embedded url, use the Embed content class."
            )
        # Assing audio node properties
        self._story = kwargs.pop("story", None)
        self._type = "audio"
        self.node = kwargs.pop("node_id", None)
        # If node does not exist yet, create new instance
        existing = self._check_node()
        if existing is True:
            # Get existing resouce node
            self.resource_node = self._story._properties["nodes"][self.node]["data"][
                "audio"
            ]
            # Get existing audio path
            self._path = self._story._properties["resources"][self.resource_node][
                "data"
            ]["resourceId"]
        else:
            # Create a new instance
            self._path = path
            self.node = "n-" + uuid.uuid4().hex[0:6]
            self.resource_node = "r-" + uuid.uuid4().hex[0:6]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties for the Audio.

        :return:
            A dictionary depicting the node dictionary and resource
            dictionary for the audio.

            If nothing is returned, make sure the content is part of the story.

        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
                "resource_dict": self._story._properties["resources"][
                    self.resource_node
                ],
            }

    # ----------------------------------------------------------------------
    @property
    def audio(self):
        """
        Get/Set the audio path.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        audio               String. The new audio path for the Audio.
        ==================  ========================================

        :return:
            The audio that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["resources"][self.resource_node]["data"][
                "resourceId"
            ]

    # ----------------------------------------------------------------------
    @audio.setter
    def audio(self, path):
        if _parse.urlparse(path).scheme == "https":
            raise ValueError(
                "To add an audio from an embedded url, use the Embed content class. Update audio with file path only."
            )
        if self._check_node() is True:
            self._update_audio(path)
            return self.audio

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the audio.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Audio.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if self._check_node() is True:
            if isinstance(caption, str):
                self._story._properties["nodes"][self.node]["data"]["caption"] = caption
            return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the audio.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Audio.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
            return self.alt_text

    # ----------------------------------------------------------------------
    @property
    def display(self):
        """
        Get/Set display for audio.

            ``Values: "small" | "wide" | "float"``
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["config"]["size"]

    # ----------------------------------------------------------------------
    @display.setter
    def display(self, display):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["config"]["size"] = display
            return self.display

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful
        """
        return self._story._delete(self.node, self.resource_node)

    # ----------------------------------------------------------------------
    def _add_audio(
        self,
        caption=None,
        alt_text=None,
        display=None,
        story=None,
    ):
        self._story = story
        # Make an add resource call
        self._story._add_resource(self._path)
        # Create image nodes
        self._story._properties["nodes"][self.node] = {
            "type": "audio",
            "data": {
                "audio": self.resource_node,
                "caption": "" if caption is None else caption,
                "alt": "" if alt_text is None else alt_text,
            },
            "config": {"size": display},
        }

        # Create resource node
        self._story._properties["resources"][self.resource_node] = {
            "type": "audio",
            "data": {
                "resourceId": os.path.basename(os.path.normpath(self._path)),
                "provider": "item-resource",
            },
        }

    # ----------------------------------------------------------------------
    def _update_audio(self, new_audio):
        # Assign new path
        self._path = new_audio

        # Assign new resouce id, get old one to delete resource
        resource_id = self._story._properties["resources"][self.resource_node]["data"][
            "resourceId"
        ]
        self._story._properties["resources"][self.resource_node]["data"][
            "resourceId"
        ] = os.path.basename(os.path.normpath(self._path))

        # Add new resource and remove old one
        self._story._add_resource(self._path)
        self._story._remove_resource(resource_id)

    # ----------------------------------------------------------------------
    def _check_node(self):
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Embed(object):
    """
    Class representing a ``webpage`` or ``embedded audio``.
    Embed will show as a card in the story.

    ==================      ====================================================================
    **Argument**            **Description**
    ------------------      --------------------------------------------------------------------
    path                    Required String. The url that will be added as a webpage, video, or
                            audio embed into the story.
    ==================      ====================================================================
    """

    def __init__(self, path: Optional[str] = None, **kwargs):
        self._story = kwargs.pop("story", None)
        self._type = "embed"
        self.node = kwargs.pop("node_id", None)
        # If node doesn't already exist, create new instance
        existing = self._check_node()
        if existing is True:
            # Get the link path
            self._path = self._story._properties["nodes"][self.node]["data"]["url"]
        else:
            # Create new instance, notice no resource node is needed for embed
            self._path = path
            self.node = "n-" + uuid.uuid4().hex[0:6]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties for the Embed.

        .. note::
            To change various properties of the Embed use the other property setters.

        :return:
            A dictionary depicting the node dictionary for the embed.
            If nothing is returned, make sure the content is part of the story.
        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
            }

    # ----------------------------------------------------------------------
    @property
    def link(self):
        """
        Get/Set the link property.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        link                String. The new url for the Embed.
        ==================  ========================================

        :return:
            The embed that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["url"]

    # ----------------------------------------------------------------------
    @link.setter
    def link(self, path):
        if self._check_node() is True:
            self._update_link(path)
            return self.link

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the webpage.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Embed.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if self._check_node() is True:
            if isinstance(caption, str):
                self._story._properties["nodes"][self.node]["data"]["caption"] = caption
            return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the embed.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Embed.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
            return self.alt_text

    # ----------------------------------------------------------------------
    @property
    def display(self):
        """
        Get/Set display for embed.

        ``Values: "card" | "inline"``
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["display"]

    # ----------------------------------------------------------------------
    @display.setter
    def display(self, display):
        if self._check_node():
            self._story._properties["nodes"][self.node]["data"]["display"] = display
            return self.display

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful.
        """
        return self._story._delete(self.node)

    # ----------------------------------------------------------------------
    def _add_link(self, caption=None, alt_text=None, display="card", story=None):
        self._story = story
        sections = _parse.urlparse(self._path)
        # Create embed node, no resource node needed
        self._story._properties["nodes"][self.node] = {
            "type": "embed",
            "data": {
                "url": self._path,
                "embedType": "link",
                "title": sections.netloc,
                "description": "" if caption is None else caption,
                "providerUrl": sections.netloc,
                "alt": "" if alt_text is None else alt_text,
                "display": display,
            },
        }

    # ----------------------------------------------------------------------
    def _update_link(self, new_link):
        # parse new url
        sections = _parse.urlparse(new_link)
        # set new path
        self._path = new_link
        # update dictionary properties
        self._story._properties["nodes"][self.node]["data"]["url"] = self._path
        self._story._properties["nodes"][self.node]["data"]["title"] = sections.netloc
        self._story._properties["nodes"][self.node]["data"][
            "providerUrl"
        ] = sections.netloc

    # ----------------------------------------------------------------------
    def _check_node(self):
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Map(object):
    """
    Class representing a ``webmap`` or ``webscene`` for the story

    =================       ====================================================================
    **Argument**            **Description**
    -----------------       --------------------------------------------------------------------
    item                    An Item of type :class:`~arcgis.mapping.WebMap` or
                            :class:`~arcgis.mapping.WebScene` or a String representing the item
                            id to add to the story map.
    =================       ====================================================================
    """

    def __init__(self, item: Optional[arcgis.gis.Item] = None, **kwargs):
        self._story = kwargs.pop("story", None)
        self.node = kwargs.pop("node_id", None)
        # Check if node exists else create new instance
        existing = self._check_node()
        if existing:
            # Gather all exisiting properties needed
            self.resource_node = self._story._properties["nodes"][self.node]["data"][
                "map"
            ]
            # The item id is in the resource node
            self._path = self.resource_node[2::]
            self._map_layers = self._story._properties["resources"][self.resource_node][
                "data"
            ]["mapLayers"]
            self._extent = self._story._properties["resources"][self.resource_node][
                "data"
            ]["extent"]
            self._center = self._story._properties["resources"][self.resource_node][
                "data"
            ]["center"]
            self._viewpoint = self._story._properties["resources"][self.resource_node][
                "data"
            ]["viewpoint"]
            self._zoom = self._story._properties["resources"][self.resource_node][
                "data"
            ]["zoom"]
            self._type = self._story._properties["resources"][self.resource_node][
                "data"
            ]["itemType"]
            if self._type == "Web Scene":
                self._lighting_date = self._story._properties["resources"][
                    self.resource_node
                ]["data"]["lightingDate"]
        else:
            # Create new instance
            if isinstance(item, str):
                # If string id get the item
                item = arcgis.env.active_gis.content.get(item)
            # Create map object to extract properties
            if isinstance(item, arcgis.gis.Item):
                if item.type == "Web Map":
                    map_item = arcgis.mapping.WebMap(item)
                elif item.type == "Web Scene":
                    map_item = arcgis.mapping.WebScene(item)
                else:
                    raise ValueError("Item must be of Type Web Map or Web Scene")
            # Assign properties
            self.node = "n-" + uuid.uuid4().hex[0:6]
            self.resource_node = "r-" + item.id
            self._path = item
            self._type = item.type
            if item.type == "Web Map":
                self._center = map_item._mapview.center
                self._extent = map_item._mapview.extent
                self._zoom = map_item._mapview.zoom if map_item.zoom is not False else 2
                self._viewpoint = {}

                layers = []
                # Create layer dictionary:
                for layer in map_item.layers:
                    layer_props = {}
                    layer_props["id"] = layer["id"]
                    layer_props["title"] = layer["title"]
                    if "visibility" in layer:
                        layer_props["visible"] = layer["visibility"]
                    elif "layer_visibility" in map_item:
                        layer_props["visible"] = map_item["layer_visibility"]
                    layers.append(layer_props)
                self._map_layers = layers
            # Add properties for Web Scene
            elif item.type == "Web Scene":
                layers = []
                # Create layer dictionary:
                for layer in map_item["operationalLayers"]:
                    layer_props = {}
                    layer_props["id"] = layer["id"]
                    layer_props["title"] = layer["title"]
                    if "visibility" in layer:
                        layer_props["visible"] = layer["visibility"]
                    else:
                        layer_props["visible"] = False
                    layers.append(layer_props)
                self._map_layers = layers
                # Create the Map View to use
                view = arcgis.widgets.MapView(
                    arcgis.env.active_gis, map_item, mode="3D"
                )
                self._center = view.center
                self._extent = view.extent
                self._zoom = view.zoom if view.zoom > -1 else 2
                self._viewpoint = {}
                self._camera = map_item["initialState"]["viewpoint"]
                self._lighting_date = map_item["initialState"]["environment"][
                    "lighting"
                ]["datetime"]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties for the Map.

        :return:
            A dictionary depicting the node dictionary and resource
            dictionary for the map.
            If nothing it returned, make sure the content is part of the story.

        .. note::
            To change various properties of the Map use the other property setters.
        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
                "resource_dict": self._story._properties["resources"][
                    self.resource_node
                ],
            }

    # ----------------------------------------------------------------------
    @property
    def map(self):
        """
        Get/Set the map property.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        map                 One of three choices:

                            * String being an item id for an Item of type
                            :class:`~arcgis.mapping.WebMap`
                            or :class:`~arcgis.mapping.WebScene`.

                            * An :class:`~arcgis.gis.Item` of type
                            :class:`~arcgis.mapping.WebMap`
                            or :class:`~arcgis.mapping.WebScene`.
        ==================  ========================================

        .. note::
            Only replace Map with a new map of same type.

        :return:
            The item id for the map that is being used.
        """
        if self._check_node() is True:
            map_id = self._story._properties["resources"][self.resource_node]["data"][
                "itemId"
            ]
            return self._story._gis.content.get(map_id)

    # ----------------------------------------------------------------------
    @map.setter
    def map(self, map):
        if self._check_node() is True:
            self._update_map(map)
            return self.map

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the map.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Map.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if self._check_node() is True:
            if isinstance(caption, str):
                self._story._properties["nodes"][self.node]["data"]["caption"] = caption
            return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the map.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Map.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
            return self.alt_text

    # ----------------------------------------------------------------------
    @property
    def display(self):
        """
        Get/Set the display type of the map.

        ``Values: "standard" | "wide" | "full" | "float"``
        """
        if self._check_node() is True:
            if "config" in self._story._properties["nodes"][self.node]:
                return self._story._properties["nodes"][self.node]["config"]["size"]
            else:
                return None

    # ----------------------------------------------------------------------
    @display.setter
    def display(self, display):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["config"]["size"] = display
            return self.display

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node
        """
        return self._story._delete(self.node, self.resource_node)

    # ----------------------------------------------------------------------
    def _add_map(self, caption=None, alt_text=None, display=None, story=None):
        self._story = story

        # Create webmap nodes
        # This represents the map as seen in the story
        self._story._properties["nodes"][self.node] = {
            "type": "webmap",
            "data": {
                "map": self.resource_node,
                "caption": "" if caption is None else caption,
                "alt": "" if alt_text is None else alt_text,
                "extent": self._extent,
                "center": self._center,
                "zoom": 2,
                "viewpoint": self._viewpoint,
            },
            "config": {"size": display},
        }
        # Create resource node
        # This represents the original map item and it's properties
        self._story._properties["resources"][self.resource_node] = {
            "type": "webmap",
            "data": {
                "extent": self._extent,
                "center": self._center,
                "zoom": 2,
                "mapLayers": self._map_layers,
                "viewpoint": self._viewpoint,
                "itemId": self._path.id,
                "itemType": self._type,
                "type": "default",
            },
        }

        # Add for Web Scene
        if self._type == "Web Scene":
            self._story._properties["resources"][self.resource_node]["data"][
                "lightingDate"
            ] = self._lighting_date
            self._story._properties["resources"][self.resource_node]["data"][
                "camera"
            ] = self._camera
            self._story._properties["nodes"][self.node]["data"][
                "lightingDate"
            ] = self._lighting_date
            self._story._properties["nodes"][self.node]["data"]["camera"] = self._camera

    # ----------------------------------------------------------------------
    def _update_map(self, map):
        new_map = Map(map)
        # Check for error.
        if (
            new_map._type
            != self._story._properties["resources"][self.resource_node]["data"][
                "itemType"
            ]
        ):
            raise ValueError("New Map must be of same type as the exisiting map.")

        # Get all the old properties but update with new map
        self._story._properties["resources"][
            new_map.resource_node
        ] = self._story._properties["resources"].pop(self.resource_node)
        self.resource_node = new_map.resource_node
        self._story._properties["resources"][new_map.resource_node]["data"][
            "itemId"
        ] = new_map._path.id
        # Update path to resource node
        self._story._properties["nodes"][self.node]["data"][
            "map"
        ] = new_map.resource_node

        # Add for Web Scene
        if self._type == "Web Scene":
            self._story._properties["resources"][self.resource_node]["data"][
                "lightingDate"
            ] = new_map._lighting_date
            self._story._properties["resources"][self.resource_node]["data"][
                "camera"
            ] = new_map._camera
            self._story._properties["nodes"][self.node]["data"][
                "lightingDate"
            ] = new_map._lighting_date
            self._story._properties["nodes"][self.node]["data"][
                "camera"
            ] = new_map._camera

    # ----------------------------------------------------------------------
    def _check_node(self):
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Text(object):
    """
    Class representing a ``text`` and a style of text.

    ==================      ====================================================================
    **Argument**            **Description**
    ------------------      --------------------------------------------------------------------
    text                    Required String. The text that will be shown in the story.


                                Example:
                                "Paragraph with <strong>bold</strong>,
                                <em>italic</em> and
                                <a href=\"https://www.google.com\" rel=\"noopener noreferrer\"
                                target=\"_blank\">hyperlink</a> and a
                                <span class=\"sm-text-color-080\">custom color</span>"
    ------------------      --------------------------------------------------------------------
    style                   Optional TextStyles type. There are 7 different styles of text that can be
                            added to a story.

                            ``Values: PARAGRAPH | LARGEPARAGRAPH | NUMBERLIST | BULLETLIST |
                            HEADING | SUBHEADING | QUOTE``
    ------------------      --------------------------------------------------------------------
    custom_color            Optional String. The hex color value without the #.
                            Only available when type is either 'paragraph', 'bullet-list', or
                            'numbered-list'.


                            Ex: custom_color = "080"
    ==================      ====================================================================


    Properties of the different text types:

    ===================     ====================================================================
    **Type**                **Text**
    -------------------     --------------------------------------------------------------------
    paragraph               String can contain the following tags for text formatting:
                            <strong>, <em>, <a href="{link}" rel="noopener noreferer" target="_blank"
                            and a class attribute to indicate color formatting:
                            class=sm-text-color-{values} attribute in the <strong> | <em> | <a> | <span> tags

                            ``Values: themeColor1 | themeColor2 | themeColor3 | customTextColors``
    -------------------     --------------------------------------------------------------------
    large-paragraph         String can contain the following tags for text formatting:
                            <strong>, <em>, <a href="{link}" rel="noopener noreferer" target="_blank"
                            and a class attribute to indicate color formatting:
                            class=sm-text-color-{values} attribute in the <strong> | <em> | <a> | <span> tags

                            ``Values: themeColor1 | themeColor2 | themeColor3 | customTextColors``
    -------------------     --------------------------------------------------------------------
    heading                 String can only contain <em> tag
    -------------------     --------------------------------------------------------------------
    subheading              String can only contain <em> tag
    -------------------     --------------------------------------------------------------------
    bullet-list             String can contain the following tags for text formatting:
                            <strong>, <em>, <a href="{link}" rel="noopener noreferer" target="_blank"
                            and a class attribute to indicate color formatting:
                            class=sm-text-color-{values} attribute in the <strong> | <em> | <a> | <span> tags

                            ``Values: themeColor1 | themeColor2 | themeColor3 | customTextColors``
    -------------------     --------------------------------------------------------------------
    numbered-list           String can contain the following tags for text formatting:
                            <strong>, <em>, <a href="{link}" rel="noopener noreferer" target="_blank"
                            and a class attribute to indicate color formatting:
                            class=sm-text-color-{values} attribute in the <strong> | <em> | <a> | <span> tags

                            ``Values: themeColor1 | themeColor2 | themeColor3 | customTextColors``
    -------------------     --------------------------------------------------------------------
    quote                   String can only contain <strong> and <em> tags
    ===================     ====================================================================

    """

    def __init__(
        self,
        text: Optional[str] = None,
        style: TextStyles = TextStyles.PARAGRAPH,
        color: str = "000",
        **kwargs,
    ):
        self._story = kwargs.pop("story", None)
        self._type = "text"
        self.node = kwargs.pop("node_id", None)
        # Check if node exists in story else create new instance.
        existing = self._check_node()
        if existing is True:
            self._text = self._story._properties["nodes"][self.node]["data"]["text"]
            self._style = self._story._properties["nodes"][self.node]["data"]["type"]
        else:
            self.node = "n-" + uuid.uuid4().hex[0:6]
            self._text = text
            if isinstance(style, TextStyles):
                self._style = style.value

            # Color only applies certain styles
            if self._style in [
                "paragraph",
                "large-paragraph",
                "bullet-list",
                "numbered-list",
            ]:
                self._color = color
            else:
                self._color = None

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get the properties for the text.

        :return:
            The Text dictionary for the node.
            If nothing is returned, make sure the content is part of the story.
        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
            }

    # ----------------------------------------------------------------------
    @property
    def text(self):
        """
        Get/Set the text itself for the text node.

        ==================  ==================================================
        **Argument**        **Description**
        ------------------  --------------------------------------------------
        text                Optional String. The new text to be displayed.
        ==================  ==================================================

        :return:
            The text for the node.
            If nothing is returned, make sure the content is part of the story.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["text"]

    # ----------------------------------------------------------------------
    @text.setter
    def text(self, text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["text"] = text
            return self.text

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful.
        """
        return self._story._delete(self.node)

    # ----------------------------------------------------------------------
    def _add_text(self, story=None):
        self._story = story
        self._story._properties["nodes"][self.node] = {
            "type": "text",
            "data": {
                "type": self._style,
                "text": self._text,
            },
        }
        if self._color is not None:
            self._story._properties["nodes"][self.node]["data"]["customTextColors"] = [
                self._color
            ]

    # ----------------------------------------------------------------------
    def _check_node(self):
        # Check if node exists
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Button(object):
    """
    Class representing a ``button``.

    ==================      ====================================================================
    **Argument**            **Description**
    ------------------      --------------------------------------------------------------------
    link                    Required String. When user clicks on button, they will be brought to
                            the link.
    ------------------      --------------------------------------------------------------------
    text                    Required String. The text that shows on the button.
    ==================      ====================================================================

    """

    def __init__(
        self, link: Optional[str] = None, text: Optional[str] = None, **kwargs
    ):
        self._story = kwargs.pop("story", None)
        self._type = "button"
        self.node = kwargs.pop("node_id", None)
        # Check if node exists else create new instance
        existing = self._check_node()
        if existing is True:
            self._link = self._story._properties["nodes"][self.node]["data"]["link"]
            self._text = self._story._properties["nodes"][self.node]["data"]["text"]
        else:
            self.node = "n-" + uuid.uuid4().hex[0:6]
            self._link = link
            self._text = text

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get the properties for the button.

        :return:
            The Button dictionary for the node.
            If nothing is returned, make sure the content is part of the story.
        """
        if self._check_node() is True:
            return {"node_dict": self._story._properties["nodes"][self.node]}

    # ----------------------------------------------------------------------
    @property
    def text(self):
        """
        Get/Set the text for the button.

        ==================  ==================================================
        **Argument**        **Description**
        ------------------  --------------------------------------------------
        text                Optional String. The new text to be displayed.
        ==================  ==================================================

        :return:
            The text for the node.
            If nothing is returned, make sure the content is part of the story.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["text"]

    # ----------------------------------------------------------------------
    @text.setter
    def text(self, text):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["text"] = text
            return self.text

    # ----------------------------------------------------------------------
    @property
    def link(self):
        """
        Get/Set the link for the button.

        ==================  ==================================================
        **Argument**        **Description**
        ------------------  --------------------------------------------------
        link                Optional String. The new path for the button.
        ==================  ==================================================

        :return:
            The link being used.
            If nothing is returned, make sure the content is part of the story.
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["data"]["link"]

    # ----------------------------------------------------------------------
    @link.setter
    def link(self, link):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["data"]["link"] = link
            return self.link

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node
        """
        return self._story._delete(self.node)

    # ----------------------------------------------------------------------
    def _add_button(self, story):
        self._story = story
        self._story._properties["nodes"][self.node] = {
            "type": "button",
            "data": {"text": self._text, "link": self._link},
        }

    # ----------------------------------------------------------------------
    def _check_node(self):
        # Check if node exists
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Gallery(object):
    """
    Class representing an ``image gallery``

    To begin with a new gallery, simply call the class. Once added to the story,
    you can add up to 12 images.

    .. code-block:: python

        # Images to add to the gallery.
        >>> image1 = Image(<url or path>)
        >>> image2 = Image(<url or path>)
        >>> image3 = Image(<url or path>)

        # Create a gallery and add to story before adding images to it.
        >>> gallery = Gallery()
        >>> my_story.add(gallery)
        >>> gallery.add([image1, image2, image3])
    """

    def __init__(self, **kwargs):
        """ """
        self._story = kwargs.pop("story", None)
        self._type = "gallery"
        self.node = kwargs.pop("node_id", None)
        # Check if node exists, else create new empty instance
        existing = self._check_node()
        if existing is True:
            self._children = self._story._properties["nodes"][self.node]["children"]
        elif existing is False:
            # Create new empty instance
            self._children = []
            self.node = "n-" + uuid.uuid4().hex[0:6]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties of the Gallery object

        :return:
            A dictionary depicting the node in the story.
            If nothing is returned, make sure the gallery is part of the story.
        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
            }

    # ----------------------------------------------------------------------
    @property
    def images(self):
        """
        Get/Set list of image nodes in the image gallery. Setting the lists allows the images
        to be reordered.

        ==================      ====================================================================
        **Argument**            **Description**
        ------------------      --------------------------------------------------------------------
        node_list               List of node ids for the images in the gallery. Nodes must already be
                                in the gallery and this list will adjust the order of the images.

                                To add new images to the gallery use: Gallery.add_images(images)
                                To delete an image from a gallery use: Gallery.delete_image(node_id)
        ==================      ====================================================================

        :return:
            A list of node ids in order of image appearance in the gallery.
            If nothing is returned, make sure the gallery is part of the story.
        """
        if self._check_node():
            # Update incase addition or removal was made in between last check.
            self._children = self._story._properties["nodes"][self.node]["children"]
            return self._children
        else:
            raise Warning(
                "Image Gallery must be added to the story before adding Images."
            )

    # ----------------------------------------------------------------------
    @images.setter
    def images(self, node_list):
        if self._check_node():
            self._children = node_list
            self._story._properties["nodes"][self.node]["children"] = node_list
        return self.images

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the swipe.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Gallery.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if isinstance(caption, str):
            self._story._properties["nodes"][self.node]["data"]["caption"] = caption
        return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the swipe.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Gallery.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
        return self.alt_text

    # ----------------------------------------------------------------------
    @property
    def display(self):
        """
        Get/Set the display type of the Gallery.

        ``Values: "jigsaw" | "square-dynamic"``
        """
        if self._check_node() is True:
            return self._story._properties["nodes"][self.node]["config"]["size"]

    # ----------------------------------------------------------------------
    @display.setter
    def display(self, display):
        if self._check_node() is True:
            self._story._properties["nodes"][self.node]["config"]["size"] = display
            return self.display

    # ----------------------------------------------------------------------
    def add_images(self, images: list[Image]):
        """
        ==================      ====================================================================
        **Argument**            **Description**
        ------------------      --------------------------------------------------------------------
        images                  Required list of images of type Image.
        ==================      ====================================================================
        """
        if self._check_node():
            if len(self.images) == 12:
                raise Warning(
                    "Maximum amount of images permitted is 12. Use Gallery.delete(image_node) to remove images before adding."
                )
            if images is not None:
                for image in images:
                    if image.node not in self._story._properties["nodes"]:
                        image._add_image(story=self._story)
                    self._story._properties["nodes"][self.node]["children"].append(
                        image.node
                    )
        return self.images

    # ----------------------------------------------------------------------
    def delete_image(self, image: str):
        """
        ==================      ====================================================================
        **Argument**            **Description**
        ------------------      --------------------------------------------------------------------
        image                   Required String. The node id for the image to be removed from the gallery.
        ==================      ====================================================================
        """
        if image in self.images:
            # Remove from the gallery list
            self._story._properties["nodes"][self.node]["children"].remove(image)
            # Remove from the story
            if "image" in self._story._properties["nodes"][image]["data"]:
                resource_node = self._story._properties["nodes"][image]["data"]["image"]
            else:
                resource_node = None
            self._story._delete(image, resource_node)
        return self.images

    # ----------------------------------------------------------------------
    def _add_gallery(self, caption=None, alt_text=None, display=None, story=None):
        self._story = story

        # Create image nodes
        self._story._properties["nodes"][self.node] = {
            "type": "gallery",
            "data": {
                "galleryLayout": display if display is not None else "jigsaw",
                "caption": "" if caption is None else caption,
                "alt": "" if alt_text is None else alt_text,
            },
            "children": self._children,
        }

    # ----------------------------------------------------------------------
    def _check_node(self):
        if self._story is None:
            return False
        elif self.node is None:
            return False
        else:
            return True


###############################################################################################################
class Swipe(object):
    """
    Create an Swipe object from a pre-existing ``swipe`` node.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    node                Required String. The node id for the swipe type.
    ---------------     --------------------------------------------------------------------
    story               Required StoryMap that the swipe belongs to.
    ===============     ====================================================================

    .. code-block:: python

        >>> my_story.nodes #use to find swipe node id

        # Method 1: Use the Swipe Class
        >>> swipe = Swipe(my_story, <node_id>)

        # Method 2: Use the get method in story
        >>> swipe = my_story.get(node = <node_id>)

    """

    def __init__(self, story, node: str):
        # Content must already exist in story
        self.node = node
        self._story = story
        self._type = "swipe"
        self._slides = self._story._properties["nodes"][self.node]["data"]["contents"]
        # Find the type of media that the swipe supports.
        # Both contents are of the same type so only need to look at one.
        media_node = self._story._properties["nodes"][self.node]["data"]["contents"][
            "0"
        ]
        self._media_type = story._properties["nodes"][media_node]["type"]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        Get properties of the Swipe object

        :return:
            A dictionary depicting the node in the story.
        """
        if self._check_node() is True:
            return {
                "node_dict": self._story._properties["nodes"][self.node],
            }

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the swipe.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Swipe.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if isinstance(caption, str):
            self._story._properties["nodes"][self.node]["data"]["caption"] = caption
        return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the swipe.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Swipe.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
        return self.alt_text

    # ----------------------------------------------------------------------
    def edit(
        self,
        content: Optional[Union[Image, Map]] = None,
        position: str = "right",
    ):
        """
        Edit the media content of a Swipe item.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        content             Required story content of type: Image or Map.
        ---------------     --------------------------------------------------------------------
        position            Optional String. Either "right" or "left". Default is "right" so content
                            will be added to right panel.
        ===============     ====================================================================

        """
        # Media type must be same for right and left slide.
        if isinstance(content, Image) and self._media_type == "webmap":
            raise ValueError(
                "Media type is established as webmap. Can only accept another webmap."
            )
        if isinstance(content, Map) and self._media_type == "image":
            raise ValueError(
                "Media type is established as image. Can only accept another image."
            )
        if content.node not in self._story._properties["nodes"]:
            # If user has created the content but not added to the story yet.
            if isinstance(content, Image):
                content._add_image(story=self._story)
            elif isinstance(content, Map):
                content._add_map(story=self._story)
        # Add to content in position wanted
        if position == "left":
            self._story._properties["nodes"][self.node]["data"]["content"][
                "0"
            ] = content.node
        else:
            self._story._properties["nodes"][self.node]["data"]["content"][
                "1"
            ] = content.node

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful.
        """
        return self._story._delete(self.node)


###############################################################################################################
class Sidecar(object):
    """
    Create an Sidecar immersive object from a pre-existing ``immersive`` node.

    A sidecar is composed of slides. Slides are composed of two nodes: a narrative panel and a media node.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    node_id             Required String. The node id for the sidecar type.
    ---------------     --------------------------------------------------------------------
    story               Required StoryMap that the sidecar belongs to.
    ===============     ====================================================================

    .. code-block:: python

        >>> my_story.nodes #use to find sidecar node id

        # Method 1: Use the Sidecar Class
        >>> sidecar = Sidecar(my_story, <node_id>)

        # Method 2: Use the get method in story
        >>> sidecar = my_story.get(node = <node_id>)
    """

    def __init__(self, story, node: str):
        # Content must already exist in the story
        self._story = story
        self.node = node
        self._type = story._properties["nodes"][node]["data"]["type"]
        if self._type != "sidecar":
            raise Exception("This node is not of type sidecar.")
        self._subtype = story._properties["nodes"][node]["data"]["subtype"]
        self._slides = story._properties["nodes"][node]["children"]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        List all slides and their children

        :return:
            A list where the first item is the node id for the sidecar. Next
            items are dictionary of slides and their children.
        """
        sidecar_tree = [self.node]
        for slide in self._slides:
            narrative_panel = self._story._properties["nodes"][slide]["children"][0]
            text = (
                self._story._properties["nodes"][narrative_panel]["children"][0]
                if "children" in self._story._properties["nodes"][narrative_panel]
                else ""
            )
            media_item = self._story._properties["nodes"][slide]["children"][1]
            sidecar_tree.append(
                {
                    "Slide: "
                    + slide: [
                        "Narrative Panel: " + narrative_panel,
                        "Text: " + text,
                        "Media Item: " + media_item,
                    ]
                }
            )
        return sidecar_tree

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the sidecar.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Sidecar.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if isinstance(caption, str):
            self._story._properties["nodes"][self.node]["data"]["caption"] = caption
        return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the sidecar.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Sidecar.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
        return self.alt_text

    # ----------------------------------------------------------------------
    def edit(
        self,
        content: Union[Image, Video, Map, Text, Embed],
        slide_number: int,
    ):
        """
        Edit slide text or media content. Media Content can be of type Image, Video, Map, or Embed.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        content             Required content to replace current media content.
                            Item type can be Image, Video, Map, Embed or Text.
        ---------------     --------------------------------------------------------------------
        slide_number        Required Integer. The slide that will be edited. First slide is 1.
        ===============     ====================================================================
        """
        # Find children nodes
        slide = self._slides[slide_number - 1]
        slide_node = self._story._properties["nodes"][slide]
        narrative_panel = slide_node["children"][0]
        media_item = None
        if len(slide_node["children"]) == 2:
            media_item = slide_node["children"][1]

        # Check to see if content has been added to node properties
        if content.node not in self._story._properties["nodes"]:
            self._add_item_story(content)

        # Insert new content
        if isinstance(content, Text):
            # If content is text then update the narrative panel by removing old text and adding new
            old_text_node = narrative_panel["children"][0]
            self._story._properties["nodes"][narrative_panel]["children"].pop(0)
            self._story._delete(old_text_node)
            self._story._properties["nodes"][narrative_panel]["children"].insert(
                0, content.node
            )
        else:
            # Remove current media content and add new content as media
            if media_item:
                self._story._delete(media_item)
                self._story._properties["nodes"][slide]["children"].pop(1)
            self._story._properties["nodes"][slide]["children"].insert(1, content.node)

    # ----------------------------------------------------------------------
    def remove_slide(self, slide: str):
        """
        Remove a slide from the sidecar.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        slide               Required String. The node id for the slide that will be removed.
        ===============     ====================================================================
        """
        # Remove slide and all associated children.
        self._story._properties["nodes"][self.node]["children"].remove(slide)
        self._slide.remove(slide)
        self._story._delete(slide)
        self._remove_associated(slide)

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful.
        """
        return self._story._delete(self.node)

    # ----------------------------------------------------------------------
    def _remove_associated(self, slide):
        # Remove narrative panel and text associated
        narrative_panel = self._story._properties["nodes"][slide]["children"][0]
        self._story._delete(narrative_panel["children"][0])
        self._story._delete(narrative_panel)

        # Remove media item and resource node if one exists
        if len(self._story._properties["nodes"][slide]["children"]) > 1:
            media_item = self._story._properties["nodes"][slide]["children"][1]
            if "image" in self._story._properties["nodes"][media_item]["data"]:
                resource_node = self._story._properties["nodes"][media_item]["data"][
                    "image"
                ]
            elif "video" in self._story._properties["nodes"][media_item]["data"]:
                resource_node = self._story._properties["nodes"][media_item]["data"][
                    "video"
                ]
            elif self._story._properties["nodes"][media_item]["type"] == "webmap":
                resource_node = self._story._properties["nodes"][media_item]["data"][
                    "map"
                ]
            else:
                resource_node = None
            self._story._delete(media_item, resource_node)

    # ----------------------------------------------------------------------
    def _add_item_story(self, content):
        if isinstance(content, Image):
            content._add_image(story=self._story)
        elif isinstance(content, Video):
            content._add_video(story=self._story)
        elif isinstance(content, Embed):
            content._add_link(story=self._story)
        elif isinstance(content, Map):
            content._add_map(story=self._story)
        elif isinstance(content, Text):
            content._add_text(story=self._story)


###############################################################################################################
class Timeline(object):
    """
    Create an Timeline object from a pre-existing ``timeline`` node.

    A timeline is composed of events.
    Events are composed of maximum three nodes: an image, a sub-heading text, and a paragraph text.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    node_id             Required String. The node id for the timeline type.
    ---------------     --------------------------------------------------------------------
    story               Required StoryMap that the timeline belongs to.
    ===============     ====================================================================

    .. code-block:: python

        >>> my_story.nodes #use to find timeline node id

        # Method 1: Use the Timeline Class
        >>> timeline = Timeline(my_story, <node_id>)

        # Method 2: Use the get method in story
        >>> timeline = my_story.get(node = <node_id>)
    """

    def __init__(self, story, node: str):
        # Content must already exist in the story
        self._story = story
        self.node = node
        self._type = story._properties["nodes"][node]["type"]
        if self._type != "timeline":
            raise Exception("This node is not of type timeline.")
        self._subtype = story._properties["nodes"][node]["data"]["type"]
        self._events = story._properties["nodes"][node]["children"]

    # ----------------------------------------------------------------------
    @property
    def properties(self):
        """
        List all events and their children

        :return:
            A list where the first item is the node id for the timeline. Next
            items are dictionary of events and their children.
        """
        timeline = {self.node: {}}
        for event in self._events:
            timeline[self.node][event] = {}
            for child in self._story._properties["nodes"][event]["children"]:
                node_type = self._story._properties["nodes"][child]["type"]
                if node_type == "text":
                    node_type = self._story._properties["nodes"][child]["data"]["type"]
                    if node_type == "h3":
                        node_type = "subheading"
                timeline[self.node][event][node_type] = child
        return timeline

    # ----------------------------------------------------------------------
    @property
    def style(self):
        """
        Get/Set the style of the timeline

        ``Values: "waterfall" | "single-slide" | "condensed"``
        """
        return self._story._properties["nodes"][self.node]["data"]["type"]

    # ----------------------------------------------------------------------
    @style.setter
    def style(self, style):
        self._story._properties["nodes"][self.node]["data"]["type"] = style
        return self.style

    # ----------------------------------------------------------------------
    @property
    def caption(self):
        """
        Get/Set the caption property for the timeline.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        caption             String. The new caption for the Timeline.
        ==================  ========================================

        :return:
            The caption that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["caption"]

    # ----------------------------------------------------------------------
    @caption.setter
    def caption(self, caption):
        if isinstance(caption, str):
            self._story._properties["nodes"][self.node]["data"]["caption"] = caption
        return self.caption

    # ----------------------------------------------------------------------
    @property
    def alt_text(self):
        """
        Get/Set the alternte text property for the timeline.

        ==================  ========================================
        **Argument**        **Description**
        ------------------  ----------------------------------------
        alt_text            String. The new alt_text for the Timeline.
        ==================  ========================================

        :return:
            The alternate text that is being used.
        """
        return self._story._properties["nodes"][self.node]["data"]["alt"]

    # ----------------------------------------------------------------------
    @alt_text.setter
    def alt_text(self, alt_text):
        self._story._properties["nodes"][self.node]["data"]["alt"] = alt_text
        return self.alt_text

    # ----------------------------------------------------------------------
    def edit(
        self,
        content: Union[Image, Text],
        event: int,
    ):
        """
        Edit event text or image content.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        content             Required content to replace current content.
                            Item type can be Image or Text.

                            Text can only be of style TextStyles.SUBHEADING or TextStyles.PARAGRAPH
        ---------------     --------------------------------------------------------------------
        event               Required Integer. The event that will be edited. First event is 1.
        ===============     ====================================================================
        """
        # Find children nodes
        event = self._events[event - 1]

        # Get position of new item, if None: needs to be added in.
        position = self._find_position_content(content, event)

        # Check to see if content has been added to node properties
        if content.node not in self._story._properties["nodes"]:
            self._add_item_story(content)

        # Insert new content
        if isinstance(content, Text):
            # Can either be the heading or subheading of the timeline.
            # Need to either replace old or add new if not already existing.
            if position:
                old_text_node = self._story._properties["nodes"][event]["children"].pop(
                    position
                )
                self._story._delete(old_text_node)
                self._story._properties["nodes"][event]["children"].insert(
                    position, content.node
                )
            else:
                self._story._properties["nodes"][event]["children"].append(content.node)
        elif isinstance(content, Image):
            # Remove current image content and add new content if image already present
            if position:
                old_image_node = self._story._properties["nodes"][event][
                    "children"
                ].pop(position)
                if "image" in self._story._properties["nodes"][old_image_node]["data"]:
                    resource_node = self._story._properties["nodes"][old_image_node][
                        "data"
                    ]["image"]
                else:
                    resource_node = None
                self._story._delete(old_image_node, resource_node)
                self._story._properties["nodes"][event]["children"].insert(
                    position, content.node
                )
            else:
                # Image was not currently present so simply add
                self._story._properties["nodes"][event]["children"].append(content.node)

    # ----------------------------------------------------------------------
    def remove_event(self, event: str):
        """
        Remove an event from the timeline.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        event               Required String. The node id for the timeline event that will be removed.
        ===============     ====================================================================
        """
        self._story._properties["nodes"][self.node]["children"].remove(event)
        self._events.remove(event)
        self._story._delete(event)
        self._remove_associated(event)

    # ----------------------------------------------------------------------
    def delete(self):
        """
        Delete the node

        :return: True if successful.
        """
        return self._story._delete(self.node)

    # ----------------------------------------------------------------------
    def _remove_associated(self, event):
        # Remove narrative panel and text associated
        children = self._story._properties["nodes"][event]["children"]
        for child in children:
            if self._story._properties["nodes"][child]["type"] == "image":
                if "image" in self._story._properties["nodes"][child]["data"]:
                    resource_node = self._story._properties["nodes"][child]["data"][
                        "image"
                    ]
            else:
                resource_node = None
            self._story._delete(child, resource_node)
        self._story._delete(event)

    # ----------------------------------------------------------------------
    def _find_position_content(self, content, event_node):
        # Find the position in which to insert the new content
        if isinstance(content, Text):
            content_type = "text"
            subtype = content._style
        elif isinstance(content, Image):
            content_type = "image"

        # Find the position of the node that corresponds to the content being added
        # If a user does not previously have a type of content, the position is None.
        for child in self._story._properties["nodes"][event_node]["children"]:
            if (
                self._story._properties["nodes"][child]["type"] == content_type
                and content_type == "image"
            ):
                position = self._story._properties["nodes"][event_node][
                    "children"
                ].index(child)
            elif (
                self._story._properties["nodes"][child]["type"] == content_type
                and self._story._properties["nodes"][child]["data"]["type"] == subtype
            ):
                position = self._story._properties["nodes"][event_node][
                    "children"
                ].index(child)
            else:
                # Content type doesn't exist yet and will need to be added in.
                position = None
        return position

    # ----------------------------------------------------------------------
    def _add_item_story(self, content):
        if isinstance(content, Image):
            content._add_image(story=self._story)
        elif isinstance(content, Text):
            content._add_text(story=self._story)
