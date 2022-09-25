"""
Utility functions useful for Business Analyst - the glue functions not fitting neatly anywhere else.
"""
from collections import Iterable
from functools import wraps, lru_cache
import importlib
from typing import AnyStr, Union

from arcgis.gis import GIS, User
from arcgis.geometry import Geometry, SpatialReference
import numpy as np
import pandas as pd


def module_avail(module_name: AnyStr) -> bool:
    """
    Determine if module is available in this environment.
    """
    if importlib.util.find_spec(module_name) is not None:
        avail = True
    else:
        avail = False
    return avail


# flag a couple of useful module availabilities
avail_arcpy = module_avail("arcpy")
avail_shapely = module_avail("shapely")


def local_vs_gis(fn):
    """Decorator to facilitate bridging between local and remote resources."""
    # get the method - this will be used to redirect the function call
    fn_name = fn.__name__

    @wraps(fn)
    def wrapped(self, *args, **kwargs):

        # get source no matter how defined
        for val in ["source", "_source", "_gis", "gis"]:
            if val in self.__dict__.keys():
                src = getattr(self, val)
                break

        # if performing analysis locally, try to access the function locally, but if not implemented, catch the error
        if src == "local":
            try:
                fn_to_call = getattr(self, f"_{fn_name}_local")
            except AttributeError:
                raise NotImplementedError(
                    f"'{fn_name}' not available using 'local' as the source."
                )

        # now, if performing analysis using a Web GIS, then access the function referencing remote resources
        elif isinstance(src, GIS):
            try:
                fn_to_call = getattr(self, f"_{fn_name}_gis")
            except AttributeError:
                raise NotImplementedError(
                    f"'{fn_name}' not available using a Web GIS as the source."
                )

        # if another source, we don't plan on doing that any time soon
        else:
            raise NotImplementedError(f"'{self.source}' is not a recognized source.")

        return fn_to_call(*args, **kwargs)

    return wrapped


@lru_cache(maxsize=10)
def local_business_analyst_avail() -> bool:
    """
    Check if a local installation of Business Analyst is available.
    """
    avail = False

    if avail_arcpy is True:
        import arcpy

        if arcpy.CheckExtension("Business"):
            avail = True

    return avail


@lru_cache(maxsize=10)
def local_ba_data_avail() -> bool:
    """
    Check to see if any local business analyst data packs are installed.
    """
    avail = False

    if local_business_analyst_avail():

        # lazy load to avoid import issues
        import arcpy._ba

        # TODO: remove once bapy patched
        # addresses issue with bapy not being part of Notebook server docker image
        if "getLocalDatasets" in arcpy._ba.__dict__.keys() or module_avail("bapy"):

            # if data is available, there will be more than one dataset available
            avail = len(list(arcpy._ba.ListDatasets())) > 0

    return avail


def set_source(in_source: Union[str, GIS] = None) -> Union[str, GIS]:
    """
    Helper function to check source input. The source can be set explicitly, but if nothing is provided, it
    assumes the order of local first and then a Web GIS. Along the way, it also checks to see if a GIS object
    instance is available in the current session.
    """
    # lazy import to load the active_gis
    from arcgis.env import active_gis

    # if string input is provided, should be 'local'
    if isinstance(in_source, str):

        # cast to lowercast
        in_source = in_source.lower()

        # account for setting to "pro"
        if in_source == "pro":
            in_source = "local"

        if in_source != "local":
            raise Exception(
                f'Source must be either "local" or a Web GIS instance, not {in_source}.'
            )

        elif in_source == "local" and not local_business_analyst_avail():
            raise Exception(
                f"If using local source, the Business Analyst extension must be available."
            )

        elif in_source == "local":
            source = "local"

    # if nothing provided, default to local if arcpy is available, and remote if arcpy not available
    elif in_source is None and local_business_analyst_avail() and local_ba_data_avail():
        source = "local"

    # if a web gis is not provided, check to see if working session has one available
    elif in_source is None and active_gis:
        source = active_gis

    # if not using local, use a GIS
    elif isinstance(in_source, GIS):
        source = in_source

    # provide a fall-though catch
    else:
        raise Exception(
            'Source must be either "local" if using ArcGIS Pro with Business Analyst, or a GIS object '
            "instance connected ot ArcGIS Enterprise with Business Analyst Server or ArcGIS Online."
        )

    return source


