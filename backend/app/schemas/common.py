from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

# Timestamps are stored as naive UTC; send them to the browser as ISO-8601 with a "Z".
UtcDatetime = Annotated[
    datetime,
    PlainSerializer(lambda d: d.replace(tzinfo=None).isoformat() + "Z", return_type=str),
]