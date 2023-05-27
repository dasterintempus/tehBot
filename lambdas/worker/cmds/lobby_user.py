from tehbot.discord import api as discord_api
from tehbot.steam import api as steam_api, SteamAPIException
from tehbot.steam.lobbies.players import Player
from tehbot.steam.lobbies import Lobby, LobbyAlreadyExistsException, LobbyProfileNotLinkedException, LobbyNotFoundException
# from tehbot.aws import client as awsclient
# from tehbot.settings import get_settings, upsert_settings
from tehbot.util import CONTEXT
from steam.steamid import SteamID
from steam.client import SteamClient
from steam.core.msg import MsgProto
from steam.enums.emsg import EMsg
from steam.enums import EResult
import traceback
import pprint

def lobby_optin(body):
    guildid = body["guild_id"]
    steam_profile_url = body["data"]["options"][0]["options"][0]["value"]
    try:
        steamapi = steam_api(CONTEXT["secrets"]["steam_api_key"])
    except SteamAPIException as e:
        return False, {"json": {"content": "Steam API returned an error. Will retry..."}}
    if steam_profile_url[-1] == "/":
        steam_profile_url = steam_profile_url[:-1]
    vanity = steam_profile_url.split("/")[-1]
    pprint.pprint(vanity)
    response = steamapi.ISteamUser.ResolveVanityURL(vanityurl=vanity)["response"]
    pprint.pprint(response)
    try:
        steamid = SteamID(response["steamid"])
    except:
        steamid = SteamID(vanity)
    if str(steamid.as_64) == "0":
        return True, {"json": {"content": "Unable to find your Steam profile. Please use the full URL from your Steam Profile, such as: 'https://steamcommunity.com/id/dasterin/' or 'https://steamcommunity.com/profiles/76561197966215444'."}}
    existing_player_steam = Player.load_from_steamid(steamid, guildid)
    
    discord_id = body["member"]["user"]["id"]
    discord_username = body["member"]["user"]["username"]
    discord_discriminator = body["member"]["user"]["discriminator"]
    existing_player_discord = Player.load_from_discord(discord_id, guildid)
    if existing_player_discord is not None and existing_player_steam is not None and existing_player_discord.steamid == existing_player_steam.steamid:
        return True, {"json": {"content": "You have already opted in to this Steam profile.\nYou can use the Lobby features such as `/lobby friend` and `/lobby link`."}}
    elif existing_player_discord is not None:
        return True, {"json": {"content": "You have already opted in to another Steam profile!\nYou can use `/lobby opt-out` to remove your existing Steam profile link."}}
    elif existing_player_steam is not None:
        return True, {"json": {"content": "This Steam profile is already linked!\nYou can use `/lobby opt-out` from the corresponding Discord account to remove your existing Steam profile link, or contact your bot administrator."}}

    player = Player(discord_id, discord_username, discord_discriminator, steamid, guildid)

    player.save()

    return True, {"json": {"content": "Now tracking your lobbies!"}}

def lobby_optout(body):
    guildid = body["guild_id"]
    discord_id = body["member"]["user"]["id"]
    player = Player.load_from_discord(discord_id, guildid)
    if player is None:
        return True, {"json": {"content": "You have not yet opted in."}}
    player.drop()

    return True, {"json": {"content": "No longer tracking your lobbies."}}

# def lobby_preferences(body):
#     guildid = body["guild_id"]
#     discord_id = body["member"]["user"]["id"]
#     player = Player.load_from_discord(discord_id, guildid)
#     if player is None:
#         return False, {"json": {"content": "You have not yet opted in."}}
#     preference_value = body["data"]["options"][0]["options"][0]["name"]
    
#     if preference_value == "enable-auto-track":
#         player.settings["auto-track"] = True
#     elif preference_value == "disable-auto-track":
#         del player.settings["auto-track"]
#     player.save()
    
#     return True, {"json": {"content": "Preferences updated."}}

def lobby_friend(body):
    guildid = body["guild_id"]
    discord_id = body["member"]["user"]["id"]
    posting_player = Player.load_from_discord(discord_id, guildid)
    if posting_player is None:
        return True, {"json": {"content": "Your Steam profile is not linked. Please use `/lobby opt-in`."}}
    
    client = SteamClient()

    @client.on("error")
    def steam_error(result):
        print(f"Steam Error: {repr(result)}")
    
    try:
        client.login(username=CONTEXT["secrets"]["steam_username"], password=CONTEXT["secrets"]["steam_password"])
    except:
        return True, {"json": {"content": "tehBot is unable to login to Steam..."}}
    
    if posting_player.steamid in client.friends:
        return True, {"json": {"content": "You are already Steam Friends with tehBot."}}

    msg = MsgProto(EMsg.ClientAddFriend)
    msg.body.steamid_to_add = posting_player.steamid
    resp = client.send_message_and_wait(msg, EMsg.ClientAddFriendResponse)
    if resp.eresult == EResult.OK:
        return True, {"json": {"content": "tehBot has sent you a Friend Request on Steam."}}
    else:
        return True, {"json": {"content": "tehBot was unable to send you a Friend Request."}}

