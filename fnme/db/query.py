import sqlalchemy as sql


def run_query(db, query):
    with db.connect() as conn:
        result = conn.execute(sql.text(query))
        return result.fetchall()
