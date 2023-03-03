import os

from tehbot.discord import is_admin_issuer, is_self_issuer, api as discord_api
from tehbot.chart.users import User
from tehbot.aws import client as awsclient
from tehbot.settings import get_settings

def chart_user_add(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    memberobj = body["data"]["resolved"]["members"][userval]
    avatar = memberobj["avatar"]
    if avatar is None:
        avatar = userobj["avatar"]
    if avatar is None:
        return False, {"json": {"content": "That user has no avatar image! Users must have an avatar set to be added to the alignment chart."}}
    
    user = User.load(userobj["id"], guild_id)
    if user is None:
        user = User(userobj["id"], userobj["username"], userobj["discriminator"], avatar, [1/3, 1/3, 1/3], guild_id)
        user.save()
        return True, {"json": {"content": "User added!"}}
    else:
        return False, {"json": {"content": "That user already exists! Perhaps you meant to add a variant?"}}

def chart_user_list(body):
    guild_id = body["guild_id"]

    dynamo = awsclient("dynamodb")
    filterexpr = "GuildId = :guildid"
    filtervals = {
        ":guildid": {"S": guild_id}
    }
    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_CHART"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )
    if len(response["Items"]) == 0:
        return False, {"json": {"content": "No users found."}}
    msg = "Users:\n"
    names = []
    for item in response["Items"]:
        user = User.from_item(item)
        if user.variantname is None:
            names.append(user.name)
        else:
            names.append(f"{user.name} ({user.variantname})")
    msg = msg + "\n".join(names)
    return True, {"json": {"content": msg}}

def chart_user_place(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    top_amount = float(body["data"]["options"][0]["options"][0]["options"][1]["value"])
    right_amount = float(body["data"]["options"][0]["options"][0]["options"][2]["value"])
    left_amount = float(body["data"]["options"][0]["options"][0]["options"][3]["value"])
    
    user = User.load(userobj["id"], guild_id)
    if user is None:
        return False, {"json": {"content": "User not found."}}
    total = top_amount + right_amount + left_amount
    user.coordinates = [top_amount/total, right_amount/total, left_amount/total]
    user.save()
    return True, {"json": {"content": "User placed!"}}


def chart_user_move(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    direction = body["data"]["options"][0]["options"][0]["options"][1]["value"]
    amount = float(body["data"]["options"][0]["options"][0]["options"][2]["value"])
    user = User.load(userobj["id"], guild_id)
    if user is None:
        return False, {"json": {"content": "User not found."}}
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

def chart_user_reset(body):
    if not is_admin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    user = User.load(userobj["id"], guild_id)
    if user is None:
        return False, {"json": {"content": "User not found."}}
    user.coordinates = [1/3, 1/3, 1/3]
    user.save()
    return True, {"json": {"content": "User reset!"}}

def chart_user_print(body):
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    user = User.load(userobj["id"], guild_id)
    if user is None:
        return False, {"json": {"content": "User not found."}}
    top_settings = get_settings(guild_id, "chart_settings.top")
    right_settings = get_settings(guild_id, "chart_settings.right")
    left_settings = get_settings(guild_id, "chart_settings.left")
    top_rolename = top_settings['role_name']['S']
    if top_rolename.endswith("s"):
        top_rolename = top_rolename[:-1]
    right_rolename = right_settings['role_name']['S']
    if right_rolename.endswith("s"):
        right_rolename = right_rolename[:-1]
    left_rolename = left_settings['role_name']['S']
    if left_rolename.endswith("s"):
        left_rolename = left_rolename[:-1]
    return True, {"json": {"content": f"{user.name} is located at:\n{top_rolename}: {user.coordinates[0]:.4f}\n{right_rolename}: {user.coordinates[1]:.4f}\n{left_rolename}: {user.coordinates[2]:.4f}"}}

def chart_user_remove(body):
    if not is_admin_issuer() and not is_self_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    user = User.load(userobj["id"], guild_id)
    if user is None:
        return False, {"json": {"content": "User not found."}}
    user.drop()
    return True, {"json": {"content": "User removed."}}

def chart_user(body):
    subopt = body["data"]["options"][0]["options"][0]["name"]
    if subopt in ("add", "list", "place", "move", "reset", "print", "remove"):
        fname = f"chart_user_{subopt}"
        f = globals()[fname]
        return f(body)
    else:
        return False, {"json": {"content": "???"}}