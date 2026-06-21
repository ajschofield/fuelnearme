import os

import sqlalchemy as sql


def connect_db(URL):
    engine = sql.create_engine(URL, echo=False)
    return engine
