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
import pprint

def lambda_handler(event, context):
    print(json.dumps(event))
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}

    guild_id = event["pathParameters"]["guild_id"]
    quote_name = event["pathParameters"]["quote_name"]
    
    ok, response_body = check_token_validity(event, guild_id)
    if not ok:
        return response_body

    quote = Quote.find_by_name(quote_name, guild_id)
    if quote is None:
        return make_response(404, {"error": {"code": "NotFound", "msg": "No known quote with that name."}})

    quote.drop()

    response_body = {"success": True}

    return make_response(200, response_body)