from tehbot.settings import get_settings
import re
import os
import json
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings
from tehbot.discord import build_oauth_client, api as discordapi
from tehbot.util import CONTEXT
from tehbot.api import make_response, get_json_body
from tehbot.api.shorturl import ShortUrl
import base64
import traceback

import logging
from http.client import HTTPConnection # py3

import json
import logging

logging.basicConfig(force=True, format="%(asctime)s %(levelname)s - %(name)s %(pathname)s.%(funcName)s:%(lineno)s %(message)s")
logger = logging.getLogger(__name__)

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
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}

    shortstr = event["pathParameters"]["shortstr"]
    
    url = ShortUrl.from_shortstr(shortstr)
    if url is None:
        return make_response(404, body="Not Found")

    target_url = url.target_url
    response_body = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Refresh" content="0; URL={target_url}" />
    <title>tehBot Link Shortener Redirect</title>
  </head>
  <body>
    <div class="container-fluid" id="content"><a href="{target_url}">{target_url}</a></div>
  </body>
</html>
'''
    return make_response(308, body=response_body, headers={"Location": target_url})