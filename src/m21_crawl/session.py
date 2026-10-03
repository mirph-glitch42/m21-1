"""session: anonymous session acquisition + shared transport contract (TDD).

The Knowva portal requires an `X-egain-session` token (returned by the
anonymous authentication endpoint) on every subsequent API call.

This module also defines the `Transport` protocol and `Response` dataclass
that decouple HTTP from logic, so every module is testable with a fake
transport (no network in the unit suite).
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Response:
    """A decoded HTTP response (status, headers, raw body)."""

    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def json(self) -> Any:
        """Decode the body as JSON (raises ValueError on non-JSON bodies)."""
        import json

        return json.loads(self.body.decode("utf-8"))


class Transport(Protocol):
    """One HTTP round-trip. Implementations must not raise on 4xx/5xx status.

    `url` must be absolute; `headers` are request headers. The implementation
    is responsible for timeouts and connection errors (map them to exceptions).
    """

    def __call__(self, method: str, url: str, headers: dict[str, str]) -> Response: ...


class SessionAcquisitionError(RuntimeError):
    """Raised when the anonymous session endpoint does not return a token."""


def acquire_session(
    transport: Transport,
    *,
    portal_id: str,
    system_base: str,
    endpoint: str,
    lang: str,
) -> str:
    """POST to the anonymous authentication endpoint; return the session token.

    Contract (verified live 2026-10-02):
      - request:  POST {system_base}{endpoint.format(portal_id=portal_id)}
                  with Accept: application/json,
                  Content-Type: application/json,
                  Accept-Language: {lang}, body b"" (empty).
      - success:  status 204 and a non-empty `X-egain-session` response header
                  (header matching is case-insensitive).
      - failure:  any other status, or a missing/empty header, raises
                  SessionAcquisitionError.
    """
    url = system_base + endpoint.format(portal_id=portal_id)
    resp = transport(
        "POST",
        url,
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": lang,
        },
    )
    if resp.status != 204:
        raise SessionAcquisitionError(f"anonymous auth returned HTTP {resp.status}")
    token = _header_value(resp.headers, "X-egain-session")
    if not token:
        raise SessionAcquisitionError("anonymous auth returned no X-egain-session header")
    return token


def _header_value(headers: dict[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (dict keys may be any case)."""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None
