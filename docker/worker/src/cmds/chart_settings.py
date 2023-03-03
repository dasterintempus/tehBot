import os
import io
import requests

from tehbot.aws import client as awsclient
from tehbot.discord import is_admin_issuer, is_self_issuer
from tehbot.chart.users import User
from tehbot.chart.render import FACTION_SIZE
from tehbot.util import BUCKET_NAME
from tehbot.settings import upsert_settings

from PIL import Image, ImageColor, ImageOps, ImageDraw, ImageFont

def save_faction_image(url, guild_id, faction_pos):
    s3 = awsclient("s3")
    key = f"factionimages/{guild_id}/{faction_pos}.png"
    avatarbytes = io.BytesIO(requests.get(url).content)
    img = Image.open(avatarbytes)
    img = img.resize(FACTION_SIZE)
    image_bytes = io.BytesIO()
    img.save(image_bytes, "PNG")
    image_bytes.seek(0)
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=image_bytes)
    return f"factionimages/{guild_id}/{faction_pos}.png"

def chart_settings_faction(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    faction_pos = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    faction_roleval = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    faction_roleobj = body["data"]["resolved"]["roles"][faction_roleval]
    faction_imageurl = body["data"]["options"][0]["options"][0]["options"][2]["value"]
    
    factionbg_image_key = save_faction_image(faction_imageurl, guild_id, faction_pos)
    upsert_settings(guild_id, f"chart_settings.{faction_pos}", role_name=faction_roleobj["name"], bg_image_key=factionbg_image_key)

    return True, {"json": {"content": f"Faction configured."}}

def chart_settings(body):
    subopt = body["data"]["options"][0]["options"][0]["name"]
    if subopt in ("faction",):
        fname = f"chart_settings_{subopt}"
        f = globals()[fname]
        return f(body)
    else:
        return False, {"json": {"content": "???"}}