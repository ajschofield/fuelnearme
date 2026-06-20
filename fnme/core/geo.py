from geopy import exc
from geopy.geocoders import Nominatim
from geopy.location import Location

from fnme.exceptions import LocationError


def get_location(address: str) -> tuple[float, float]:

    if not isinstance(address, str) or not address.strip():
        raise LocationError(message=f"Invalid address: '{address}'")

    geolocator = Nominatim(user_agent="FuelNearMe")

    try:
        result = geolocator.geocode(address)
    except exc.GeopyError as e:
        raise LocationError(message=f"Location service error: {e}")

    if not isinstance(result, Location):
        raise LocationError(message=f"Unknown location: '{address}'")
    return (result.latitude, result.longitude)
