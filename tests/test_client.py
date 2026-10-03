"""client: HTTP transport + retrying JSON client (TDD, scripted transport)."""

import json
from collections.abc import Callable

from m21_crawl import config
from m21_crawl.client import ApiError, Client
from m21_crawl.session import Response


class ScriptedTransport:
    """Returns canned Responses (or raises) in order; records every call."""

    def __init__(self, *script: Response | BaseException) -> None:
        self._script: list[Response | BaseException] = list(script)
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def __call__(self, method: str, url: str, headers: dict[str, str]) -> Response:
        self.calls.append((method, url, dict(headers)))
        if not self._script:
            raise AssertionError("transport called more times than scripted")
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _body(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _client(
    transport: ScriptedTransport,
    *,
    retries: int = 3,
    sleep: Callable[[float], None] | None = None,
    session_acquirer: Callable[[], str] | None = None,
) -> Client:
    return Client(
        transport,
        system_base=config.SYSTEM_BASE,
        portal_id=config.PORTAL_ID,
        endpoint_anon_auth=config.ENDPOINT_ANON_AUTH,
        lang=config.LANG,
        retries=retries,
        backoff_seconds=1.0,
        sleep=sleep if sleep is not None else (lambda seconds: None),
        session_acquirer=session_acquirer,
    )


AUTH_URL = (
    "https://www.knowva.ebenefits.va.gov/system"
    "/ws/v15/ss/portal/554400000001018/authentication/anonymous"
)


def test_get_acquires_session_then_returns_json() -> None:
    """Default path: POST anonymous auth (204 + token), then GET with token header."""
    transport = ScriptedTransport(
        Response(status=204, headers={"X-egain-session": "tok-live"}),
        Response(status=200, headers={}, body=_body({"article": []})),
    )
    sleeps: list[float] = []
    client = _client(transport, sleep=sleeps.append)
    result = client.get(
        "/ws/v11/ss/article",
        {"portalId": config.PORTAL_ID, "usertype": "customer", "topicId": "1", "$lang": "en-US"},
    )
    assert result == {"article": []}
    assert len(transport.calls) == 2
    method, url, headers = transport.calls[0]
    assert (method, url) == ("POST", AUTH_URL)
    method, url, headers = transport.calls[1]
    assert method == "GET"
    assert url == (
        "https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article"
        "?portalId=554400000001018&usertype=customer&topicId=1&$lang=en-US"
    )
    assert headers["X-egain-session"] == "tok-live"
    assert headers["Accept"] == "application/json"
    assert sleeps == []


def test_injected_session_acquirer_skips_auth_call() -> None:
    """When a token source is injected, no auth round-trip happens."""
    transport = ScriptedTransport(Response(status=200, headers={}, body=_body({"ok": True})))
    client = _client(transport, session_acquirer=lambda: "tok-injected")
    assert client.get("/x", {}) == {"ok": True}
    assert transport.calls[0][0] == "GET"
    assert transport.calls[0][2]["X-egain-session"] == "tok-injected"


def test_429_retries_then_succeeds() -> None:
    transport = ScriptedTransport(
        Response(status=429, headers={}, body=b""),
        Response(status=200, headers={}, body=_body({"ok": True})),
    )
    sleeps: list[float] = []
    client = _client(transport, sleep=sleeps.append, session_acquirer=lambda: "t")
    assert client.get("/x", {}) == {"ok": True}
    assert sleeps == [1.0]


def test_5xx_retries_with_exponential_backoff() -> None:
    transport = ScriptedTransport(
        Response(status=500, headers={}, body=b""),
        Response(status=503, headers={}, body=b""),
        Response(status=200, headers={}, body=_body({"ok": True})),
    )
    sleeps: list[float] = []
    client = _client(transport, sleep=sleeps.append, session_acquirer=lambda: "t")
    assert client.get("/x", {}) == {"ok": True}
    assert sleeps == [1.0, 2.0]


def test_retry_exhaustion_raises_api_error() -> None:
    transport = ScriptedTransport(
        Response(status=429, headers={}, body=b""),
        Response(status=429, headers={}, body=b""),
        Response(status=429, headers={}, body=b""),
        Response(status=429, headers={}, body=b""),
    )
    sleeps: list[float] = []
    client = _client(transport, sleep=sleeps.append, session_acquirer=lambda: "t")
    try:
        client.get("/x", {})
    except ApiError as err:
        assert err.status == 429
    else:
        raise AssertionError("expected ApiError")
    assert len(transport.calls) == 4
    assert sleeps == [1.0, 2.0, 4.0]


def test_401_refreshes_session_and_retries_once() -> None:
    """401 → re-acquire session → one retry with the new token."""
    transport = ScriptedTransport(
        Response(status=401, headers={}, body=b""),
        Response(status=200, headers={}, body=_body({"ok": True})),
    )
    tokens = iter(["tok-old", "tok-new"])
    client = _client(transport, session_acquirer=lambda: next(tokens))
    assert client.get("/x", {}) == {"ok": True}
    assert transport.calls[0][2]["X-egain-session"] == "tok-old"
    assert transport.calls[1][2]["X-egain-session"] == "tok-new"


def test_401_twice_raises_after_single_refresh() -> None:
    """The session is re-acquired only once per request."""
    transport = ScriptedTransport(
        Response(status=401, headers={}, body=b""),
        Response(status=401, headers={}, body=b""),
    )
    acquisitions = []
    client = _client(
        transport,
        session_acquirer=lambda: acquisitions.append(1) or "tok",
    )
    try:
        client.get("/x", {})
    except ApiError as err:
        assert err.status == 401
    else:
        raise AssertionError("expected ApiError")
    # Initial acquisition + exactly one re-acquisition after the first 401.
    assert len(acquisitions) == 2
    # ...and exactly one retry call (no second refresh).
    assert len(transport.calls) == 2


def test_other_4xx_fail_immediately() -> None:
    """404 is a hard error: no retries, no backoff, one call."""
    transport = ScriptedTransport(Response(status=404, headers={}, body=b'{"error": "nf"}'))
    sleeps: list[float] = []
    client = _client(transport, sleep=sleeps.append, session_acquirer=lambda: "t")
    try:
        client.get("/x", {})
    except ApiError as err:
        assert err.status == 404
    else:
        raise AssertionError("expected ApiError")
    assert len(transport.calls) == 1
    assert sleeps == []


def test_transport_oserror_retries_then_succeeds() -> None:
    """Transient connection errors (OSError) consume a retry attempt."""
    transport = ScriptedTransport(
        OSError("connection reset"),
        Response(status=200, headers={}, body=_body({"ok": True})),
    )
    sleeps: list[float] = []
    client = _client(transport, sleep=sleeps.append, session_acquirer=lambda: "t")
    assert client.get("/x", {}) == {"ok": True}
    assert sleeps == [1.0]


def test_transport_oserror_exhaustion_reraises() -> None:
    """After retries are spent, the transport error propagates."""
    transport = ScriptedTransport(
        OSError("connection reset"),
        OSError("connection reset"),
        OSError("connection reset"),
        OSError("connection reset"),
    )
    client = _client(transport, session_acquirer=lambda: "t")
    try:
        client.get("/x", {})
    except OSError:
        pass
    else:
        raise AssertionError("expected OSError to propagate")
    assert len(transport.calls) == 4
