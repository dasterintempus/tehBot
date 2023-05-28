import json
import io
import os
import boto3
import hashlib

import logging
from http.client import HTTPConnection # py3

logging.basicConfig(force=True, format="%(asctime)s %(levelname)s - %(name)s %(pathname)s.%(funcName)s:%(lineno)s %(message)s")
logger = logging.getLogger(__name__)

from tehbot.discord import api as discord_api
from tehbot.util import CONTEXT
# from cmds import chart_show, chart_user, chart_variant, chart_settings
from cmds import lobby_admin, lobby_optin, lobby_optout, lobby_link, lobby_friend, lobby_url, lobby_private_url
from cmds import quote_search, quote_suggest
from cmds import quotemod_add, quotemod_delete, quotemod_print, quotemod_list, quotemod_modify_tags
from cmds import quotemod_alias_add, quotemod_alias_delete, quotemod_alias_print, quotemod_alias_list, quotemod_alias_modify_values
# from cmds import generate_tierlist
from cmds import meta_maintenance_start, meta_maintenance_end

# def say_cmd(body):
#     line = body["data"]["options"][0]["value"]
#     if "member" in body:
#         user_id = body["member"]["user"]["id"]
#     elif "user" in body:
#         user_id = body["user"]["id"]
#     v = Voice.generate_from_hash(hashlib.sha256(user_id.encode("utf-8")).digest())
#     audio = v.say(line)
#     files = {}
#     files["file[0]"] = ("botsay.wav", audio, "audio/wav")
#     outbody = {
#         "content": line#,
#         #"embeds": [{
#         #    "rich": {
#         #        "url": "attachment://botsay.wav"
#         #    }
#         #}]
#     }
#     files["payload_json"] = ("", json.dumps(outbody), "application/json")
#     return True, {"files": files}

# def chart_cmd(body):
#     if body["data"]["options"][0]["name"] == "show":
#         return chart_show()
#     elif body["data"]["options"][0]["name"] == "user":
#         return chart_user(body)
#     elif body["data"]["options"][0]["name"] == "variant":
#         return chart_variant(body)
#     elif body["data"]["options"][0]["name"] == "settings":
#         return chart_settings(body)

def lobby_cmd(body):
    subcmd = body["data"]["options"][0]["name"]
    if subcmd == "admin":
        return lobby_admin(body)
    elif subcmd == "opt-in":
        return lobby_optin(body)
    elif subcmd == "opt-out":
        return lobby_optout(body)
    elif subcmd == "link":
        return lobby_link(body)
    elif subcmd == "friend":
        return lobby_friend(body)
    elif subcmd == "url":
        return lobby_url(body)
    elif subcmd == "private-url":
        return lobby_private_url(body)

def quote_cmd(body):
    return quote_search(body)

def quotemod_cmd(body):
    subcmd = body["data"]["options"][0]["name"]
    if subcmd == "add":
        return quotemod_add(body)
    elif subcmd == "delete":
        return quotemod_delete(body)
    elif subcmd == "print":
        return quotemod_print(body)
    elif subcmd == "list":
        return quotemod_list(body)
    elif subcmd == "modify_tags":
        return quotemod_modify_tags(body)
    elif subcmd == "alias":
        return quotemod_alias_cmd(body)

def quotemod_alias_cmd(body):
    subcmd = body["data"]["options"][0]["options"][0]["name"]
    if subcmd == "add":
        return quotemod_alias_add(body)
    elif subcmd == "delete":
        return quotemod_alias_delete(body)
    elif subcmd == "print":
        return quotemod_alias_print(body)
    elif subcmd == "list":
        return quotemod_alias_list(body)
    elif subcmd == "modify_values":
        return quotemod_alias_modify_values(body)

def meta_record(body):
    subcmd = body["_meta"]
    if subcmd == "maintenance-start":
        return meta_maintenance_start(body)
    elif subcmd == "maintenance-end":
        return meta_maintenance_end(body)
    elif subcmd == "fail-test":
        return False

def handle_record(body):
    print(json.dumps(body))
    print("Starting")
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = boto3.client("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["request"] = body
    CONTEXT["cache"] = {}
    if "_meta" in body:
        response = meta_record(body)
        return response
    # elif body["data"]["name"] == "chart":
    #     response = chart_cmd(body)
    elif body["data"]["name"] == "lobby":
        response = lobby_cmd(body)
    elif body["data"]["name"] == "quote":
        response = quote_cmd(body)
    elif body["data"]["name"] == "SuggestQuote":
        response = quote_suggest(body)
    elif body["data"]["name"] == "quotemod":
        response = quotemod_cmd(body)
    # elif body["data"]["name"] == "tierlist":
    #     response = tierlist_cmd(body)
    else:
        response = (False, {})
    print("Got Response")
    if response is not None:
        interaction_token = body["token"]
        url = f"webhooks/{CONTEXT['secrets']['application_id']}/{interaction_token}/messages/@original"
        
        if response[1] == "__DELETE":
            print("Deleting Interaction message")
            r = discord_api.delete(url)
        else:
            print("Updating Interaction message")
            r = discord_api.patch(url, **response[1])
        print(r.status_code)
        print(r.text)
        if r.status_code == 400:
            print("Discord API error on updating interaction.")
            r = discord_api.patch(url, json={"content": "???"})
            return True
        return response[0]
    else:
        interaction_token = body["token"]
        url = f"webhooks/{CONTEXT['secrets']['application_id']}/{interaction_token}/messages/@original"
        
        r = discord_api.patch(url, json={"content": "???"})
        print(r.status_code)
        print(r.text)
        return True

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
    failures = []
    for record in event["Records"]:
        body = json.loads(record["body"])
        response = handle_record(body)
        if response is not True:
            failures.append(record["messageId"])
    print(f"Items failed: {len(failures)}")
    return {"batchItemFailures": [{"itemIdentifier": failure} for failure in failures]}