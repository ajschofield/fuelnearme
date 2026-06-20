import requests

_BASE_URL = "https://www.fuel-finder.service.gov.uk/api/v1"
_HEADERS = {"User-Agent": "FuelNearMe"}


def _get_batch(url: str, batch_number: int, effective_start_timestamp: str | None) -> list[dict]:
    params: dict = {"batch-number": batch_number}
    if effective_start_timestamp is not None:
        params["effective-start-timestamp"] = effective_start_timestamp

    response = requests.get(url, headers=_HEADERS, params=params, timeout=10)

    if response.status_code != 200:
        raise RuntimeError(
            f"Unexpected status {response.status_code} fetching {url} batch {batch_number}"
        )

    return response.json()


def fetch_stations_batch(
    batch_number: int, effective_start_timestamp: str | None = None
) -> list[dict]:
    return _get_batch(f"{_BASE_URL}/pfs", batch_number, effective_start_timestamp)


def fetch_prices_batch(
    batch_number: int, effective_start_timestamp: str | None = None
) -> list[dict]:
    return _get_batch(f"{_BASE_URL}/pfs/fuel-prices", batch_number, effective_start_timestamp)
