from ..aws import build_dynamo_value, client as awsclient, extract_dynamo_value
import os
import uuid
import json
from typing import Iterable, Tuple, Optional


DYNAMOTABLE_CONTROLLERLAYOUTS = os.environ.get("DYNAMOTABLE_CONTROLLERLAYOUTS")

class Game:
    @staticmethod
    def find_by_key(key, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "GameKey = :gamekey and GuildId = :guild_id"
        filtervals = {
            ":gamekey": {"S": key},
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
            return Game.from_item(item)
    
    @staticmethod
    def find_by_name(name, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "contains(GameName, :gamename) and GuildId = :guild_id"
        filtervals = {
            ":gamename": {"S": name},
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Game.from_item(item) for item in response["Items"]]

    @staticmethod
    def find_all(guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(GameKey) and GuildId = :guild_id"
        filtervals = {
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Game.from_item(item) for item in response["Items"]]
    
    @staticmethod
    def find_all_with_combos(guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(GameKey) and GuildId = :guild_id and attribute_exists(ComboInputs)"
        filtervals = {
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_CONTROLLERLAYOUTS,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Game.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_item(item):
        if "ComboInputs" in item:
            game = Game(
                item["GameKey"]["S"],
                item["GameName"]["S"],
                extract_dynamo_value(item["GameInputs"]),
                extract_dynamo_value(item["ComboInputs"]),
                item["GuildId"]["S"]
            )
        else:
            game = Game(
                item["GameKey"]["S"],
                item["GameName"]["S"],
                extract_dynamo_value(item["GameInputs"]),
                None,
                item["GuildId"]["S"]
            )
        game.entryid = item["EntryId"]["S"]
        return game

    def __init__(self:"Game", key:str, name:str, inputs:Iterable[str], combo_inputs:"Optional[Iterable[str]]", guild_id:str) -> None:
        self.entryid = str(uuid.uuid4())
        self.key = key
        self.name = name
        self.inputs = inputs
        self.combo_inputs = combo_inputs
        self.guild_id = guild_id

    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "GameKey": {"S": self.key},
            "GameName": {"S": self.name},
            "GameInputs": build_dynamo_value(self.inputs),
            "ComboInputs": build_dynamo_value(self.combo_inputs),
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
        
