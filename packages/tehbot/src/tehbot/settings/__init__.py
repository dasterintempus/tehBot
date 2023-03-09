import os
import uuid
from typing import Optional, Iterable, Tuple
from ..aws import client as awsclient, add_to_dynamo_item

def get_guildid(guild_name:str) -> Optional[str]:
    dynamo = awsclient("dynamodb")

    filterexpr = "GuildName = :guildname AND SettingsKey = :settingskey"
    filtervals = {
        ":guildid": {"S": guild_name},
        ":settingskey": {"S": "guild_status"}
    }

    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )
    # try:
    # except:
    #     # print(f"Could not get settings for guild {guild_id} and key {key}")
    #     raise
    return response["Items"][0]["GuildId"]["S"]

def list_guilds() -> Iterable[Tuple[str, str]]:
    dynamo = awsclient("dynamodb")
    filterexpr = "SettingsKey = :settingskey"
    filtervals = {
        ":settingskey": {"S": "guild_status"}
    }
    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )
    return [(i["GuildName"]["S"], i["GuildId"]["S"]) for i in response["Items"]]

def get_settings(guild_id, key):
    dynamo = awsclient("dynamodb")

    filterexpr = "GuildId = :guildid AND SettingsKey = :settingskey"
    filtervals = {
        ":guildid": {"S": guild_id},
        ":settingskey": {"S": key}
    }

    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )
    try:
        settings = response["Items"][0]
    except:
        print(f"Could not get settings for guild {guild_id} and key {key}")
        raise
    return settings

def upsert_settings(guild_id, key, **kwargs):
    dynamo = awsclient("dynamodb")
    filterexpr = "GuildId = :guildid AND SettingsKey = :settingskey"
    filtervals = {
        ":guildid": {"S": guild_id},
        ":settingskey": {"S": key}
    }

    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )

    try:
        item = response["Items"][0]
    except:
        item = {}
        item["EntryId"] = {"S": str(uuid.uuid4())}
        item["GuildId"] = {"S": guild_id}
        item["SettingsKey"] = {"S": key}
    add_to_dynamo_item(item, **kwargs)
    dynamo.put_item(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        Item=item
    )

def delete_settings(guild_id, key, *args):
    dynamo = awsclient("dynamodb")
    filterexpr = "GuildId = :guildid AND SettingsKey = :settingskey"
    filtervals = {
        ":guildid": {"S": guild_id},
        ":settingskey": {"S": key}
    }

    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )

    try:
        item = response["Items"][0]
    except:
        item = {}
        item["EntryId"] = {"S": str(uuid.uuid4())}
        item["GuildId"] = {"S": guild_id}
        item["SettingsKey"] = {"S": key}
    else:
        for setting in args:
            if setting in item:
                del item[setting]
    dynamo.put_item(
        TableName=os.environ.get("DYNAMOTABLE_SETTINGS"),
        Item=item
    )