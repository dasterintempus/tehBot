import json
import os
from re import L
from symbol import varargslist
from .token import Token
def make_response(code, body=None, headers=None):
    if body is None:
        body = {}
    if headers is None:
        headers = {}
    response = {}
    headers["Content-Type"] = headers.get("Content-Type", "application/json")
    headers["Access-Control-Allow-Headers"] = "Content-Type,X-teh-Auth"
    headers["Access-Control-Allow-Origin"] = os.environ.get("WEB_URL")
    headers["Access-Control-Allow-Methods"] = "OPTIONS,POST,GET,PUT,PATCH,DELETE"

    response["statusCode"] = code
    response["headers"] = headers
    response["isBase64Encoded"] = False
    # response["multiValueHeaders"] = {}
    response["body"] = json.dumps(body)
    return response


def check_token_validity(event, guild_id):
    tokenval = event["headers"].get("x-teh-auth", None)
    if tokenval is None:
        return False, make_response(401, {"error": {"code": "NoToken", "msg": "Missing authentication token."}})
    token = Token.from_token_value(tokenval)
    if token is None:
        return False, make_response(401, {"error": {"code": "InvalidToken", "msg": "Invalid authentication token."}})
    validity = token.get_validity_for_guild_id(guild_id)
    if validity == "expired":
        return False, make_response(403, {"error": {"code": "ExpiredToken", "msg": "Authentication token is expired."}})
    elif validity == "unauthorized":
        return False, make_response(403, {"error": {"code": "UnauthorizedToken", "msg": "Authentication token does not include authorization for the requested guild id."}})
    return True, None