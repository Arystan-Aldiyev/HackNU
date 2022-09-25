import json
from arcgis.gis import Layer, _GISResource, Item, GIS
from arcgis.auth.tools import LazyLoader

_services = LazyLoader("arcgis.gis.server.admin._services")


class SceneLayerManager(_GISResource):
    """
    The ``SceneLayerManager`` class allows administration (if access permits) of ArcGIS Online hosted scene layers.
    A :class:`~arcgis.mapping.SceneLayerManager` offers access to map and layer content.
    """

    def __init__(self, url, gis=None, scene_lyr=None):
        if url.split("/")[-1].isdigit():
            url = url.replace(f"/{url.split('/')[-1]}", "")
        super(SceneLayerManager, self).__init__(url, gis)
        self._sl = scene_lyr

    # ----------------------------------------------------------------------
    def refresh(self, service_definition=True):
        """
        The ``refresh`` operation refreshes a service, which clears the web
        server cache for the service.
        """
        url = self._url + "SceneServer/refresh"
        params = {"f": "json", "serviceDefinition": service_definition}

        res = self._con.post(url, params)

        super(SceneLayerManager, self)._refresh()

        self._ms._refresh()

        return res

    # ----------------------------------------------------------------------
    def swap(self, target_service_name):
        """
        The swap operation replaces the current service cache with an existing one.

        .. note::
            The ``swap`` operation is for ArcGIS Online only.

        ====================        ====================================================
        **Argument**                **Description**
        --------------------        ----------------------------------------------------
        target_service_name         Required string. Name of service you want to swap with.
        ====================        ====================================================

        :returns: dictionary indicating success or error

        """
        url = self._url + "/swap"
        params = {"f": "json", "targetServiceName": target_service_name}
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def jobs(self):
        """
        The tile service job summary (jobs) resource represents a
        summary of all jobs associated with a vector tile service.
        Each job contains a jobid that corresponds to the specific
        jobid run and redirects you to the Job Statistics page.

        """
        url = self._url + "/jobs"
        params = {"f": "json"}
        return self._con.get(url, params)

    # ----------------------------------------------------------------------
    def cancel_job(self, job_id):
        """
        The ``cancel_job`` operation supports cancelling a job while update
        tiles is running from a hosted feature service. The result of this
        operation is a response indicating success or failure with error
        code and description.

        ===============     ====================================================
        **Argument**        **Description**
        ---------------     ----------------------------------------------------
        job_id               Required String. The ``job id`` to cancel.
        ===============     ====================================================

        """
        url = self._url + "/jobs/%s/cancel" % job_id
        params = {"f": "json"}
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def job_statistics(self, job_id):
        """
        Returns the job statistics for the given jobId

        """
        url = self._url + "/jobs/%s" % job_id
        params = {"f": "json"}
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def import_tiles(self, item, levels=None, extent=None, merge=False, replace=False):
        """
        The ``import_tiles`` method imports tiles from an :class:`~arcgis.gis.Item` object.

        ===============     ====================================================
        **Argument**        **Description**
        ---------------     ----------------------------------------------------
        item                Required ItemId or :class:`~arcgis.gis.Item` object. The TPK file's item id.
                            This TPK file contains to-be-extracted bundle files
                            which are then merged into an existing cache service.
        ---------------     ----------------------------------------------------
        levels              Optional String / List of integers, The level of details
                            to update. Example: "1,2,10,20" or [1,2,10,20]
        ---------------     ----------------------------------------------------
        extent              Optional String / Dict. The area to update as Xmin, YMin, XMax, YMax
                            example: "-100,-50,200,500" or
                            {'xmin':100, 'ymin':200, 'xmax':105, 'ymax':205}
        ---------------     ----------------------------------------------------
        merge               Optional Boolean. Default is false and applicable to
                            compact cache storage format. It controls whether
                            the bundle files from the TPK file are merged with
                            the one in the existing cached service. Otherwise,
                            the bundle files are overwritten.
        ---------------     ----------------------------------------------------
        replace             Optional Boolean. Default is false, applicable to
                            compact cache storage format and used when
                            merge=true. It controls whether the new tiles will
                            replace the existing ones when merging bundles.
        ===============     ====================================================

        :return:
            A dictionary

        .. code-block:: python

            # USAGE EXAMPLE

            >>> from arcgis.gis import GIS
            >>> from arcgis.mapping import SceneLayer

            # connect to your GIS and get the web map item
            >>> gis = GIS(url, username, password)
            >>> scene_item = gis.content.get('abcd_item-id')
            >>> scene_layer = SceneLayer(scene_item.sourceUrl, gis)
            >>> sl_manager = scene_layer.manager
            >>> imported_tiles = sl_manager.import_tiles(item = "<item_id>",
                                                          levels = "11-20",
                                                          extent = {"xmin":6224324.092137296,
                                                                    "ymin":487347.5253569535,
                                                                    "xmax":11473407.698535524,
                                                                    "ymax":4239488.369818687,
                                                                    "spatialReference":{"wkid":102100}
                                                                    },
                                                          merge = True,
                                                        replace = True
                                                          )
            >>> type(imported_tiles)
            <Dictionary>

        """
        params = {
            "f": "json",
            "sourceItemId": None,
            "extent": extent,
            "levels": levels,
            "mergeBundle": merge,
            "replaceTiles": replace,
        }
        if isinstance(item, str):
            params["sourceItemId"] = item
        elif isinstance(item, Item):
            params["sourceItemId"] = item.itemid
        else:
            raise ValueError("The `item` must be a string or Item")
        url = self._url + "/importTiles"
        res = self._con.post(url, params)
        return res

    # ----------------------------------------------------------------------
    def update_tiles(self, levels=None, extent=None):
        """
        The ``update_tiles`` method starts tile generation for ArcGIS Online. The levels of detail
        and the extent are needed to determine the area where tiles need
        to be rebuilt.

        .. note::
            The ``update_tiles`` operation is for ArcGIS Online only.

        ===============     ====================================================
        **Argument**        **Description**
        ---------------     ----------------------------------------------------
        levels              Optional String / List of integers, The level of details
                            to update. Example: "1,2,10,20" or [1,2,10,20]
        ---------------     ----------------------------------------------------
        extent              Optional String / Dict. The area to update as Xmin, YMin, XMax, YMax
                            example: "-100,-50,200,500" or
                            {'xmin':100, 'ymin':200, 'xmax':105, 'ymax':205}
        ===============     ====================================================

        :return:
           Dictionary. If the product is not ArcGIS Online tile service, the
           result will be None.

        .. code-block:: python

            # USAGE EXAMPLE

            >>> from arcgis.gis import GIS
            >>> from arcgis.mapping import SceneLayer

            # connect to your GIS and get the web map item
            >>> gis = GIS(url, username, password)
            >>> scene_item = gis.content.get('abcd_item-id')
            >>> scene_layer = SceneLayer(scene_item.sourceUrl, gis)
            >>> sl_manager = scene_layer.manager
            >>> update_tiles = sl_manager.update_tiles(levels = "11-20",
                                                        extent = {"xmin":6224324.092137296,
                                                                    "ymin":487347.5253569535,
                                                                    "xmax":11473407.698535524,
                                                                    "ymax":4239488.369818687,
                                                                    "spatialReference":{"wkid":102100}
                                                                    }
                                                        )
            >>> type(update_tiles)
            <Dictionary>
        """
        if self._gis._portal.is_arcgisonline:
            url = "%s/updateTiles" % self._url
            params = {"f": "json"}
            if levels:
                if isinstance(levels, list):
                    levels = ",".join(str(e) for e in levels)
                params["levels"] = levels
            if extent:
                if isinstance(extent, dict):
                    extent2 = "{},{},{},{}".format(
                        extent["xmin"], extent["ymin"], extent["xmax"], extent["ymax"]
                    )
                    extent = extent2
                params["extent"] = extent
            return self._con.post(url, params)
        return None

    # ----------------------------------------------------------------------
    @property
    def rerun_job(self, job_id, code):
        """
        The ``rerun_job`` operation supports re-running a canceled job from a
        hosted map service. The result of this operation is a response
        indicating success or failure with error code and description.

        ===============     ====================================================
        **Argument**        **Description**
        ---------------     ----------------------------------------------------
        code                required string, parameter used to re-run a given
                            jobs with a specific error
                            code: ``ALL | ERROR | CANCELED``
        ---------------     ----------------------------------------------------
        job_id              required string, job to reprocess
        ===============     ====================================================

        :return:
           A boolean or dictionary
        """
        url = self._url + "/jobs/%s/rerun" % job_id
        params = {"f": "json", "rerun": code}
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def edit_tile_service(
        self,
        service_definition=None,
        min_scale=None,
        max_scale=None,
        source_item_id=None,
        export_tiles_allowed=False,
        max_export_tile_count=100000,
    ):
        """
        The ``edit_tile_service`` operation updates a Tile Service's properties.

        =====================       ======================================================
        **Argument**                **Description**
        ---------------------       ------------------------------------------------------
        service_definition          Required String. Updates a service definition.
        ---------------------       ------------------------------------------------------
        min_scale                   Required float. Sets the services minimum scale for caching.
        ---------------------       ------------------------------------------------------
        max_scale                   Required float. Sets the services maximum scale for caching.
        ---------------------       ------------------------------------------------------
        source_item_id              Required String. The Source Item ID is the GeoWarehouse Item ID of the scene service
        ---------------------       ------------------------------------------------------
        export_tiles_allowed        Required boolean. ``exports_tiles_allowed`` sets the value to let users export tiles
        ---------------------       ------------------------------------------------------
        max_export_tile_count       Optional float. ``max_export_tile_count``sets the maximum amount of tiles to be exported from a single call.

                                    .. note::
                                        The default value is 100000.
        =====================       ======================================================

        .. code-block:: python

            # USAGE EXAMPLE

            >>> from arcgis.mapping import SceneLayerManager
            >>> from arcgis.gis import GIS

            # connect to your GIS and get the web map item
            >>> gis = GIS(url, username, password)

            >>> SceneLayerManager.edit_tile_service(service_definition = "updated service definition",
                                                        min_scale = 50,
                                                        max_scale = 100,
                                                        source_item_id = "geowarehouse_item_id",
                                                        export_tiles_allowed = True,
                                                        max_Export_Tile_Count = 10000
                                                        )
        """
        params = {
            "f": "json",
        }
        if not service_definition is None:
            params["serviceDefinition"] = service_definition
        if not min_scale is None:
            params["minScale"] = float(min_scale)
        if not max_scale is None:
            params["maxScale"] = float(max_scale)
        if not source_item_id is None:
            params["sourceItemId"] = source_item_id
        if not export_tiles_allowed is None:
            params["exportTilesAllowed"] = export_tiles_allowed
        if not max_export_tile_count is None:
            params["maxExportTileCount"] = int(max_export_tile_count)
        url = self._url + "/edit"
        return self._con.post(url, params)

    # ----------------------------------------------------------------------
    def delete_tiles(self, levels, extent=None):
        """
        The ``delete_tiles`` method deletes tiles from the current cache.

        ===============     ====================================================
        **Argument**        **Description**
        ---------------     ----------------------------------------------------
        extent              optional dictionary,  If specified, the tiles within
                            this extent will be deleted or will be deleted based
                            on the service's full extent.
        ---------------     ----------------------------------------------------
        levels              required string, The level to delete.
                            Example, 0-5,10,11-20 or 1,2,3 or 0-5
        ===============     ====================================================

        :return:
           A dictionary

        .. code-block:: python

            # USAGE EXAMPLE

            >>> from arcgis.mapping import SceneLayerManager
            >>> from arcgis.gis import GIS

            # connect to your GIS and get the web map item
            >>> gis = GIS(url, username, password)

            >>> deleted_tiles = SceneLayerManager.delete_tiles(levels = "11-20",
                                                  extent = {"xmin":6224324.092137296,
                                                            "ymin":487347.5253569535,
                                                            "xmax":11473407.698535524,
                                                            "ymax":4239488.369818687,
                                                            "spatialReference":{"wkid":102100}
                                                            }
                                                  )
            >>> type(deleted_tiles)
            <Dictionary>
        """
        params = {
            "f": "json",
            "levels": levels,
        }
        if extent:
            params["extent"] = extent
        url = self._url + "/deleteTiles"
        return self._con.post(url, params)


