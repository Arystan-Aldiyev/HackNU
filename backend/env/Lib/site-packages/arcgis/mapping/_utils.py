import os
import logging as _logging
import arcgis


_log = _logging.getLogger(__name__)

_use_async = False


def _get_list_value(index, array):
    """
    helper operation to loop a list of values regardless of the index value

    Example:
    >>> a = [111,222,333]
    >>> list_loop(15, a)
    111
    """
    if len(array) == 0:
        return None
    elif index >= 0 and index < len(array):
        return array[index]
    return array[index % len(array)]


def export_map(
    web_map_as_json=None, format="""PDF""", layout_template="""MAP_ONLY""", gis=None
):
    """
    The ``export_map`` function takes the state of the ``WebMap`` object (for example, included services, layer visibility
    settings, client-side graphics, and so forth) and returns either (a) a page layout or
    (b) a map without page surrounds of the specified area of interest in raster or vector format.
    The input for this function is a piece of text in JavaScript object notation (JSON) format describing the layers,
    graphics, and other settings in the web map. The JSON must be structured according to the WebMap specification
    in the ArcGIS Help.

    .. note::
        The ``export_map`` tool is shipped with ArcGIS Server to support web services for printing, including the
        preconfigured service named ``PrintingTools``.


    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    web_map_as_json        Web Map JSON along with export options. See the
                           `Export Web Map Specifications <https://developers.arcgis.com/rest/services-reference/exportwebmap-specification.htm>`_
                           for more information on structuring this JSON.
    ------------------     --------------------------------------------------------------------
    format                 Format (str). Optional parameter.  The format in which the map image
                           for printing will be delivered. The following strings are accepted.
                           For example:PNG8
                           Choice list:['PDF', 'PNG32', 'PNG8', 'JPG', 'GIF', 'EPS', 'SVG', 'SVGZ']
    ------------------     --------------------------------------------------------------------
    layout_template        Layout Template (str). Optional parameter.  Either a name of a
                           template from the list or the keyword MAP_ONLY. When MAP_ONLY is chosen
                           or an empty string is passed in, the output map does not contain any
                           page layout surroundings (for example title, legends, scale bar,
                           and so forth). Choice list:['A3 Landscape', 'A3 Portrait',
                           'A4 Landscape', 'A4 Portrait', 'Letter ANSI A Landscape',
                           'Letter ANSI A Portrait', 'Tabloid ANSI B Landscape',
                           'Tabloid ANSI B Portrait', 'MAP_ONLY']. You can get the layouts
                           configured with your GIS by calling the
                           :meth:get_layout_templates<arcgis.mapping.get_layout_templates> function
    ------------------     --------------------------------------------------------------------
    gis                    The :class:GIS<arcgis.gis.GIS> to use for printing. Optional
                           parameter. When not specified, the active GIS will be used.
    ==================     ====================================================================

    Returns:
        A dictionary with URL to download the output file.
    """

    from arcgis.geoprocessing import DataFile
    from arcgis.geoprocessing._support import _execute_gp_tool

    param_db = {
        "web_map_as_json": (str, "Web_Map_as_JSON"),
        "format": (str, "Format"),
        "layout_template": (str, "Layout_Template"),
        "output_file": (DataFile, "Output File"),
    }
    return_values = [
        {"name": "output_file", "display_name": "Output File", "type": DataFile},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    kwargs = {
        "web_map_as_json": web_map_as_json,
        "format": format,
        "layout_template": layout_template,
        "gis": gis,
    }
    url = os.path.dirname(gis.properties.helperServices.printTask.url)
    return _execute_gp_tool(
        gis, "Export Web Map Task", kwargs, param_db, return_values, _use_async, url
    )


export_map.__annotations__ = {
    "web_map_as_json": str,
    "format": str,
    "layout_template": str,
}


def get_layout_templates(gis=None):
    """

    The ``get_layout_templates`` method returns the content of the :class:`~arcgis.gis.GIS` object's layout templates.

    .. note::
        The layout templates are formatted as a dictionary.

    .. note::
        See the
        `Get Layout Templates Info Task <https://utility.arcgisonline.com/arcgis/rest/directories/arcgisoutput/Utilities/PrintingTools_GPServer/Utilities_PrintingTools/GetLayoutTemplatesInfo.htm>`_
        for additional help on the ``get_layout_templates`` method.


    ==================     ====================================================================
    **Argument**           **Description**
    ------------------     --------------------------------------------------------------------
    gis                    Optional :class:`~arcgis.gis.GIS` object. The ``GIS`` on which ``get_layout_templates`` runs.

                           .. note::
                            If ``gis`` is not specified, the active GIS is used.

    ==================     ====================================================================

    Returns:
       ``output_json`` - The layout templates as Python dictionary


    """
    from arcgis.geoprocessing import DataFile
    from arcgis.geoprocessing._support import _execute_gp_tool

    param_db = {
        "output_json": (str, "Output JSON"),
    }
    return_values = [
        {"name": "output_json", "display_name": "Output JSON", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis

    url = os.path.dirname(gis.properties.helperServices.printTask.url)
    kwargs = {"gis": gis}
    return _execute_gp_tool(
        gis,
        "Get Layout Templates Info Task",
        kwargs,
        param_db,
        return_values,
        _use_async,
        url,
    )


get_layout_templates.__annotations__ = {"return": str}
