__all__ = ['connect']

from pymongo import MongoClient
import os

def connect():
    db_username = os.environ.get('DB_USERNAME')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST') or '127.0.0.1'
    db_port = os.environ.get('DB_PORT') or 27017
    db = MongoClient(host=db_host, port=db_port, username=db_username, password=db_password).bpmcrawl
    return db