import os

from tehbot.discord import is_admin_issuer, is_self_issuer, api as discord_api
from tehbot.chart.users import User
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings, upsert_settings

def lobby_admin_enable(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    channelid = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    guildid = body["guild_id"]
    upsert_settings(guildid, "lobby_tracker", status_channel=channelid)

    return True, {"json": {"content": f"Lobby auto-tracker activated for specified channel."}}

def lobby_admin_disable(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guildid = body["guild_id"]
    upsert_settings(guildid, "lobby_tracker", status_channel="")

    return True, {"json": {"content": f"Lobby auto-tracker deactivated."}}

def lobby_admin(body):
    subopt = body["data"]["options"][0]["options"][0]["name"]
    if subopt in ("enable", "disable"):
        fname = f"lobby_admin_{subopt}"
        f = globals()[fname]
        return f(body)
    else:
        return False, {"json": {"content": "???"}}