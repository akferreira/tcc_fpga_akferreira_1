DB_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "tcc"
def get_database(MongoClient):
    client = MongoClient(DB_CONNECTION_STRING)
    return client[DB_NAME]



