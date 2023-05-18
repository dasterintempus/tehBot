from ..aws import build_dynamo_value, client as awsclient, extract_dynamo_value
import os
import uuid
import json
import hashlib
from typing import Set
import datetime

DYNAMOTABLE_API = os.environ.get("DYNAMOTABLE_API")
API_URL = os.environ.get("API_URL")

class ShortUrl:
    @staticmethod
    def find_issued_before(datetime : datetime.datetime):
        dynamo = awsclient("dynamodb")
        epoch = str(int(datetime.timestamp()))
        filterexpr = "IssuedEpoch < :epoch and attribute_exists(TargetUrl)"
        filtervals = {
            ":epoch": {"N": epoch}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [ShortUrl.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_shortstr(shortstr):
        dynamo = awsclient("dynamodb")
        filterexpr = "ShortStr = :shortstr and attribute_exists(TargetUrl)"
        filtervals = {
            ":shortstr": {"S": shortstr}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return ShortUrl.from_item(item)
    
    @staticmethod
    def from_target_url(target_url):
        dynamo = awsclient("dynamodb")
        filterexpr = "TargetUrl = :target_url"
        filtervals = {
            ":target_url": {"S": target_url}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return ShortUrl.from_item(item)

    @staticmethod
    def from_entryid(entryid):
        dynamo = awsclient("dynamodb")
        filterexpr = "EntryId = :entryid and attribute_exists(TargetUrl)"
        filtervals = {
            ":entryid": {"S": entryid}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return ShortUrl.from_item(item)

    @staticmethod
    def find_all():
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(TargetUrl) and attribute_exists(IssuedEpoch)"
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr
        )
        return [ShortUrl.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_item(item):
        token = ShortUrl(
            item["TargetUrl"]["S"]
        )
        token.entryid = item["EntryId"]["S"]
        token.shortstr = item["ShortStr"]["S"]
        token.issued = datetime.datetime.utcfromtimestamp(int(item["IssuedEpoch"]["N"]))
        return token
    
    @staticmethod
    def gen_shortstr(entryid):
        if ShortUrl.from_entryid(entryid) is not None:
            return None
        hexdigest = hashlib.sha256(entryid).hexdigest()
        for l in range(6, len(hexdigest)):
            if ShortUrl.from_shortstr(hexdigest[:l]) is None:
                return hexdigest[:l]
        return hexdigest

    def __init__(self:"ShortUrl", target_url:str) -> None:
        self.entryid = str(uuid.uuid4())
        self.target_url = target_url
        self.shortstr = ShortUrl.gen_shortstr(self.entryid)
        self.issued = datetime.datetime.utcnow()
    
    def __str__(self):
        return f"https://{API_URL}/link/{self.shortstr}"

    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "TargetUrl": {"S": self.target_url},
            "ShortStr": {"S": self.shortstr},
            "IssuedEpoch": {"N": str(int(self.issued.timestamp()))}
        }
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=DYNAMOTABLE_API,
            Item=item
        )
    
    def drop(self):
        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=DYNAMOTABLE_API,
            Key={"EntryId": {"S": self.entryid}}
        )