###########################################################################
class EnterpriseSceneLayerManager(_GISResource):
    """
    The ``EnterpriseSceneLayerManager`` class allows administration (if access permits) of ArcGIS Enterprise hosted scene layers.
    A :class:`~arcgis.mapping.SceneLayer` offers access to layer content.

    ..note:: Url must be admin url such as: https://services.myserver.com/arcgis/rest/admin/services/serviceName/SceneServer/
    """

    def __init__(self, url, gis=None, scene_lyr=None):
        if url.split("/")[-1].isdigit():
            url = url.replace(f"/{url.split('/')[-1]}", "")
        super(SceneLayerManager, self).__init__(url, gis)
        self._sl = scene_lyr

    # ----------------------------------------------------------------------
    def edit(self, service_dictionairy):
        """
        To edit a service, you need to submit the complete JSON
        representation of the service, which includes the updates to the
        service properties. Editing a service causes the service to be
        restarted with updated properties.

        ===================     ====================================================================
        **Argument**            **Description**
        -------------------     --------------------------------------------------------------------
        service_dictionairy     Required dict. The service JSON as a dictionary.
        ===================     ====================================================================


        :return: boolean
        """
        sl_service = _services.Service(self.url, self._gis)
        return sl_service.edit(service_dictionairy)

    # ----------------------------------------------------------------------
    def start(self):
        """starts the specific service"""
        sl_service = _services.Service(self.url, self._gis)
        return sl_service.start()

    # ----------------------------------------------------------------------
    def stop(self):
        """stops the specific service"""
        sl_service = _services.Service(self.url, self._gis)
        return sl_service.stop()

    # ----------------------------------------------------------------------
    def change_provider(self, provider: str):
        """
        Allows for the switching of the service provide and how it is hosted on the ArcGIS Server instance.

        Values:

           + 'ArcObjects' means the service is running under the ArcMap runtime i.e. published from ArcMap
           + 'ArcObjects11': means the service is running under the ArcGIS Pro runtime i.e. published from ArcGIS Pro
           + 'DMaps': means the service is running in the shared instance pool (and thus running under the ArcGIS Pro provider runtime)

        :return: Boolean

        """
        sl_service = _services.Service(self.url, self._gis)
        return sl_service.change_provider(provider)

    # ----------------------------------------------------------------------
    def delete(self):
        """deletes a service from arcgis server"""
        sl_service = _services.Service(self.url, self._gis)
        return sl_service.delete()


