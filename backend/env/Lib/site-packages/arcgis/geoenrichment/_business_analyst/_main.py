from collections import Iterable
from copy import deepcopy

from pathlib import Path
import re
from typing import Union
import uuid
from warnings import warn

from arcgis.features import GeoAccessor
from arcgis.gis import GIS
from arcgis.geometry import SpatialReference
from arcgis._impl.common._utils import _lazy_property as lazy_property
import pandas as pd

from ._utils import (
    local_vs_gis,
    get_helper_service_url,
    set_source,
    geography_iterable_to_arcpy_geometry_list,
    get_sanitized_names,
    pep8ify,
    validate_spatial_reference,
    get_spatially_enabled_dataframe,
    pro_at_least_version,
)
from ._spatial import change_spatial_reference

__all__ = ["BusinessAnalyst", "Country"]


class AOI(object):
    """
    An AOI (area of interest) delineates the area being used for enrichment.
    Currently this is implemented as a Country, but is classed as a parent
    so later areas of interest can be delineated spanning country borders.
    """

    def __repr__(self):
        repr_str = f"<{type(self).__name__} ({self.source})>"
        return repr_str

    @property
    def source(self) -> Union[str, GIS]:
        return self._source

    @source.setter
    def source(self, in_source: Union[str, GIS] = None) -> None:
        """
        Source being used.
        """
        self._source = set_source(in_source)

        # if working with a GIS object instance, we need to set a few extra properties
        if isinstance(self.source, GIS):

            # run a few checks and get the helper service for geoenrichment
            self._base_url = get_helper_service_url(self.source, "geoenrichment")

            # run a check for nuances of hosted notebooks
            if self.source._is_hosted_nb_home:
                self._base_url = self._validate_url(self._base_url)

    def _validate_url(self, url):
        res = self.source._private_service_url(url)
        url = (
            res["privateServiceUrl"]
            if "privateServiceUrl" in res
            else res["serviceUrl"]
        )
        return url

    @lazy_property
    @local_vs_gis
    def enrich_variables(self):
        """Pandas DataFrame of available enrichment enrich_variables."""
        pass

    def _enrich_variables_gis(self):
        """GIS implementation of enrich_variables property."""

        # construct the url with the option to simply not explicitly specify a iso3
        url = f"{self._base_url}/Geoenrichment/DataCollections/"
        if hasattr(self, "iso3"):
            url = f"{url}{self.iso3}"

        # get the data collections from the GIS enrichment REST endpoint
        res = self.source._con.get(url, params={"f": "json"})
        assert "DataCollections" in res.keys(), (
            "Could not retrieve enrichment enrich_variables (DataCollections) from "
            "the GIS instance."
        )

        # list to store all the dataframes as they are created for each data collection
        mstr_lst = []

        # iterate the data collections
        for col in res["DataCollections"]:
            # create a dataframe of the enrich_variables, keep only needed columns, and add the data collection name
            coll_df = pd.json_normalize(col["data"])[
                ["id", "alias", "description", "vintage", "units"]
            ]
            coll_df["data_collection"] = col["dataCollectionID"]

            # schema cleanup
            coll_df.rename(columns={"id": "name"}, inplace=True)
            coll_df = coll_df[
                ["name", "alias", "data_collection", "description", "vintage", "units"]
            ]

            # append the list
            mstr_lst.append(coll_df)

        # combine all the dataframes into a single master dataframe
        var_df = pd.concat(mstr_lst)

        # create the column for enrichment
        var_df.insert(3, "enrich_name", var_df.data_collection + "." + var_df.name)

        # create column for matching to previously enriched column names
        regex = re.compile(r"(^\d+)")
        fld_vals = var_df.enrich_name.apply(
            lambda val: regex.sub(r"F\1", val.replace(".", "_"))
        )
        var_df.insert(4, "enrich_field_name", fld_vals)

        return var_df

    def get_enrich_variables_from_name_list(
        self, enrich_variables: Union[Iterable, pd.Series], drop_duplicates=True
    ) -> pd.DataFrame:
        """Get a dataframe of enrich enrich_variables associated with the list of enrich_variables
        passed in. This is especially useful when needing aliases (*human readable
        names*), or are interested in enriching more data using previously enriched
        data as a template.

        Args:
            enrich_variables: Iterable (normally a list) of enrich_variables correlating to
                enrichment enrich_variables. These variable names can be simply the name, the
                name prefixed by the collection separated by a dot, or the output from
                enrichment in ArcGIS Pro with the field name modified to fit field naming
                and length constraints.
            drop_duplicates: Optional boolean (default True) indicating whether to drop
                duplicates. Since the same enrich_variables appear in multiple data collections,
                multiple instances of the same variable can be found. Dropping duplicates
                removes redundant matches.

        Returns:
            Pandas DataFrame of enrich enrich_variables with the different available aliases.

        .. code-block:: python

            from pathlib import Path

            import arcpy
            from business_analyst import BusinessAnalyst, Country

            # paths
            gdb = Path(r'C:/path/to/geodatabase.gdb')
            enriched_fc_pth = gdb/'enriched_data'
            features_to_be_enriched = gdb/'block_groups_pdx'
            new_fc_pth = gdb/'block_groups_pdx_enriched'

            # get a list of column names from previously enriched data
            attr_lst = [c.name for c in arcpy.ListFields(str(enriched_fc_pth))

            # get a country to work in
            cntry = BusinessAnalyst('local').get_country('USA')

            # get dataframe of enrich_variables used for previously enriched data
            enrich_vars = cntry.get_enrich_variables_from_name_list(attr_lst)

            # enrich block groups in new area of interest using the same enrich_variables
            bg_df = pd.DataFrame.spatial.from_featureclass(features_to_be_enriched)
            enrich_df = cntry.enrich(new_fc_pth)

            # save the enriched data
            enrich_df.spatial.to_featureclass(new_fc_pth)
        """
        # enrich variable dataframe column names
        enrich_nm_col, enrich_nmpro_col, enrich_str_col = (
            "name",
            "enrich_field_name",
            "enrich_name",
        )
        col_nm_san, col_pronm_san, col_estr_san = "nm_san", "nmpro_san", "estr_san"

        # get shorter version of variable name to work with and also one to modify if necessary
        ev_df = self.enrich_variables

        # make sure the input is a series
        enrich_variables = (
            pd.Series(enrich_variables)
            if isinstance(enrich_variables, Iterable)
            else enrich_variables
        )

        # get a series of submitted enrich enrich_variables all lowercase to account for case variations
        ev_lower = enrich_variables.str.lower()

        # default to trying to find enrich enrich_variables using the enrich string values
        enrich_vars_df = ev_df[ev_df[enrich_str_col].str.lower().isin(ev_lower)]

        # if nothing was returned, try using just the variable names (common if using previously enriched data)
        if len(enrich_vars_df.index) == 0:
            enrich_vars_df = ev_df[ev_df[enrich_nm_col].str.lower().isin(ev_lower)]

        # the possibly may exist where names are from columns in data enriched using local enrichment in Pro
        if len(enrich_vars_df.index) == 0:
            enrich_vars_df = ev_df[ev_df[enrich_nmpro_col].str.lower().isin(ev_lower)]

        # try to find enrich enrich_variables using the enrich string values sanitized (common if exporting from SeDF)
        if len(enrich_vars_df.index) == 0:
            ev_df[col_estr_san] = get_sanitized_names(ev_df[enrich_str_col])
            enrich_vars_df = ev_df[ev_df[col_estr_san].str.lower().isin(ev_lower)]

        # try columns in data enriched using local enrichment in Pro and sanitized (common if exporting from SeDF)
        if len(enrich_vars_df.index) == 0:
            ev_df[col_pronm_san] = get_sanitized_names(enrich_nmpro_col)
            enrich_vars_df = ev_df[ev_df[col_pronm_san].isin(ev_lower)]

        # if nothing was returned, try using just the variable names possibly sanitized (anticipate this to be rare)
        if len(enrich_vars_df.index) == 0:
            ev_df[col_nm_san] = get_sanitized_names(ev_df[enrich_nm_col])
            enrich_vars_df = ev_df[ev_df[col_nm_san].str.lower().isin(ev_lower)]

        # make sure something was found, but don't break the runtime
        if len(enrich_vars_df) == 0:
            warn(
                f"It appears none of the input enrich enrich_variables were found in the {self.source} country.",
                UserWarning,
            )

        # if drop_duplicates, drop on variable name column to remove redundant matches
        if drop_duplicates:
            enrich_vars_df = enrich_vars_df.drop_duplicates(enrich_nm_col)

        # clean up the index
        enrich_vars_df.reset_index(drop=True, inplace=True)

        return enrich_vars_df

    def _enrich_variable_preprocessing(
        self, enrich_variables: Union[Iterable, pd.DataFrame]
    ) -> pd.DataFrame:
        """Provide flexibility for enrich variable preprocessing by enabling enrich enrich_variables
        to be specified in a variety of iterables, but always provide a standardized variable
        DataFrame as output.

        Args:
            enrich_variables: Iterable or pd.DataFrame of enrich enrich_variables.

        Returns:
            Pandas DataFrame of enrich enrich_variables.
        """
        # enrich variable dataframe column name
        enrich_str_col = "enrich_name"
        enrich_nm_col = "name"

        # if just a single variable is provided pipe it into a pandas series
        if isinstance(enrich_variables, str):
            enrich_variables = pd.Series([enrich_variables])

        # toss the enrich_variables into a pandas Series if an iterable was passed in
        elif isinstance(enrich_variables, Iterable) and not isinstance(
            enrich_variables, pd.DataFrame
        ):
            enrich_variables = pd.Series(enrich_variables)

        # if the enrich dataframe is passed in, check to make sure it has what we need, the right columns
        if isinstance(enrich_variables, pd.DataFrame):
            assert enrich_str_col in enrich_variables.columns, (
                f"It appears the dataframe used for enrichment does"
                f" not have the column with enrich string names "
                f"({enrich_str_col})."
            )
            assert enrich_nm_col in enrich_variables.columns, (
                f"It appears the dataframe used for enrichment does "
                f"not have the column with the enrich enrich_variables names "
                f"({enrich_nm_col})."
            )
            enrich_vars_df = enrich_variables

        # otherwise, create a enrich enrich_variables dataframe from the enrich series for a few more checks
        else:

            # get the enrich enrich_variables dataframe
            enrich_vars_df = self.get_enrich_variables_from_name_list(enrich_variables)

        # now, drop any duplicates so we're not getting the same variable twice from different data collections
        enrich_vars_df = enrich_vars_df.drop_duplicates("name").reset_index(drop=True)

        # note any enrich_variables submitted, but not found
        if len(enrich_variables) > len(enrich_vars_df.index):
            missing_count = len(enrich_variables) - len(enrich_vars_df.index)
            warn(
                "Some of the enrich_variables provided are not available for enrichment "
                f"(missing count: {missing_count:,}).",
                UserWarning,
            )

        # check to make sure there are enrich_variables for enrichment
        if len(enrich_vars_df.index) == 0:
            raise Exception(
                "There appear to be no enrich_variables selected for enrichment."
            )

        # get a list of the enrich_variables for enrichment
        enrich_variables = enrich_vars_df[enrich_str_col].reset_index()[enrich_str_col]

        return enrich_variables

    @lazy_property
    @local_vs_gis
    def geography_levels(self) -> pd.DataFrame:
        """Dataframe of available geography levels."""
        pass

    def get_geography_level(
        self,
        selector: [str, pd.DataFrame] = None,
        selection_field: str = "NAME",
        query_string: str = None,
        output_spatial_reference: Union[SpatialReference, dict, int] = 4326,
        return_geometry: bool = True,
    ) -> pd.DataFrame:
        """
        Get a DataFrame at an available geography_level level.

        Args:
            selector: Spatially Enabled DataFrame or string value used to select features.
                If a specific value can be identified using a string, even if
                just part of the field value, you can insert it here.
            selection_field: This is the field to be searched for the string values
                input into selector. It defaults to ``NAME``.
            query_string: If a more custom query is desired to filter the output, please
                use SQL here to specify the query. The normal query is ``UPPER(NAME) LIKE
                UPPER('%<selector>%')``. However, if a more specific query is needed, this
                can be used as the starting point to get more specific.
            output_spatial_reference: Desired spatial reference for returned data. This can be
                a spatial reference WKID as an integer, a dictionary representing the spatial
                reference, or a Spatial Reference object. The default is WGS84 (WKID 4326).
            return_geometry: Boolean indicating if geometry should be returned. While
                typically the case, there are instances where it is useful to not
                retrieve the geometries. This includes testing to create a query  only
                retrieving one area of interest.

        Returns:
            Pandas DataFrame of values fulfilling selection.
        """
        pass

    @lazy_property
    @local_vs_gis
    def travel_modes(self) -> pd.DataFrame:
        """Dataframe of available travel modes."""
        pass

    @local_vs_gis
    def enrich(
        self,
        geographies: Union[pd.DataFrame, Iterable, Path],
        enrich_variables: Union[pd.DataFrame, Iterable],
        return_geometry: bool = True,
        standard_geography_level: Union[int, str] = None,
        standard_geography_id_column: str = None,
        proximity_type: str = "straight_line",
        proximity_value: Union[float, int] = 1,
        proximity_metric: str = "Kilometers",
        output_spatial_reference: Union[int, dict, SpatialReference] = 4326,
        estimate_credits: bool = False,
        **kwargs,
    ) -> Union[pd.DataFrame, Path, float]:
        """
        Get demographic data apportioned to the input geographies based on population density
        weighting. Input geographies can be polygons or points. If providing point geographies,
        an area surrounding every point will be used to determine the area for enrichment.

        .. note::

            By default, point area is typically a buffered straight-line distance. However,
            if a transportation network is available, more accurate proximity metrics may be
            available, such as drive distance or drive time. This is the case if using ``local``
            (ArcGIS Pro with Business Analyst and local data) or a ``GIS`` object connected to ArcGIS
            Online, and very well may also the be the case if using an instance of ArcGIS Enterprise.

        Args:
            geographies: Required geographic areas or points to be enriched.
            enrich_variables: Enrichment enrich_variables to be used, typically discovered using
                the "enrich_variables" property.
            return_geometry: Optional boolean indicating if geometry is desired in the output.
                Default is True.
            standard_geography_level: If the input geographies are a standard geography level,
                it can be specified using either the standard geography index or the standard
                geography identifier retrieved using the Country.geography_levels property.
            standard_geography_id_column: Column with values uniquely identifying the input
                geographies using a standard level of geography. For example, in the United
                States, typically block groups are used for analysis if possible, and these
                block groups all have a unique identifier, typically referred to as the FIPS.
                If you have this value in a column of your data, it will *dramatically* speed
                up the enrichment process if you specify it in this parameter.
            proximity_type: Type of area to create around each point.
            proximity_value: Scalar value representing the proximity around each point to
                be used for creating an area for enrichment. For instance, if using 1.2 km,
                the input for this parameter is 1.2.
            proximity_metric: Scalar metric defining the point_proximity_value. Again, if
                1.2 km, the input for this metric will be kilometers.
            output_spatial_reference: Desired spatial reference for returned data. This can be
                a spatial reference WKID as an integer, a dictionary representing the spatial
                reference, or a Spatial Reference object. The default is WGS84 (WKID 4326).
            estimate_credits: While only useful for ArcGIS Online, enables populating the
                parameters just as you would for enriching using ArcGIS Online, and getting an
                estimate of the number of credits, which will be consumed if the enrich
                operation is performed. If this parameter is populated, the function will *not*
                perform the enrich operation or consume credits. Rather, it will *only* provide
                a credit consumption estimate.

        Returns:
            Pandas DataFrame, path to the output Feature Class or table, or float of predicted
            credit consumption.
        """
        pass


