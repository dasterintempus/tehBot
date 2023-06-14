from ..discord import api as discord_api, cdn as discord_cdn, RateLimitException
from ..aws import client as awsclient
import os
import uuid
import io

from ..util import CONTEXT, BUCKET_NAME
from ..settings import get_settings

class UserException(Exception):
    def __init__(self, user, msg):
        self.user = user
        self.msg = msg

class User:
    @staticmethod
    def load(userid, guildid, variantname = None):
        dynamo = awsclient("dynamodb")
        filterexpr = "UserId = :userid AND GuildId = :guildid"
        filtervals = {
            ":userid": {"S": userid},
            ":guildid": {"S": guildid}
        }
        if variantname:
            filterexpr = filterexpr + " AND VariantName = :variantname"
            filtervals[":variantname"] = {"S": variantname}
        else:
            filterexpr = filterexpr + " AND attribute_not_exists(VariantName)"
        response = dynamo.scan(
            TableName=os.environ.get("DYNAMOTABLE_CHART"),
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        if len(response["Items"]) == 0:
            return None
        else:
            item = response["Items"][0]
            return User.from_item(item)

    @staticmethod
    def get_all_users(guildid):
        dynamo = awsclient("dynamodb")
        filterexpr = "GuildId = :guildid AND attribute_not_exists(VariantName)"
        filtervals = {
            ":guildid": {"S": guildid}
        }
        response = dynamo.scan(
            TableName=os.environ.get("DYNAMOTABLE_CHART"),
            FilterExpression=filterexpr,
            ExpressionAttributeValues=filtervals
        )
        return [User.from_item(item) for item in response["Items"]]

    @staticmethod
    def from_item(item):
        user = User(
            item["UserId"]["S"],
            item["Username"]["S"],
            item["Discriminator"]["S"],
            item["Avatar"]["S"],
            [float(i["N"]) for i in item["Coordinates"]["L"]],
            item["GuildId"]["S"],
            item.get("HasGuildAvatar", {}).get("BOOL", False),
            item.get("VariantName", {}).get("S", None))
        user.entryid = item["EntryId"]["S"]
        return user

    def __init__(self, user_id, name, discrim, avatar, coordinates, guild_id, has_guild_avatar=False, variantname=None):
        self.entryid = str(uuid.uuid4())
        self.id = user_id
        self.name = name
        self.discrim = discrim
        self.avatar = avatar
        self.coordinates = coordinates
        self.guild_id = guild_id
        self.has_guild_avatar = has_guild_avatar
        self.variantname = variantname
    
    def save(self):
        item = {
            "EntryId": {"S": self.entryid},
            "UserId": {"S": self.id},
            "Username": {"S": self.name},
            "Discriminator": {"S": self.discrim},
            "IsVariant": {"BOOL": False},
            "Avatar": {"S": self.avatar},
            "GuildId": {"S": self.guild_id},
            "HasGuildAvatar": {"BOOL": self.has_guild_avatar},
            "Coordinates": {"L": [{"N": str(i)} for i in self.coordinates]},
        }
        if self.variantname is not None:
            item["VariantName"] = {"S": self.variantname}
            item["IsVariant"] = {"BOOL": True}
        
        dynamo = awsclient("dynamodb")
        dynamo.put_item(
            TableName=os.environ.get("DYNAMOTABLE_CHART"),
            Item=item
        )
    
    def drop(self):
        dynamo = awsclient("dynamodb")
        dynamo.delete_item(
            TableName=os.environ.get("DYNAMOTABLE_CHART"),
            Key={"EntryId": self.entryid}
        )

def populate_role_cache():
    guild_id = CONTEXT["request"]["guild_id"]
    top_settings = get_settings(CONTEXT["request"]["guild_id"], "chart_settings.top")
    right_settings = get_settings(CONTEXT["request"]["guild_id"], "chart_settings.right")
    left_settings = get_settings(CONTEXT["request"]["guild_id"], "chart_settings.left")
    roles_filter = [item["role_name"]["S"].lower() for item in (top_settings, right_settings, left_settings)]
    url = f"guilds/{guild_id}/roles"
    r = discord_api.get(url)
    if r.status_code != 200:
        raise Exception(f"Discord API returned: {r.status_code}" + r.text)
    CONTEXT["cache"]["roles"] = [role for role in r.json() if role["name"].lower() in roles_filter]
    for role in CONTEXT["cache"]["roles"]:
        colorint = role["color"]
        if colorint == 0:
            continue
        r = int((colorint & 0xFF0000) >> 16)
        g = int((colorint & 0x00FF00) >> 8)
        b = int((colorint & 0x0000FF) >> 0)
        role["colortuple"] = (r,g,b,255)

def populate_member_cache(guild_id):
    CONTEXT["cache"]["members"] = {}
    url = f"guilds/{guild_id}/members?limit=250"
    r = discord_api.get(url)
    if r.status_code != 200:
        print(f"Discord API returned: {r.status_code}" + r.text)
        r.raise_for_status()
    else:
        for member in r.json():
            user_id = member["user"]["id"]
            CONTEXT["cache"]["members"][user_id] = member

def find_user_color(user):
    #guild_id = CONTEXT["request"]["guild_id"]
    guild_id = user.guild_id
    if "roles" not in CONTEXT["cache"]:
        populate_role_cache()
    if "members" not in CONTEXT["cache"]:
        populate_member_cache(guild_id)
    if user.id not in CONTEXT["cache"]["members"]:
        url = f"guilds/{guild_id}/members/{user.id}"
        r = discord_api.get(url)
        if r.status_code != 200:
            print(f"Discord API returned: {r.status_code}" + r.text)
            return (0,0,0,0)
        CONTEXT["cache"]["members"][user.id] = r.json()
    member = CONTEXT["cache"]["members"][user.id]
    for role in CONTEXT["cache"]["roles"]:
        if role["id"] in member["roles"]:
            if "colortuple" in role:
                return role["colortuple"]
    return (0,0,0,255)
        
def update_user(user):
    user_id = user.id
    print("updating: %s" % user_id)
    r = discord_api.get(f"users/{user_id}")
    if r.status_code != 200:
        raise UserException(user, f"Unable to query user: {r.status_code}")
    userblob = r.json()
    user.name = userblob["username"]
    user.discrim = userblob["discriminator"]
    user.avatar = userblob["avatar"]
    user.has_guild_avatar = False
    r = discord_api.get(f"guilds/{user.guild_id}/members/{user_id}")
    if r.status_code == 200:
        memberblob = r.json()
        if "avatar" in memberblob and memberblob["avatar"] is not None:
            user.has_guild_avatar = True
            user.avatar = memberblob["avatar"]
    user.save()

def get_avatar_bytes(user):
    avatario = None
    if user.variantname is not None:
        print("Making s3 client")
        s3 = awsclient("s3")
        print("Getting avatar for variant")
        avatario = s3.get_object(Bucket=BUCKET_NAME, Key=user.avatar)["Body"]
    else:
        if user.has_guild_avatar is True:
            print("Getting guild member avatar")
            r = discord_cdn.get(f"guilds/{user.guild_id}/users/{user.id}/avatars/{user.avatar}.png")
            if r.status_code == 200:
                avatario = io.BytesIO(r.content)
            else:
                raise UserException(user, "Member avatar missing")
        else:
            print("Getting user avatar")
            r = discord_cdn.get(f"avatars/{user.id}/{user.avatar}.png")
            if r.status_code == 200:
                avatario = io.BytesIO(r.content)
            else:
                raise UserException(user, "User avatar missing")
    return avatario