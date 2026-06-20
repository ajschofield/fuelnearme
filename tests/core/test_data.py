from fnme.core.data import get_latest_data


def test_get_latest_data_should_not_return_empty_dataframe():
    df, last_modified = get_latest_data()
    assert not df.empty, "DataFrame should not be empty"
    assert last_modified is None or isinstance(last_modified, str), "Last modified should be a string or None"

