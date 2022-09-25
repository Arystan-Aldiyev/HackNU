import collections
from functools import wraps
import re
from typing import Any, Union

from arcgis import __version__
from arcgis import env
from arcgis.features import FeatureSet, GeoAccessor, GeoSeriesAccessor
from arcgis.geometry import Geometry
from arcgis.gis import GIS
from arcgis._impl.common._deprecate import deprecated
from arcgis._impl.common._utils import _lazy_property
import pandas as pd

from . import _business_analyst
from ._business_analyst._utils import (
    local_vs_gis,
    local_business_analyst_avail,
    local_ba_data_avail,
)
from ._ge import _GeoEnrichment


def _check_active_gis(gis=None):
    """Helper function to get an active gis if no gis already declared in session."""
    # prioritize active_gis
    if gis is None and env.active_gis is not None:
        gis = env.active_gis

    return gis


def _call_method_by_source(fn) -> callable:
    """Function flow control based on gis or source - 'local' versus GIS object instance."""

    # get the method name - this will be used to redirect the function call
    fn_name = fn.__name__

    @wraps(fn)
    def wrapped(*args, **kwargs) -> Any:

        # try to pull out the source or gis caller
        src = None
        for param_src in ["source", "gis"]:
            if param_src in kwargs.keys():
                src = kwargs[param_src]
                break

        # if the source was not found in kwargs, look through the args
        if src is None:
            for p in args:
                if isinstance(p, str):
                    p = p.lower()
                    if p == "local":
                        src = p.lower()
                        break
                elif isinstance(p, GIS):
                    src = p
                    break

        # TODO: Swap the precedence of these once all methods are implemented
        # check if active gis is in session
        src = _check_active_gis(src)

        # if nothing found, interrogate the local session and see if the environment has everything for local
        if src is None and local_business_analyst_avail() and local_ba_data_avail():
            src = "local"

        # make sure a source was located or bingo out
        src_msg = (
            "The gis parameter needs to be populated with a valid GIS instance since there is not an active GIS "
            "object in the session."
        )
        assert src is not None, src_msg

        # build function name to call
        fn_nm_to_call = (
            f"_{fn_name}_gis" if isinstance(src, GIS) else f"_{fn_name}_local"
        )

        # get the function if it is implemented
        if fn_nm_to_call not in globals().keys():
            src_nm = (
                "Web GIS"
                if isinstance(src, GIS)
                else "local (ArcGIS Pro with Business Analyst)"
            )
            raise NotImplementedError(
                f"The {fn_name} function is not yet implemented with a {src_nm} source."
            )
        else:
            fn_to_call = globals()[fn_nm_to_call]

        # invoke the function and return the result
        return fn_to_call(*args, **kwargs)

    return wrapped


BufferStudyArea = collections.namedtuple(
    "BufferStudyArea", "area radii units overlap travel_mode"
)
BufferStudyArea.__new__.__defaults__ = (None, None, None, True, None)
BufferStudyArea.__doc__ = """BufferStudyArea allows you to buffer point and street address study areas.

Parameters:
area: the point geometry or street address (string) study area to be buffered
radii: list of distances by which to buffer the study area, eg. [1, 2, 3]
units: distance unit, eg. Miles, Kilometers, Minutes (when using drive times/travel_mode)
overlap: boolean, uses overlapping rings when True, or non-overlapping disks when False
travel_mode: None or string, one of the supported travel modes when using network service areas, eg. Driving, Trucking, Walking.
"""


def _pep8ify(name):
    """PEP8ify name"""
    if "." in name:
        name = name[name.rfind(".") + 1 :]
    if name[0].isdigit():
        name = "level_" + name
    name = name.replace(".", "_")
    if "_" in name:
        return name.lower()
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class NamedArea(object):
    """
    Represents named geographical places in a country. Each named area has attributes for the
    supported subgeography levels within it, and the value of those attributes are dictionaries containing the named
    places within that level of geography. This allows for interactive selection of places using intellisense and a
    notation such as the following:

    .. code-block:: python

        # Usage Example

        usa = Country.get('USA')
        usa.subgeographies.states['California'].counties['San_Bernardino_County']

    """

    def __init__(self, country, name=None, level=None, areaid="01", geometry=None):
        self._gis = country._gis
        self._country = country
        self._currlvl = level
        self._areaid = areaid
        if geometry is not None:
            self.geometry = geometry
        if name is None:
            name = country.properties.name
        self._name = name
        self._level_mappings = {}

        for childlevel in self._childlevels:
            setattr(self, childlevel, None)

    @property
    def __studyarea__(self):
        return {
            "sourceCountry": self._country.properties.iso3,
            "layer": self._currlvl,
            "ids": [self._areaid],
        }

    def __str__(self):
        return '<%s name:"%s" area_id="%s", level="%s", country="%s">' % (
            type(self).__name__,
            self._name,
            self._areaid,
            self._currlvl,
            self._country.properties.name,
        )

    def __repr__(self):
        return '<%s name:"%s" area_id="%s", level="%s", country="%s">' % (
            type(self).__name__,
            self._name,
            self._areaid,
            self._currlvl,
            self._country.properties.name,
        )

    @property
    def _childlevels(self):
        dset = [
            dset
            for dset in self._country._geog_levels
            if dset["datasetID"] == self._country.dataset
        ][0]
        whole_country_levelid = [
            lvl["id"] for lvl in dset["levels"] if lvl["isWholeCountry"]
        ][0]
        if self._currlvl is None:
            self._currlvl = whole_country_levelid

        is_whole_country = self._currlvl == whole_country_levelid

        childlevels = set()
        for branch in dset["branches"]:

            levels = branch["levels"]
            if is_whole_country and self._currlvl not in levels:
                level_attr = _pep8ify(levels[0])
                childlevels.add(level_attr)
                self._level_mappings[level_attr] = levels[0]

            elif self._currlvl in levels:
                try:
                    nextlevel = levels[levels.index(self._currlvl) + 1]
                    level_attr = _pep8ify(nextlevel)
                    childlevels.add(level_attr)
                    self._level_mappings[level_attr] = nextlevel
                except IndexError:
                    # no nextlevel
                    pass
        return childlevels

    def __getattribute__(self, name):
        if not name.startswith("_") and not name in ["geometry"]:
            val = object.__getattribute__(self, name)
            if val is None:
                # print('Fetching {}'.format(name))
                self._fetch_subgeographies(name)
            return object.__getattribute__(self, name)

        else:
            return object.__getattribute__(self, name)

    def _fetch_subgeographies(self, name):
        df = standard_geography_query(
            source_country=self._country.properties.iso3,
            layers=[self._currlvl],
            ids=[self._areaid],
            return_sub_geography=True,
            sub_geography_layer=self._level_mappings[name],
            return_geometry=True,
            as_featureset=False,
            gis=self._country._gis,
        )

        places = {}
        for index, row in df.iterrows():
            #     print(dict(row))
            plc = dict(row)
            place = NamedArea(
                country=self._country,
                name=plc["AreaName"],
                level=plc["DataLayerID"],
                areaid=plc["AreaID"],
                geometry=Geometry(plc["SHAPE"]),
            )
            place_name = plc["AreaName"].replace(" ", "_")
            if self._level_mappings[name] == "US.ZIP5":
                place_name = plc["AreaID"]
            places[place_name] = place
        setattr(self, name, places)


