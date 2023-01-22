from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
BotocoreInstrumentor().instrument()
import json
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import boto3
import os
import pprint
import requests

# from tehbot.settings import get_settings

secrets_arn = os.environ.get("SECRETS_ARN")
secrets = boto3.client("secretsmanager")
secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
PUBLIC_KEY = secret_blob["discord_public_key"]
QUEUE_URL = os.environ.get("SQSQUEUE_INTERACTIONS")
# DEVQUEUE_URL = os.environ.get("SQSQUEUE_DEVINTERACTIONS")

verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

def verify(event):
    try:
        signature = event["headers"]["x-signature-ed25519"]
        timestamp = event["headers"]["x-signature-timestamp"]
    except:
        print("VERIFY FAILED, NO HEADERS")
        return False
    body = event["body"]

    try:
        verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
    except BadSignatureError:
        print("VERIFY FAILED")
        return False
    else:
        return True

# def is_stable_guild(body):
#     guildid = body["guild_id"]
#     try:
#         settings = get_settings(guildid, "meta")
#         return settings["stable"]["BOOL"]
#     except:
#         return False

def json_response(r, code=200):
    return {
            "statusCode": code,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(r)
        }

def forward_response(bodystr, interaction_type):
    sqs = boto3.client("sqs")
    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=bodystr)
    if interaction_type == 3:
        return json_response({"type": 4, "data": {"content": ":eyes:"}})
    else:
        return json_response({"type": 5})

def interact(event, context):
    if not verify(event):
        return {
            "statusCode": 401,
            "body": ""
        }
    if not event["headers"]["content-type"].startswith("application/json"):
        return {
            "statusCode": 400,
            "body": ""
        }
    try:
        body = json.loads(event["body"])
        print(event["body"])
    except:
        pprint.pprint(event)
        return {
            "statusCode": 400,
            "body": ""
        }
    if body["type"] == 1:
        print("PING")
        return json_response({"type": 1})
    elif body["data"]["name"] in ("chart", "lobby", "quote", "quotemod", "SuggestQuote"):
        return forward_response(event["body"], body["data"]["type"])
    elif body["data"]["name"] in ("say",):
        return json_response({"type": 4, "data": {
            "content": "This command has been removed :( Please use '!botsing' instead."
        }})
    else:
        pprint.pprint(event)
        return json_response({"type": 4, "data": {
            "content": "Unrecognized webhook!"
        }})

def lambda_handler(event, context):
    headers = event.get("headers")
    if headers is None:
        headers = {}
    if "x-forwarded-proto" in headers and headers["x-forwarded-proto"] == "http":
        return {
            "statusCode": 301,
            "headers": {
                "Location": f"https://{headers['host']}"
            }
        }
    elif event["path"] in ("/", "/discord-interactions") and event["httpMethod"] == "POST":
        return interact(event, context)
    else:
        pprint.pprint(event)
        return {
            "statusCode": 400,
            "body": ""
        }