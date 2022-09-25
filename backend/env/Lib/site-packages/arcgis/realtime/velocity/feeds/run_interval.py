from dataclasses import dataclass, asdict, field
from typing import Dict, Union, Optional, Any, ClassVar
import pytz


@dataclass(frozen=True)
class RunInterval:
    """
    Set the run interval for the feed.

    ===============     ================================================================================================
    **Argument**        **Description**
    ---------------     ------------------------------------------------------------------------------------------------
    cron_expression     str. Default value - if nothing is specified following expression will be used to configure the
                        feed:
                        example - "0 * * ? * * *" - Runs every minute

                        Cron Expression that specifies the run interval. Please use the
                        following link to generate the cron expression:
    ---------------     ------------------------------------------------------------------------------------------------
    timezone            str. Default value - "America/Los_Angeles"
                        Run interval timezone to use.
                        refer: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for strings
    ===============     ================================================================================================

    :return: `True` if the operation is a success

    .. code-block:: python

        # Usage Example

        feed.run_interval = RunInterval(
            cron_expression="0 * * ? * * *", timezone="America/Los_Angeles",
        )

        # Seconds value must be between 10 and 59
        # Minutes value must be between 1 and 59
        # Hours value must be between 1 and 23

    """

    cron_expression: str
    timezone: str = field(default="America/Los_Angeles")

    def __post_init__(self):
        if self.cron_expression in (None, ""):
            raise ValueError("Cron expression cannot be empty or None")
        elif self.timezone not in pytz.all_timezones:
            raise ValueError("Invalid time zone string")

    def _build(self):
        return {
            "recurrence": {
                "expression": self.cron_expression,
                "timeZone": self.timezone,
            }
        }
