from fnme.db.schema import create_tables
from fnme.db.query import run_query
from sqlalchemy import create_engine


def test_table_schema_is_correct():
	
	# Create a test database connection
	db = create_engine("sqlite:///:memory:", echo=False)
	
	create_tables(db)

	# Run a query to get the table schema for the "stations" table
	schema_query = "PRAGMA table_info(stations);"
	schema_result = run_query(db, schema_query)

	assert len(schema_result) == 5  # Check that there are 5 columns in the "stations" table
	assert schema_result[0][1] == "node_id"  # Check the name of the first column