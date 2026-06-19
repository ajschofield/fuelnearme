import os

import sqlalchemy as sql


def connect_db():
    DATABASE_URL = os.environ["DATABASE_URL"]
    engine = sql.create_engine(DATABASE_URL, echo=False)
    return engine