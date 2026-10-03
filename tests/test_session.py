"""session: anonymous session acquisition (TDD, fake transport — no network)."""

from m21_crawl import config
from m21_crawl.session import (
    Response,
    SessionAcquisitionError,
    acquire_session,
)

EXPECTED_URL = (
    "https://www.knowva.ebenefits.va.gov/system"
    "/ws/v15/ss/portal/554400000001018/authentication/anonymous"
)


class FakeTransport:
    """Records calls and returns a canned Response."""

    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def __call__(self, method: str, url: str, headers: dict[str, str]) -> Response:
        self.calls.append((method, url, headers))
        return self.response


def _args() -> dict[str, object]:
    return {
        "portal_id": config.PORTAL_ID,
        "system_base": config.SYSTEM_BASE,
        "endpoint": config.ENDPOINT_ANON_AUTH,
        "lang": config.LANG,
    }


def test_acquires_token_from_204_header() -> None:
    """A 204 with X-egain-session returns that token."""
    fake = FakeTransport(Response(status=204, headers={"X-egain-session": "tok-123"}))
    assert acquire_session(fake, **_args()) == "tok-123"


def test_request_shape() -> None:
    """POST to the anonymous endpoint with JSON accept + Accept-Language."""
    fake = FakeTransport(Response(status=204, headers={"X-egain-session": "t"}))
    acquire_session(fake, **_args())
    method, url, headers = fake.calls[0]
    assert method == "POST"
    assert url == EXPECTED_URL
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept-Language"] == "en-US"


def test_header_lookup_is_case_insensitive() -> None:
    """Servers may return any header case."""
    fake = FakeTransport(Response(status=204, headers={"x-EGAIN-SESSION": "tok"}))
    assert acquire_session(fake, **_args()) == "tok"


def test_non_204_raises() -> None:
    """401/403/500 are all hard failures at acquisition time."""
    for status in (401, 500):
        fake = FakeTransport(Response(status=status, headers={"X-egain-session": "t"}))
        try:
            acquire_session(fake, **_args())
        except SessionAcquisitionError:
            pass
        else:
            raise AssertionError(f"expected SessionAcquisitionError for HTTP {status}")


def test_missing_or_empty_header_raises() -> None:
    """A 204 without the token header is unusable."""
    fake = FakeTransport(Response(status=204, headers={"JSESSIONID": "abc"}))
    try:
        acquire_session(fake, **_args())
    except SessionAcquisitionError:
        pass
    else:
        raise AssertionError("expected SessionAcquisitionError for missing header")

    fake = FakeTransport(Response(status=204, headers={"X-egain-session": ""}))
    try:
        acquire_session(fake, **_args())
    except SessionAcquisitionError:
        pass
    else:
        raise AssertionError("expected SessionAcquisitionError for empty header")
