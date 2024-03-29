from ..aws import build_dynamo_value, client as awsclient, extract_dynamo_value
import os
import uuid
import json

from typing import Set
import datetime

DYNAMOTABLE_API = os.environ.get("DYNAMOTABLE_API")

class Token:
    @staticmethod
    def find_issued_before(datetime : datetime.datetime):
        dynamo = awsclient("dynamodb")
        epoch = str(int(datetime.timestamp()))
        filterexpr = "IssuedEpoch < :epoch and attribute_exists(AuthGuildIds)"
        filtervals = {
            ":epoch": {"N": epoch}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Token.from_item(item) for item in response["Items"]]
    
    @staticmethod
    def from_token_value(tokenvalue):
        tokenuuid = tokenvalue.split("|")[0]
        tokenepoch = str(int(tokenvalue.split("|")[1]))
        dynamo = awsclient("dynamodb")
        filterexpr = "IssuedEpoch = :tokenepoch and EntryId = :tokenuuid and attribute_exists(AuthGuildIds)"
        filtervals = {
            ":tokenepoch": {"N": tokenepoch},
            ":tokenuuid": {"S": tokenuuid}
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
            return Token.from_item(item)

    @staticmethod
    def find_by_discord_userid(userid):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(AuthGuildIds) and attribute_exists(IssuedEpoch) and DiscordUserId = :userid"
        filtervals = {
            ":userid": {"S": userid}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Token.from_item(item) for item in response["Items"]]

    @staticmethod
    def find_all():
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(AuthGuildIds) and attribute_exists(IssuedEpoch)"
        response = dynamo.scan(
            TableName=DYNAMOTABLE_API,
            FilterExpression=filterexpr
        )
        return [Token.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_item(item):
        token = Token(
            item["DiscordUserId"]["S"],
            item["DiscordUserDisplayName"]["S"],
            extract_dynamo_value(item["AuthGuildIds"])
        )
        token.entryid = item["EntryId"]["S"]
        token.issued = datetime.datetime.utcfromtimestamp(int(item["IssuedEpoch"]["N"]))
        return token

    def __init__(self:"Token", user_id:str, user_display_name:str, auth_guild_ids:Set[str]) -> None:
        self.entryid = str(uuid.uuid4())
        self.user_id = user_id
        self.user_display_name = user_display_name
        self.issued = datetime.datetime.utcnow()
        self.auth_guild_ids = auth_guild_ids
    
    def __str__(self):
        return self.entryid + "|" + str(int(self.issued.timestamp()))

    def get_validity_for_guild_id(self, guild_id):
        now = datetime.datetime.utcnow()
        if (now - self.issued) > datetime.timedelta(seconds=3600):
            return "expired"
        if guild_id not in self.auth_guild_ids:
            return "unauthorized"
        return "valid"

    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "DiscordUserId": {"S": self.user_id},
            "DiscordUserDisplayName": {"S": self.user_display_name},
            "AuthGuildIds": build_dynamo_value(self.auth_guild_ids),
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