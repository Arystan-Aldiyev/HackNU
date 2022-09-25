from dataclasses import dataclass, asdict, field
from typing import Dict, Union, Optional, Any, ClassVar


@dataclass(frozen=True)
class TimeInstant:
    """
    Data class that holds the Instant Time configuration

    =====================      ====================================================================
    **Argument**               **Description**
    ---------------------      --------------------------------------------------------------------
    time_field                 str. Time field name
    =====================      ====================================================================

    =====================      ====================================================================
    **Optional Argument**      **Description**
    ---------------------      --------------------------------------------------------------------
    date_format                str. If the field does not contain epoch value a date format can be
                               defined for the time field
    =====================      ====================================================================

    :return: boolean `True` if the operation is a success

    .. code-block:: python

        # Usage Example

        time = TimeInstant(time_field="time_field")

    """

    time_field: str
    date_format: str = None


@dataclass(frozen=True)
class TimeInterval:
    """
    Data class that holds the Interval Time configuration

    =====================     ====================================================================
    **Argument**              **Description**
    ---------------------     --------------------------------------------------------------------
    interval_start_field      str. Start-time field name for the time interval
    ---------------------     --------------------------------------------------------------------
    interval_end_field        str. End-time field name for the time interval
    =====================     ====================================================================

    =====================     ====================================================================
    **Optional Argument**     **Description**
    ---------------------     --------------------------------------------------------------------
    date_format               str. If the field does not contain epoch value a date format can be
                              defined for the time field
    =====================     ====================================================================

    :return: boolean `True` if the operation is a success

    .. code-block:: python

        # Usage Example

        time = TimeInterval(
            interval_start_field="start_field",
            interval_end_field="end_field"
        )

    """

    interval_start_field: str
    interval_end_field: str
    date_format: str = None


_START_TIME_TAG = "START_TIME"
_END_TIME_TAG = "END_TIME"


class _HasTime:
    # ---> Inheriting classes MUST declare the following Optional fields. <---
    # These are commented variables because of a limitation in dataclass where base class properties get ordered before
    # the derived class properties. Since these are optional properties, the init will order them before the non-optional
    # derived class properties leading to errors like - TypeError: non-default argument 'rss_url' follows default argument
    #
    # time: Optional[Union[TimeInstant, TimeInterval]] = None

    def set_time_config(self, time: Union[TimeInstant, TimeInterval]) -> bool:
        """
        Configures the time property for a feed

        ==============          ====================================================================
        **Argument**            **Description**
        ---------------         --------------------------------------------------------------------
        time                    Union[TimeInstant, TimeInterval].
                                Time object used to configure the feed
        ===============         ====================================================================

        :return: boolean `True` if the operation is a success

        .. code-block:: python

            # Usage Example

            feed.set_time_config(time=time)

        """

        if isinstance(time, TimeInstant):
            if time.date_format is not None and self.data_format is not None:
                self.data_format.date_format = time.date_format

            is_success = False
            for field in self._fields["attributes"]:
                if field["name"] == time.time_field:
                    field["tags"] = [_START_TIME_TAG]

                    self._fields["time"] = {"timeType": "Instant"}
                    is_success = True
                    break

            if not is_success:
                raise ValueError(f"invalid time_field: '{time.time_field}'")
            else:
                return True

        elif isinstance(time, TimeInterval):
            if time.date_format is not None and self.data_format is not None:
                self.data_format.date_format = time.date_format

            is_success_1 = False
            is_success_2 = False
            for field in self._fields["attributes"]:
                if field["name"] == time.interval_start_field:
                    field["tags"] = [_START_TIME_TAG]
                    is_success_1 = True
                elif field["name"] == time.interval_end_field:
                    field["tags"] = [_END_TIME_TAG]
                    is_success_2 = True

            if not is_success_1:
                raise ValueError(
                    f"invalid interval_start_field: '{time.interval_start_field}'"
                )
            elif not is_success_2:
                raise ValueError(
                    f"invalid interval_end_field: '{time.interval_end_field}'"
                )
            else:
                self._fields["time"] = {"timeType": "Interval"}

                return True
