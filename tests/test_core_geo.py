from types import SimpleNamespace

import pytest
from geopy.geocoders import Nominatim

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


def test_get_location_non_string_address():
    with pytest.raises(LocationError):
        get_location(12345)
    with pytest.raises(LocationError):
        get_location(None)
    with pytest.raises(LocationError):
        get_location("")


def test_get_location_mocked_non_location_result(monkeypatch):

    def mock_geo(self, address, *args, **kwargs):
        return SimpleNamespace(latitude=51.5074, longitude=-0.1278)

    monkeypatch.setattr(Nominatim, "geocode", mock_geo)

    with pytest.raises(LocationError):
        get_location("London, UK")


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
