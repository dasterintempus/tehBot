from datetime import datetime
from ...discord import api as discord_api#, cdn as discord_cdn, RateLimitException
from ...aws import client as awsclient
import os
import uuid
from steam.steamid import SteamID
from ..store import get_app_name, get_app_header_url
from .players import Player
from ...cache import populate_member_cache_v2
from ...settings import get_settings
from ...util import CONTEXT
import requests
from bs4 import BeautifulSoup
from collections import namedtuple
import pprint
import logging
logger = logging.getLogger(__name__)

from typing import List

STEAM_API_KEY = os.environ.get("STEAM_API_KEY")
DYNAMOTABLE_STEAM_LOBBY = os.environ.get("DYNAMOTABLE_STEAM_LOBBY")
API_URL = os.environ.get("API_URL")

LobbyKey = namedtuple("LobbyKey", ["appid", "lobbyid"])

class LobbyException(Exception):
    pass

class LobbyNotFoundException(LobbyException):
    pass

class LobbyProfileNotLinkedException(LobbyException):
    pass

class LobbyAlreadyExistsException(LobbyException):
    def __init__(self, status_channel, status_message):
        self.status_channel = status_channel
        self.status_message = status_message

class Lobby:
    @staticmethod
    def build_lobby_from_discord_command(body, allow_duplicates=False):
        guildid = body["guild_id"]
        discord_id = body["member"]["user"]["id"]
        posting_player = Player.load_from_discord(discord_id, guildid)
        if posting_player is None:
            raise LobbyProfileNotLinkedException()
        
        summaries = Player.get_player_summaries(guildid)
        #print("summaries")
        #pprint.pprint(summaries)
        lobby = None
        #build lobby
        try:
            summary_entry = summaries[str(posting_player.steamid.as_64)]
            appid = summary_entry["gameid"]
            lobbyid = summary_entry["lobbysteamid"]
        except:
            raise LobbyNotFoundException()
        if allow_duplicates is False:
            previous_lobby = Lobby.load_from_steaminfo(appid, lobbyid, guildid)
            if previous_lobby is not None:
                raise LobbyAlreadyExistsException(previous_lobby.status_channel, previous_lobby.status_message)
        lobby = Lobby(appid, lobbyid, guildid, "manual")
        try:
            description = body["data"]["options"][0]["options"][0]["value"]
            lobby.description = description
        except:
            pass
        
        return lobby

    @staticmethod
    def get_stored_lobbies(guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "GuildId = :guildid AND attribute_exists(AppId)"
        filtervals = {
            ":guildid": {"S": guildid}
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        lobbies = [Lobby.from_item(i) for i in response["Items"]]
        lobbies_d = {LobbyKey(lobby.appid, lobby.lobbyid) : lobby for lobby in lobbies}
        return lobbies_d

    @staticmethod
    def get_manual_lobbies(guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "GuildId = :guildid AND Origin = :origin AND attribute_exists(AppId)"
        filtervals = {
            ":guildid": {"S": guildid},
            ":origin": {"S": "manual"},
        }
        response = dynamo.scan(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        lobbies = [Lobby.from_item(i) for i in response["Items"]]
        lobbies_d = {LobbyKey(lobby.appid, lobby.lobbyid) : lobby for lobby in lobbies}
        # current_lobbykeys = [LobbyKey(summary["appid"], summary["lobbyid"]) for summary in summaries.values()]
        # lobbies = [lobby for lobby in lobbies if LobbyKey(lobby.appid, lobby.lobbyid) in current_lobbykeys]
        return lobbies_d

    @staticmethod
    def get_auto_lobbies(guildid, summaries):
        players = Player.get_all(guildid)
        print("Players:")
        pprint.pprint(players)
        print("Player settings")
        pprint.pprint([player.settings for player in players])
        auto_steamids = [player.steamid for player in players if player.settings.get("auto-track", False)]
        print("Auto steam ids:")
        pprint.pprint(auto_steamids)
        # summaries = Player.get_player_summaries(steamids)
        lobbies_d = {}
        for player_steamid in summaries:
            steamid = SteamID(player_steamid)
            if steamid not in auto_steamids:
                continue
            summary_entry = summaries[player_steamid]
            try:
                appid = summary_entry["gameid"]
                lobbyid = summary_entry["lobbysteamid"]
                lobbykey = LobbyKey(appid, lobbyid)
            except:
                continue
            if lobbykey not in lobbies_d:
                #try to find in DB first
                lobby = Lobby.load_from_steaminfo(appid, lobbyid, guildid)
                if lobby is None:
                    #make a new one
                    lobby = Lobby(appid, lobbyid, guildid, "autodiscovery")
                    lobby.save()
                lobbies_d[lobbykey] = lobby
        return lobbies_d

    @staticmethod
    def clean_old_lobbies(guildid, summaries):
        current_lobbykeys = [LobbyKey(summary["gameid"], summary["lobbysteamid"]) for summary in summaries.values() if "gameid" in summary and "lobbysteamid" in summary]
        stored_lobbies_d = Lobby.get_stored_lobbies(guildid)
        print("stored lobbies")
        pprint.pprint(stored_lobbies_d)
        for stored_lobbykey in stored_lobbies_d:
            if stored_lobbykey not in current_lobbykeys:
                stored_lobbies_d[stored_lobbykey].drop()
    
    @staticmethod
    def post_lobby_statuses(guildid, lobbies_d, summaries):
        lobby_settings = get_settings(guildid, "lobby_tracker")
        for lobbykey in lobbies_d:
            lobby = lobbies_d[lobbykey]
            print("posting status")
            lobby.post_status_message(summaries)

    @staticmethod
    def load_from_steaminfo(appid, lobbyid, guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "AppId = :appid AND LobbyId = :lobbyid AND GuildId = :guildid"
        filtervals = {
            ":appid": {"S": appid},
            ":lobbyid": {"S": lobbyid},
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
            return Lobby.from_item(item)

    @staticmethod
    def from_entryid(entryid, guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "EntryId = :entryid AND GuildId = :guildid AND attribute_exists(AppId)"
        filtervals = {
            ":entryid": {"S": entryid},
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
            return Lobby.from_item(item)

    @staticmethod
    def from_item(item):
        lobby = Lobby(
            item["AppId"]["S"],
            item["LobbyId"]["S"],
            item["GuildId"]["S"],
            item["Origin"]["S"],
        )
        lobby.entryid = item["EntryId"]["S"]
        if "Description" in item:
            lobby.description = item["Description"]["S"]
        if "StatusChannel" in item:
            lobby.status_channel = item["StatusChannel"]["S"]
        if "StatusMessage" in item:
            lobby.status_message = item["StatusMessage"]["S"]
        return lobby

    def __init__(self, appid, lobbyid, guildid, origin, description=None):
        self.entryid = str(uuid.uuid4())
        self.appid = appid
        self.lobbyid = lobbyid
        self.guildid = guildid
        self.origin = origin
        self.description = description
        self.status_channel = None
        self.status_message = None
    
    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "AppId": {"S": self.appid},
            "LobbyId": {"S": self.lobbyid},
            "GuildId": {"S": self.guildid},
            "Origin": {"S": self.origin}
        }
        if self.description is not None:
            item["Description"] = {"S": self.description}
        if self.status_channel is not None:
            item["StatusChannel"] = {"S": self.status_channel}
        if self.status_message is not None:
            item["StatusMessage"] = {"S": self.status_message}
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            Item=item
        )
    
    def drop(self):
        if self.status_channel is not None and self.status_message is not None:
            r = discord_api.delete(f"/channels/{self.status_channel}/messages/{self.status_message}")
            print(r.status_code)
            print(r.text)
            if r.status_code != 404:
                r.raise_for_status()

        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=DYNAMOTABLE_STEAM_LOBBY,
            Key={"EntryId": {"S": self.entryid}}
        )

    def __eq__(self, other) -> bool:
        return self.appid == other.appid and self.lobbyid == other.lobbyid and self.guildid == other.guildid
    
    def __hash__(self):
        return hash((self.appid, self.lobbyid, self.guildid))
    
    def get_lobby_players(self, summaries):
        from .players import Player
        # all_players = Player.get_all(self.guildid)
        # all_steamids = [player.steamid for player in all_players]
        lobby_players = []
        for player_steamid in summaries:
            steamid = SteamID(player_steamid)
            # if steamid not in all_steamids:
            #     continue
            summary_entry = summaries[player_steamid]
            try:
                appid = summary_entry["gameid"]
                lobbyid = summary_entry["lobbysteamid"]
            except:
                continue
            if appid == self.appid and lobbyid == self.lobbyid:
                player = Player.load_from_steamid(steamid, self.guildid)
                if player is not None:
                    lobby_players.append(player)
        print("getting lobby players")
        pprint.pprint(lobby_players)
        return lobby_players

    def post_status_message(self, summaries):
        lobby_players = self.get_lobby_players(summaries)
        msg_body = self.render_status_message(lobby_players)
        lobby_settings = get_settings(self.guildid, "lobby_tracker")
        channel_id = lobby_settings["status_channel"]["S"]
        if self.status_channel is None and self.status_message is None:
            self.status_channel = channel_id
            r = discord_api.post(f"/channels/{self.status_channel}/messages", json=msg_body)
            r.raise_for_status()
            self.status_message = r.json()["id"]
        else:
            r = discord_api.patch(f"/channels/{self.status_channel}/messages/{self.status_message}", json=msg_body)
            if r.status_code == 404: #if we can't update a message (admin delete for example) then drop that entry immediately and cease tracking
                self.drop()
                return
            r.raise_for_status()
        self.save()
    
    def render_steam_url(self, player: "Player"):
        return f"steam://joinlobby/{self.appid}/{self.lobbyid}/{player.steamid.as_64}"

    def render_redirect_url(self, player: "Player"):
        from tehbot.api.shorturl import ShortUrl
        target_url = f"https://{API_URL}/guilds/{self.guildid}/steam/lobby/{self.entryid}/player/{player.entryid}/redirect"
        url = ShortUrl.from_target_url(target_url)
        if url is None:
            url = ShortUrl(target_url)
            url.save()
        return str(url)

    def render_status_message(self, lobby_players: List["Player"]):
        try:
            r = requests.get(f"https://store.steampowered.com/app/{self.appid}")
            soup = BeautifulSoup(r.text, "html.parser")
            appname = get_app_name(soup)
            appheaderurl = get_app_header_url(soup)
        except:
            logger.traceback("Unable to parse app name and app header image URL")
            appname = "UNKNOWN GAME"
            appheaderurl = None

        if self.guildid not in CONTEXT["cache"] or self.guildid not in CONTEXT["cache"]["members"]:
            populate_member_cache_v2(self.guildid)

        text = f"**{appname} Lobby!**\n"
        if self.description is not None:
            text = text + f"*{self.description}*\n"
        text = text + "\n***Currently Playing:***"
        for player in lobby_players:
            username = CONTEXT["cache"]["members"][self.guildid][player.discord_id]["nick"]
            if username is None:
                username = CONTEXT["cache"]["members"][self.guildid][player.discord_id]["user"]["username"]
            redirect_url = self.render_redirect_url(player)
            steam_url = self.render_steam_url(player)
            text = text + f"\n\t{username}: {steam_url} ({redirect_url})"
        text = text + f"\n\n*{datetime.now().isoformat()}*"
        return {
            "embeds": [
                    {
                        "image": {"url": appheaderurl}
                    }
                ],
            "content": text
        }