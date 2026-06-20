import pytest
from pygments.unistring import Lo

from fnme.exceptions import DataFetchError, InvalidDataError, LocationError


def test_datafetcherror_str():
    error = DataFetchError(message="Failed to fetch data")
    assert str(error) == "Failed to fetch data"


def test_invaliddataerror_str():
    error = InvalidDataError(message="Invalid data format")
    assert str(error) == "Invalid data format"


def test_locationerror_str():
    error = LocationError(message="Invalid address")
    assert str(error) == "Invalid address"
