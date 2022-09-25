from typing import Tuple
from requests.auth import AuthBase
from ._schain import SupportMultiAuth
from ..tools._lazy import LazyLoader
from ..tools import parse_url

os = LazyLoader("os")
tempfile = LazyLoader("tempfile")
_dt = LazyLoader("datetime")
requests = LazyLoader("requests")
###########################################################################
class EsriPKIAuth(AuthBase, SupportMultiAuth):
    """Handles PKI authentication when tokens are needed"""

    _token_url = None
    _server_log = None
    _server_log_count = None
    _tokens = None
    _session = None

    def __init__(
        self, cert: Tuple[str], referer: str = None, verify_cert: bool = True, **kwargs
    ):
        self._server_log = {}
        self._server_log_time = {}
        self._tokens = {}
        self._token_url = None
        self.verify_cert = verify_cert
        self.cert = cert
        self.auth = kwargs.pop("auth", None)
        if referer is None:
            self.referer = "http"
        else:
            self.referer = referer
        self._session = kwargs.pop("session", requests.Session())

    # ----------------------------------------------------------------------
    def __str__(self):
        return f"<{self.__class__.__name__}>"

    # ----------------------------------------------------------------------
    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    # ----------------------------------------------------------------------
    @property
    def token(self) -> str:
        """
        returns the authentication token
        """
        return None

    # ----------------------------------------------------------------------
    def generate_portal_server_token(self, r, **kwargs):
        """generates a server token using Portal token"""
        parsed = parse_url(r.url)
        if (
            r.text.lower().find("invalid token") > -1
            or r.text.lower().find("token required") > -1
            or r.text.lower().find("token not found") > -1
        ) or parsed.netloc in self._server_log:
            expiration = 16000
            if parsed.port:
                server_url = f'{parsed.scheme}://{parsed.netloc}:{parsed.port}/{parsed.path[1:].split("/")[0]}'
            else:
                server_url = (
                    f'{parsed.scheme}://{parsed.netloc}/{parsed.path[1:].split("/")[0]}'
                )
            postdata = {
                "request": "getToken",
                "serverURL": server_url,
                "referer": self.referer or "http",
                "f": "json",
            }
            if expiration:
                postdata["expiration"] = expiration
            if parsed.netloc in self._server_log:
                token_url = self._server_log[parsed.netloc]
                self._server_log_time[
                    parsed.netloc
                ] = _dt.datetime.now() + _dt.timedelta(minutes=expiration)
            else:
                info = self._session.get(
                    server_url + "/rest/info?f=json",
                    cert=(self.cert[0], self.cert[1]),
                    verify=self.verify_cert,
                    auth=self.auth,
                ).json()
                token_url = info["authInfo"]["tokenServicesUrl"]
                self._server_log[parsed.netloc] = token_url
            if server_url in self._tokens:
                if _dt.datetime.now() >= self._server_log_time[parsed.netloc]:
                    del self._tokens[server_url]
                    return self.generate_portal_server_token(r)
                token_str = self._tokens[server_url]
            else:
                token = self._session.post(
                    token_url,
                    data=postdata,
                    cert=(self.cert[0], self.cert[1]),
                    auth=self.auth,
                    verify=self.verify_cert,
                )
                token_str = token.json().get("token", None)
                if token_str is None:
                    return r
                self._tokens[server_url] = token_str
            # Recreate the request with the token
            #
            r.content
            r.raw.release_conn()
            r.request.headers["referer"] = self.referer or "http"
            r.request.headers["X-Esri-Authorization"] = f"Bearer {token_str}"
            _r = r.connection.send(r.request, **kwargs)
            _r.headers["referer"] = self.referer or "http"
            _r.headers["X-Esri-Authorization"] = f"Bearer {token_str}"
            _r.history.append(r)
            return _r
        return r

    # ----------------------------------------------------------------------
    def __call__(self, r):
        if self.auth:
            self.auth.__call__(r)
        r.register_hook("response", self.generate_portal_server_token)
        return r
