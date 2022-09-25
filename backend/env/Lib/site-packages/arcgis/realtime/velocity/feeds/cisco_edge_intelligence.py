from typing import ClassVar

from arcgis.realtime.velocity.feeds.mqtt import MQTT


class CiscoEdgeIntelligence(MQTT):
    """
    Receives events from a Cisco Edge Intelligence broker. This data class can be used to define the feed configuration
    and use it to create the feed.

    =====================       ========================================================================================
    **Argument**                **Description**
    ---------------------       ----------------------------------------------------------------------------------------
    label                       str. Unique label for this feed instance.
    ---------------------       ----------------------------------------------------------------------------------------
    description                 str. Feed description.
    ---------------------       ----------------------------------------------------------------------------------------
    host                        str. Hostname of the Edge Intelligence broker prefixed with
                                "tcp://" for non-SSL and "ssl://" for SSL connections
    ---------------------       ----------------------------------------------------------------------------------------
    port                        str. Port on which the Edge Intelligence broker is accessible.
    ---------------------       ----------------------------------------------------------------------------------------
    topic                       str. Topic over which event messages stream.
    ---------------------       ----------------------------------------------------------------------------------------
    qos_level                   int. Quality of Service (QoS) level defines the guarantee of delivery for a specific
                                message. In MQTT 3.1.1, a QoS of 0 means a message is delivered at most once, a QoS of 1
                                at least once, and a Qos of 2 exactly once.

                                default value - 0
    =====================       ========================================================================================

    =====================       ========================================================================================
    **Optional Argument**       **Description**
    =====================       ========================================================================================
    username                    Username for basic authentication
    ---------------------       ----------------------------------------------------------------------------------------
    password                    Password for basic authentication
    ---------------------       ----------------------------------------------------------------------------------------
    client_id                   Client ID ArcGIS Velocity will use to connect to the Edge
                                Intelligence broker
    ---------------------       ----------------------------------------------------------------------------------------
    data_format                 Union[DelimitedFormat, EsriJsonFormat, GeoJsonFormat, JsonFormat, XMLFormat].
                                An instance that contains the data-format configuration for this feed. Configure only
                                allowed formats. If this is not set right during initialization, a format will be
                                auto-detected and set from a sample of the incoming data. This sample will be fetched
                                from the configuration provided so far in the init.
    ---------------------       ----------------------------------------------------------------------------------------
    track_id_field              str. name of the field from the incoming data that should be set as
                                track_id.
    ---------------------       ----------------------------------------------------------------------------------------
    geometry                    Union[XYZGeometry, SingleFieldGeometry]. An instance of geometry configuration
                                that will be used to create geometry objects from the incoming data.
    ---------------------       ----------------------------------------------------------------------------------------
    time                        Union[TimeInstant, TimeInterval]. An instance of time configuration that
                                will be used to create time info from the incoming data.
    =====================       ========================================================================================

    :return: A data class with cisco edge intelligence feed configuration.

    .. code-block:: python

        # Usage Example

        from arcgis.realtime.velocity.feeds import CiscoEdgeIntelligence
        from arcgis.realtime.velocity.feeds.geometry import XYZGeometry, SingleFieldGeometry
        from arcgis.realtime.velocity.feeds.time import TimeInterval, TimeInstant

        cisco_edge_config = CiscoEdgeIntelligence(
            label="feed_name",
            description="feed_description",
            host="cisco_host",
            port="cisco_port",
            topic="cisco_topic",
            qos_level=0,
            username="cisco_username",
            password="cisco_password",
            client_id="cisco_client_id",
            data_format=None
        )

        # use velocity object to get the FeedsManager instance
        feeds = velocity.feeds

        # use the FeedsManager object to create a feed from this feed configuration
        cisco_edge_feed = feeds.create(cisco_edge_config)
        cisco_edge_feed.start()
        feeds.items

    """

    # FeedTemplate properties
    _name: ClassVar[str] = "kinetic"