class Country(AOI):
    """
    Country enables access to Business Analyst functionality. Business Analyst
    data is available by iso3 using both ``local`` (ArcGIS Pro with the Business
    Analyst extension and local data) and ``GIS`` sources.

    Args:
            iso3: The country's ISO3 identifier.
            source: Optional ``GIS`` object or ``local`` keyword specifying the Business
                Analyst data and analysis source. If ``local``, the Python
                environment *must* have ``arcpy`` installed with bindings to ArcGIS
                Pro with the Business Analyst extension. If connecting to a ``GIS``
                instance, both ArcGIS Enterprise with Business Analyst and ArcGIS
                Online are supported. However, please be aware, any geoenrichment or
                analysis *will* consume ArcGIS Online credits.
            year: Optional integer explicitly specifying the year to reference.
                This is only honored if using local resources and the specified
                year is available.
    """

    def __init__(
        self, iso3: str, source: Union[str, GIS] = None, year: int = None, **kwargs
    ) -> None:

        # set the enrichment property
        self._ba = self._ba = (
            kwargs["enrichment"] if "enrichment" in kwargs else BusinessAnalyst(source)
        )

        # set the source (taking advantage of the setter in the parent)
        self.source = self._ba.source

        # set the iso3 property based on the iso3
        self.iso3 = self._ba._standardize_country_str(iso3)

        # use the iso3 to filter the available countries
        sel_df = self._ba.countries[self._ba.countries["iso3"] == self.iso3]

        # if the data source is local, but no year was provided, get the year
        if self.source == "local" and year is None:
            year = sel_df.vintage.max()

        # if the year is provided, validate
        elif self.source == "local" and year is not None:
            lcl_yr_vals = list(self._ba.countries.vintage)
            assert year in lcl_yr_vals, (
                f'The year you provided, "{year}" is not among the available '
                f'years ({", ".join([str(v) for v in lcl_yr_vals])}) for "{self.iso3.upper()}".'
            )

        # if source is GIS and year is provided, warn will be ignored
        elif isinstance(self.source, GIS) and year is not None:
            warn(
                "Explicitly specifying a year (vintage) is not supported when using a GIS instance as the source."
            )

        # add the properties for the iso3
        self.properties = (
            sel_df[sel_df.vintage == year].iloc[0]
            if self.source == "local"
            else sel_df.iloc[0]
        )

        # if local, set a few more properties
        if self.source == "local":

            # to avoid confusion, add year as alias to vintage
            self.properties["year"] = self.properties["vintage"]

            # ensure analysis uses correct data source
            self._set_local_data_source()

            # set the path to the network dataset
            self.properties["network_path"] = self._get_network_dataset_path_local()

    def __repr__(self):
        repr_str = f"<{type(self).__name__} - {self.iso3}"

        if self.source == "local":
            repr_str = f"{repr_str} {self.properties.vintage} (local)>"
        else:
            repr_str = f"{repr_str} ({self.source})>"

        return repr_str

    def _get_network_dataset_path_local(self) -> str:
        """Get the path to the network dataset for this country."""
        import arcpy

        # get a dictionary of dataset properties
        ds_dict = {ds["id"]: ds for ds in arcpy._ba.getLocalDatasets()}

        # get the path to the network dataset using the country id
        src_pth = ds_dict[self.properties.country_id]["networkDatasetPath"]

        return src_pth

    def _set_local_data_source(self) -> None:
        """Ensure analysis uses the correct data source."""
        import arcpy

        arcpy.env.baDataSource = f"LOCAL;;{self.properties.country_id}"

    def _enrich_variables_local(self) -> pd.DataFrame:
        """Local implementation of enrich_variables property and only available by iso3 currently."""
        # lazy load
        from arcpy._ba import ListVariables

        # pull out the iso3 dataframe to a variable for clarity
        cntry_df = self._ba.countries

        # create a filter to select the right iso3 and year dataset
        dataset_fltr = (cntry_df["iso3"] == self.iso3) & (
            cntry_df["vintage"] == int(self.properties.vintage)
        )

        # get the iso3 identifier needed for listing enrich_variables
        ba_id = cntry_df[dataset_fltr].iloc[0]["country_id"]

        # retrieve variable objects
        var_gen = ListVariables(ba_id)

        # use a list comprehension to unpack the properties of the enrich_variables into a dataframe
        var_df = pd.DataFrame(
            (
                (v.Name, v.Alias, v.DataCollectionID, v.FullName, v.OutputFieldName)
                for v in var_gen
            ),
            columns=[
                "name",
                "alias",
                "data_collection",
                "enrich_name",
                "enrich_field_name",
            ],
        )

        return var_df

    def _geography_levels_local(self):
        """Local implementation of geography_levels."""
        import arcpy

        # get a dataframe of level properties for the country
        geo_lvl_df = pd.DataFrame.from_records(
            [
                lvl.__dict__
                for lvl in arcpy._ba.ListGeographyLevels(self.properties.country_id)
            ]
        )

        # reverse sorting order so smallest is at the top
        geo_lvl_df = geo_lvl_df.iloc[::-1].reset_index(drop=True)

        # calculate a field for use in the accessor
        geo_lvl_df.insert(
            0,
            "level_name",
            geo_lvl_df["LevelID"].apply(lambda val: pep8ify(val.split(".")[1])),
        )

        # purge columns and include AdminLevel if present (added in Pro 2.9)
        out_col_lst = [
            "level_name",
            "SingularName",
            "PluralName",
            "LevelName",
            "LayerID",
            "IDField",
            "NameField",
        ]
        if "AdminLevel" in list(geo_lvl_df.columns):
            out_col_lst = out_col_lst + ["AdminLevel"]
        geo_lvl_df.drop(
            columns=[c for c in geo_lvl_df.columns if c not in out_col_lst], drop=True
        )

        # rename fields for consistency
        out_rename_dict = {
            "SingularName": "singular_name",
            "PluralName": "plural_name",
            "LevelName": "alias",
            "LayerID": "level_id",
            "IDField": "id_field",
            "NameField": "name_field",
            "AdminLevel": "admin_level",
        }
        geo_lvl_df.rename(columns=out_rename_dict, inplace=True, errors="ignore")

        return geo_lvl_df

    def _geography_levels_gis(self):
        """GIS implementation of geography levels."""
        # unpack the geoenrichment url from the properties
        enrich_url = self.source.properties.helperServices.geoenrichment.url

        # construct the url to the standard geography levels
        url = f"{enrich_url}/Geoenrichment/standardgeographylevels"

        # get the geography levels from the enrichment server
        res_json = self.source._con.post(url, {"f": "json"})

        # unpack the geography levels from the json
        geog_lvls = res_json["geographyLevels"]

        # get matching geography levels out of the list of countries
        for lvl in geog_lvls:
            if lvl["countryID"] == self.properties.iso2:
                geog = lvl
                break  # once found, bust out of the loop

        # get the hierarchical levels out as a dataframe
        geo_lvl_df = pd.DataFrame(geog["hierarchies"][0]["levels"])

        # reverse the sorting so the smallest is at the top
        geo_lvl_df = geo_lvl_df.iloc[::-1].reset_index(drop=True)

        # create consistent naming convention
        geo_lvl_df["level_name"] = geo_lvl_df["id"].apply(
            lambda val: pep8ify(val.split(".")[1])
        )

        # clean up the field names so they follow more pythonic conventions and are consistent
        geo_lvl_df = geo_lvl_df[
            ["level_name", "singularName", "pluralName", "name", "id", "adminLevel"]
        ].copy()
        geo_lvl_df.columns = [
            "level_name",
            "singular_name",
            "plural_name",
            "alias",
            "level_id",
            "admin_level",
        ]

        return geo_lvl_df

    def _travel_modes_local(self):
        """Local implementation of travel modes."""
        # get a list of useful information about each travel mode
        mode_lst = [
            [
                mode.name,
                mode.description,
                mode.type,
                mode.impedance,
                mode.timeAttributeName,
                mode.distanceAttributeName,
            ]
            for mode in self._travel_modes_dict_local.values()
        ]

        # create a dataframe of the travel modes
        mode_df = pd.DataFrame(
            mode_lst,
            columns=[
                "alias",
                "description",
                "type",
                "impedance",
                "time_attribute_name",
                "distance_attribute_name",
            ],
        )

        # add a pep8tified name for each travel mode
        mode_name = mode_df["alias"].apply(lambda val: pep8ify(val))
        mode_df.insert(0, "name", mode_name)

        # calculate impedance category
        imped_cat = mode_df["impedance"].apply(
            lambda val: "temporal" if val.lower().endswith("time") else "distance"
        )
        insert_idx = mode_df.columns.get_loc("impedance") + 1
        mode_df.insert(insert_idx, "impedance_category", imped_cat)

        return mode_df

    @lazy_property
    def _travel_modes_dict_local(self) -> dict:
        """Since looking up the travel modes is time consuming, use a lazy property to cache it."""
        import arcpy

        return arcpy.nax.GetTravelModes(self.properties.network_path)

    def _enrich_local(
        self,
        geographies: Union[pd.DataFrame, Iterable, Path],
        enrich_variables: Union[pd.DataFrame, Iterable],
        return_geometry: bool = True,
        standard_geography_level: Union[int, str] = None,
        standard_geography_id_column: str = None,
        proximity_type: str = "straight_line",
        proximity_value: Union[float, int] = 1,
        proximity_metric: str = "Kilometers",
        output_spatial_reference: Union[int, dict, SpatialReference] = 4326,
        estimate_credits: bool = False,
        **kwargs,
    ) -> Union[pd.DataFrame, Path, float]:
        """Local enrich method implementation."""
        # throw error if trying to estimate credits
        msg_crdt = (
            "Credit estimation is only relevant and supported with ArcGIS Online."
        )
        assert not estimate_credits, msg_crdt

        # lazy load arcpy
        import arcpy

        # make sure the correct data source is being used
        self._set_local_data_source()

        # if the geographies was input as a string path, make it into a path
        if isinstance(geographies, str):
            geographies = Path(geographies)

        # if a dataframe
        if isinstance(geographies, pd.DataFrame):

            # if a standard_geography_id_column is provided
            if standard_geography_id_column:

                # ensure column is in table
                assert standard_geography_id_column in list(geographies.columns), (
                    f"The provided "
                    f"standard_geography_id_column, "
                    f"{standard_geography_id_column}, "
                    f"does not appear to be one of the "
                    f"column names in the provided "
                    f"geographies dataframe."
                )

                # set the geographies to a list of standard geographies pulled from the specified column
                geographies = list(geographies[standard_geography_id_column])

            # if no standard geography id column
            else:

                # make sure the dataframe is spatial
                assert geographies.spatial.validate(), (
                    "If providing a dataframe for enrich without a "
                    "standard_geography_id_column, it must be a Spatially Enabled "
                    "DataFrame."
                )

                # convert to a list of arcpy geometry objects
                geographies = geography_iterable_to_arcpy_geometry_list(geographies)

        # if using standard geographies with a table input, either non-spatial or spatial (feature class)
        if isinstance(geographies, Path):

            # if a standard geography column is provided
            if standard_geography_id_column:

                # validate is recognized format by ArcGIS
                assert arcpy.Exists(str(geographies)), (
                    f"It appears the path to the enrich geographies you input, "
                    f"{str(geographies)}, is not a path to a supported ArcGIS "
                    f"dataset."
                )

                # ensure the standard_geography_id_column is in the input geographies
                fld_nm_lst = [f.name for f in arcpy.ListFields(geographies)]
                assert standard_geography_id_column in fld_nm_lst, (
                    "It appears the provided "
                    "standard_geography_id_column is not a field name "
                    "in the input geographies."
                )

                # get a list of standard geography identifiers from the standard geography column
                geographies = [
                    r[0]
                    for r in arcpy.da.SearchCursor(
                        str(geographies), standard_geography_id_column
                    )
                ]

            # otherwise, just get a list of geometry objects for processing
            else:
                geographies = [
                    r[0] for r in arcpy.da.SearchCursor(geographies, "SHAPE@")
                ]

        # ensure if a standard geography column is provided, a standard geography level is provided as well
        if standard_geography_id_column:
            assert standard_geography_level is not None, (
                "If providing a standard_geography_id_column, a "
                "standard_geography_level must also be specified."
            )

        # if a standard geography level is provided
        if standard_geography_level is not None:

            # if a table is provided, make sure a column is specified with the geography identifiers
            if isinstance(geographies, (Path, pd.DataFrame)):
                assert standard_geography_id_column is not None, (
                    "If providing a path to tabular data (table or "
                    "Feature Class), and also providing a "
                    "standard_geography_id_column, you must also "
                    "specify a standard_geography_level. These can be "
                    f"discovered using {self.__name__}.geography_levels."
                )

            # otherwise, if an iterable is provided, ensure the iterable is all integers or strings
            else:
                assert all([isinstance(val, (int, str)) for val in geographies]), (
                    "If providing a list of geography "
                    "identifiers, you must also "
                    "specify a "
                    "standard_geography_level. These "
                    "can be discovered using "
                    f"{self.__name__}.geography_levels."
                )

            # get the geography level if index passed in
            if isinstance(standard_geography_level, int):
                msg_std_geo = (
                    f"There are only {len(self.geography_levels.index)} available. Please use an index "
                    f"between 0 and {len(self.geography_levels.index) - 1}.",
                )
                ast_stdgeo = standard_geography_level <= len(
                    self.geography_levels.index
                )
                assert ast_stdgeo, msg_std_geo
                geo_lvl = self.geography_levels.iloc[standard_geography_level][
                    "level_id"
                ]

            # get the geography level if the string level passed in
            elif isinstance(standard_geography_level, str):
                geo_lvl_df = self.geography_levels[
                    self.geography_levels["level_name"] == standard_geography_level
                ]
                assert len(geo_lvl_df.index) > 0, (
                    f"The specified geography level, {standard_geography_level}, does "
                    f"not appear to be one of the available standard geography levels. "
                    f'This must be a value from the "level_name" column in the '
                    f'dataframe available from the "{self.__name__}.geography_levels" '
                    f"property."
                )
                geo_lvl = geo_lvl_df.iloc[0]["level_id"]

            # if not an integer or string, provide a fall through
            else:
                raise ValueError(
                    "The standard_geography_level must be either an integer or string. Valid values can "
                    f"be discovered using {self.__name__}.geography_levels. Either the index or "
                    f"level_name can be used."
                )

            # create a standard geography level feature class in memory to speed up the Enrich Layer tool
            id_lst = ",".join([str(v) for v in geographies])
            geographies = arcpy.ba.StandardGeographyTA(
                geo_lvl,
                out_feature_class=f"memory/std_geo_lvl_{uuid.uuid4().hex}",
                input_type="LIST",
                ids_list=id_lst,
            )[0]

        # prep the enrich enrich_variables
        enrich_vars = self._enrich_variable_preprocessing(enrich_variables)
        vars_str = ";".join(enrich_vars)

        # check the geometry type if list of geographies is being used and the geometry type is a point
        is_pt = (
            geographies[0].type.lower() == "point"
            if isinstance(geographies, list)
            else False
        )

        if is_pt:

            # make sure the proximity_type is lowercase
            proximity_type = proximity_type.lower()

            # if just straight line, set the impedance category to distance and travel mode
            if proximity_type == "straight_line" or proximity_type == "straight line":
                impd_cat = "distance"
                trvl_md = proximity_type

            # otherwise, try to pull it out of travel modes
            else:

                # try to get the travel mode by name
                if proximity_type in self.travel_modes["name"].values:
                    trvl_md = self.travel_modes[
                        self.travel_modes["name"] == proximity_type
                    ].iloc[0]

                # try to get travel mode by alias
                elif proximity_type in self.travel_modes["alias"].values:
                    trvl_md = self.travel_modes[
                        self.travel_modes["alias"] == proximity_type
                    ].iloc[0]

                # try to get travel mode by index
                elif isinstance(proximity_type, int):

                    assert len(self.travel_modes.index) >= proximity_type, (
                        "The travel mode index is not  in "
                        "the range of available indicies, "
                        f"0-{len(self.travel_modes.index)}."
                    )
                    trvl_md = self.travel_modes.loc[proximity_type]

                # if travel mode not found, error out
                else:
                    raise ValueError(
                        f"proximity_type must be among those available from "
                        f"{self.__name__}.travel_modes in the name column or simply "
                        f'"straight_line". You provided {proximity_type}.'
                    )

                # finally, pull the impedance category out of the retrieved series
                impd_cat = trvl_md["impedance_category"]

            # based on the impedance category (temporal or distance) get valid proximity metrics
            if impd_cat == "distance":
                valid_metric_lst = ["Miles", "Yards", "Feet", "Kilometers", "Meters"]
            else:
                valid_metric_lst = ["Hours", "Minutes", "Seconds"]

            # ensure the proximity metric input first letter is capitalized
            proximity_metric = proximity_metric.title()

            # validate the input proximity metric
            assert proximity_metric in valid_metric_lst, (
                f"If using a {impd_cat} proximity type, the "
                f"proximty_metric must be one of "
                f'[{",".join(valid_metric_lst)}]'
            )

            # TODO - remove once issue with point geometry list error is addressed
            if not pro_at_least_version("2.9"):
                geographies = arcpy.management.CopyFeatures(
                    geographies, f"memory/points_{uuid.uuid4().hex}"
                )[0]

            # invoke enrichment using proximity around points
            enrich_fc = arcpy.ba.EnrichLayer(
                geographies,
                out_feature_class=f"memory/enrich_{uuid.uuid4().hex}",
                variables=vars_str,
                buffer_type=trvl_md,
                distance=proximity_value,
                unit=proximity_metric,
            )[0]

            # TODO - remove once issue with point geometry list error is addressed
            if not pro_at_least_version("2.9"):
                arcpy.management.Delete(geographies)

        # if not points, just enrich
        else:
            enrich_fc = arcpy.ba.EnrichLayer(
                geographies,
                out_feature_class=f"memory/enrich_{uuid.uuid4().hex}",
                variables=vars_str,
            )[0]

        # if geometry is not desired, load the data using a cursor for efficiency
        if return_geometry:
            oid_col = arcpy.da.Describe(enrich_fc)["OIDFieldName"]
            enrich_df = GeoAccessor.from_featureclass(enrich_fc).drop(columns=oid_col)
            enrich_df.spatial.set_geometry("SHAPE")

            # validate and set output spatial reference
            out_sr = validate_spatial_reference(output_spatial_reference)
            enrich_df = change_spatial_reference(enrich_df, out_sr)

        # if not retaining the geometry, build the dataframe using a cursor...much faster
        else:
            oid_col = arcpy.da.Describe(enrich_fc)["OIDFieldName"]
            cols = [
                f.name
                for f in arcpy.ListFields(enrich_fc)
                if f.name.lower() != "shape" and f.name != oid_col
            ]
            data = [r for r in arcpy.da.SearchCursor(enrich_fc, cols)]
            enrich_df = pd.DataFrame(data, columns=cols)

        # clean up temp datasets
        arcpy.management.Delete(enrich_fc)
        if isinstance(geographies, str):
            if "std_geo_lvl" in geographies:
                arcpy.management.Delete(geographies)

        # standardize column names to be consistent with results from REST enrich services
        mtch_df = self.get_enrich_variables_from_name_list(enrich_df.columns).set_index(
            "enrich_field_name"
        )
        col_lst = [
            mtch_df.loc[col]["name"] if col in mtch_df.index else col
            for col in enrich_df.columns
        ]
        col_lst = [col.upper() if col == "shape" else pep8ify(col) for col in col_lst]
        enrich_df.columns = col_lst

        # put the source in the attrs for potential later access
        enrich_df.attrs["ba_aoi"] = self

        return enrich_df

    def _enrich_gis(
        self,
        geographies: Union[pd.DataFrame, Iterable, Path],
        enrich_variables: Union[pd.DataFrame, Iterable],
        return_geometry: bool = True,
        standard_geography_level: Union[int, str] = None,
        standard_geography_id_column: str = None,
        proximity_type: str = "straight_line",
        proximity_value: Union[float, int] = 1,
        proximity_metric: str = "Kilometers",
        output_spatial_reference: Union[int, dict, SpatialReference] = 4326,
        estimate_credits: bool = False,
        **kwargs,
    ) -> Union[pd.DataFrame, Path, float]:
        """Web GIS enrich method implementation."""
        # get the enrichment variables as a dataframe
        evars = self._enrich_variable_preprocessing(enrich_variables)

        # start building out the package for enrich REST call
        params = {"f": "json", "analysisVariables": list(evars)}

        # get the maximum batch size
        svc_lmt_url = f'{self.source.properties.helperServices("geoenrichment").url}/Geoenrichment/ServiceLimits'
        max_batch_res = self.source._con.get(svc_lmt_url)
        std_batch_size = [
            v["value"]
            for v in max_batch_res["serviceLimits"]["value"]
            if v["paramName"] == "maxRecordCount"
        ][0]
        geom_batch_size = [
            v["value"]
            for v in max_batch_res["serviceLimits"]["value"]
            if v["paramName"] == "optimalBatchStudyAreasNumber"
        ][0]

        # list to store inputs and results
        in_req_list, out_df_lst = [], []

        # if using standard geography level ...
        if (
            standard_geography_level is not None
            or standard_geography_id_column is not None
        ):

            # try to get the geography level row using the name or index
            geo_lvl_df = self.geography_levels[
                (self.geography_levels["level_name"] == standard_geography_level)
                | (self.geography_levels.index == standard_geography_level)
            ]
            assert len(geo_lvl_df.index) > 0, (
                f"The specified geography level, {standard_geography_level} does not "
                f"appear to be one of the available geography levels. This must be a "
                f'value from the "name" column in the dataframe available from the '
                f"{self.__name__}.geography_levels property."
            )

            # cannot simply toss in random iterable - need a dataframe or path
            msg_isgeo = "If using standard geographies, the input geographies must be a dataframe or Iterable."
            assert isinstance(geographies, (Iterable, pd.Series)), msg_isgeo

            # if a dataframe is being used for input
            if isinstance(geographies, pd.DataFrame):

                # must have both the level and the column with the ID's specified
                msg_lvlandid = (
                    "Both standard_geography_level and standard_geography_id_column must be provided to "
                    "enrich using standard geographies."
                )
                ast_lvlandid = (
                    standard_geography_level is not None
                    and standard_geography_id_column is not None
                )
                assert ast_lvlandid, msg_lvlandid

                # make sure the standard geography id column is available
                msg_idandcols = (
                    f"The provided standard_geography_id_column, {standard_geography_id_column}, does "
                    f"not appear to be an available column."
                )
                ast_idandcols = standard_geography_id_column in geographies.columns
                assert ast_idandcols, msg_idandcols

                # create a list of standard geography id's to use for enrichment
                std_geo_id_lst = list(geographies[standard_geography_id_column])

            # if a pd.Series, make into a list
            elif isinstance(geographies, pd.Series):
                std_geo_id_lst = list(geographies)

            # otherwise, just put the iterable into the std geo is list
            else:
                std_geo_id_lst = geographies

            # get the geography level id out of the dataframe
            geo_lvl = geo_lvl_df.iloc[0]["level_id"]

            # get the length of geographies for iteration
            len_geo = (
                len(geographies.index)
                if isinstance(geographies, pd.DataFrame)
                else len(geographies)
            )

            # use the count of features and the max batch size to iteratively enrich the input data
            for x in range(0, len_geo, std_batch_size):

                # peel off just the id's for this batch
                batch_id_lst = std_geo_id_lst[x : x + std_batch_size]

                params["studyAreas"] = [
                    {
                        "sourceCountry": geo_lvl.split(".")[0],
                        "layer": geo_lvl,
                        "ids": batch_id_lst,
                    }
                ]

                # add the payload onto the list
                in_req_list.append(deepcopy(params))

        # if not using standard geographies, working with geometries
        else:

            # handle all manner of possible inputs
            geographies = get_spatially_enabled_dataframe(geographies)

            # do not need to return geography since have it already in source data
            return_geometry = False

            # use the count of features and the max batch size to iteratively create batched payloads
            for x in range(0, len(geographies.index), geom_batch_size):

                # get a slice of the input data to enrich for this
                in_batch_df = geographies.iloc[x : x + geom_batch_size]

                # format the features for sending - keep it light, just the geometry
                features = in_batch_df[in_batch_df.spatial.name].to_frame()
                features.spatial.set_geometry(geographies.spatial.name)
                features = features.spatial.to_featureset().features
                params["studyAreas"] = [f.as_dict for f in features]

                # get the input spatial reference
                params["insr"] = geographies.spatial.sr

                # ensure the value is correct for returning geometry...or not
                params["returnGeometry"] = "true" if return_geometry else "false"

                # add the payload onto the list
                in_req_list.append(deepcopy(params))

        # iterate the packaged request payloads
        for idx, req_params in enumerate(in_req_list):

            # send the request to the server using post because if sending geometry, the message can be big
            enrich_url = self.source.properties.helperServices("geoenrichment").url
            r_json = self.source._con.post(
                f"{enrich_url}/Geoenrichment/Enrich", params=req_params
            )

            # ensure a valid result is received
            if "error" in r_json:
                err = r_json["error"]
                raise Exception(
                    f"Error in enriching data using Business Analyst Enrich REST endpoint. Error "
                    f'Code {err["code"]}: {err["message"]}'
                )

            # unpack the enriched results - reaching into the FeatureSet for just the attributes
            r_df = pd.DataFrame(
                [
                    f["attributes"]
                    for f in r_json["results"][0]["value"]["FeatureSet"][0]["features"]
                ]
            )

            # add the dataframe to the list
            out_df_lst.append(r_df)

        # combine all the received enriched data, and get rid of extra columns and add onto the original data
        enrich_df = pd.concat(out_df_lst).reset_index(drop=True)
        del out_df_lst
        drop_cols = [c for c in enrich_df.columns if "objectid" in c.lower()] + ["ID"]
        enrich_df.drop(columns=drop_cols, inplace=True)

        # if the input dataframe has geometry, but the geometry is not desired from the output, get rid of it
        if isinstance(geographies, pd.DataFrame):
            if geographies.spatial.validate():
                geographies.drop(columns=geographies.spatial.name, inplace=True)

        # if the input was just a list of id's, just convert the dataframe
        if isinstance(geographies, pd.DataFrame):
            out_df = pd.concat([geographies, enrich_df], axis=1, sort=False)
        else:
            out_df = enrich_df

        # if geometry, which may not be, but if there is, clean up and make sure everything is as expected
        if "SHAPE" in out_df.columns:

            # ensure it is valid to begin with - doubtful after the join
            out_df.spatial.set_geometry("SHAPE")

            # shuffle columns so geometry is at the end
            out_df = out_df[[c for c in out_df.columns if c != "SHAPE"] + ["SHAPE"]]

            # set the geometry
            out_df.spatial.set_geometry("SHAPE")

            # set to output spatial reference
            out_df = change_spatial_reference(out_df, output_spatial_reference)

        # proactively change the column names so no surprises if exporting to a feature class later
        out_df.columns = [pep8ify(c) if c != "SHAPE" else c for c in out_df.columns]

        # put the source in the attrs for potential later access
        out_df.attrs["ba_aoi"] = self

        return out_df


