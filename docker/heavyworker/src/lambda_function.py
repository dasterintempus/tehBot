import json
import io
import os
import boto3
import hashlib

from tehbot.discord import api as discord_api
from tehbot.util import CONTEXT
from cmds import chart_show, chart_user, chart_variant, chart_settings
from cmds import generate_tierlist

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

def chart_cmd(body):
    if body["data"]["options"][0]["name"] == "show":
        return chart_show()
    elif body["data"]["options"][0]["name"] == "user":
        return chart_user(body)
    elif body["data"]["options"][0]["name"] == "variant":
        return chart_variant(body)
    elif body["data"]["options"][0]["name"] == "settings":
        return chart_settings(body)

def tierlist_cmd(body):
    if "options" in body["data"] and len(body["data"]["options"]) > 0:
        url = body["data"]["options"][0]["value"].lower()
    else:
        url = None
    out_im = generate_tierlist(url)
    if out_im is None:
        return True, {"json": {"content": "An Error Occured. :("}}
    out_body = io.BytesIO()
    out_im.save(out_body, "png")
    out_body.seek(0)
    files = {}
    files["file[0]"] = ("tierlist.png", out_body)
    outbody = {
        "embeds": [{
            "image": {
                "url": "attachment://tierlist.png"
            }
        }]
    }
    files["payload_json"] = ("", json.dumps(outbody), "application/json")
    return True, {"files": files}

def handle_record(body):
    print(json.dumps(body))
    print("Starting")
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = boto3.client("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["request"] = body
    CONTEXT["cache"] = {}
    if body["data"]["name"] == "chart":
        response = chart_cmd(body)
    elif body["data"]["name"] == "tierlist":
        response = tierlist_cmd(body)
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
    failures = []
    for record in event["Records"]:
        body = json.loads(record["body"])
        response = handle_record(body)
        if response is not True:
            failures.append(record["messageId"])
    print(f"Items failed: {len(failures)}")
    return {"batchItemFailures": [{"itemIdentifier": failure} for failure in failures]}

if __name__ == "__main__":
    out_im = generate_tierlist(None)
    out_im.save("out.png")