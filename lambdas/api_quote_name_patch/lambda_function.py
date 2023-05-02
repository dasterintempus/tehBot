from tehbot.settings import get_settings
import re
import os
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings
from tehbot.discord import build_oauth_client, api as discordapi
from tehbot.util import CONTEXT
from tehbot.api import make_response, has_permission, make_forbidden_response
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
    quote_name = event["pathParameters"]["quote_name"]
    
    if not has_permission(event, guild_id, "quotemod"):
        return make_forbidden_response()
    # ok, response_body = check_token_validity(event, guild_id)
    # if not ok:
    #     return response_body

    quote = Quote.find_by_name(quote_name, guild_id)
    if quote is None:
        return make_response(404, {"error": {"code": "NotFound", "msg": "No known quote with that name."}})

    body_str = event.get("body")
    if body_str is None:
        body_str = "{}"
    try:
        request_body = json.loads(body_str)
    except:
        return make_response(400, {"error": {"code": "InvalidJson", "msg": "Request body was not valid JSON."}})
    tags = request_body.get("tags", list(quote.tags))
    new_name = request_body.get("name", quote.name)
    
    other = Quote.find_by_name(new_name, guild_id)
    if other is not None and other.entryid != quote.entryid:
        return make_response(400, {"error": {"code": "QuoteAlreadyExists", "msg": "Cannot rename quote to a name that already exists."}})

    if len(tags) == 0:
        return make_response(400, {"error": {"code": "NoTags", "msg": "Must have at least one tag for searchability."}})


    quote.tags = set(tags)
    quote.name = new_name
    quote.save()

    response_body = {"success": True, "quote": quote.to_dict()}

    return make_response(200, response_body)