def _assert_privileges_access(user: User) -> None:
    """Helper function determining if can access user privileges."""
    assert "privileges" in user.keys(), (
        f"Cannot access privileges of {user.username}. Please ensure either this is "
        "your username, or you are logged in as an administrator to be able to "
        "view privileges."
    )


def get_helper_service_url(gis: GIS, service_key: str) -> str:
    """Helper function to ensure helper service is defined in gis properties."""
    err_msg = (
        f"It appears {service_key} is not available in your Web GIS. Please ensure a {service_key} service is "
        "defined."
    )
    assert service_key in gis.properties.helperServices, err_msg
    url = gis.properties.helperServices[service_key]["url"]
    assert len(url), err_msg
    return url


def can_enrich_gis(user: User) -> bool:
    """Determine if the provided user has data enrichment privileges in the Web GIS.

    .. note::

        The current user can be retrieved using `gis.users.me` for input.

    Args:
        user: Required `arcgis.gis.User` object instance.

    Returns:
       Boolean indicating if the provided user has enrichment privileges in the Web GIS.
    """
    # privileges may no be available
    _assert_privileges_access(user)

    # use list comprehension to account for future modifications to privilege descriptions
    bool_enrich = len([priv for priv in user["privileges"] if "enrich" in priv]) > 0

    return bool_enrich


def has_networkanalysis_gis(user: User, network_function: str = None) -> bool:
    """Determine if the provided user has network analysis privileges in the Web GIS.

    .. note::

        The current user can be retrieved using `gis.users.me` for input.

    Args:
        user: Required `arcgis.gis.User` object instance.
        network_function: Optional string describing specific network function to check for.
            Valid values include 'closestfacility', 'locationallocation', 'optimizedrouting',
            'origindestinationcostmatrix', 'routing', 'servicearea', or 'vehiclerouting'.

    Returns: Boolean indicating if the provided user has network analysis privileges in the Web GIS.
    """
    # validate network_function if provided
    if network_function is not None:
        ntwrk_fn_lst = [
            "closestfacility",
            "locationallocation",
            "optimizedrouting",
            "origindestinationcostmatrix",
            "routing",
            "servicearea",
            "vehiclerouting",
        ]
        assert network_function in ntwrk_fn_lst, (
            f'The network function provided, f"{network_function}," is not in '
            f'the list of network functions [{", ".join(ntwrk_fn_lst)}.'
        )

    # privileges may no be available
    _assert_privileges_access(user)

    # get the network analysis capabilities from the privileges
    prv_tail_lst = [
        prv.split(":")[-1] for prv in user["privileges"] if "networkanalysis" in prv
    ]

    # if nothing was found, there are not any capabilities
    if len(prv_tail_lst) == 0:
        bool_net = False

    # if no specific network capability is being requested, check for overall access
    elif not network_function:
        bool_net = "networkanalysis" in prv_tail_lst

    # if a specific network function is being checked
    else:

        # just in case, ensure the input is lowercase
        network_function = network_function.lower()

        # check to ensure function is in capabilities determining if user has privileges
        bool_net = network_function in prv_tail_lst

    return bool_net


