"""
WAQI API client
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

import requests

API_ROOT = "https://api.waqi.info/feed/{}/?token={}"  # WAQI endpoint


def fetch_aqi(city: str, token: str) -> Dict[str, Any]:
    """Return WAQI JSON for given *city* (or station id).

    Parameters
    ----------
    city : str
        WAQI city / station identifier (e.g. ``"antalya"`` or ``"@4018"``).
    token : str
        Your personal WAQI API token.

    Raises
    ------
    RuntimeError
        If WAQI responds with a non-"ok" status.
    """
    url = API_ROOT.format(city, token)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data: Dict[str, Any] = response.json()

    if data["status"] != "ok":
        raise RuntimeError(str(data.get("data")))

    return data


def _get_token() -> str:
    """Return token from ``$WAQI_TOKEN`` env or Streamlit secrets."""
    token = os.getenv("WAQI_TOKEN")
    if token:
        return token

    # Fall back to Streamlit secrets when running inside Streamlit Cloud
    try:
        import streamlit as st  # type: ignore

        return st.secrets["WAQI_TOKEN"]  # type: ignore[index]
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(
            "WAQI_TOKEN not found in environment variables or Streamlit secrets"
        ) from exc


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python aqi_client.py <city_id>")
        sys.exit(1)

    city_id: str = sys.argv[1]
    api_token: str = _get_token()
    print(fetch_aqi(city_id, api_token))