from functools import lru_cache

from geopy import exc
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.location import Location

from fnme.exceptions import LocationError


_geolocator = Nominatim(
    user_agent="FuelNearMe (https://github.com/ajschofield/FuelNearMe)"
)
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1)


@lru_cache(maxsize=1024)
def _geocode_address(address: str):
    return _geocode(address)


def get_location(address: str) -> tuple[float, float]:

    if not isinstance(address, str) or not address.strip():
        raise LocationError(message=f"Invalid address: '{address}'")

    try:
        result = _geocode_address(address)
    except exc.GeopyError as e:
        raise LocationError(message=f"Location service error: {e}")

    if not isinstance(result, Location):
        raise LocationError(message=f"Unknown location: '{address}'")
    return (result.latitude, result.longitude)