def geography_iterable_to_arcpy_geometry_list(
    geography_iterable: Union[pd.DataFrame, Iterable, Geometry],
    geometry_filter: str = None,
) -> list:
    """
    Processing helper to convert a iterable of geography_levels to a list of ArcPy Geometry objects suitable for input
    into ArcGIS ArcPy geoprocessing tools.

    Args:
        geography_iterable:
            Iterable containing valid geographies.
        geometry_filter:
            String point|polyline|polygon to use for validation to ensure correct geometry type.

    Returns:
        List of ArcPy objects.
    """
    if not avail_arcpy:
        raise Exception(
            "Converting to ArcPy geometry requires an environment with ArcPy available."
        )

    # do some error checking on the geometry filter
    geometry_filter = (
        geometry_filter.lower() if geometry_filter is not None else geometry_filter
    )
    if (
        geometry_filter not in ["point", "polyline", "polygon"]
        and geometry_filter is not None
    ):
        raise Exception(
            f"geometry_filter must be point|polyline|polygon {geometry_filter}"
        )

    # if a DataFrame, check to ensure is spatial, and convert to list of arcgis Geometry objects
    if isinstance(geography_iterable, pd.DataFrame):
        if geography_iterable.spatial.validate() is True:
            geom_col = [
                col
                for col in geography_iterable.columns
                if geography_iterable[col].dtype.name.lower() == "geometry"
            ][0]
            geom_lst = list(geography_iterable[geom_col].values)
        else:
            raise Exception(
                "The provided geography_iterable DataFrame does not appear to be a Spatially Enabled "
                "DataFrame or if so, all geographies do not appear to be valid."
            )

    # accommodate handling pd.Series input
    elif isinstance(geography_iterable, pd.Series):
        if (
            "SHAPE" not in geography_iterable.keys()
            or geography_iterable.name != "SHAPE"
        ):
            raise Exception(
                "SHAPE geometry field must be in the pd.Series or the pd.Series must be the SHAPE to use "
                "a pd.Series as input."
            )

        # if just a single row passed in
        elif "SHAPE" in geography_iterable.keys():
            geom_lst = [geography_iterable["SHAPE"]]

        # otherwise, is a series of geometry objects, and just pass over to geom_lst since will be handled as iterable
        else:
            geom_lst = geography_iterable

    # if a list, ensure all child objects are polygon geographies and convert to list of arcpy.Geometry objects
    elif isinstance(geography_iterable, list):
        for geom in geography_iterable:
            if not isinstance(geom, Geometry):
                raise Exception(
                    "The provided geographies in the selecting_geometry list do not appear to all be "
                    "valid."
                )
        geom_lst = geography_iterable

    # if a single geometry object instance, ensure is polygon and make into single item list of arcpy.Geometry
    elif isinstance(geography_iterable, Geometry):
        geom_lst = [geography_iterable]

    else:
        raise Exception(
            "geography_iterable must be either a Spatially Enabled Dataframe, pd.Series with a SHAPE "
            f"column, list or single geometry object - not {type(geography_iterable)}."
        )

    # ensure all geographies are correct geometry type if provided
    if geometry_filter is not None:
        for geom in geom_lst:
            if geom.geometry_type != geometry_filter:
                raise Exception(
                    "geography_iterable geographies must be polygons. It appears you have provided at "
                    f'least one "{geom.geometry_type}" geometry.'
                )

    # convert the objects in the geometry list to ArcPy Geometry objects
    arcpy_lst = [geom.as_arcpy for geom in geom_lst]

    return arcpy_lst


def get_sanitized_names(names: Union[str, list, tuple, pd.Series]) -> pd.Series:
    """
    Sanitize the column names to be PEP 8 compliant.
    Useful when trying to match up column names from previously enriched data.

    Args:
        names: Iterable (list, tuple, pd.Series) of names to be "sanitized"

    Returns:
        pd.Series of column names
    """
    # if just one name was passed in, make it an iterable
    names = [names] if isinstance(names, str) else names

    # sanititze the column names and drop into a series
    sani_names = pd.Series(map(pep8ify, names))

    return sani_names


def validate_spatial_reference(
    spatial_reference: Union[str, int, dict, SpatialReference]
) -> SpatialReference:
    """Validate the variety of ways a spatial reference can be inputted. This does not validate the WKID."""
    # instantiate the output spatial reference variable
    sr = None

    if isinstance(spatial_reference, dict):
        assert "wkid" in spatial_reference.keys(), (
            "If providing spatial reference as a dictionary, it must conform "
            'look like {"wkid": <WKID>}, such as {"wkid": 4326}.'
        )
        sr = spatial_reference
    elif isinstance(spatial_reference, str):
        assert spatial_reference.isdecimal(), (
            "If providing a string to identify a spatial reference, it must be a "
            "WKID for your desired spatial reference."
        )
        sr = {"wkid": spatial_reference}
    elif isinstance(spatial_reference, int):
        sr = {"wkid": spatial_reference}
    elif isinstance(spatial_reference, SpatialReference):
        sr = SpatialReference
    elif avail_arcpy:
        import arcpy

        if isinstance(spatial_reference, arcpy.SpatialReference):
            sr = SpatialReference(spatial_reference.factoryCode)

    # if nothing has been found, something is wrong
    if sr is None:
        raise Exception(
            "The spatial reference must be either a string or integer specify the WKID, a dictionary "
            'specifying the WKID such as {"wkid": 4326}, or a SpatialReference object.'
        )

    return sr


