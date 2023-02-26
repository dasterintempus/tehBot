from tehbot.settings import get_settings
import re
import os
import json
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings
from tehbot.discord import build_oauth_client, api as discordapi
from tehbot.util import CONTEXT
from tehbot.api import make_response
from tehbot.api.token import Token
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

    try:
        event_body = event["body"]
        if event["isBase64Encoded"]:
            event_body = base64.b64decode(event_body)
    except:
        return make_response(500, {"error": {"code": "ProcessingError", "msg": "Unable to load event body..."}})
    try:
        request_body = json.loads(event_body)
    except:
        return make_response(400, {"error": {"code": "InvalidJson", "msg": "Request body was not valid JSON."}})

    try:
        oauth_discord_client = build_oauth_client(request_body["code"])
    except Exception as e:
        print(traceback.format_exc())
        return make_response(403, {"error": {"code": "DiscordGetTokenFail", "msg": "Could not authenticate with Discord OAuth2 code."}})

    guilds_r = oauth_discord_client.get("users/@me/guilds").json()
    guild_ids = [guild["id"] for guild in guilds_r if guild["id"] in CONTEXT["secrets"]["guild_accept_list"]]
    if len(guild_ids) == 0:
        return make_response(403, {"error": {"code": "NoGuilds", "msg": "No accepted guilds found for this user."}})
    
    auth_guild_ids = []
    for guild_id in guild_ids:
        guild_roles_r = discordapi.get(f"guilds/{guild_id}/roles").json()
        guild_admin_settings = get_settings(guild_id, "admin_settings")
        approved_roles = []
        approved_roles.extend([role_name.lower() for role_name in guild_admin_settings["admin_roles"]["S"].split(",")])
        approved_roles.extend([role_name.lower() for role_name in guild_admin_settings["quotemod_roles"]["S"].split(",")])
        guild_admin_role_ids = [role["id"] for role in guild_roles_r if role["name"].lower() in approved_roles]

        guild_member_r = oauth_discord_client.get(f"users/@me/guilds/{guild_id}/member").json()
        user_role_ids = guild_member_r["roles"]

        user_admin_role_ids = [role for role in user_role_ids if role in guild_admin_role_ids]
        if len(user_admin_role_ids) > 0:
            auth_guild_ids.append(guild_id)

    if len(auth_guild_ids) == 0:
        return make_response(403, {"error": {"code": "NoRoles", "msg": "No accepted roles found for accepted guilds for this user."}})

    identity_r = oauth_discord_client.get("users/@me").json()
    user_id = identity_r["id"]
    user_display_name = identity_r["username"]+"#"+identity_r["discriminator"]

    token = Token(user_id, user_display_name, auth_guild_ids)
    token.save()

    response_body = {}
    response_body["token"] = str(token)
    response_body["user_display_name"] = user_display_name
    response_body["user_avatar"] = identity_r["avatar"]
    response_body["guilds"] = {guild["id"] : {"name": guild["name"], "id": guild["id"], "icon": guild["icon"]} for guild in guilds_r if guild["id"] in auth_guild_ids}

    return make_response(200, response_body)