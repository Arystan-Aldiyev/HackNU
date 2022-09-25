"""
The arcgis.velocity module provides API functions mapping to automate the ArcGIS Velocity REST API.
ArcGIS Velocity is a real-time and big data processing and analysis capability of ArcGIS Online.
It enables you to ingest, visualize, analyze, store, and act upon data from Internet of Things (IoT) sensors.

The arcgis.realtime.StreamLayer provides types and functions for receiving real-time data feeds and sensor data streamed from
the GIS to perform continuous processing and analysis. It includes support for stream layers that allow Python scripts
to subscribe to the streamed feature data or broadcast updates or alerts.
"""

from .stream_layer import StreamLayer
from .velocity import Velocity