def get_spatially_enabled_dataframe(
    input_object: Union[pd.DataFrame, pd.Series, Geometry, Iterable, np.ndarray],
    spatial_column: str = "SHAPE",
) -> pd.DataFrame:
    """Garbage disposal taking variety of possible inputs and outputting, if possible, a Pandas Spatially Enabled
    DataFrame."""
    # if just a geometry passed in, we need to get it into an iterable
    if isinstance(input_object, Geometry):
        input_object = [input_object]

    # now, if any type of iterable other than a series, make into a series
    if isinstance(input_object, (Iterable, np.ndarray)) and not isinstance(
        input_object, pd.DataFrame
    ):
        input_object = pd.Series(input_object)

    # at this juncture, the only real options are either a Series or DataFrame, so if Series, make into DataFrame
    if isinstance(input_object, pd.Series):
        input_object = input_object.to_frame("SHAPE")

    # if the geometry has not been set, take care of it
    if input_object.spatial.name is None:
        assert spatial_column in input_object.columns, (
            f"The spatial column cannot be set to {spatial_column}, "
            f"because it is not a column in the input DataFrame."
        )
        input_object.spatial.set_geometry(spatial_column)

    return input_object


def preproces_code_inputs(codes):
    """helper function to preprocess naics or sic codes"""
    if isinstance(codes, (str, int)):
        codes = [codes]

    elif isinstance(codes, (pd.Series, list, tuple, np.ndarray)):
        codes = [str(cd) if isinstance(cd, int) else cd for cd in codes]

    return codes


def get_top_codes(codes: Union[pd.Series, list, tuple], threshold=0.5) -> list:
    """Get the top category codes by only keeping those compromising 50% or greater of the records.

    Args:
        codes: Iterable, preferable a Pandas Series, of code values to filter.
        threshold: Decimal value representing the proportion of values to use for creating
            the list of top values.

    Returns:
        List of unique code values.
    """
    # check the threshold to ensure it is deicmal
    msg_thrshld = (
        f'"threshold" must be a decimal value between zero and one, not {threshold}'
    )
    assert 0 < threshold < 1, msg_thrshld

    # ensure the input codes iterable is a Pandas Series
    cd_srs = codes if isinstance(codes, pd.Series) else pd.Series(codes)

    # get the instance count for each unique code value
    cnt_df = cd_srs.value_counts().to_frame("cnt")

    # calculate the percent each of the codes comprises of the total values as a decimal
    cnt_df["pct"] = cnt_df.cnt.apply(lambda x: x / cnt_df.cnt.sum())

    # calculate a running total of the percent for each value (running total percent)
    cnt_df["pct_cumsum"] = cnt_df["pct"].cumsum()

    # finally, get the values comprising the code values for the top threshold
    cd_vals = list(
        cnt_df[(cnt_df["pct_cumsum"] < threshold) | (cnt_df["pct"] > threshold)].index
    )

    return cd_vals


def pep8ify(name):
    """PEP8ify name"""
    import re

    if "." in name:
        name = name[name.rfind(".") + 1 :]
    if name[0].isdigit():
        name = "level_" + name
    name = name.replace(".", "_")
    if "_" in name:
        name = name.lower()
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    s3 = s2.replace(" ", "")
    return s3


def pro_at_least_version(version: str) -> bool:
    """
    Test the current ArcGIS Pro version to be equal or greater than.
    Args:
        version: Version number eg ('2', '2.1', '2.8.1')
    Returns:
        Boolean indicating if version is at least or greater than specified version.
    """

    # late import since may or may not already be loaded
    import arcpy

    # get parts of the current version
    v_lst = [int(v) for v in arcpy.GetInstallInfo()["Version"].split(".")]

    # get parts of the version to test for
    in_lst = [int(v) for v in version.split(".")]

    # extend the shorter version list to match the longer
    max_len = max((len(v_lst), len(in_lst)))
    v_lst, in_lst = [lst + ([0] * (max_len - len(lst))) for lst in [v_lst, in_lst]]

    # variable to store status
    at_least = True

    # test all the parts of the input version against the current version
    for idx in range(0, max_len):

        # evaluate if the part and if greater, break and report status
        if v_lst[idx] < in_lst[idx]:
            at_least = False
            break

    return at_least
