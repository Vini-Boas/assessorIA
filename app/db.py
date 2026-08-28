from app.config import (
    URL_DB,
    MONGODB_URI
)

import psycopg2
from pymongo import MongoClient

_pgsql_conn = None
_mongo_conn = None

def get_pgsql_conn():
    global _pgsql_conn
    if _pgsql_conn is None or _pgsql_conn.closed:
        _pgsql_conn = psycopg2.connect(URL_DB)
    return _pgsql_conn

def get_mongo_conn():
    global _mongo_conn
    if _mongo_conn is None:
        _mongo_conn = MongoClient(MONGODB_URI)
    return _mongo_conn

def pgsql_disconnect():
    global _pgsql_conn
    if _pgsql_conn is not None:
        _pgsql_conn.close()
        _pgsql_conn = None

def mongo_disconnect():
    global _mongo_conn
    if _mongo_conn is not None:
        _mongo_conn.close()
        _mongo_conn = None