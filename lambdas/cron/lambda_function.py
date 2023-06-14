import datetime
from tehbot.settings import get_settings, upsert_settings, list_guilds
from tehbot.steam.lobbies import Lobby, LobbyKey
from tehbot.steam.lobbies.players import Player
from tehbot.aws import client as awsclient
from steam.utils.throttle import ConstantRateLimit
import os
import json
from tehbot.aws import client as awsclient
from tehbot.util import CONTEXT
from tehbot.api.token import Token
from tehbot.api.shorturl import ShortUrl
from tehbot.chart.users import User, update_user as update_chart_user
import pprint

def lobby_update(guildid):
    try:
        lobby_settings = get_settings(guildid, "lobby_tracker")
    except:
        return
    if lobby_settings["status_channel"]["S"] == "":
        return
    summaries = Player.get_player_summaries(guildid)
    print("summaries")
    pprint.pprint(summaries)
    Lobby.clean_old_lobbies(guildid, summaries)
    
    stored_lobbies_d = Lobby.get_stored_lobbies(guildid)
    print("stored lobbies")
    pprint.pprint(stored_lobbies_d)
    auto_lobbies_d = Lobby.get_auto_lobbies(guildid, summaries)
    print("auto lobbies")
    pprint.pprint(auto_lobbies_d)
    current_lobbies_d = dict(stored_lobbies_d)
    for auto_lobbykey in auto_lobbies_d:
        if auto_lobbykey not in current_lobbies_d:
            current_lobbies_d[auto_lobbykey] = auto_lobbies_d[auto_lobbykey]
    print("current lobbies")
    pprint.pprint(current_lobbies_d)
    Lobby.post_lobby_statuses(guildid, current_lobbies_d, summaries)

def token_cleanup():
    tokens = Token.find_issued_before(datetime.datetime.utcnow() - datetime.timedelta(seconds=3600))
    for token in tokens:
        token.drop()

def url_cleanup():
    urls = ShortUrl.find_issued_before(datetime.datetime.utcnow() - datetime.timedelta(seconds=3600*48))
    for url in urls:
        url.drop()

def chart_user_updates(guildid):
    users = User.get_all_users(guildid)
    for user in users:
        update_chart_user(user)

def lambda_handler(event, context):
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}
    print(json.dumps(event))

    op = event["op"]
    if op == "lobby_update":
        if "guildid" in event:
            guildid = event["guildid"]
            lobby_update(guildid)
        else:
            guilds = list_guilds()
            lam = awsclient("lambda")
            for guildname, guildid in guilds:
                lam.invoke(FunctionName=context.invoked_function_arn, InvocationType="Event", Payload=json.dumps({"op": op, "guildid": guildid}).encode())
    elif op == "chart_user_update":
        if "guildid" in event:
            guildid = event["guildid"]
            chart_user_updates(guildid)
        else:
            guilds = list_guilds()
            lam = awsclient("lambda")
            for guildname, guildid in guilds:
                lam.invoke(FunctionName=context.invoked_function_arn, InvocationType="Event", Payload=json.dumps({"op": op, "guildid": guildid}).encode())
    elif op == "token_cleanup":
        token_cleanup()
    elif op == "url_cleanup":
        url_cleanup()