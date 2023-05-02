from tehbot.settings import get_settings
import re
import os
import json
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings
from tehbot.discord import build_oauth_client, api as discordapi
from tehbot.util import CONTEXT
from tehbot.api import make_response, get_json_body, has_permission, make_forbidden_response
from tehbot.quotes import Quote
import pprint

import json
import logging

logging.basicConfig(force=True, format="%(asctime)s %(levelname)s - %(name)s %(pathname)s.%(funcName)s:%(lineno)s %(message)s")
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    if "dev" in context.function_name.lower():
        logger.setLevel(logging.DEBUG)
        print(json.dumps(event))
    else:
        logger.setLevel(logging.INFO)
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}

    guild_id = event["pathParameters"]["guild_id"]
    
    if not has_permission(event, guild_id, "quotemod"):
        return make_forbidden_response()
    # ok, response_body = check_token_validity(event, guild_id)
    # if not ok:
    #     return response_body

    
    try:
        request_body = get_json_body(event)
    except:
        return make_response(400, {"error": {"code": "InvalidJson", "msg": "Request body was not valid JSON."}})
    terms = request_body.get("terms", [])
    offset = request_body.get("offset", 0)
    count = request_body.get("count", 100)
    if count > 100:
        return make_response(400, {"error": {"code": "InvalidRequestParameter", "msg": "'count' has a maximum value of 100"}})
    
    if len(terms) > 0:
        quote_list = Quote.search(terms, guild_id)
    else:
        quote_list = Quote.find_all(guild_id)
    quote_list.sort(key=lambda q: q.name)
    response_body = {"total_hits": len(quote_list), "quotes": [quote.to_dict() for quote in quote_list[offset:offset+count]]}

    return make_response(200, response_body)