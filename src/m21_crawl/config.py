"""Portal constants and endpoint templates for the Knowva eBenefits crawl.

All values are fixed by the (reverse-engineered) portal API contract; see the
live samples verified on 2026-10-02. Nothing in this module reads the network.
"""

# --- identity ---------------------------------------------------------------
PORTAL_ID = "554400000001018"
ROOT_TOPIC_ID = "554400000004049"
USERTYPE = "customer"
LANG = "en-US"

# --- origins ----------------------------------------------------------------
BASE_URL = "https://www.knowva.ebenefits.va.gov"
SYSTEM_BASE = BASE_URL + "/system"

# --- endpoint templates (placeholders filled by client) ----------------------
ENDPOINT_ANON_AUTH = "/ws/v15/ss/portal/{portal_id}/authentication/anonymous"
ENDPOINT_TOPIC = "/ws/v11/ss/topic/{topic_id}"
ENDPOINT_ARTICLE_LIST = "/ws/v11/ss/article"
ENDPOINT_ARTICLE = "/ws/v11/ss/article/{article_id}"

# --- transport defaults -------------------------------------------------------
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30.0
# Politeness delay between successive article fetches (seconds).
CRAWL_DELAY_SECONDS = 0.1

# --- deliverable --------------------------------------------------------------
MANUAL_FILENAME = "M21-1-Adjudication-Procedures-Manual.md"
