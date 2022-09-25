import urllib.parse as urllib_parse
from functools import lru_cache


@lru_cache(maxsize=255)
def parse_url(url: str) -> object:
    """
    Parses a URL string into it's pieces.

    :returns: Named Tuple
    """
    return urllib_parse.urlparse(url)
