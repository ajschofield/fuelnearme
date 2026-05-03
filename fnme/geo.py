from geopy.geocoders import Nominatim
from geopy.location import Location


def get_location(address: str) -> tuple[float, float]:
    geolocator = Nominatim(user_agent="FuelNearMe")
    result = geolocator.geocode(address)
    if not isinstance(result, Location):
        raise ValueError(f"Failed to get location from address: '{address}'")
    return (result.latitude, result.longitude)
