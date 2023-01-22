import os
import uuid

from ..aws import client as awsclient, add_to_dynamo_item

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