class Country(object):
    """
    Enables access to data and methods for a specific country. This
    class can reference country data and methods available using data accessed through
    both a Web GIS and a local installation of `ArcGIS Pro with the Business Analyst
    extension and local country data` installed. Specifying this source is accomplished
    using the ``gis`` parameter when instantiating
    (See :meth:`~arcgis.geoenrichment.Country.get`). If using the keyword ``Pro``,
    ``Country`` will try to use ArcGIS Pro with Business Analyst
    and will error if the specified country is not available locally. Available
    countries can be discovered using the :func:`~arcgis.geoenrichment.get_countries`
    function.

    .. note::
        Currently, when using a `GIS('Pro')` instance, only the ``data_collections``
        and ``enrich_variables`` properties are supported to discover available
        enrichment variables.

    """

    @classmethod
    def get(cls, name: str, gis: GIS = None, year: Union[str, int] = None):
        """
        Gets a reference to a particular country, given its name, or its
        two letter abbreviation or three letter ISO3 code.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        name              Required string. The country name, two letter code or
                          three letter ISO3 code identifying the country.
        ----------------  --------------------------------------------------------
        gis               Optional :class:`~arcgis.gis.GIS` instance. This
                          specifies what GIS country sources are available based
                          on the GIS source, a Web GIS (either `ArcGIS Online` or
                          `ArcGIS Enterprise`) or `ArcGIS Pro with the Business
                          Analyst extension and at least one country data pack`.
                          If not explicitly specified, it tries to use an active
                          GIS already created in the Python session. If an active
                          GIS is not available, it then tries to use local
                          resources, ArcGIS Pro with Business Analyst and at least
                          one country dataset installed locally. Finally, if
                          neither of these (Pro or an active GIS) are available,
                          a :class:`~arcgis.gis.GIS` object instance must be
                          explicitly provided.
        ----------------  --------------------------------------------------------
        year              Optional integer. Explicitly specifying the vintage
                          (year) of data to use. This option is only available
                          when using a `'local'` GIS source, and will be
                          ignored if used with a Web GIS source.
        ================  ========================================================

        :return:
            :class:`~arcgis.geoenrichment.Country` instance for the requested country.
        """
        return cls(name, gis, year)

    # noinspection PyMissingConstructor
    def __init__(
        self,
        iso3: str,
        gis: GIS = None,
        year: Union[str, int] = None,
        **kwargs,
    ) -> None:

        # handle the caveat of using a GIS('Pro') input
        if isinstance(gis, GIS):
            if gis._con._auth == "PRO":
                gis = "local"

        # prioritize active_gis
        gis = _check_active_gis(gis)

        # instantiate a BA object instance
        ba = _business_analyst.BusinessAnalyst(gis)

        # pull the source out of the ba object since it takes care of all defaults and validation
        self._gis = ba.source

        # stash for use later
        self._ba_cntry = ba.get_country(iso3, year=year)

        # if the source is a GIS set a few more properties
        if isinstance(self._gis, GIS):

            # get the helper services to work with
            hlp_svcs = self._gis.properties["helperServices"]

            # legacy parameter support
            if "purl" in kwargs:
                self._base_url = kwargs["purl"]

            # otherwise, get the url if available
            else:
                assert (
                    "geoenrichment" in hlp_svcs.keys()
                ), "Geoenrichment does not appear to be configured for your portal."
                self._base_url = hlp_svcs["geoenrichment"]["url"]

            # if a hosted notebook environment, get the private service url
            if gis._is_hosted_nb_home:
                res = self._gis._private_service_url(self._base_url)
                prv_url = (
                    res["privateServiceUrl"]
                    if "privateServiceUrl" in res
                    else res["serviceUrl"]
                )
                self._base_url = prv_url

            # set the dataset_id to the default
            self._dataset_id = self._ba_cntry.properties.default_dataset

    def __repr__(self):
        if self._gis == "local":
            repr = (
                f"<{type(self).__name__} - {self.properties.country_name} {self.properties.year} "
                f"({self._gis.__repr__()})>"
            )
        else:
            repr = f"<{type(self).__name__} - {self.properties.country_name} ({self._gis.__repr__()})>"
        return repr

    @property
    def properties(self):
        return self._ba_cntry.properties

    @_lazy_property
    def geometry(self):
        if isinstance(self._gis, GIS):
            lvlid = [lvl["id"] for lvl in self.levels if lvl["isWholeCountry"]][0]
            df = standard_geography_query(
                source_country=self.properties.iso2,
                layers=[lvlid],
                ids=["01"],
                return_sub_geography=False,
                return_geometry=True,
                as_featureset=False,
                gis=self._gis,
            )
            geom = Geometry(df.iloc[0]["SHAPE"])

        else:
            raise NotImplementedError(
                f"'geometry' not available using 'local' as the source."
            )

        return geom

    @_lazy_property
    def _geog_levels(self):
        """
        Returns levels of geography in this country, including branches for all datasets
        """
        params = {"f": "json"}
        url = self._base_url + "/Geoenrichment/standardgeographylevels/%s" % (
            self.properties.iso2
        )
        res = self._gis._con.post(url, params)
        return res["geographyLevels"][0]["datasets"]

    @property
    @local_vs_gis
    def levels(self):
        """
        Returns levels of geography in this country, for the current dataset
        """
        pass

    def _levels_gis(self):
        """GIS levels implementation."""
        dset = [d for d in self._geog_levels if d["datasetID"] == self._dataset_id][0]
        lvls = dset["levels"]
        return lvls

    @property
    def dataset(self):
        """
        Returns the currently used dataset for this country
        """
        if isinstance(self._gis, GIS):
            ds_id = self._dataset_id
        else:
            raise NotImplementedError(
                f"'dataset' not available using 'local' as the source."
            )
        return ds_id

    @dataset.setter
    def dataset(self, value):
        if isinstance(self._gis, GIS):
            if value in self.properties.datasets:
                self._dataset_id = value
                try:
                    delattr(self, "_lazy_subgeographies")
                    delattr(self, "_lazy__geog_levels")
                except:
                    pass
            else:
                raise ValueError(
                    "The specified dataset is not available in this country. Choose one of "
                    + str(self.properties.datasets)
                )
        else:
            raise NotImplementedError(
                f"'dataset' not available using 'local' as the source."
            )

    @_lazy_property
    @local_vs_gis
    def data_collections(self):
        """
        Returns the supported data collections and analysis variables as a Pandas dataframe.

        The dataframe is indexed by the data collection id(``dataCollectionID``) and
        contains columns for analysis variables(``analysisVariable``).
        """
        pass

    def _data_collections_gis(self):
        """GIS implementation of data_collections"""
        import pandas as pd

        df = pd.json_normalize(
            (
                _data_collections(
                    country=self.properties.iso2,
                    out_fields=[
                        "id",
                        "dataCollectionID",
                        "alias",
                        "fieldCategory",
                        "vintage",
                    ],
                )
            )["DataCollections"],
            "data",
            "dataCollectionID",
        )
        df["analysisVariable"] = df["dataCollectionID"] + "." + df["id"]
        df = df[
            [
                "dataCollectionID",
                "analysisVariable",
                "alias",
                "fieldCategory",
                "vintage",
            ]
        ]
        df.set_index("dataCollectionID", inplace=True)
        return df

    def _data_collections_local(self):
        """Local implementation for data_collections"""
        # get the variables and reorganize the dataframe to be as similar as possible to the existing online response
        col_map = {
            "data_collection": "dataCollectionID",
            "enrich_name": "analysisVariable",
        }
        dc_df = self._ba_cntry.enrich_variables.rename(columns=col_map).set_index(
            "dataCollectionID"
        )
        dc_df = dc_df[["analysisVariable", "alias"]].copy()
        return dc_df

    @property
    def enrich_variables(self):
        """
        Pandas Dataframe of available geoenrichment variables.
        """
        return self._ba_cntry.enrich_variables

    @_lazy_property
    @local_vs_gis
    def subgeographies(self):
        """
        Returns the named geographical places in this country, as NamedArea objects. Each named area has attributes for the
        supported subgeography levels within it, and the value of those attributes are dictionaries containing the named
        places within that level of geography. This allows for interactive selection of places using intellisense and a
        notation such as the following:

        .. code-block:: python

            # Usage Example 1

            usa = Country.get('USA')
            usa.subgeographies.states['California'].counties['San_Bernardino_County']

        .. code-block:: python

                # Usage Example 2

                india.named_places.states['Bihar'].districts['Aurangabad'].subdistricts['Barun']
        """
        pass

    def _subgeographies_gis(self):
        """GIS implementation of subgeographies."""
        return NamedArea(self)

    @local_vs_gis
    def search(self, query, layers=["*"]):
        """
        Searches this country for places that have the specified query string in their name.

        Returns a list of named areas matching the specified query

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        query             Required string. The query string to search for places
                          within this country.
        ----------------  --------------------------------------------------------
        levels            Optional list of layer ids. Layer ids for a country
                          can be queried using Country.levels properties.
        ================  ========================================================

        :return:
            A list of named areas that match the query string
        """

    def _search_gis(self, query, layers=["*"]):
        """GIS search implementation."""
        df = standard_geography_query(
            source_country=self.properties.iso2,
            geoquery=query,
            layers=layers,
            return_geometry=True,
            as_featureset=False,
            gis=self._gis,
        )

        places = []
        for index, row in df.iterrows():
            plc = dict(row)
            place = NamedArea(
                country=self,
                name=plc["AreaName"],
                level=plc["DataLayerID"],
                areaid=plc["AreaID"],
                geometry=plc["SHAPE"],
            )
            places.append(place)

        return places

    @_lazy_property
    @local_vs_gis
    def reports(self):
        """Returns the available reports for this country as a Pandas dataframe"""
        pass

    def _reports_gis(self):
        """GIS implementation of reports."""
        rdf = _find_report(self.properties.iso2)
        df = pd.json_normalize(rdf)
        df = df[
            ["reportID", "metadata.title", "metadata.categories", "formats"]
        ].rename(
            columns={
                "reportID": "id",
                "metadata.title": "title",
                "metadata.categories": "categories",
            }
        )
        return df


