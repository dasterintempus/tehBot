from ...discord import api as discord_api#, cdn as discord_cdn, RateLimitException
from ...aws import build_dynamo_value, client as awsclient, extract_dynamo_value
import os
import uuid
from .. import api as steam_api
from steam.steamid import SteamID
from steam.utils.throttle import ConstantRateLimit

from ...util import CONTEXT

DYNAMOTABLE_STEAM_LOBBY = os.environ.get("DYNAMOTABLE_STEAM_LOBBY")

class PlayerException(Exception):
    def __init__(self, player, msg):
        self.player = player
        self.msg = msg

class Player:
    @staticmethod
    def populate_summaries_cache(guildid):
        players = Player.get_all(guildid)
        steamids = [player.steamid for player in players]
        if len(steamids) == 0:
            return {}
        steamclient = steam_api(CONTEXT["secrets"]["steam_api_key"])
        count = (len(steamids)//100)+1
        summaries = {}
        with ConstantRateLimit(1, 2) as limiter:
            for n in range(count):
                ids = steamids[n*100:(n+1)*100]
                if len(ids) == 0:
                    break
                blob = steamclient.ISteamUser.GetPlayerSummaries(steamids=",".join([str(id.as_64) for id in ids]))
                for entry in blob["response"]["players"]:
                    entry_steamid = entry["steamid"]
                    summaries[entry_steamid] = entry
                limiter.wait()
        for entry_steamid in summaries:
            summary_entry = summaries[entry_steamid]
            print("SteamAPI results:", entry_steamid, summary_entry.get("gameid"), summary_entry.get("lobbysteamid"))
        CONTEXT["cache"]["player_summaries"] = {}
        CONTEXT["cache"]["player_summaries"][guildid] = summaries

    @staticmethod
    def get_player_summaries(guildid):
        if "player_summaries" not in CONTEXT["cache"] or guildid not in CONTEXT["cache"]["player_summaries"]:
            Player.populate_summaries_cache(guildid)
        return CONTEXT["cache"]["player_summaries"][guildid]

    @staticmethod
    def get_all(guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "GuildId = :guildid AND attribute_exists(DiscordId)"
        filtervals = {
            ":guildid": {"S": guildid}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [Player.from_item(item) for item in response["Items"]]

    @staticmethod
    def load_from_discord(discordid, guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "DiscordId = :discordid AND GuildId = :guildid"
        filtervals = {
            ":discordid": {"S": discordid},
            ":guildid": {"S": guildid}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return Player.from_item(item)
    
    @staticmethod
    def load_from_steamid(steamid, guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "SteamID = :steamid AND GuildId = :guildid"
        filtervals = {
            ":steamid": {"S": str(steamid.as_64)},
            ":guildid": {"S": guildid}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return Player.from_item(item)

    @staticmethod
    def from_item(item):
        user = Player(
            item["DiscordId"]["S"],
            item["Username"]["S"],
            item["Discriminator"]["S"],
            SteamID(item["SteamID"]["S"]),
            item["GuildId"]["S"],
        )
        user.entryid = item["EntryId"]["S"]
        user.settings = extract_dynamo_value(item["Settings"])
        return user

    def __init__(self, discord_id, discord_name, discord_discrim, steamid, guild_id):
        self.entryid = str(uuid.uuid4())
        self.discord_id = discord_id
        self.discord_name = discord_name
        self.discord_discrim = discord_discrim
        self.steamid = steamid
        self.guild_id = guild_id
        self.settings = {}
    
    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "DiscordId": {"S": self.discord_id},
            "Username": {"S": self.discord_name},
            "Discriminator": {"S": self.discord_discrim},
            "GuildId": {"S": self.guild_id},
            "SteamID": {"S": str(self.steamid.as_64)},
            "Settings": build_dynamo_value(self.settings)
        }
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            Item=item
        )
    
    def drop(self):
        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            Key={"EntryId": {"S": self.entryid}}
        )
        
def update_player(player):
    user_id = player.discord_id
    r = discord_api.get(f"users/{user_id}")
    if r.status_code != 200:
        raise PlayerException(player, f"Unable to query user: {r.status_code}")
    userblob = r.json()
    player.discord_name = userblob["username"]
    player.discord_discrim = userblob["discriminator"]
    player.guild_id = CONTEXT["request"]["guild_id"]
    player.save()
