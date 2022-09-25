import platform
from requests.auth import AuthBase
from urllib.parse import parse_qs
from ._schain import SupportMultiAuth
from ..tools._lazy import LazyLoader
from ..tools import parse_url

HAS_SSPI = False
HAS_NTLM2 = False
HAS_GSSAPI = False
HAS_KERBEROS = False

if platform.platform().lower().find("windows") > -1:
    try:
        requests_negotiate_sspi = LazyLoader("requests_negotiate_sspi", strict=True)
        HAS_SSPI = True
    except:
        HAS_SSPI = False

try:
    requests_gssapi = LazyLoader("requests_gssapi", strict=True)
    HAS_GSSAPI = True
except:
    HAS_GSSAPI = False

try:
    requests_kerberos = LazyLoader("requests_kerberos", strict=True)
    HAS_KERBEROS = True
except:
    HAS_KERBEROS = False

try:
    requests_ntlm2 = LazyLoader("requests_ntlm2", strict=True)
    HAS_NTLM2 = True
except:
    HAS_NTLM2 = False


requests_ntlm = LazyLoader("requests_ntlm", strict=True)
requests = LazyLoader("requests")


class EsriWindowsAuth(AuthBase, SupportMultiAuth):

    _token_url = None
    _server_log = None
    _tokens = None

    def __init__(
        self,
        username: str = None,
        password: str = None,
        referer: str = None,
        verify_cert: bool = True,
        **kwargs,
    ):
        self.legacy = kwargs.pop("legacy", False)
        self._server_log = {}
        self._tokens = {}
        self._token_url = None
        self.verify_cert = verify_cert
        if referer is None:
            self.referer = "http"
        else:
            self.referer = referer

        try:
            if not username and not password and HAS_SSPI:
                self.auth = requests_negotiate_sspi.HttpNegotiateAuth()
            elif not username and not password and HAS_GSSAPI:
                self.auth = requests_gssapi.HTTPSPNEGOAuth()
            elif username and password:
                send_cbt = kwargs.pop("send_cbt", True)
                if HAS_NTLM2:

                    ntlm_compatibility = kwargs.pop(
                        "ntlm_compatibility",
                        requests_ntlm2.NtlmCompatibility.NTLMv2_DEFAULT,
                    )
                    ntlm_strict_mode = kwargs.pop("ntlm_strict_mode", False)
                    self.auth = requests_ntlm2.HttpNtlmAuth(
                        username,
                        password,
                        send_cbt=send_cbt,
                        ntlm_compatibility=ntlm_compatibility,
                        ntlm_strict_mode=ntlm_strict_mode,
                    )
                else:
                    self.auth = requests_ntlm.HttpNtlmAuth(
                        username, password, send_cbt=send_cbt
                    )
            else:
                raise ValueError("")
        except ImportError:
            raise Exception(
                "NTLM authentication requires requests_negotiate_sspi module."
            )

    # ----------------------------------------------------------------------
    def __str__(self):
        return f"<{self.__class__.__name__}>"

    # ----------------------------------------------------------------------
    def __repr__(self):
        return f"<{self.__class__.__name__}>"

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
            else:
                info = requests.get(
                    server_url + "/rest/info?f=json",
                    auth=self.auth,
                    verify=self.verify_cert,
                ).json()
                token_url = info["authInfo"]["tokenServicesUrl"]
                self._server_log[parsed.netloc] = token_url
            if server_url in self._tokens:
                token_str = self._tokens[server_url]
            else:
                token = requests.post(token_url, data=postdata, auth=self.auth)
                token_str = token.json().get("token", None)
                if token_str is None:
                    return r
                self._tokens[server_url] = token_str
            # Recreate the request with the token
            #
            r.content
            r.raw.release_conn()
            r.request.headers["referer"] = self.referer or "http"

            if self.legacy and r.request.method == "GET":
                r.request.prepare_url(url=r.url, params={"token": token_str})
            elif self.legacy and r.request.method == "POST":
                data = parse_qs(r.request.body)
                data["token"] = token_str
                r.request.prepare_body(data, None, None)
            else:
                r.request.headers["X-Esri-Authorization"] = f"Bearer {token_str}"

            # r.request.headers["X-Esri-Authorization"] = f"Bearer {token_str}"
            _r = r.connection.send(r.request, **kwargs)
            _r.headers["referer"] = self.referer or "http"
            _r.headers["X-Esri-Authorization"] = f"Bearer {token_str}"
            _r.history.append(r)
            return _r
        return r

    # ----------------------------------------------------------------------
    @property
    def token(self) -> str:
        """
        Gets the token.  This is always `None` for `EsriWindowsAuth`

        :returns: String
        """
        return None

    # ----------------------------------------------------------------------
    def __call__(self, r):
        self.auth.__call__(r)
        r.register_hook("response", self.generate_portal_server_token)
        return r


class EsriKerberosAuth(AuthBase, SupportMultiAuth):

    _token_url = None
    _server_log = None
    _tokens = None

    def __init__(self, referer: str = None, verify_cert: bool = True, **kwargs):
        """initializer"""
        if HAS_KERBEROS == False:
            raise ImportError(
                "requests_kerberos is required to use this authentication handler."
            )
        self.legacy = kwargs.pop("legacy", False)
        self._server_log = {}
        self._tokens = {}
        self._token_url = None
        self.verify_cert = verify_cert
        if referer is None:
            self.referer = "http"
        else:
            self.referer = referer

        try:
            import requests_kerberos

            self.auth = requests_kerberos.HTTPKerberosAuth(
                mutual_authentication=requests_kerberos.OPTIONAL
            )
        except ImportError:
            raise Exception(
                "Kerberos authentication requires `requests_kerberos` module."
            )

    # ----------------------------------------------------------------------
    def __str__(self):
        return f"<{self.__class__.__name__}>"

    # ----------------------------------------------------------------------
    def __repr__(self):
        return f"<{self.__class__.__name__}>"

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
            else:
                info = requests.get(
                    server_url + "/rest/info?f=json",
                    auth=self.auth,
                    verify=self.verify_cert,
                ).json()
                token_url = info["authInfo"]["tokenServicesUrl"]
                self._server_log[parsed.netloc] = token_url
            if server_url in self._tokens:
                token_str = self._tokens[server_url]
            else:
                token = requests.post(
                    token_url,
                    data=postdata,
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

            if self.legacy and r.request.method == "GET":
                r.request.prepare_url(url=r.url, params={"token": token_str})
            elif self.legacy and r.request.method == "POST":
                data = parse_qs(r.body)
                data["token"] = token_str
                r.request.prepare_body(data, None, None)
            else:
                r.request.headers["X-Esri-Authorization"] = f"Bearer {token_str}"

            _r = r.connection.send(r.request, **kwargs)
            _r.headers["referer"] = self.referer or "http"
            _r.headers["X-Esri-Authorization"] = f"Bearer {token_str}"
            _r.history.append(r)
            return _r
        return r

    # ----------------------------------------------------------------------
    @property
    def token(self) -> str:
        """
        Gets the token.  This is always `None` for `KerberosAuth`

        :returns: String
        """
        return None

    # ----------------------------------------------------------------------
    def __call__(self, r):
        self.auth.__call__(r)
        r.register_hook("response", self.generate_portal_server_token)
        return r