def get_countries(gis: GIS = None, as_df: bool = False):
    """
    Retrieve available countries based on the GIS source being used.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    gis                    Optional :class:`~arcgis.gis.GIS` instance. This specifies what GIS
                           country sources are available based on the Web GIS source, whether
                           it be `ArcGIS Online`, `ArcGIS Enterprise`, or `ArcGIS Pro with the
                           Business Analyst extension and at least one country data pack`. If
                           not specified, it tries to use an active GIS already created in the
                           Python session. If an active GIS is not available, it then tries to
                           use local resourcea, ArcGIS Pro with Business and at least one
                           country dataset installed locally. Finally, if neither of these
                           sources are available, a :class:`~arcgis.gis.GIS` object must be
                           explicitly provided.

    as_df                  Optional boolean, specifying if a Pandas DataFrame output is
                           desired. If ``False`` (the default), a list of
                           :class:`~arcgis.geoenrichment.Country` objects will be
                           returned. If ``True``, a Pandas DataFrame of available countries is
                           returned.
    ==================     ====================================================================

    :return:
        Available countries as a list of :class:`~arcgis.geoenrichment.Country` objects, or a
        Pandas DataFrame of available countries.
    """
    # preprocess the gis object to determine if a local (ArcGIS Pro) gis source
    if isinstance(gis, GIS):
        if gis._con._auth == "PRO":
            gis = "local"

    # prioritize active_gis
    gis = _check_active_gis(gis)

    # get the dataframe of available countries
    out_res = _business_analyst.BusinessAnalyst(gis).countries

    # if a dataframe is not desired, use the ISO3 codes to crate a list of Countries from the ISO3 codes
    if as_df is False:
        if "vintage" in out_res.columns:
            out_res = [
                Country(cntry[1][0], gis=gis, year=cntry[1][1])
                for cntry in out_res[["iso3", "vintage"]].iterrows()
            ]
        else:
            out_res = [
                Country(cntry[1], gis=gis) for cntry in out_res["iso3"].iteritems()
            ]

    return out_res


