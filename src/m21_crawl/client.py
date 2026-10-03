"""client: HTTP transport and retrying JSON client for the Knowva portal API.

`HttpTransport` adapts `requests` to the `Transport` protocol defined in
`session.py`. `Client` adds the portal's session handling (the
`X-egain-session` token on every call) and a bounded retry policy:

  - 429 / 5xx, and transient transport errors (OSError): retry up to
    `retries` times with exponential backoff (backoff_seconds * 2**attempt);
  - 401 / 403 (stale/revoked session): re-acquire the session once, then
    retry the same request with the new token;
  - any other status: raise ApiError immediately.

`sleep` and `session_acquirer` are injectable so the unit suite never
touches the network or the real clock.
"""

import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import requests

from .config import (
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_RETRIES,
    ENDPOINT_ANON_AUTH,
    LANG,
    PORTAL_ID,
    REQUEST_TIMEOUT_SECONDS,
    SYSTEM_BASE,
)
from .session import Response, Transport, acquire_session

#: HTTP statuses that are retried with backoff (rate limiting / server errors).
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
#: HTTP statuses that mean the session token is stale and must be re-acquired.
SESSION_STALE_STATUSES = frozenset({401, 403})


class ApiError(RuntimeError):
    """A portal API response that failed and must not be retried further."""

    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        message = f"portal API returned HTTP {status}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


class HttpTransport:
    """Production Transport backed by a `requests.Session` (connection reuse).

    Connection errors and timeouts surface as OSError subclasses
    (requests.exceptions.RequestException extends IOError), which `Client`
    treats as transient.
    """

    def __init__(self, timeout: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout
        self._http = requests.Session()

    def __call__(self, method: str, url: str, headers: dict[str, str]) -> Response:
        response = self._http.request(
            method,
            url,
            headers=headers,
            timeout=self._timeout,
        )
        return Response(
            status=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )


class Client:
    """JSON GET client with session handling and bounded retries.

    Parameters
    ----------
    transport:
        The low-level HTTP transport (see `session.Transport`).
    system_base / portal_id / endpoint_anon_auth / lang:
        Portal identity; used for URL building and (by default) for
        anonymous session acquisition.
    retries:
        Maximum retry count per request for 429/5xx/OSError.
    backoff_seconds:
        Base delay; the n-th retry waits backoff_seconds * 2**(n-1).
    sleep:
        Injectable delay (tests pass a recorder instead of time.sleep).
    session_acquirer:
        Injectable ``() -> token`` factory; defaults to
        `session.acquire_session` over the same transport.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        system_base: str = SYSTEM_BASE,
        portal_id: str = PORTAL_ID,
        endpoint_anon_auth: str = ENDPOINT_ANON_AUTH,
        lang: str = LANG,
        retries: int = DEFAULT_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        session_acquirer: Callable[[], str] | None = None,
    ) -> None:
        self._transport = transport
        self._system_base = system_base
        self._portal_id = portal_id
        self._endpoint_anon_auth = endpoint_anon_auth
        self._lang = lang
        self._retries = retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._session_acquirer = (
            session_acquirer if session_acquirer is not None else self._default_session_acquirer
        )
        self._token: str | None = None

    def _default_session_acquirer(self) -> str:
        """Acquire an anonymous session over the same transport."""
        return acquire_session(
            self._transport,
            portal_id=self._portal_id,
            system_base=self._system_base,
            endpoint=self._endpoint_anon_auth,
            lang=self._lang,
        )

    def _ensure_token(self) -> str:
        """Return the session token, acquiring one on first use."""
        if self._token is None:
            self._token = self._session_acquirer()
        return self._token

    def _headers(self) -> dict[str, str]:
        """Request headers: JSON accept + portal language + session token."""
        return {
            "Accept": "application/json",
            "Accept-Language": self._lang,
            "X-egain-session": self._ensure_token(),
        }

    def get(self, path: str, params: dict[str, str]) -> Any:
        """GET `system_base + path` (query string from `params`) as JSON.

        Raises `ApiError` for non-retryable statuses or exhausted retries;
        re-raises the transport OSError if retries are exhausted on it.
        """
        url = self._system_base + path
        if params:
            # `safe="$"` keeps the portal's `$level`/`$lang` query names literal,
            # exactly as in the verified live request samples.
            url = f"{url}?{urlencode(params, safe='$')}"
        attempts = self._retries
        session_refreshed = False
        while True:
            try:
                response = self._transport("GET", url, self._headers())
            except OSError:
                if attempts == 0:
                    raise
                attempts -= 1
                self._sleep(self._backoff_seconds * 2 ** (self._retries - attempts - 1))
                continue

            if response.status == 200:
                return response.json()

            if response.status in RETRYABLE_STATUSES:
                if attempts == 0:
                    raise ApiError(response.status)
                attempts -= 1
                self._sleep(self._backoff_seconds * 2 ** (self._retries - attempts - 1))
                continue

            if response.status in SESSION_STALE_STATUSES:
                if not session_refreshed:
                    session_refreshed = True
                    self._token = self._session_acquirer()
                    continue
                raise ApiError(response.status)

            raise ApiError(response.status)
