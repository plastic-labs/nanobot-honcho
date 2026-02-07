"""HTTP and JSON utility functions."""

import asyncio
import json
from typing import Any

import httpx
from loguru import logger


def safe_json_parse(raw: str, source: str = "source") -> dict[str, Any] | None:
    """
    Safely parse JSON string.

    Args:
        raw: Raw JSON string to parse.
        source: Source identifier for logging.

    Returns:
        Parsed dict or None on error.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from {source}: {raw[:100]}")
        return None


async def http_post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    json_data: dict[str, Any],
    max_retries: int = 3,
    timeout: float = 10.0,
) -> httpx.Response | None:
    """
    POST request with automatic rate limit handling.

    Args:
        client: HTTP client to use.
        url: URL to POST to.
        headers: Request headers.
        json_data: JSON payload.
        max_retries: Maximum retry attempts.
        timeout: Request timeout in seconds.

    Returns:
        Response object or None on failure.
    """
    for attempt in range(max_retries):
        try:
            response = await client.post(url, headers=headers, json=json_data, timeout=timeout)
            if response.status_code == 429:
                data = response.json()
                retry_after = float(data.get("retry_after", 1.0))
                logger.warning(f"Rate limited, retrying in {retry_after}s")
                await asyncio.sleep(retry_after)
                continue
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"HTTP POST failed after {max_retries} attempts: {e}")
                return None
            await asyncio.sleep(1)
    return None