@_call_method_by_source
def create_report(
    study_areas,
    report=None,
    export_format="pdf",
    report_fields=None,
    options=None,
    return_type=None,
    use_data=None,
    in_sr=4326,
    out_name=None,
    out_folder=None,
    gis=None,
):
    """
    The Create Report method allows you to create many types of high quality reports for a
    variety of use cases describing the input area. If a point is used as a study area, the
    service will create a 1-mile ring buffer around the point to collect and append enrichment
    data. Optionally, you can create a buffer ring or drive-time service area around points of
    interest to generate PDF or Excel reports containing relevant information for the area on
    demographics, consumer spending, tapestry market, business or market potential.

    Report options are available and can be used to describe and gain a better understanding
    about the market, customers / clients and competition associated with an area of interest.


    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    study_areas            required list. Required parameter: Study areas may be defined by
                           input points, polygons, administrative boundaries or addresses.
    ------------------     --------------------------------------------------------------------
    report                 optional string. identify the id of the report. This may be one of
                           the many default reports available along with our demographic data
                           collections or a customized report. Custom report templates are
                           stored in an ArcGIS Online organization as a Report Template item.
                           The organization URL and a valid ArcGIS Online authentication token
                           is required for security purposes to access these templates. If no
                           report is specified, the default report is census profile for United
                           States and a general demographic summary report for most countries.
    ------------------     --------------------------------------------------------------------
    export_format          Optional parameter to specify the format of the generated report.
                           Supported formats include PDF and XLSX.
    ------------------     --------------------------------------------------------------------
    report_fields          Optional parameter specifies additional choices to customize
                           reports. Below is an example of the position on the report header
                           for each field.
    ------------------     --------------------------------------------------------------------
    options                Optional parameter to specify the properties for the study area
                           buffer. For a full list of valid buffer properties values and
                           further examples review the Input XY Locations' options parameter.

                           By default a 1 mile radius buffer will be applied to point(s) and
                           address locations to define a study area.
    ------------------     --------------------------------------------------------------------
    return_type            Optional parameter used for storing an output report item to Portal
                           for ArcGIS instead of returning a report to a customer via binary
                           stream. The attributes are used by Portal to determine where and how
                           an item is stored. Parameter attributes include: user, folder,
                           title, item_properties, URL, token, and referrer.
                           Example

                           Creating a new output in a Portal for ArcGIS Instance:

                           return_type = {'user' : 'testUser',
                                          'folder' : 'FolderName',
                                          'title' : 'Report Title',
                                          'item_properties' : '<properties>',
                                          'url' : 'https://hostname.domain.com/webadaptor',
                                          'token' : 'token', 'referrer' : 'referrer'}
    ------------------     --------------------------------------------------------------------
    use_data               Optional dictionary. This parameter explicitly specify the country
                           or dataset to query. When all input features specified in the
                           study_areas parameter describe locations or areas that lie in the
                           same country or dataset, this parameter can be specified to provide
                           an additional 'performance hint' to the service.

                           By default, the service will automatically determine the country or
                           dataset that is associated with each location or area submitted in
                           the study_areas parameter. Specifying a specific dataset or country
                           through this parameter will potentially improve response time.

                           By default, the data apportionment method is determined by the size
                           of the study area. Small study areas use block apportionment for
                           higher accuracy whereas large study areas (100 miles or more) will
                           use a cascading centroid apportionment method to maintain
                           performance. This default behavior can be overridden by using the
                           detailed_aggregation parameter.
    ------------------     --------------------------------------------------------------------
    in_sr                  Optional parameter to define the input geometries in the study_areas
                           parameter in a specified spatial reference system.
                           When input points are defined in the study_areas parameter, this
                           optional parameter can be specified to explicitly indicate the
                           spatial reference system of the point features. The parameter value
                           can be specified as the well-known ID describing the projected
                           coordinate system or geographic coordinate system.
                           The default is 4326
    ------------------     --------------------------------------------------------------------
    out_name               Optional string.  Name of the output file [ending in .pdf or .xlsx)
    ------------------     --------------------------------------------------------------------
    out_folder             Optional string. Name of the save folder
    ==================     ====================================================================
    """
    pass


def _create_report_gis(
    study_areas,
    report=None,
    export_format="pdf",
    report_fields=None,
    options=None,
    return_type=None,
    use_data=None,
    in_sr=4326,
    out_name=None,
    out_folder=None,
    gis=None,
):
    """GIS implementation of create report."""
    if gis is None:
        gis = env.active_gis

    areas = []
    for area in study_areas:
        area_dict = area
        if isinstance(
            area, str
        ):  # street address - {"address":{"text":"380 New York St Redlands CA 92373"}}
            area_dict = {"address": {"text": area}}
        elif isinstance(area, dict):  # pass through - user knows what they're sending
            pass
        elif isinstance(area, Geometry):  # geometry, polygons, points
            area_dict = {"geometry": dict(area)}
        elif isinstance(area, BufferStudyArea):

            # namedtuple('BufferStudyArea', 'area radii units overlap travel_mode')
            g = area.area
            if isinstance(g, str):
                area_dict = {"address": {"text": g}}
            elif isinstance(g, dict):
                area_dict = g
            elif isinstance(g, Geometry):  # geometry, polygons, points
                area_dict = {"geometry": dict(g)}
            else:
                raise ValueError(
                    "BufferStudyArea is only supported for Point geometry and addresses"
                )

            area_type = "RingBuffer"
            if area.travel_mode is None:
                if not area.overlap:
                    area_type = "RingBufferBands"
            else:
                area_type = "NetworkServiceArea"

            area_dict["areaType"] = area_type
            area_dict["bufferUnits"] = area.units
            area_dict["bufferRadii"] = area.radii
            if area.travel_mode is not None:
                area_dict["travel_mode"] = area.travel_mode

        elif isinstance(area, NamedArea):  # named area
            area_dict = area.__studyarea__
        elif isinstance(area, list):  # list of named areas, (union)
            first_area = area[0]
            ids = []
            if isinstance(first_area, NamedArea):
                for namedarea in area:
                    a = namedarea.__studyarea__
                    if (
                        a["layer"] != first_area["layer"]
                        or a["sourceCountry"] != first_area["sourceCountry"]
                    ):
                        raise ValueError(
                            "All NamedAreas in the list must have the same source country and level"
                        )
                    ids.append(a["ids"])
                area_dict = {
                    "sourceCountry": first_area["sourceCountry"],
                    "layer": first_area["layer"],
                    "ids": [ids.join(",")],
                }
            else:
                raise ValueError("Lists members must be NamedArea instances")
        else:
            raise ValueError(
                "Don't know how to handle study areas of type " + str(type(area))
            )

        areas.append(area_dict)
    ge = _GeoEnrichment(gis=gis)
    return ge.create_report(
        study_areas=areas,
        report=report,
        export_format=export_format,
        report_fields=report_fields,
        options=options,
        return_type=return_type,
        use_data=use_data,
        in_sr=in_sr,
        out_folder=out_folder,
        out_name=out_name,
    )


