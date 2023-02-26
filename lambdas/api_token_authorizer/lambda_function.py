from tehbot.api.token import Token
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
    try:
        tokenval = event["identitySource"][0]
    except KeyError:
        logger.debug("Payload issue? Key error with getting identity source.")
        return {
            "isAuthorized": False,
            "context": {}
        }
    except IndexError:
        logger.debug("Payload issue? Index error with getting identity source.")
        return {
            "isAuthorized": False,
            "context": {}
        }
    logger.debug("tokenval: %s", tokenval)
    token = Token.from_token_value(tokenval)
    if token is None:
        logger.debug("Token not found.")
        return {
            "isAuthorized": False,
            "context": {}
        }
    if "guild_id" in event["pathParameters"]:
        guild_id = event["pathParameters"]["guild_id"]
        validity = token.get_validity_for_guild_id(guild_id)
        if validity == "expired":
            logger.debug("Token expired.")
            return {
                "isAuthorized": False,
                "context": {
                    "user_id": token.user_id,
                    "user_display_name": token.user_display_name
                }
            }
        elif validity == "unauthorized":
            logger.debug("Token unauthorized.")
            return {
                "isAuthorized": False,
                "context": {
                    "user_id": token.user_id,
                    "user_display_name": token.user_display_name
                }
            }
    logger.debug("Token ok!")
    return {
        "isAuthorized": True,
        "context": {
            "tokenval": tokenval,
            "user_id": token.user_id,
            "user_display_name": token.user_display_name
        }
    }