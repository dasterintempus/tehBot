from ..aws import build_dynamo_value, client as awsclient, extract_dynamo_value
import os
import uuid
import json
from typing import Iterable, Tuple


DYNAMOTABLE_CONTROLLERLAYOUTS = os.environ.get("DYNAMOTABLE_CONTROLLERLAYOUTS")

class Controller:
    @staticmethod
    def find_by_key(key, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "ControllerKey = :controllerkey and GuildId = :guild_id"
        filtervals = {
            ":controllerkey": {"S": key},
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return Controller.from_item(item)
    
    @staticmethod
    def find_by_name(name, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "contains(ControllerName, :controllername) and GuildId = :guild_id"
        filtervals = {
            ":controllername": {"S": name},
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Controller.from_item(item) for item in response["Items"]]

    @staticmethod
    def find_all(guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(ControllerKey) and GuildId = :guild_id"
        filtervals = {
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Controller.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_item(item):
        alias = Controller(
            item["ControllerKey"]["S"],
            item["ControllerName"]["S"],
            item["ControllerImagePath"]["S"],
            extract_dynamo_value(item["ControllerButtons"]),
            item["GuildId"]["S"]
        )
        alias.entryid = item["EntryId"]["S"]
        return alias

    def __init__(self:"Controller", key:str, name:str, imagepath:str, buttons:Iterable[Tuple[int, int]], guild_id:str) -> None:
        self.entryid = str(uuid.uuid4())
        self.key = key
        self.name = name
        self.imagepath = imagepath
        self.buttons = buttons
        self.guild_id = guild_id

    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "ControllerKey": {"S": self.key},
            "ControllerName": {"S": self.name},
            "ControllerImagePath": {"S": self.imagepath},
            "ControllerButtons": build_dynamo_value(self.buttons),
            "GuildId": {"S": self.guild_id}
        }
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            Item=item
        )
    
    def drop(self):
        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            Key={"EntryId": {"S": self.entryid}}
        )
        