# ----------------------------------------------------------------------
def _data_collections(
    country=None,
    collection_name=None,
    variables=None,
    out_fields="*",
    hide_nulls=True,
    gis=None,
    as_dict=True,
):
    """
    The GeoEnrichment class uses the concept of a data collection to define the data
    attributes returned by the enrichment service. Each data collection has a unique name
    that acts as an ID that is passed in the data_collections parameter of the GeoEnrichment
    service.

    Some data collections (such as default) can be used in all supported countries. Other data
    collections may only be available in one or a collection of countries. Data collections may
    only be available in a subset of countries because of differences in the demographic data
    that is available for each country. A list of data collections for all available countries
    can be generated with the data collection discover method seen below.
    Return a list of data collections that can be run for any country.

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    country                optional string. lets the user supply and optional name of a country
                           in order to get information about the data collections in that given
                           country.
    ------------------     --------------------------------------------------------------------
    dataset                Optional string. Name of the data collection to examine.
    ------------------     --------------------------------------------------------------------
    variables              Optional string/list. This parameter to specifies a list of field
                           names that include variables for the derivative statistics.
    ------------------     --------------------------------------------------------------------
    out_fields             Optional string. This parameter is a string of comma seperate field
                           names.
    ------------------     --------------------------------------------------------------------
    hide_nulls             Optional boolean. parameter to return only values that are not NULL
                           in the output response. Adding the optional suppress_nulls parameter
                           to any data collections discovery method will reduce the size of the
                           output that is returned.
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS.  If None, the GIS object will be used from the
                           arcgis.env.active_gis.  This GIS object must be authenticated and
                           have the ability to consume credits
    ------------------     --------------------------------------------------------------------
    as_dict                Opional boolean. If True, the result comes back as a python
                           dictionary, else the value will returns as a Python DataFrame.
    ==================     ====================================================================

    :return: dictionary, describing the requested return data.
    """
    if gis is None:
        gis = env.active_gis
    ge = _GeoEnrichment(gis=gis)

    return ge.data_collections(
        country=country,
        collection_name=collection_name,
        variables=variables,
        out_fields=out_fields,
        hide_nulls=hide_nulls,
        as_dict=as_dict,
    )


@_call_method_by_source
def service_limits(gis=None):
    """
    Returns a Pandas' DataFrame describing limitations for each input parameter.

    :return: Pandas DataFrame
    """
    pass


def _service_limits_gis(gis=None):
    """Local implementation of service limits."""
    if gis is None:
        gis = env.active_gis
    ge = _GeoEnrichment(gis=gis)
    return ge.limits


@_call_method_by_source
def enrich(
    study_areas,
    data_collections=None,
    analysis_variables=None,
    comparison_levels=None,
    add_derivative_variables=None,
    intersecting_geographies=None,
    return_geometry=True,
    gis=None,
):
    """
    Returns demographic and other requested information for the specified study areas.
    Study areas define the location of the point or area that you want to enrich
    with additional information or create reports about. If one or many points are input as
    a study area, the method will create a 1-mile ring buffer around
    the point to collect and append enrichment data. You can optionally
    change the ring buffer size or create drive-time service areas
    around the point.

    You can create a buffer ring or drive-time service
    area around the points to aggregate data for the study areas. You
    can also return enrichment data for buffers around input line
    features.

    =========================     ====================================================================
    **Argument**                  **Description**
    -------------------------     --------------------------------------------------------------------
    study_areas                   Required list, FeatureSet or SpatiallyEnabledDataFrame containing
                                  the input areas to be enriched.

                                  study_areas can be a SpatiallyEnabledDataFrame, FeatureSet or a
                                  lists of the following types:
                                  * addresses, points of interest, place names or other
                                  supported locations as strings.
                                  * dicts such as [{"address":{"Address":"380 New York St.",
                                  "Admin1":"Redlands","Admin2":"CA","Postal":"92373",
                                  "CountryCode":"USA"}}] for multiple field addresses
                                  * arcgis.gis.Geometry instances
                                  * BufferStudyArea instances. By default, one-mile ring
                                  buffers are created around the points to collect and append
                                  enrichment data. You can use BufferStudyArea to change the ring
                                  buffer size or create drive-time service areas around the points.
                                  * NamedArea instances to support standard geography. They are
                                  obtained using Country.subgeographies()/search(). When
                                  the NamedArea instances should be combined together (union), a list
                                  of such NamedArea instances should constitute a study area in the
                                  list of requested study areas.
    -------------------------     --------------------------------------------------------------------
    data_collections              Optional list. A Data Collection is a preassembled list of
                                  attributes that will be used to enrich the input features.
                                  Enrichment attributes can describe various types of information such
                                  as demographic characteristics and geographic context of the
                                  locations or areas submitted as input features in study_areas.
    -------------------------     --------------------------------------------------------------------
    analysis_variables            Optional list. A Data Collection is a preassembled list of
                                  attributes that will be used to enrich the input features. With the
                                  analysis_variables parameter you can return a subset of variables
                                  enrichment attributes can describe various types of information such
                                  as demographic characteristics and geographic context of the
                                  locations or areas submitted as input features in study_areas.
    -------------------------     --------------------------------------------------------------------
    add_derivative_variables      Optional list. This parameter is used to specify an array of string
                                  values that describe what derivative variables to include in the
                                  output. The list of accepted values includes:
                                  ['percent','index','average','all','*']
    -------------------------     --------------------------------------------------------------------
    comparison_levels             Optional list of layer IDs for which the intersecting
                                  geographies should be geoenriched.
    -------------------------     --------------------------------------------------------------------
    intersecting_geographies      Optional parameter to explicitly define the geographic layers used
                                  to provide geographic context during the enrichment process. For
                                  example, you can use this optional parameter to return the U.S.
                                  county and ZIP Code that each input study area intersects.
                                  You can intersect input features defined in the study_areas
                                  parameter with standard geography layers that are provided by the
                                  GeoEnrichment class for each country. You can also intersect
                                  features from a publicly available feature service.
    -------------------------     --------------------------------------------------------------------
    return_geometry               Optional boolean. A parameter to request the output geometries in
                                  the response.
    -------------------------     --------------------------------------------------------------------
    gis                           Optional GIS.  If None, the GIS object will be used from the
                                  arcgis.env.active_gis.  This GIS object must be authenticated and
                                  have the ability to consume credits
    =========================     ====================================================================

    Refer to https://developers.arcgis.com/rest/geoenrichment/api-reference/street-address-locations.htm for
    the format of intersection_geographies parameter.

    Performance Tip: If you wish to speed up the operation and don't care about the geometries, set
    return_geometry=False

    :return: Spatial DataFrame or Panda's DataFrame with the requested information for the study areas
    """
    pass


