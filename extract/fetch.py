from collections.abc import Callable

import requests

_BASE_URL = "https://www.fuel-finder.service.gov.uk/api/v1"
_HEADERS = {"User-Agent": "FuelNearMe"}


def generate_access_token(client_id: str, client_secret: str) -> str:
    response = requests.post(
        f"{_BASE_URL}/oauth/generate_access_token",
        json={"client_id": client_id, "client_secret": client_secret},
        headers=_HEADERS,
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to generate access token: {response.status_code}")
    return response.json()["data"]["access_token"]


def _get_batch(
    url: str,
    batch_number: int,
    access_token: str,
    effective_start_timestamp: str | None,
) -> list[dict]:
    params: dict = {"batch-number": batch_number}
    if effective_start_timestamp is not None:
        params["effective-start-timestamp"] = effective_start_timestamp

    headers = {**_HEADERS, "Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers, params=params, timeout=10)

    if response.status_code == 404:
        return []

    if response.status_code != 200:
        raise RuntimeError(
            f"Unexpected status {response.status_code} "
            f"fetching {url} batch {batch_number}"
        )

    return response.json()


def fetch_stations_batch(
    batch_number: int, access_token: str, effective_start_timestamp: str | None = None
) -> list[dict]:
    return _get_batch(
        f"{_BASE_URL}/pfs",
        batch_number,
        access_token,
        effective_start_timestamp,
    )


def fetch_prices_batch(
    batch_number: int, access_token: str, effective_start_timestamp: str | None = None
) -> list[dict]:
    return _get_batch(
        f"{_BASE_URL}/pfs/fuel-prices",
        batch_number,
        access_token,
        effective_start_timestamp,
    )


def _fetch_all(
    fetch_fn: Callable, access_token: str, effective_start_timestamp: str | None = None
) -> list[dict]:
    results = []
    batch_number = 1
    while True:
        batch = fetch_fn(batch_number, access_token, effective_start_timestamp)
        if not batch:
            break
        results.extend(batch)
        batch_number += 1
    return results


def fetch_all_stations(
    access_token: str, effective_start_timestamp: str | None = None
) -> list[dict]:
    return _fetch_all(fetch_stations_batch, access_token, effective_start_timestamp)


def fetch_all_prices(
    access_token: str, effective_start_timestamp: str | None = None
) -> list[dict]:
    return _fetch_all(fetch_prices_batch, access_token, effective_start_timestamp)
