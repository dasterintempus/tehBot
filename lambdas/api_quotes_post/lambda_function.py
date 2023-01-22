from urllib import request
from tehbot.settings import get_settings
import re
import os
import json
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings
from tehbot.discord import build_oauth_client, api as discordapi
from tehbot.util import CONTEXT
from tehbot.api import make_response, check_token_validity
from tehbot.api.token import Token
from tehbot.quotes import Quote
import requests
import pprint

def lambda_handler(event, context):
    print(json.dumps(event))
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}

    guild_id = event["pathParameters"]["guild_id"]
    
    ok, response_body = check_token_validity(event, guild_id)
    if not ok:
        return response_body

    body_str = event.get("body")
    if body_str is None:
        body_str = "{}"
    try:
        request_body = json.loads(body_str)
    except:
        return make_response(400, {"error": {"code": "InvalidJson", "msg": "Request body was not valid JSON."}})
    
    try:
        name = request_body["name"]
    except:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "'name' is a required parameter."}})
    other = Quote.find_by_name(name, guild_id)
    if other is not None:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "Name already exists."}})

    try:
        url = request_body["url"]
    except:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "'url' is a required parameter."}})    
    try:
        requests.head(url).raise_for_status()
    except:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "URL is invalid or not reachable."}})
    
    try:
        tags = request_body["tags"]
    except:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "'tags' is a required parameter."}})
    if len(tags) == 0:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "Tags must not be empty."}})

    quote = Quote(url, name, set(tags), guild_id)
    quote.save()

    response_body = {"success": True, "quote": quote.to_dict()}

    return make_response(200, response_body)