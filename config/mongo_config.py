from pydantic import BaseModel


class MongoConfig(BaseModel):
    uri: str
    database: str
    test_database: str
