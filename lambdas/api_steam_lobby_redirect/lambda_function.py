from tehbot.settings import get_settings
import re
import os
import json
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings
from tehbot.discord import build_oauth_client, api as discordapi
from tehbot.util import CONTEXT
from tehbot.api import make_response, get_json_body
from tehbot.steam.lobbies import Lobby
from tehbot.steam.lobbies.players import Player
import base64
import traceback

import logging
from http.client import HTTPConnection # py3

import json
import logging

logging.basicConfig(force=True, format="%(asctime)s %(levelname)s - %(name)s %(pathname)s.%(funcName)s:%(lineno)s %(message)s")
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    if "dev" in context.function_name.lower():
        logger.setLevel(logging.DEBUG)
        HTTPConnection.debuglevel = 1
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        print(json.dumps(event))
    else:
        logger.setLevel(logging.INFO)
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}

    guild_id = event["pathParameters"]["guild_id"]
    lobby_id = event["pathParameters"]["lobby_uuid"]
    player_id = event["pathParameters"]["player_uuid"]
    
    lobby = Lobby.from_entryid(lobby_id, guild_id)
    if lobby is None:
        return make_response(404, body="Not Found")

    player = Player.from_entryid(player_id, guild_id)

    lobby_url = lobby.render_steam_url(player)
    response_body = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Refresh" content="0; URL={lobby_url}" />
    <title>tehBot Steam Lobby Redirect</title>
  </head>
  <body>
    <div class="container-fluid" id="content"><a href="{lobby_url}">{lobby_url}</a></div>
  </body>
</html>
'''
    return make_response(308, body=response_body, headers={"Location": lobby_url})