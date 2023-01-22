from ..aws import build_dynamo_value, client as awsclient, extract_dynamo_value
import os
import uuid
import json
from typing import Set


DYNAMOTABLE_QUOTES = os.environ.get("DYNAMOTABLE_QUOTES")

class Alias:
    @staticmethod
    def find_by_key(key, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "AliasKey = :aliaskey and GuildId = :guild_id"
        filtervals = {
            ":aliaskey": {"S": key},
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_QUOTES,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return Alias.from_item(item)
    
    @staticmethod
    def find_by_value(aliasvalue, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "contains(AliasValues, :aliasvalue) and GuildId = :guild_id"
        filtervals = {
            ":aliasvalue": {"S": aliasvalue},
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_QUOTES,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Alias.from_item(item) for item in response["Items"]]

    @staticmethod
    def find_all(guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(AliasKey) and GuildId = :guild_id"
        filtervals = {
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_QUOTES,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Alias.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_item(item):
        alias = Alias(
            item["AliasKey"]["S"],
            extract_dynamo_value(item["AliasValues"]),
            item["GuildId"]["S"]
        )
        alias.entryid = item["EntryId"]["S"]
        return alias

    def __init__(self:"Quote", key:str, values:Set[str], guild_id:str) -> None:
        self.entryid = str(uuid.uuid4())
        self.key = key
        self.values = values
        self.guild_id = guild_id

    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "AliasKey": {"S": self.key},
            "AliasValues": build_dynamo_value(self.values),
            "GuildId": {"S": self.guild_id}
        }
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=DYNAMOTABLE_QUOTES,
            Item=item
        )
    
    def drop(self):
        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=DYNAMOTABLE_QUOTES,
            Key={"EntryId": {"S": self.entryid}}
        )
        

class Quote:
    @staticmethod
    def find_by_name(name, guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(QuoteUrl) and QuoteName = :name and GuildId = :guild_id"
        filtervals = {
            ":name": {"S": name},
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_QUOTES,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return Quote.from_item(item)
    
    @staticmethod
    def find_all(guild_id):
        dynamo = awsclient("dynamodb")
        filterexpr = "attribute_exists(QuoteUrl) and GuildId = :guild_id"
        filtervals = {
            ":guild_id": {"S": guild_id}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_QUOTES,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        items = []
        lastkey = None
        while True:
            if lastkey is None:
                response = dynamo.scan(
                    TableName=DYNAMOTABLE_QUOTES,
                    FilterExpression=filterexpr,
                    ExpressionAttributeValues=filtervals
                )
            else:
                response = dynamo.scan(
                    TableName=DYNAMOTABLE_QUOTES,
                    FilterExpression=filterexpr,
                    ExpressionAttributeValues=filtervals,
                    ExclusiveStartKey=lastkey
                )
            items.extend(response["Items"])
            try:
                lastkey = response["LastEvaluatedKey"]
            except:
                break
        return [Quote.from_item(item) for item in items]

    @staticmethod
    def search(terms, guild_id):
        dynamo = awsclient("dynamodb")
        counter = 0
        filterexpr = "attribute_exists(QuoteUrl) and GuildId = :guild_id"
        filtervals = {":guild_id": {"S": guild_id}}
        for term in terms:
            acceptable = [term]
            aliases = Alias.find_by_value(term, guild_id)
            if len(aliases) > 0:
                for alias in aliases:
                    acceptable.extend(alias.values)
            filterexpr_parts = []
            for accept in acceptable:
                filterexpr_parts.append(f"contains(Tags, :term{counter})")
                filtervals[f":term{counter}"] = {"S": accept}
                counter+=1
            # if len(term) > 3:
            #     #allow searching on name substring too
            filterexpr_parts.append(f"contains(QuoteName, :term{counter})")
            filtervals[f":term{counter}"] = {"S": accept}
            counter+=1
            filterexpr_chunk = " ( " + " or ".join(filterexpr_parts) + " ) "
            filterexpr = filterexpr + " and " + filterexpr_chunk
            print(filterexpr)
            print(json.dumps(filtervals))
        items = []
        lastkey = None
        while True:
            if lastkey is None:
                response = dynamo.scan(
                    TableName=DYNAMOTABLE_QUOTES,
                    FilterExpression=filterexpr,
                    ExpressionAttributeValues=filtervals
                )
            else:
                response = dynamo.scan(
                    TableName=DYNAMOTABLE_QUOTES,
                    FilterExpression=filterexpr,
                    ExpressionAttributeValues=filtervals,
                    ExclusiveStartKey=lastkey
                )
            items.extend(response["Items"])
            try:
                lastkey = response["LastEvaluatedKey"]
            except:
                break
        return [Quote.from_item(item) for item in items]

    @staticmethod
    def from_item(item):
        quote = Quote(
            item["QuoteUrl"]["S"],
            item["QuoteName"]["S"],
            extract_dynamo_value(item["Tags"]),
            item["GuildId"]["S"]
        )
        quote.entryid = item["EntryId"]["S"]
        return quote

    def __init__(self:"Quote", url:str, name:str, tags:Set[str], guild_id:str) -> None:
        self.entryid = str(uuid.uuid4())
        self.url = url
        self.name = name
        self.tags = tags
        self.guild_id = guild_id

    def to_dict(self):
        tags = list(self.tags)
        tags.sort()
        return {
            "name": self.name,
            "tags": tags,
            "url": self.url
        }

    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "QuoteUrl": {"S": self.url},
            "QuoteName": {"S": self.name},
            "Tags": build_dynamo_value(self.tags),
            "GuildId": {"S": self.guild_id}
        }
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=DYNAMOTABLE_QUOTES,
            Item=item
        )
    
    def drop(self):
        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=DYNAMOTABLE_QUOTES,
            Key={"EntryId": {"S": self.entryid}}
        )
        