def _enrich_gis(
    study_areas,
    data_collections=None,
    analysis_variables=None,
    comparison_levels=None,
    add_derivative_variables=None,
    intersecting_geographies=None,
    return_geometry=True,
    gis=None,
):
    """GIS implementation of enrich."""

    def _chunks(l, n):
        """yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i : i + n]

    if gis is None:
        gis = env.active_gis
    ge = _GeoEnrichment(gis=gis)

    areas = study_areas
    if isinstance(study_areas, FeatureSet):
        areas = FeatureSet.sdf
    elif isinstance(
        study_areas, dict
    ):  # could be dict of NamedAreas, eg usa.subgeographies.states['California'].counties
        areas = list(study_areas.values())
        study_areas = areas

    # convert to dict
    # add comparison levels if any
    # add buffer info - network, ring
    if isinstance(areas, list):
        areas = []
        for area in study_areas:
            area_dict = area
            if isinstance(
                area, str
            ):  # street address - {"address":{"text":"380 New York St Redlands CA 92373"}}
                area_dict = {"address": {"text": area}}
            elif isinstance(area, Geometry):  # geometry, polygons, points
                area_dict = {"geometry": dict(area)}
            elif isinstance(area, BufferStudyArea):
                # namedtuple('BufferStudyArea', 'area radii units overlap travel_mode')
                g = area.area
                if isinstance(g, str):
                    area_dict = {"address": {"text": g}}
                elif isinstance(g, Geometry):  # geometry, polygons, points
                    area_dict = {"geometry": dict(g)}
                elif isinstance(g, dict):
                    area_dict = g
                else:
                    raise ValueError(
                        "BufferStudyArea is only supported for Point geometry and addresses"
                    )

                area_type = "RingBuffer"
                if area.travel_mode is None:
                    if not area.overlap:
                        area_type = "RingBufferBands"
                else:
                    area_type = "NetworkServiceArea"

                area_dict["areaType"] = area_type
                area_dict["bufferUnits"] = area.units
                area_dict["bufferRadii"] = area.radii
                if area.travel_mode is not None:
                    area_dict["travel_mode"] = area.travel_mode

            elif isinstance(area, NamedArea):  # named area
                area_dict = area.__studyarea__

            elif isinstance(
                area, dict
            ):  # pass through - user knows what they're sending
                pass
            elif isinstance(area, list):  # list of named areas, (union)
                first_area = area[0]
                ids = []
                if isinstance(first_area, NamedArea):
                    for namedarea in area:
                        a = namedarea.__studyarea__
                        if (
                            a["layer"] != first_area["layer"]
                            or a["sourceCountry"] != first_area["sourceCountry"]
                        ):
                            raise ValueError(
                                "All NamedAreas in the list must have the same source country and level"
                            )
                        ids.append(a["ids"])
                    area_dict = {
                        "sourceCountry": first_area["sourceCountry"],
                        "layer": first_area["layer"],
                        "ids": [ids.join(",")],
                    }
                else:
                    raise ValueError("Lists members must be NamedArea instances")
            else:
                raise ValueError(
                    "Don't know how to handle study areas of type " + str(type(area))
                )

            if comparison_levels is not None:
                # add "comparisonLevels":[{"layer": "Admin2"}, {"layer": "Admin3"}]}]
                layers = []
                for level in comparison_levels:
                    layers.append({"layer": level})

                area_dict["comparisonLevels"] = layers

            areas.append(area_dict)

    # chunking if len > 100
    if isinstance(areas, (SpatialDataFrame, pd.DataFrame, list)) and len(areas) > 100:
        import concurrent.futures

        parts = []
        concurrent_parts = {}  # []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            for idx, chunk in enumerate(_chunks(l=areas, n=100)):
                f = executor.submit(
                    fn=ge.enrich,
                    **{
                        "study_areas": chunk.copy(),
                        "data_collections": data_collections,
                        "analysis_variables": analysis_variables,
                        "add_derivative_variables": add_derivative_variables,
                        "intersecting_geographies": intersecting_geographies,
                        "return_geometry": return_geometry,
                        "out_sr": env.out_spatial_reference,
                        "as_featureset": False,
                    },
                )

                concurrent_parts[idx] = f  # .append(f)
                del chunk
        futures = concurrent.futures.wait(list(concurrent_parts.values()))
        exceptions = [f.exception() is None for f in futures.done]
        results = [result.result() for result in concurrent_parts.values()]
        if all(exceptions) == False:
            import json

            exceptions = [
                f.exception() for f in futures.done if not f.exception() is None
            ]
            raise Exception(json.dumps(exceptions))
        if isinstance(areas, (SpatialDataFrame, pd.DataFrame)):
            enrich_res = pd.concat(results)
            if len(enrich_res) != len(study_areas):
                if "OBJECTID" in enrich_res.columns:
                    missing_q = study_areas.OBJECTID.isin(
                        list(set(study_areas.OBJECTID) - set(enrich_res.OBJECTID))
                    )

                    enrich_res = pd.concat(
                        [enrich_res, study_areas[missing_q]]
                    ).set_index(
                        keys=areas.index,
                        drop=True,
                        append=False,
                        inplace=False,
                        verify_integrity=False,
                    )

            elif len(enrich_res) == len(study_areas):
                enrich_res = enrich_res.set_index(
                    keys=areas.index,
                    drop=True,
                    append=False,
                    inplace=False,
                    verify_integrity=False,
                )

        else:
            enrich_res = pd.concat(results)

        # set the spatial column
        if return_geometry:
            enrich_res.spatial.set_geometry("SHAPE")

    # no chunking, len < 100, or FeatureSet
    else:
        enrich_res = ge.enrich(
            study_areas=areas,
            data_collections=data_collections,
            analysis_variables=analysis_variables,
            add_derivative_variables=add_derivative_variables,
            intersecting_geographies=intersecting_geographies,
            return_geometry=return_geometry,
            out_sr=env.out_spatial_reference,
        )

    return enrich_res


# ----------------------------------------------------------------------
def _find_report(country, gis=None):
    """
    Returns a list of reports by a country code

    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    country                optional string. lets the user supply and optional name of a country
                           in order to get information about the data collections in that given
                           country. This should be a two country code name.
                           Example: United States as US
    ------------------     --------------------------------------------------------------------
    gis                    Optional GIS.  If None, the GIS object will be used from the
                           arcgis.env.active_gis.  This GIS object must be authenticated and
                           have the ability to consume credits
    ==================     ====================================================================

    :return: Panda's DataFrame
    """
    if gis is None:
        gis = env.active_gis
    ge = _GeoEnrichment(gis=gis)
    return ge.find_report(country=country)


# ----------------------------------------------------------------------
# def get_variables(country,
#                   dataset=None,
#                   text=None,
#                   gis=None):
#     """
#     The GeoEnrichment get_variables method allows you to search the data
#     collections for variables that contain specific keywords.
#
#     ======================     ====================================================================
#     **Argument**               **Description**
#     ----------------------     --------------------------------------------------------------------
#     country                    Optional string. Specifies the source country for the search. Use
#                                this parameter to limit the search and query of standard geographic
#                                features to one country. This parameter supports both the
#                                two-digit and three-digit country codes illustrated in the
#                                coverage table.
#
#                                Example 1 - Set source country to the United States:
#                                country=US
#
#                                Example 2 - Set source country to the Canada:
#                                country=CA
#
#                                Additional notes
#                                Currently, the service is available for Canada, the United States
#                                and a number of European countries. Other countries will be added
#                                in the near future.
#     ----------------------     --------------------------------------------------------------------
#     dataset                    optional string/list. Optional parameter to specify a specific
#                                dataset within a defined country. This parameter will not be used
#                                in the Beta release. In the future, some countries may have two or
#                                more datasets that may have different vintages and standard
#                                geography areas. For example, in the United States, there may be
#                                an optional dataset with historic census data from previous years.
#                                Examples
#                                dataset=USA_ESRI_2013
#     ----------------------     --------------------------------------------------------------------
#     text                       Optional string. Use this parameter to specify the text to query and
#                                search the data collections for the country and datasets specified.
#                                You can use this parameter to query and find specific keywords that
#                                are contained in a data collection.
#     ------------------         --------------------------------------------------------------------
#     gis                        Optional GIS.  If None, the GIS object will be used from the
#                                arcgis.env.active_gis.  This GIS object must be authenticated and
#                                have the ability to consume credits
#     ======================     ====================================================================
#
#     returns: Pandas' DataFrame
#     """
#     if gis is None:
#         gis = env.active_gis
#     ge = _GeoEnrichment(gis=gis)
#     return ge.get_variables(country=country,
#                              dataset=dataset,
#                              text=text)
# ----------------------------------------------------------------------
# def report_metadata(country, gis=None):
#     """
#     This method returns information about a given country's available reports and provides
#     detailed metadata about each report.
#
#     :Usage:
#     >>> df = arcgis.geoenrichment.report_metadata("al", gis=gis)
#     # returns basic report metadata for Albania
#
#     ==================     ====================================================================
#     **Argument**           **Description**
#     ------------------     --------------------------------------------------------------------
#     country                Required string. lets the user supply and optional name of a country
#                            in order to get information about the data collections in that given
#                            country. This can be the two letter country code or the coutries
#                            full name.
#     ------------------     --------------------------------------------------------------------
#     gis                    Optional GIS.  If None, the GIS object will be used from the
#                            arcgis.env.active_gis.  This GIS object must be authenticated and
#                            have the ability to consume credits
#     ==================     ====================================================================
#
#:return: Pandas' DataFrame """ if gis is None: gis = env.active_gis ge =\
# _GeoEnrichment(gis=gis) return ge.report_metadata(country=country)\
# ----------------------------------------------------------------------
@deprecated(
    deprecated_in="1.4.1",
    removed_in="1.5.0",
    current_version=__version__,
    details="Method was removed due to changes in the GeoEnrichment API",
)
def find_businesses(
    type_filters=None,
    feature_limit=1000,
    feature_offset=0,
    exact_match=False,
    search_string=None,
    spatial_filter=None,
    simple_search=False,
    dataset_id=None,
    full_error_message=False,
    out_sr=4326,
    return_geometry=False,
    as_featureset=False,
    gis=None,
):
    """
    The find_businesses method returns business points matching a given search criteria.
    Business points can be selected using any combination of three search criteria: search
    string, spatial filter and business type. A business point will be selected if it matches
    all search criteria specified.

    ======================     ====================================================================
    **Argument**               **Description**
    ----------------------     --------------------------------------------------------------------
    type_filters               Optional list. List of business type filters restricting the search.
                               For USA, either the NAICS or SIC filter is useful as a business type
                               filter. If both filters are specified in the type_filters parameter
                               value, selected business points will match both of them.
    ----------------------     --------------------------------------------------------------------
    feature_limit              Optional integer. The limit of returned business points.
    ----------------------     --------------------------------------------------------------------
    feature_offset             Optional integer. Start the results on the number of the record
                               specified.
    ----------------------     --------------------------------------------------------------------
    exact_match                Optional boolean. True value of the parameter means the exact match
                               of the string to search.
    ----------------------     --------------------------------------------------------------------
    search_string              Optional string. A string of characters which is used in the search
                               query.
    ----------------------     --------------------------------------------------------------------
    spatial_filter             Optional SpatialFilter. A spatial filter restricting the search.
    ----------------------     --------------------------------------------------------------------
    simple_search              Optional boolean. A spatial filter restricting the search. True
                               value of the parameter means a simple search (e.g., in company
                               names only).
    ----------------------     --------------------------------------------------------------------
    dataset_id                 Optional string. ID of the active dataset.
    ----------------------     --------------------------------------------------------------------
    full_error_message         Optional boolean. Parameter for composing error message.
    ----------------------     --------------------------------------------------------------------
    out_sr                     Optional integer. Parameter specifying the spatial reference to
                               return the output dataframe.
    ----------------------     --------------------------------------------------------------------
    return_geometry            Optional boolean. When true, geometries are returned with the
                               response.
    ----------------------     --------------------------------------------------------------------
    as_featureset              Optional boolean.  The default is False. If True, the result will be
                               a arcgis.features.FeatureSet object instead of a SpatailDataFrame or
                               Pandas' DataFrame.
    ----------------------     --------------------------------------------------------------------
    gis                        Optional GIS.  If None, the GIS object will be used from the
                               arcgis.env.active_gis.  This GIS object must be authenticated and
                               have the ability to consume credits
    ======================     ====================================================================

    returns: DataFrame (Spatial or Pandas), FeatureSet, or dictionary on error.
    """
    raise Exception("This method is deprecated.")


