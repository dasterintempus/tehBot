import requests
import time
import os
import boto3
import json

from ..util import CONTEXT
from ..settings import get_settings

from typing import Optional

secrets_arn = os.environ.get("SECRETS_ARN")
secrets = boto3.client("secretsmanager")
secret_blob = json.loads(secrets.get_secret_value(SecretId=secrets_arn)["SecretString"])
BOT_TOKEN = secret_blob["discord_bot_token"]

API_BASE_URL = "https://discord.com/api/v8"
CDN_BASE_URL = "https://cdn.discordapp.com"

def build_bot_session():
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bot {BOT_TOKEN}",
        "User-Agent": "tehBot (0.1.0)"
    })
    return session

def build_oauth_session(code):
    token_r = get_oauth_token(code)
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token_r['access_token']}",
        "User-Agent": "tehBot (0.1.0)"
    })
    return session

def build_oauth_client(code):
    return Wrapper(API_BASE_URL, build_oauth_session(code))

class RateLimitException(Exception):
    pass

class Wrapper():
    def __init__(self, baseurl: str, session: Optional[requests.Session] = None):
        self.baseurl = baseurl
        self.session = session or build_bot_session()
        self.ratelimit_remaining = None
        self.ratelimit_reset_at = None
    
    def request(self, method, url, **kwargs) -> requests.Response:
        if self.ratelimit_remaining is not None and self.ratelimit_reset_at is not None:
            if self.ratelimit_remaining <= 1:
                sleeptime = 0.1 + (self.ratelimit_reset_at - time.time())
                if sleeptime > 0:
                    print(f"SLEEPING FOR {sleeptime} TO AVOID RATE LIMIT")
                    time.sleep(sleeptime)
        r = getattr(self.session, method)(f"{self.baseurl}/{url}", **kwargs)
        if r.status_code == 429:
            raise RateLimitException("Discord rate-limiting, immediately halting.")
        try:
            self.ratelimit_remaining = int(r.headers["X-RateLimit-Remaining"])
            self.ratelimit_reset_at = time.time() + float(r.headers["X-RateLimit-Reset-After"])
            # if int(r.headers["X-RateLimit-Remaining"]) <= 2:
            #     sleeptime = float(r.headers["X-RateLimit-Reset-After"])
            #     print(f"SLEEPING FOR {sleeptime} TO AVOID RATE LIMIT")
            #     time.sleep(sleeptime)
        except:
            self.ratelimit_remaining = None
            self.ratelimit_reset_at = None
        return r

    def get(self, url, **kwargs) -> requests.Response:
        return self.request("get", url, **kwargs)

    def post(self, url, **kwargs) -> requests.Response:
        return self.request("post", url, **kwargs)

    def delete(self, url, **kwargs) -> requests.Response:
        return self.request("delete", url, **kwargs)

    def patch(self, url, **kwargs) -> requests.Response:
        return self.request("patch", url, **kwargs)

api = Wrapper(API_BASE_URL)
cdn = Wrapper(CDN_BASE_URL)

def get_oauth_token(code):
    data = {}
    data["client_id"] = secret_blob["client_id"]
    data["client_secret"] = secret_blob["client_secret"]
    data["redirect_uri"] = secret_blob["redirect_uri"]
    data["grant_type"] = "authorization_code"
    data["code"] = code

    headers = {}
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "tehBot (https://[dev-]api.dasterin.net/discord-interactions, 0.1.0)"
    })
    r = session.post(f"{API_BASE_URL}/oauth2/token", data=data, headers=headers)
    try:
        r.raise_for_status()
    except Exception as e:
        print("DISCORD OAUTH EXCEPTION")
        print("Request:")
        print(json.dumps(data))
        print(json.dumps(headers))
        print("Response:")
        print(e)
        print(r.text)
        raise
    return r.json()

def is_root_issuer():
    if CONTEXT["request"]["member"]["user"]["id"] == os.environ.get("ROOT_DISCORD_USER_ID"):
        return True
    else:
        return False

def is_admin_issuer():
    if is_root_issuer():
        return True
    guild_id = CONTEXT["request"]["guild_id"]
    guild_admin_settings = get_settings(guild_id, "admin_settings")
    admin_role_names = [role.lower().strip() for role in guild_admin_settings["admin_roles"]["S"].split(",")]
    issuer_roles = CONTEXT["request"]["member"]["roles"]
    admin_role_ids = []
    url = f"guilds/{guild_id}/roles"
    r = api.get(url)
    for role in r.json():
        if role["name"].lower() in admin_role_names:
            admin_role_ids.append(role["id"])
    for issuer_role in issuer_roles:
        if issuer_role in admin_role_ids:
            return True
    return False

def is_quoteadmin_issuer():
    if is_root_issuer():
        return True
    if is_admin_issuer():
        return True
    guild_id = CONTEXT["request"]["guild_id"]
    guild_quote_settings = get_settings(guild_id, "admin_settings")
    quotemod_role_names = [role.lower().strip() for role in guild_quote_settings["quotemod_roles"]["S"].split(",")]
    issuer_roles = CONTEXT["request"]["member"]["roles"]
    admin_role_ids = []
    url = f"guilds/{guild_id}/roles"
    r = api.get(url)
    for role in r.json():
        if role["name"].lower() in quotemod_role_names:
            admin_role_ids.append(role["id"])
    for issuer_role in issuer_roles:
        if issuer_role in admin_role_ids:
            return True
    return False

def is_self_issuer(body):
    return body["user"]["id"] == body["data"]["options"][0]["options"][0]["options"][0]["value"]