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
HEAVY_QUEUE_URL = os.environ.get("SQSQUEUE_INTERACTIONS_HEAVY")
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

def forward_response(body:dict):
    sqs = boto3.client("sqs")
    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(body))
    if body["data"]["name"] == "SuggestQuote":
        return json_response({"type": 4, "data": {"content": ":eyes:"}})
    else:
        return json_response({"type": 5})
    
def forward_response_heavy(body:dict):
    sqs = boto3.client("sqs")
    # print(DAEMON_QUEUE_URL)
    sqs.send_message(QueueUrl=HEAVY_QUEUE_URL, MessageBody=json.dumps(body))
    if body["data"]["type"] == 3:
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
        print(json.dumps(event))
        return {
            "statusCode": 400,
            "body": ""
        }
    if body["type"] == 1:
        print("PING")
        return json_response({"type": 1})
    elif body["data"]["name"] in ("lobby", "quote", "quotemod", "SuggestQuote", "combo", "ScoreKeySmash"):
        return forward_response(body)
    elif body["data"]["name"] in ("chart", "tierlist", "controller"):
        return forward_response_heavy(body)
    elif body["data"]["name"] in ("say",):
        return json_response({"type": 4, "data": {
            "content": "This command has been removed :( Please use '!botsing' instead."
        }})
    else:
        print(json.dumps(event))
        return json_response({"type": 4, "data": {
            "content": "Unrecognized webhook!"
        }})

def lambda_handler(event, context):
    try:
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
        elif event["requestContext"]["http"]["path"] in ("/", "/discord-interactions") and event["requestContext"]["http"]["method"] == "POST":
            return interact(event, context)
        else:
            print(json.dumps(event))
            return {
                "statusCode": 400,
                "body": ""
            }
    except:
        print(json.dumps(event))
        raise