def lobby_link(body):
    guildid = body["guild_id"]
    try:
        lobby = Lobby.build_lobby_from_discord_command(body)
    except LobbyNotFoundException as e:
        return True, {"json": {"content": "Lobby not found. Are you offline/invisible/private on Steam?"}}
    except LobbyProfileNotLinkedException as e:
        traceback.print_exc()
        return True, {"json": {"content": "Your Steam profile is not linked. Please use `/lobby opt-in`."}}
    except LobbyAlreadyExistsException as e:
        traceback.print_exc()
        if e.status_channel is not None and e.status_message is not None:
            return True, {"json": {"content": f"Lobby already linked here: https://discord.com/channels/{guildid}/{e.status_channel}/{e.status_message}"}}
        else:
            return True, {"json": {"content": f"Lobby currently being posted, please check the server's lobby channel."}}
    except SteamAPIException as e:
        traceback.print_exc()
        return False, {"json": {"content": "Steam API returned an error. Will retry..."}}
    
    summaries = Player.get_player_summaries(guildid)

    try:
        lobby.post_status_message(summaries)
    except:
        traceback.print_exc()
        return True, {"json": {"content": "Unable to post lobby link to Discord..."}}
    lobby.save()

    return True, {"json": {"content": f"Posted lobby link here: https://discord.com/channels/{guildid}/{lobby.status_channel}/{lobby.status_message}"}}

def lobby_url(body):
    guildid = body["guild_id"]
    try:
        lobby = Lobby.build_lobby_from_discord_command(body)
    except LobbyNotFoundException as e:
        return True, {"json": {"content": "Lobby not found. Are you offline/invisible/private on Steam?"}}
    except LobbyProfileNotLinkedException as e:
        traceback.print_exc()
        return True, {"json": {"content": "Your Steam profile is not linked. Please use `/lobby opt-in`."}}
    except LobbyAlreadyExistsException as e:
        traceback.print_exc()
        if e.status_channel is not None and e.status_message is not None:
            return True, {"json": {"content": f"Lobby already linked here: https://discord.com/channels/{guildid}/{e.status_channel}/{e.status_message}"}}
        else:
            return True, {"json": {"content": f"Lobby currently being posted, please check the server's lobby channel."}}
    except SteamAPIException as e:
        traceback.print_exc()
        return False, {"json": {"content": "Steam API returned an error. Will retry..."}}

    try:
        discord_id = body["member"]["user"]["id"]
        player = Player.load_from_discord(discord_id, guildid)
        url = lobby.render_standalone_redirect_url(player)
    except:
        traceback.print_exc()
        return True, {"json": {"content": "Unable to post lobby link to Discord..."}}
    #do not save lobby!

    return True, {"json": {"content": f"Lobby URL: {url}"}}

def lobby_private_url(body):
    guildid = body["guild_id"]
    try:
        lobby = Lobby.build_lobby_from_discord_command(body)
    except LobbyNotFoundException as e:
        return True, {"json": {"content": "Lobby not found. Are you offline/invisible/private on Steam?"}}
    except LobbyProfileNotLinkedException as e:
        traceback.print_exc()
        return True, {"json": {"content": "Your Steam profile is not linked. Please use `/lobby opt-in`."}}
    except LobbyAlreadyExistsException as e:
        traceback.print_exc()
        if e.status_channel is not None and e.status_message is not None:
            return True, {"json": {"content": f"Lobby already linked here: https://discord.com/channels/{guildid}/{e.status_channel}/{e.status_message}"}}
        else:
            return True, {"json": {"content": f"Lobby currently being posted, please check the server's lobby channel."}}
    except SteamAPIException as e:
        traceback.print_exc()
        return False, {"json": {"content": "Steam API returned an error. Will retry..."}}

    try:
        discord_id = body["member"]["user"]["id"]
        player = Player.load_from_discord(discord_id, guildid)
        url = lobby.render_standalone_redirect_url(player)
    except:
        traceback.print_exc()
        return True, {"json": {"content": "Unable to post lobby link to Discord..."}}
    #do not save lobby!

    r = discord_api.post(f"/users/@me/channels", json={"recipient_id": discord_id})
    try:
        r.raise_for_status()
    except:
        traceback.print_exc()
        print(r.text)
        return True, {"json": {"content": f"tehBot is not able to DM you on Discord..."}}
    
    channel_id = r.json()["id"]
    r = discord_api.post(f"/channels/{channel_id}/messages", json={"content": f"Lobby URL: {url}"})
    try:
        r.raise_for_status()
    except:
        traceback.print_exc()
        print(r.text)
        return True, {"json": {"content": f"tehBot is not able to DM you on Discord..."}}
        
    return True, {"json": {"content": f"Lobby URL has been DM'd to you."}}