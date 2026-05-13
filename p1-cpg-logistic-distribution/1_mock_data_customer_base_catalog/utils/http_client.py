"""
Thin HTTP wrapper around the Overpass API.
"""

import logging
import time
import requests

from config.settings import (
    OVERPASS_SERVERS,
    APP_NAME,
    MAX_RETRIES,
    TIMEOUT,
    RETRY_WAIT,
    RATE_LIMIT_WAIT,
)

logger = logging.getLogger(__name__)


def post_overpass_query(
    query: str,
    servers: list[str] = OVERPASS_SERVERS,
    user_agent: str = APP_NAME,
    max_retries: int = MAX_RETRIES,
    timeout: int = TIMEOUT,
) -> dict | None:
    """POST a query to the Overpass API and return the parsed JSON.
    """
    headers = {"User-Agent": user_agent}

    for attempt in range(max_retries):
        for server in servers:
            try:
                response = requests.post(
                    server,
                    data={"data": query},
                    headers=headers,
                    timeout=timeout,
                )
                if response.status_code == 200 and response.text.strip():
                    return response.json()

                if response.status_code == 429:
                    logger.warning(
                        "Rate-limited by %s (attempt %d/%d). Waiting %ds…",
                        server, attempt + 1, max_retries, RATE_LIMIT_WAIT,
                    )
                    time.sleep(RATE_LIMIT_WAIT)
                    continue

                logger.warning(
                    "Unexpected status %d from %s.", response.status_code, server
                )

            except requests.exceptions.Timeout:
                logger.debug("Timeout connecting to %s.", server)
            except requests.exceptions.RequestException as exc:
                logger.error("Request error querying %s: %s", server, exc)

            time.sleep(RETRY_WAIT)

    logger.error("All %d retries exhausted. Returning None.", max_retries)
    return None