###########################################################################
class Object3DLayer(Layer):
    """
    The ``Object3DLayer`` rresents a Web scene 3D Object layer.

    .. note::
        Web scene layers are cached web layers that are optimized for displaying a large amount of 2D and 3D features.
        See the :class:`~arcgis.mapping.SceneLayer` class for more information.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.Point3DLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __init__(self, url, gis=None):
        """
        Constructs a SceneLayer given a web scene layer URL
        """
        super(Object3DLayer, self).__init__(url, gis)
        self._admin = None

    @property
    def _lyr_dict(self):
        url = self.url

        lyr_dict = {"type": "SceneLayer", "url": url}
        if self._token is not None:
            lyr_dict["serviceToken"] = self._token

        if self.filter is not None:
            lyr_dict["filter"] = self.filter
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def _lyr_json(self):
        url = self.url
        if self._token is not None:  # causing geoanalytics Invalid URL error
            url += "?token=" + self._token

        lyr_dict = {"type": "SceneLayer", "url": url}

        if self.filter is not None:
            lyr_dict["options"] = json.dumps({"definition_expression": self.filter})
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def manager(self):
        if self._admin is None:
            """
            The ``manager`` property returns an instance of :class:`~arcgis.mapping.SceneLayerManager` class
            or :class:`~arcgis.mapping.EnterpriseSceneLayerManager` class
            which provides methods and properties for administering this service.
            """
            if self._gis._portal.is_arcgisonline:
                rd = {"/rest/services/": "/rest/admin/services/"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = SceneLayerManager(adminURL, self._gis, self)
            else:
                rd = {"/rest/": "/admin/", "/SceneServer": ".SceneServer"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = EnterpriseSceneLayerManager(adminURL, self._gis, self)
        return self._admin

    # ----------------------------------------------------------------------
    def _str_replace(self, mystring, rd):
        """Replaces a value based on a key/value pair where the
        key is the text to replace and the value is the new value.

        The find/replace is case insensitive.

        """
        import re

        patternDict = {}
        for key, value in rd.items():
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            patternDict[value] = pattern
        for key in patternDict:
            regex_obj = patternDict[key]
            mystring = regex_obj.sub(key, mystring)
        return mystring


###########################################################################
class IntegratedMeshLayer(Layer):
    """
    The ``IntegratedMeshLayer`` class represents a Web scene Integrated Mesh layer.

    .. note::
        Web scene layers are cached web layers that are optimized for displaying a large amount of 2D and 3D features.
        See the :class:`~arcgis.mapping.SceneLayer` class for more information.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.Point3DLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __init__(self, url, gis=None):
        """
        Constructs a SceneLayer given a web scene layer URL
        """
        super(IntegratedMeshLayer, self).__init__(url, gis)
        self._admin = None

    @property
    def _lyr_dict(self):
        url = self.url

        lyr_dict = {"type": "IntegratedMeshLayer", "url": url}
        if self._token is not None:
            lyr_dict["serviceToken"] = self._token

        if self.filter is not None:
            lyr_dict["filter"] = self.filter
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def _lyr_json(self):
        url = self.url
        if self._token is not None:  # causing geoanalytics Invalid URL error
            url += "?token=" + self._token

        lyr_dict = {"type": "IntegratedMeshLayer", "url": url}

        if self.filter is not None:
            lyr_dict["options"] = json.dumps({"definition_expression": self.filter})
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def manager(self):
        if self._admin is None:
            """
            The ``manager`` property returns an instance of :class:`~arcgis.mapping.SceneLayerManager` class
            or :class:`~arcgis.mapping.EnterpriseSceneLayerManager` class
            which provides methods and properties for administering this service.
            """
            if self._gis._portal.is_arcgisonline:
                rd = {"/rest/services/": "/rest/admin/services/"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = SceneLayerManager(adminURL, self._gis, self)
            else:
                rd = {"/rest/": "/admin/", "/SceneServer": ".SceneServer"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = EnterpriseSceneLayerManager(adminURL, self._gis, self)
        return self._admin

    # ----------------------------------------------------------------------
    def _str_replace(self, mystring, rd):
        """Replaces a value based on a key/value pair where the
        key is the text to replace and the value is the new value.

        The find/replace is case insensitive.

        """
        import re

        patternDict = {}
        for key, value in rd.items():
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            patternDict[value] = pattern
        for key in patternDict:
            regex_obj = patternDict[key]
            mystring = regex_obj.sub(key, mystring)
        return mystring


###########################################################################
class Point3DLayer(Layer):
    """
    The ``Point3DLayer`` class represents a Web scene 3D Point layer.

    .. note::
        Web scene layers are cached web layers that are optimized for displaying a large amount of 2D and 3D features.
        See the :class:`~arcgis.mapping.SceneLayer` class for more information.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.Point3DLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __init__(self, url, gis=None):
        """
        Constructs a SceneLayer given a web scene layer URL
        """
        super(Point3DLayer, self).__init__(url, gis)
        self._admin = None

    # ----------------------------------------------------------------------
    @property
    def _lyr_dict(self):
        url = self.url

        lyr_dict = {"type": "SceneLayer", "url": url}
        if self._token is not None:
            lyr_dict["serviceToken"] = self._token

        if self.filter is not None:
            lyr_dict["filter"] = self.filter
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def _lyr_json(self):
        url = self.url
        if self._token is not None:  # causing geoanalytics Invalid URL error
            url += "?token=" + self._token

        lyr_dict = {"type": "SceneLayer", "url": url}

        if self.filter is not None:
            lyr_dict["options"] = json.dumps({"definition_expression": self.filter})
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def manager(self):
        if self._admin is None:
            """
            The ``manager`` property returns an instance of :class:`~arcgis.mapping.SceneLayerManager` class
            or :class:`~arcgis.mapping.EnterpriseSceneLayerManager` class
            which provides methods and properties for administering this service.
            """
            if self._gis._portal.is_arcgisonline:
                rd = {"/rest/services/": "/rest/admin/services/"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = SceneLayerManager(adminURL, self._gis, self)
            else:
                rd = {"/rest/": "/admin/", "/SceneServer": ".SceneServer"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = EnterpriseSceneLayerManager(adminURL, self._gis, self)
        return self._admin

    # ----------------------------------------------------------------------
    def _str_replace(self, mystring, rd):
        """Replaces a value based on a key/value pair where the
        key is the text to replace and the value is the new value.

        The find/replace is case insensitive.

        """
        import re

        patternDict = {}
        for key, value in rd.items():
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            patternDict[value] = pattern
        for key in patternDict:
            regex_obj = patternDict[key]
            mystring = regex_obj.sub(key, mystring)
        return mystring


###########################################################################
class PointCloudLayer(Layer):
    """
    The ``PointCloudLayer`` class represents a Web scene Point Cloud layer.

    .. note::
        Point Cloud layers are cached web layers that are optimized for displaying a large amount of 2D and 3D features.
        See the :class:`~arcgis.mapping.SceneLayer` class for more information.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.PointCloudLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __init__(self, url, gis=None):
        """
        Constructs a SceneLayer given a web scene layer URL
        """
        super(PointCloudLayer, self).__init__(url, gis)
        self._admin = None

    @property
    def _lyr_dict(self):
        url = self.url

        lyr_dict = {"type": "PointCloudLayer", "url": url}
        if self._token is not None:
            lyr_dict["serviceToken"] = self._token

        if self.filter is not None:
            lyr_dict["filter"] = self.filter
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def _lyr_json(self):
        url = self.url
        if self._token is not None:  # causing geoanalytics Invalid URL error
            url += "?token=" + self._token

        lyr_dict = {"type": "PointCloudLayer", "url": url}

        if self.filter is not None:
            lyr_dict["options"] = json.dumps({"definition_expression": self.filter})
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def manager(self):
        if self._admin is None:
            """
            The ``manager`` property returns an instance of :class:`~arcgis.mapping.SceneLayerManager` class
            or :class:`~arcgis.mapping.EnterpriseSceneLayerManager` class
            which provides methods and properties for administering this service.
            """
            if self._gis._portal.is_arcgisonline:
                rd = {"/rest/services/": "/rest/admin/services/"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = SceneLayerManager(adminURL, self._gis, self)
            else:
                rd = {"/rest/": "/admin/", "/SceneServer": ".SceneServer"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = EnterpriseSceneLayerManager(adminURL, self._gis, self)
        return self._admin

    # ----------------------------------------------------------------------
    def _str_replace(self, mystring, rd):
        """Replaces a value based on a key/value pair where the
        key is the text to replace and the value is the new value.

        The find/replace is case insensitive.

        """
        import re

        patternDict = {}
        for key, value in rd.items():
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            patternDict[value] = pattern
        for key in patternDict:
            regex_obj = patternDict[key]
            mystring = regex_obj.sub(key, mystring)
        return mystring


###########################################################################
class BuildingLayer(Layer):
    """
    The ``BuildingLayer`` class represents a Web building layer.

    .. note::
        Web scene layers are cached web layers that are optimized for displaying a large amount of 2D and 3D features.
        See the :class:`~arcgis.mapping.SceneLayer` class for more information.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.BuildingLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __init__(self, url, gis=None):
        """
        Constructs a SceneLayer given a web scene layer URL
        """
        super(BuildingLayer, self).__init__(url, gis)
        self._admin = None

    @property
    def _lyr_dict(self):
        url = self.url

        lyr_dict = {"type": "BuildingSceneLayer", "url": url}
        if self._token is not None:
            lyr_dict["serviceToken"] = self._token

        if self.filter is not None:
            lyr_dict["filter"] = self.filter
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def _lyr_json(self):
        url = self.url
        if self._token is not None:  # causing geoanalytics Invalid URL error
            url += "?token=" + self._token

        lyr_dict = {"type": "BuildingSceneLayer", "url": url}

        if self.filter is not None:
            lyr_dict["options"] = json.dumps({"definition_expression": self.filter})
        if self._time_filter is not None:
            lyr_dict["time"] = self._time_filter
        return lyr_dict

    # ----------------------------------------------------------------------
    @property
    def manager(self):
        if self._admin is None:
            """
            The ``manager`` property returns an instance of :class:`~arcgis.mapping.SceneLayerManager` class
            or :class:`~arcgis.mapping.EnterpriseSceneLayerManager` class
            which provides methods and properties for administering this service.
            """
            if self._gis._portal.is_arcgisonline:
                rd = {"/rest/services/": "/rest/admin/services/"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = SceneLayerManager(adminURL, self._gis, self)
            else:
                rd = {"/rest/": "/admin/", "/SceneServer": ".SceneServer"}
                adminURL = self._str_replace(self._url, rd)
                if adminURL.split("/")[-1].isdigit():
                    adminURL = adminURL.replace(f'/{adminURL.split("/")[-1]}', "")
                self._admin = EnterpriseSceneLayerManager(adminURL, self._gis, self)
        return self._admin

    # ----------------------------------------------------------------------
    def _str_replace(self, mystring, rd):
        """Replaces a value based on a key/value pair where the
        key is the text to replace and the value is the new value.

        The find/replace is case insensitive.

        """
        import re

        patternDict = {}
        for key, value in rd.items():
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            patternDict[value] = pattern
        for key in patternDict:
            regex_obj = patternDict[key]
            mystring = regex_obj.sub(key, mystring)
        return mystring


###########################################################################
class _SceneLayerFactory(type):
    """
    Factory that generates the Scene Layers

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.PointCloudLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __call__(cls, url, gis=None):
        lyr = Layer(url=url, gis=gis)
        props = lyr.properties
        if "sublayers" in props:
            return BuildingLayer(url=url, gis=gis)
        elif "layerType" in props:
            lt = props.layerType
        else:
            lt = props.layers[0].layerType
        if str(lt).lower() == "pointcloud":
            return PointCloudLayer(url=url, gis=gis)
        elif str(lt).lower() == "point":
            return Point3DLayer(url=url, gis=gis)
        elif str(lt).lower() == "3dobject":
            return Object3DLayer(url=url, gis=gis)
        elif str(lt).lower() == "building":
            return BuildingLayer(url=url, gis=gis)
        elif str(lt).lower() == "IntegratedMesh".lower():
            return IntegratedMeshLayer(url=url, gis=gis)
        return lyr


###########################################################################
class SceneLayer(Layer, metaclass=_SceneLayerFactory):
    """
    The ``SceneLayer`` class represents a Web scene layer.

    .. note::
        Web scene layers are cached web layers that are optimized for displaying a large amount of 2D and 3D features.

    .. note::
        Web scene layers can be used to represent 3D points, point clouds, 3D objects and
        integrated mesh layers.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    url                    Required string, specify the url ending in /SceneServer/
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS object. If not specified, the active GIS connection is
                           used.
    ==================     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE 1: Instantiating a SceneLayer object

        from arcgis.mapping import SceneLayer
        s_layer = SceneLayer(url='https://your_portal.com/arcgis/rest/services/service_name/SceneServer/')

        type(s_layer)
        >> arcgis.mapping._types.PointCloudLayer

        print(s_layer.properties.layers[0].name)
        >> 'your layer name'
    """

    def __init__(self, url, gis=None):
        """
        Constructs a SceneLayer given a web scene layer URL
        """
        super(SceneLayer, self).__init__(url, gis)
