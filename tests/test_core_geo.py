from fnme.core.geo import get_location
from fnme.exceptions import LocationError

def test_get_location_valid_address():
    address = "London, UK"
    lat, lon = get_location(address)
    assert isinstance(lat, float)
    assert isinstance(lon, float)

def test_get_location_invalid_address():
    address = "This is not a real address"
    try:
        get_location(address)
        assert False
    except LocationError as e:
        assert isinstance(e, LocationError)

def test_get_location_empty_address():
    address = ""
    try:
        get_location(address)
        assert False
    except LocationError as e:
        assert isinstance(e, LocationError)

def test_get_location_none_address():
    address = None
    try:
        get_location(address)
        assert False
    except LocationError as e:
        assert isinstance(e, LocationError)

def test_get_location_numeric_address():
    address = 12345
    try:
        get_location(address)
        assert False
    except LocationError as e:
        assert isinstance(e, LocationError)

def test_get_location_special_characters_address():
    address = "!@#$%^&*()"
    try:
        get_location(address)
        assert False
    except LocationError as e:
        assert isinstance(e, LocationError)

def test_get_location_long_address():
    address = "This address doesn't exist, and it doesn't exist, and it \
    doesn't exist, and it doesn't exist, and it doesn't exist, and it doesn't \
    exist, and it doesn't exist, and it doesn't exist, and it doesn't exist"
    try:
        get_location(address)
        assert False
    except LocationError as e:
        assert isinstance(e, LocationError)