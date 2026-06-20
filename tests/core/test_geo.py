from types import SimpleNamespace

import pytest
from geopy import exc
from geopy.location import Location

from fnme.core.geo import get_location
from fnme.exceptions import LocationError


def test_get_location_valid_address(monkeypatch):
    def ok(addr):
        return Location(
            "London, UK", (51.5, -0.1), {"display_name": "London, UK"}
        )

    monkeypatch.setattr("fnme.core.geo._geocode_address", ok)
    lat, lon = get_location("London, UK")
    assert lat == 51.5
    assert lon == -0.1


def test_get_location_invalid_address(monkeypatch):
    def none(addr):
        return None

    monkeypatch.setattr("fnme.core.geo._geocode_address", none)
    with pytest.raises(LocationError):
        get_location("This isn't a real address.")


def test_get_location_non_string_address():
    with pytest.raises(LocationError):
        get_location(12345)
    with pytest.raises(LocationError):
        get_location(None)
    with pytest.raises(LocationError):
        get_location("")


def test_get_location_mocked_non_location_result(monkeypatch):

    def mock_geo(address):
        return SimpleNamespace(latitude=51.5074, longitude=-0.1278)

    monkeypatch.setattr("fnme.core.geo._geocode_address", mock_geo)

    with pytest.raises(LocationError):
        get_location("London, UK")


def test_get_location_special_characters_address(monkeypatch):
    def none(addr):
        return None

    monkeypatch.setattr("fnme.core.geo._geocode_address", none)
    with pytest.raises(LocationError):
        get_location("!@#$%^&*()")


def test_get_location_long_address(monkeypatch):
    def none(addr):
        return None

    monkeypatch.setattr("fnme.core.geo._geocode_address", none)
    address = "This address doesn't exist" * 10
    with pytest.raises(LocationError):
        get_location(address)


def test_get_location_geopy_error(monkeypatch):
    def fail(addr):
        raise exc.GeopyError("cooked")

    monkeypatch.setattr("fnme.core.geo._geocode_address", fail)
    with pytest.raises(LocationError) as ei:
        get_location("London, UK")
    assert "Location service error: cooked" in str(ei.value)
