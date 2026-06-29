import pytest
from pymongo import MongoClient
from pymongo.database import Database

from store.db import CYCLES, OPPORTUNITIES, PROFILES

TEST_DB_NAME = "test_job_hunt_db"
TEST_URI = "mongodb://localhost:27017"


@pytest.fixture
def test_db() -> Database:
    client: MongoClient = MongoClient(TEST_URI)
    db = client[TEST_DB_NAME]
    yield db
    db[PROFILES].drop()
    db[OPPORTUNITIES].drop()
    db[CYCLES].drop()
    client.close()
