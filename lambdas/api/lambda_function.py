from tehbot.settings import get_settings
import re
import os
import json
from tehbot.aws import client as awsclient
from tehbot.util import CONTEXT
import pprint

PATHSPEC_ARG_REGEX = re.compile(r'''\<(.+?)(?::([ifb]))?\>''')
ROUTES = {}

def route(pathspec, method):
    def decorator(func):
        ROUTES[(pathspec, method)] = func
        return func
    return decorator

def does_path_match(path, pathspec):
    print("Checking if path matches pathspec")
    print("Path: ", path)
    print("Pathspec: ", pathspec)
    pathsplit = path.split("/")
    pathspecsplit = pathspec.split("/")

    if len(pathsplit) != len(pathspecsplit):
        return False, []

    urlparams = {}
    for pathcomp, pathspeccomp in zip(pathsplit, pathspecsplit):
        parammatch = re.search(PATHSPEC_ARG_REGEX, pathspeccomp)
        if parammatch:
            paramtype = parammatch.group(2)
            if paramtype is None:
                paramtype = "s"
            try:
                if paramtype == "s":
                    urlparams[parammatch.group(1)] = pathcomp
                elif paramtype == "i":
                    urlparams[parammatch.group(1)] = int(pathcomp)
                elif paramtype == "f":
                    urlparams[parammatch.group(1)] = float(pathcomp)
                elif paramtype == "b":
                    urlparams[parammatch.group(1)] = pathcomp.lower() == "true"
                else:
                    print("No match because invalid param type")
                    return False, {}
            except ValueError:
                print("No match because ValueError on param conversion")
                return False, {}
        else:
            if pathcomp != pathspeccomp:
                print("No match because path not matching")
                return False, {}

def handle_request(event):
    path = event["path"].replace("/tehbot", "")
    for routekey in ROUTES:
        routepathspec = routekey[0]
        routemethod = routekey[1]
        if routemethod.lower() != event["method"].lower():
            continue
        matched, urlparams = does_path_match(path, routepathspec)
        if matched:
            f = ROUTES[routekey]
            return f(urlparams, event)

@route("/auth/token", "POST")
def get_auth_token(urlparams, event):
    discord_auth_code = urlparams["code"]
    

def lambda_handler(event, context):
    print(json.dumps(event))
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = awsclient("secretsmanager")
    secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
    CONTEXT["secrets"] = secret_blob
    CONTEXT["cache"] = {}

    return handle_request(event)