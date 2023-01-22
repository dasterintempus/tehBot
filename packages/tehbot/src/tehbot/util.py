import os

BUCKET_NAME = os.environ.get("S3BUCKET_CACHE")

class StaleDynamoItemException(Exception):
    pass

class StaleS3CacheException(Exception):
    pass

CONTEXT = {}