class BusinessAnalyst(object):
    """
    The BusinessAnalyst object enables access to Business Analyst functionality thorough a specified
    source. A source can either be in an environment with ArcGIS Pro with Business Analyst and local
    data (``local``) or a Web GIS (``GIS``) object instance. The Web GIS can reference either an
    instance of ArcGIS Enterprise with Business Analyst or ArcGIS Online.

    .. note::

        If the source is not explicitly set, the ``BusinessAnalyst`` object will first try to use
        ``local``, ArcGIS Pro with the Business Analyst extension. If this is not available,
        ``BusinessAnalyst`` will try to use a ``GIS`` object instance already in the session. If
        neither is available, and a ``source`` is not set, this will invoke an error.

    .. warning::

        GeoEnrichment (adding demographic enrich_variables) using ArcGIS Online *does* cost credits.
        Country (``BusinessAnalyst.countries``) and variable (``Country.enrich_variables``)
        introspection does *not* cost any credits.

    Args:
        source: Optional ``GIS`` object or ``local`` keyword specifying the Business
            Analyst data and analysis source. If ``local``, the Python
            environment *must* have ``arcpy`` installed with bindings to ArcGIS
            Pro with the Business Analyst extension. If connecting to a ``GIS``
            instance, both ArcGIS Enterprise with Business Analyst and ArcGIS
            Online are supported. However, please be aware, any geoenrichment or
            analysis *will* consume ArcGIS Online credits.
    """

    def __init__(self, source: Union[str, GIS] = None) -> None:

        # set the source, defaulting, based on what is available, to local or active_gis, or simply error if neither
        self.source = set_source(source)

    def __repr__(self):
        repr_str = f"<{type(self).__name__} ({self.source})>"
        return repr_str

    @lazy_property
    @local_vs_gis
    def countries(self) -> pd.DataFrame:
        """DataFrame of available countries with relevant metadata columns based on the source."""
        pass

    def _countries_local(self) -> pd.DataFrame:
        """Local countries implementation."""
        # lazy load to avoid import issues
        import arcpy._ba

        # get a generator of dataset objects
        ds_lst = list(arcpy._ba.ListDatasets())

        # throw error if no local datasets are available
        assert len(ds_lst), (
            "No datasets are available locally. If you want to locate available countries on a "
            "Web GIS, please provide a GIS object instance for the source parameter when creating "
            "the BusinessAnalyst object."
        )

        # organize all the iso3 dataset properties
        cntry_lst = [
            (
                ds.CountryInfo.Name,
                ds.Version,
                ds.CountryInfo.ISO2,
                ds.CountryInfo.ISO3,
                ds.DataSourceID,
                ds.ID,
            )
            for ds in ds_lst
        ]

        # create a dataframe of the iso3 properties
        cntry_df = pd.DataFrame(
            cntry_lst,
            columns=[
                "country_name",
                "vintage",
                "iso2",
                "iso3",
                "data_source_id",
                "country_id",
            ],
        )

        # convert the vintage years to integer
        cntry_df["vintage"] = cntry_df["vintage"].astype("int64")

        # ensure the values are in order by iso3 and year
        cntry_df.sort_values(["iso3", "vintage"], inplace=True)

        # organize the columns
        cntry_df = cntry_df[
            ["iso2", "iso3", "country_name", "vintage", "country_id", "data_source_id"]
        ]

        return cntry_df

    def _countries_gis(self) -> pd.DataFrame:
        """GIS countries implementation."""
        # make sure countries are available
        ge_err_msg = (
            "The provided GIS instance does not appear to have geoenrichment enabled and configured, "
            "so no countries are available."
        )
        assert "geoenrichment" in self.source.properties.helperServices, ge_err_msg
        assert isinstance(
            self.source.properties.helperServices.geoenrichment["url"], str
        ), ge_err_msg

        # extract out the geoenrichment url
        ge_url = self.source.properties.helperServices.geoenrichment["url"]
        if self.source._is_hosted_nb_home:
            res = self.source._private_service_url(ge_url)
            ge_url = (
                res["privateServiceUrl"]
                if "privateServiceUrl" in res
                else res["serviceUrl"]
            )

        # get a list of countries available on the Web GIS for enrichment
        url = f"{ge_url}/Geoenrichment/Countries"
        cntry_res = self.source._con.post(url, {"f": "json"})
        cntry_dict = cntry_res["countries"]

        # convert the dictionary to a dataframe
        cntry_df = pd.DataFrame(cntry_dict)

        # clean up some column names for consistency
        cntry_df.rename(
            {
                "id": "iso2",
                "abbr3": "iso3",
                "name": "country_name",
                "altName": "alt_name",
                "defaultDatasetID": "default_dataset",
            },
            inplace=True,
            axis=1,
        )
        cntry_df.drop(
            columns=[
                "distanceUnits",
                "esriUnits",
                "hierarchies",
                "currencySymbol",
                "currencyFormat",
                "defaultDataCollection",
                "dataCollections",
                "defaultReportTemplate",
                "defaultExtent",
            ],
            inplace=True,
        )
        cntry_df = cntry_df[
            [
                "iso2",
                "iso3",
                "country_name",
                "datasets",
                "default_dataset",
                "alt_name",
                "continent",
            ]
        ]

        return cntry_df

    def _standardize_country_str(self, country_string: str) -> str:
        """Internal helper method to standardize the input for iso3 identifier strings to ISO3."""
        # cast to lowercase to sidestep any issues with case
        cntry_str = country_string.lower()

        # filter functions for getting the iso3 iso3 value
        iso3_fltr = self.countries["iso3"].str.lower() == cntry_str
        iso2_fltr = self.countries["iso2"].str.lower() == cntry_str
        name_fltr = self.countries["country_name"].str.lower() == cntry_str

        # construct the filter, using alias if working online
        cntry_fltr = iso3_fltr | iso2_fltr | name_fltr
        if isinstance(self.source, GIS):
            alias_fltr = self.countries["alt_name"].str.lower() == cntry_str
            cntry_fltr = cntry_fltr | alias_fltr

        # query available countries to see if the requested iso3 is available
        fltr_df = self.countries[cntry_fltr]

        if len(fltr_df.index) > 0:
            iso3_str = fltr_df.iloc[0]["iso3"]
        else:
            raise ValueError(
                f'The provided iso3 code, "{country_string}" does not appear to be available. Please '
                f"choose from the available country iso3 codes discovered using the "
                f"BusinessAnalyst.countries property."
            )

        return iso3_str

    def get_country(self, iso3: str, year: int = None) -> Country:
        """
        Get a Country object instance.

        Args:
            iso3: Required string, the country's ISO3 identifier.
            year: Optional integer explicitly specifying the year to reference. This
                is only honored if using local resources and the specified year is
                available.

        Returns:
            Country object instance.

        A Country object instance can be created to work with Business Analyst data installed
        either locally with ArcGIS Pro or remotely through a Web GIS using a GIS object instance.

        .. code-block:: python

            from business_analyst import BusinessAnalyst
            ba = BusinessAnalyst('local')  # using ArcGIS Pro with Business Analyst
            usa = ba.get_country('USA')  # USA with most current data installed on machine

        .. code-block:: python

            from business_analyst import BusinessAnalyst
            ba = BusinessAnalyst('local')
            usa = ba.get_country('USA', year=2019)  # explicitly specifying the year with local data

        .. code-block:: python

            from arcgis.gis import GIS
            from business_analyst import BusinessAnalyst
            gis = GIS(username='my_username', password='$up3r$3cr3tP@$$w0rd')
            ba = BusinessAnalyst(gis)  # using ArcGIS Online
            usa = ba.get_country('USA')

        Once instantiated, available enrichment enrich_variables can be discovered and used for
        geoenrichment.

        .. code-block:: python

            # get the enrichment enrich_variables as a Pandas DataFrame
            evars = usa.enrich_variables

            # filter to just current year key enrich_variables
            kvars = [
                (evars.name.str.endswith('CY'))
                & (evars.data_collection.str.startswith('Key')
            ]

        Then, based on the environment being used for GeoEnrichment, these variable identifiers
        can be formatted for input into the respective enrich functions, `EnrichLayer`_ in Pro
        or `enrich`_ in the Python API. In the code below, the local and the Web GIS blocks will
        produce very similar outputs with the only differences being the column names.

        .. code-block:: python

            from arcgis.features import GeoAccessor
            import pandas as pd

            input_fc = 'C:/path/to/data.gdb/feature_class'
            output_pth = 'C:/path/to/data.gdb/enrich_features'

            # local geoenrichment
            import arcpy
            kvars_lcl = ';'.join(kvars.enrich_name)  # combine into semicolon separated string
            enrich_pth = arcpy.ba.EnrichLayer(input_fc, out_feature_class=output_pth, enrich_variables=kvars_lcl)[0]
            enrich_df = pd.DataFrame.spatial.from_featureclass(enrich_pth)  # dataframe for more analysis

            # WebGIS geoenrichment
            from arcgis.geoenrichment import enrich
            kvars_gis = ';'.join(kvars.name)
            in_df = pd.DataFrame.spatial.from_featureclass(input_fc)
            enrich_df = enrich(in_df, analysis_variables=kvars_gis, return_geometry=False)
            enrich_pth = enrich_df.spatial.to_table(output_pth)  # saving so do not have to re-run

        .. _EnrichLayer: https://pro.arcgis.com/en/pro-app/latest/tool-reference/business-analyst/enrich-layer-advanced.htm
        .. _enrich: https://developers.arcgis.com/python/api-reference/arcgis.geoenrichment.html#enrich

        """
        # standardize iso3 string to iso3 identifier
        iso3 = self._standardize_country_str(iso3)

        # create a iso3 object instance
        cntry = Country(iso3, year=year, enrichment=self)

        return cntry