# ----------------------------------------------------------------------
@_call_method_by_source
def standard_geography_query(
    source_country=None,
    country_dataset=None,
    layers=None,
    ids=None,
    geoquery=None,
    return_sub_geography=False,
    sub_geography_layer=None,
    sub_geography_query=None,
    out_sr=4326,
    return_geometry=False,
    return_centroids=False,
    generalization_level=0,
    use_fuzzy_search=False,
    feature_limit=1000,
    as_featureset=False,
    gis=None,
):
    """
    This method allows you to search and query standard geography areas so that they can be used to
    obtain facts about the location using the enrich() method or create reports about.

    GeoEnrichment uses the concept of a study area to define the location of the point
    or area that you want to enrich with additional information. Locations can also be passed as
    one or many named statistical areas. This form of a study area lets you define an area by
    the ID of a standard geographic statistical feature, such as a census or postal area. For
    example, to obtain enrichment information for a U.S. state, county or ZIP Code or a Canadian
    province or postal code, the Standard Geography Query helper method allows you to search and
    query standard geography areas so that they can be used in the GeoEnrichment method to
    obtain facts about the location.
    The most common workflow for this service is to find a FIPS (standard geography ID) for a
    geographic name. For example, you can use this service to find the FIPS for the county of
    San Diego which is 06073. You can then use this FIPS ID within the GeoEnrichment class study
    area definition to get geometry and optional demographic data for the county. This study
    area definition is passed as a parameter to the GeoEnrichment class to return data defined
    in the enrichment pack and optionally return geometry for the feature.

    ======================     ====================================================================
    **Argument**               **Description**
    ----------------------     --------------------------------------------------------------------
    source_country             Optional string. to specify the source country for the search. Use
                               this parameter to limit the search and query of standard geographic
                               features to one country. This parameter supports both the two-digit
                               and three-digit country codes illustrated in the coverage table.
    ----------------------     --------------------------------------------------------------------
    country_dataset            Optional string. parameter to specify a specific dataset within a
                               defined country.
    ----------------------     --------------------------------------------------------------------
    layers                     Optional list/string. Parameter specifies which standard geography
                               layers are being queried or searched. If this parameter is not
                               provided, all layers within the defined country will be queried.
    ----------------------     --------------------------------------------------------------------
    ids                        Optional parameter to specify which IDs for the standard geography
                               layers are being queried or searched. You can use this parameter to
                               return attributes and/or geometry for standard geographic areas for
                               administrative areas where you already know the ID, for example, if
                               you know the Federal Information Processing Standard (FIPS) Codes for
                               a U.S. state or county; or, in Canada, to return the geometry and
                               attributes for a Forward Sortation Area (FSA).
                               Example:
                               Return the state of California where the layers parameter is set to
                               layers=['US.States']
                               then set ids=["06"]
    ----------------------     --------------------------------------------------------------------
    geoquery                   Optional string/list. This parameter specifies the text to query
                               and search the standard geography layers specified. You can use this
                               parameter to query and find standard geography features that meet an
                               input term, for example, for a list of all the U.S. counties that
                               contain the word "orange". The geoquery parameter can be a string
                               that contains one or more words.
    ----------------------     --------------------------------------------------------------------
    return_sub_geography       Optional boolean. Use this optional parameter to return all the
                               subgeographic areas that are within a parent geography.
                               For example, you could return all the U.S. counties for a given
                               U.S. state or you could return all the Canadian postal areas
                               (FSAs) within a Census Metropolitan Area (city).
                               When this parameter is set to true, the output features will be
                               defined in the sub_geography_layer. The output geometries will be
                               in the spatial reference system defined by out_sr.
    ----------------------     --------------------------------------------------------------------
    sub_geography_layer        Optional string/list. Use this optional parameter to return all the
                               subgeographic areas that are within a parent geography. For example,
                               you could return all the U.S. counties within a given U.S. state or
                               you could return all the Canadian postal areas (FSAs) within a
                               Census Metropolitan Areas (city).
                               When this parameter is set to true, the output features will be
                               defined in the sub_geography_layer. The output geometries will be
                               in the spatial reference system defined by out_sr.
    ----------------------     --------------------------------------------------------------------
    sub_geography_query        Optional string.User this parameter to filter the results of the
                               subgeography features that are returned by a search term.
                               You can use this parameter to query and find subgeography
                               features that meet an input term. This parameter is used to
                               filter the list of subgeography features that are within a
                               parent geography. For example, you may want a list of all the
                               ZIP Codes that are within "San Diego County" and filter the
                               results so that only ZIP Codes that start with "921" are
                               included in the output response. The subgeography query is a
                               string that contains one or more words.
    ----------------------     --------------------------------------------------------------------
    out_sr                     Optional integer Use this parameter to request the output geometries
                               in a specified spatial reference system.
    ----------------------     --------------------------------------------------------------------
    return_geometry            Optional boolean. Use this parameter to request the output
                               geometries in the response.  The return type will become a Spatial
                               DataFrame instead of a Panda's DataFrame.
    ----------------------     --------------------------------------------------------------------
    return_centroids           Optional Boolean.  Use this parameter to request the output geometry
                               to return the center point for each feature.
    ----------------------     --------------------------------------------------------------------
    generalization_level       Optional integer that specifies the level of generalization or
                               detail in the area representations of the administrative boundary or
                               standard geographic data layers.
                               Values must be whole integers from 0 through 6, where 0 is most
                               detailed and 6 is most generalized.
    ----------------------     --------------------------------------------------------------------
    use_fuzzy_search           Optional Boolean parameter to define if text provided in the
                               geoquery parameter should utilize fuzzy search logic. Fuzzy searches
                               are based on the Levenshtein Distance or Edit Distance algorithm.
    ----------------------     --------------------------------------------------------------------
    feature_limit              Optional integer value where you can limit the number of features
                               that are returned from the geoquery.
    ----------------------     --------------------------------------------------------------------
    as_featureset              Optional boolean.  The default is False. If True, the result will be
                               a arcgis.features.FeatureSet object instead of a SpatailDataFrame or
                               Pandas' DataFrame.
    ----------------------     --------------------------------------------------------------------
    gis                        Optional GIS.  If None, the GIS object will be used from the
                               arcgis.env.active_gis.  This GIS object must be authenticated and
                               have the ability to consume credits
    ======================     ====================================================================

    :return: Spatial or Pandas Dataframe on success, FeatureSet, or dictionary on failure.

    """
    pass


def _standard_geography_query_gis(
    source_country=None,
    country_dataset=None,
    layers=None,
    ids=None,
    geoquery=None,
    return_sub_geography=False,
    sub_geography_layer=None,
    sub_geography_query=None,
    out_sr=4326,
    return_geometry=False,
    return_centroids=False,
    generalization_level=0,
    use_fuzzy_search=False,
    feature_limit=1000,
    as_featureset=False,
    gis=None,
):
    """GIS implementation of standard_geography_query."""
    if gis is None:
        gis = env.active_gis
    ge = _GeoEnrichment(gis=gis)

    return ge.standard_geography_query(
        source_country=source_country,
        country_dataset=country_dataset,
        layers=layers,
        ids=ids,
        geoquery=geoquery,
        return_sub_geography=return_sub_geography,
        sub_geography_layer=sub_geography_layer,
        sub_geography_query=sub_geography_query,
        out_sr=out_sr,
        return_geometry=return_geometry,
        return_centroids=return_centroids,
        generalization_level=generalization_level,
        use_fuzzy_search=use_fuzzy_search,
        feature_limit=feature_limit,
        as_featureset=as_featureset,
    )
