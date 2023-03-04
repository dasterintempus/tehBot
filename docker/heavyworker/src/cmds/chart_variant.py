import os
import io
import requests

from tehbot.aws import client as awsclient
from tehbot.discord import is_admin_issuer, is_self_issuer
from tehbot.chart.users import User
from tehbot.chart.render import AVATAR_INNER_SIZE
from tehbot.util import BUCKET_NAME

from PIL import Image, ImageColor, ImageOps, ImageDraw, ImageFont

def save_variant_avatar(user_id, guild_id, variantname, url):
    s3 = awsclient("s3")
    key = f"variantavatars/{guild_id}/{user_id}_{variantname}.png"
    avatarbytes = io.BytesIO(requests.get(url).content)
    img = Image.open(avatarbytes)
    img = img.resize(AVATAR_INNER_SIZE)
    image_bytes = io.BytesIO()
    img.save(image_bytes, "PNG")
    image_bytes.seek(0)
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=image_bytes)
    return key

def chart_variant_add(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    variantname = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    avatarurl = body["data"]["options"][0]["options"][0]["options"][2]["value"]
    avatarkey = save_variant_avatar(userobj["id"], guild_id, variantname, avatarurl)
    
    user = User.load(userobj["id"], guild_id, variantname)
    if user is None:
        user = User(userobj["id"], userobj["username"], userobj["discriminator"], avatarkey, [1/3, 1/3, 1/3], guild_id, False, variantname)
        user.save()
        return True, {"json": {"content": "Variant added!"}}
    else:
        return False, {"json": {"content": "That user variant already exists!"}}

def chart_variant_place(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    variantname = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    top_amount = float(body["data"]["options"][0]["options"][0]["options"][2]["value"])
    right_amount = float(body["data"]["options"][0]["options"][0]["options"][3]["value"])
    left_amount = float(body["data"]["options"][0]["options"][0]["options"][4]["value"])
    user = User.load(userobj["id"], guild_id, variantname)
    if user is None:
        return False, {"json": {"content": "User variant not found."}}
    total = top_amount + right_amount + left_amount
    user.coordinates = [top_amount/total, right_amount/total, left_amount/total]
    user.save()
    return True, {"json": {"content": "User placed!"}}

def chart_variant_move(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    variantname = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    direction = body["data"]["options"][0]["options"][0]["options"][2]["value"]
    amount = float(body["data"]["options"][0]["options"][0]["options"][3]["value"])
    user = User.load(userobj["id"], guild_id, variantname)
    if user is None:
        return False, {"json": {"content": "User variant not found."}}
    coords = user.coordinates
    if direction == "top":
        coords[0] += amount
        coords[1] -= amount/2
        coords[2] -= amount/2
    elif direction == "right":
        coords[0] -= amount/2
        coords[1] += amount
        coords[2] -= amount/2
    elif direction == "left":
        coords[0] -= amount/2
        coords[1] -= amount/2
        coords[2] += amount
    user.coordinates = coords
    user.save()
    return True, {"json": {"content": "User moved!"}}

def chart_variant_reset(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    variantname = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    user = User.load(userobj["id"], guild_id, variantname)
    if user is None:
        return False, {"json": {"content": "User variant not found."}}
    user.coordinates = [1/3, 1/3, 1/3]
    user.save()
    return True, {"json": {"content": "User reset!"}}

def chart_variant_print(body):
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    variantname = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    user = User.load(userobj["id"], guild_id, variantname)
    if user is None:
        return False, {"json": {"content": "User variant not found."}}
    return True, {"json": {"content": f"{user.name} ({user.variantname}) is located at:\nTop: {user.coordinates[0]:.4f}\nRight: {user.coordinates[1]:.4f}\nLeft: {user.coordinates[2]:.4f}"}}

def chart_variant_list(body):
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    dynamo = awsclient("dynamodb")
    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_CHART"),
        FilterExpression="UserId = :userid AND GuildId = :guildid AND IsVariant = :isvariant",
        ExpressionAttributeValues={
            ":userid": {"S": userobj["id"]},
            ":guildid": {"S": guild_id},
            ":isvariant": {"BOOL": True}
        }
    )
    if len(response["Items"]) == 0:
        return False, {"json": {"content": "User has no variants."}}
    variantnames = ["`" + item["VariantName"]["S"] + "`" for item in response["Items"]]
    variantnamestr = ", ".join(variantnames)
    return True, {"json": {"content": f"{userobj['username']} has variants: {variantnamestr}"}}

def chart_variant_remove(body):
    if not is_admin_issuer() and not is_self_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    variantname = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    user = User.load(userobj["id"], guild_id, variantname)
    if user is None:
        return False, {"json": {"content": "Variant not found."}}
    user.drop()
    s3 = awsclient("s3")
    s3.delete_object(Bucket=BUCKET_NAME, Key=f"variantavatars/{userval}_{variantname}.png")
    return True, {"json": {"content": f"Variant removed."}}

def chart_variant(body):
    subopt = body["data"]["options"][0]["options"][0]["name"]
    if subopt in ("add", "place", "move", "reset", "print", "list", "remove"):
        fname = f"chart_variant_{subopt}"
        f = globals()[fname]
        return f(body)
    else:
        return False, {"json": {"content": "???"}}