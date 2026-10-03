"""config: portal constants and endpoint templates (TDD)."""

from m21_crawl import config


def test_portal_constants_are_sane() -> None:
    """The crawl must target the M21-1 portal and manual root topic."""
    assert config.PORTAL_ID == "554400000001018"
    assert config.ROOT_TOPIC_ID == "554400000004049"
    assert config.USERTYPE == "customer"
    assert config.LANG == "en-US"


def test_base_url_is_https_absolute() -> None:
    """All URL building starts from an absolute https origin."""
    assert config.BASE_URL.startswith("https://")
    assert not config.BASE_URL.endswith("/")


def test_endpoint_templates_keep_placeholders() -> None:
    """Endpoint templates must still contain their {placeholders}."""
    assert "{portal_id}" in config.ENDPOINT_ANON_AUTH
    assert "{topic_id}" in config.ENDPOINT_TOPIC
    assert "{article_id}" in config.ENDPOINT_ARTICLE
    assert config.ENDPOINT_ARTICLE_LIST.startswith("/ws/v11/ss/article")


def test_defaults_are_sane() -> None:
    """Retry/timeout defaults must be finite positive numbers."""
    assert config.DEFAULT_RETRIES >= 1
    assert config.DEFAULT_BACKOFF_SECONDS > 0
    assert config.REQUEST_TIMEOUT_SECONDS > 0
    assert 0 <= config.CRAWL_DELAY_SECONDS <= 5


def test_manual_filename_is_stable() -> None:
    """The deliverable file name is part of the public contract."""
    assert config.MANUAL_FILENAME == "M21-1-Adjudication-Procedures-Manual.md"
