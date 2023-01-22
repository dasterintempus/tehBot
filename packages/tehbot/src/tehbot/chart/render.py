import json
import io
import hashlib
import requests
import math
import os
from PIL import Image, ImageColor, ImageOps, ImageDraw, ImageFont

from ..discord import api as discord_api, RateLimitException
from ..aws import client as awsclient
from .users import User, UserException, find_user_color, get_avatar_bytes, populate_role_cache, update_user
from .coord import bary_to_color, cart_to_bary, compute_pos
from ..util import BUCKET_NAME, CONTEXT
from ..settings import get_settings

CHART_IMAGE_SIZE = (1000,1000)
AVATAR_SIZE = (64,64)
AVATAR_INNER_SIZE = (58, 58)
FACTION_SIZE = (150,150)

# TOP_POINT = (CHART_IMAGE_SIZE[0]/2, CHART_IMAGE_SIZE[0]*9/10-(CHART_IMAGE_SIZE[0]*9/10*math.sqrt(3)/2))
# RIGHT_POINT = (CHART_IMAGE_SIZE[0]*9/10, CHART_IMAGE_SIZE[0]*9/10)
# LEFT_POINT = (CHART_IMAGE_SIZE[0]/10, CHART_IMAGE_SIZE[0]*9/10)

TOP_POINT = (500, 110)
RIGHT_POINT = (950, 890)
LEFT_POINT = (50, 890)

class UserRenderException(Exception):
    def __init__(self, item, msg):
        self.item = item
        self.msg = msg

def construct_image(lam, size):
    bio = io.BytesIO()
    for y in range(size[1]):
        for x in range(size[0]):
            pixel = lam((x, y), size)
            bio.write(bytes(pixel))
    bio.seek(0)
    b = bio.read()
    return Image.frombytes("RGBA", size, b)

def cons_gradient_factory(colors):
    def f(p, s):
        bary_p = cart_to_bary(p, (TOP_POINT, RIGHT_POINT, LEFT_POINT))
        if bary_p[0] < 0 or bary_p[1] < 0 or bary_p[2] < 0:
            return (0,0,0,0)
        return bary_to_color(bary_p, colors)
    return f

def render_triangle(settings):
    guild_id = CONTEXT["request"]["guild_id"]
    colors = []
    #top_settings = get_settings(guild_id, "chart_settings.top")
    #right_settings = get_settings(guild_id, "chart_settings.right")
    #left_settings = get_settings(guild_id, "chart_settings.left")
    top_settings = settings["top"]
    right_settings = settings["right"]
    left_settings = settings["left"]
    roles_filter = [item["role_name"]["S"].lower() for item in (top_settings, right_settings, left_settings)]
    for rolename in roles_filter:
        if "roles" not in CONTEXT["cache"]:
            populate_role_cache()
        for role in CONTEXT["cache"]["roles"]:
            #print(f"Searching role: {role['name'].lower()}")
            if rolename == role["name"].lower():
                print("Matched role")
                colors.append(role["colortuple"])
    if len(colors) != 3:
        raise Exception(f"Can't find matching roles, only found: {len(colors)}")
    rolestr = json.dumps(colors)
    print("Hashing colors")
    digest = hashlib.sha256(rolestr.encode()).hexdigest()
    print("Done hashing colors")
    s3 = awsclient("s3")
    print("Listing objects")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"triangles/{guild_id}/")
    print("Done listing objects")
    if "Contents" in response:
        for object in response["Contents"]:
            if object["Key"] == f"triangles/{guild_id}/{digest}.png":
                print("Calling get object")
                f = s3.get_object(Bucket=BUCKET_NAME, Key=f"triangles/{guild_id}/{digest}.png")["Body"]
                print("Opening image to return")
                return Image.open(f)

    print("Triangle not found in cache")
    #notify that we are rendering
    interaction_token = CONTEXT["request"]["token"]
    url = f"webhooks/{CONTEXT['secrets']['application_id']}/{interaction_token}/messages/@original"
    print("Sending temporary status")
    r = discord_api.patch(url, json={"content": f"No triangle cache entry found, re-rendering! Please hold."})
    print("Done sending temporary status")

    print("Constructing image")
    tri = construct_image(cons_gradient_factory(colors), CHART_IMAGE_SIZE)
    print("Done constructing image")
    draw = ImageDraw.Draw(tri)
    print("Drawing outline")
    draw.polygon((TOP_POINT, RIGHT_POINT, LEFT_POINT), fill=None, outline=(0,0,0,255))
    print("Done drawing outline")

    image_bytes = io.BytesIO()
    print("Saving image for s3cache")
    tri.save(image_bytes, "PNG")
    print("Done saving image for s3cache")
    image_bytes.seek(0)
    print("Putting object to s3cache")
    s3.put_object(Bucket=BUCKET_NAME, Key=f"triangles/{guild_id}/{digest}.png", Body=image_bytes)
    print("Done putting object to s3cache")

    return tri

def render_user(user):
    print("Rendering entry")
    print(f"Username: {user.name}")
    if user.variantname is not None:
        print(f"Variant Name: {user.variantname}")
    
    #TODO mask out avatar into a circle
    print("Getting user avatar")
    try:
        avatario = get_avatar_bytes(user)
    except UserException as e:
        print("Could not find avatar, attempting to update user.")
        update_user(user)
        print("User updated, retrying getting avatar")
        avatario = get_avatar_bytes(user) #retry once
    print("Done fetching avatar")
    print("Creating background image")
    out = Image.new("RGBA", AVATAR_SIZE, (0,0,0,0))
    draw = ImageDraw.Draw(out)
    print("Finding user color")
    color = find_user_color(user)
    edge = (color[0], color[1], color[2], 128)
    print("Drawing ellipse")
    draw.ellipse(((0,0), AVATAR_SIZE), fill=color, outline=edge, width=2)
    print("Reading avatar")
    avatarimg = Image.open(avatario).resize(AVATAR_INNER_SIZE).convert("RGBA")
    corner = (int((AVATAR_SIZE[0]-AVATAR_INNER_SIZE[0])/2), int((AVATAR_SIZE[1]-AVATAR_INNER_SIZE[1])/2))
    print("avatarimg", avatarimg.format, f"{avatarimg.size}x{avatarimg.mode}")
    print("outimg", out.format, f"{out.size}x{out.mode}")
    print("Starting mask")
    mask = Image.new("1", AVATAR_INNER_SIZE, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(((0,0), AVATAR_INNER_SIZE), fill=1, outline=1, width=1)
    masked_avatarimg = Image.new("RGBA", AVATAR_INNER_SIZE, (0,0,0,0))
    masked_avatarimg.paste(avatarimg, mask=mask)
    print("Compositing avatar")
    out.alpha_composite(masked_avatarimg, corner)
    print("Returning avatar image")
    return out

def render_chart():
    #cache = {}
    print("Creating blank image")
    out = Image.new("RGBA", CHART_IMAGE_SIZE, (255,255,255,0))
    print("Done creating blank image")

    print("Looking up settings")
    top_settings = get_settings(CONTEXT["request"]["guild_id"], "chart_settings.top")
    top_bg_image_key = top_settings["bg_image_key"]["S"]
    right_settings = get_settings(CONTEXT["request"]["guild_id"], "chart_settings.right")
    right_bg_image_key = right_settings["bg_image_key"]["S"]
    left_settings = get_settings(CONTEXT["request"]["guild_id"], "chart_settings.left")
    left_bg_image_key = left_settings["bg_image_key"]["S"]

    print("Making s3 client")
    s3 = awsclient("s3")

    print("Downloading top faction image")
    topio = s3.get_object(Bucket=BUCKET_NAME, Key=top_bg_image_key)["Body"]
    print("Reading top faction image")
    topim = Image.open(topio)#.resize(FACTION_SIZE)
    toppos = (int(TOP_POINT[0] - (topim.size[0]/2)), int(TOP_POINT[1] - (topim.size[1]/2)))
    print("Compositing top faction image")
    out.alpha_composite(topim, toppos)
    print("Done w/ top faction image")

    print("Downloading right faction image")
    rightio = s3.get_object(Bucket=BUCKET_NAME, Key=right_bg_image_key)["Body"]
    print("Reading right faction image")
    rightim = Image.open(rightio)#.resize(FACTION_SIZE)
    rightpos = (int(RIGHT_POINT[0] - (rightim.size[0]/2)), int(RIGHT_POINT[1] - (rightim.size[1]/2)))
    print("Compositing right faction image")
    out.alpha_composite(rightim, rightpos)
    print("Done w/ right faction image")

    print("Downloading left faction image")
    leftio = s3.get_object(Bucket=BUCKET_NAME, Key=left_bg_image_key)["Body"]
    print("Reading left faction image")
    leftim = Image.open(leftio)#.resize(FACTION_SIZE)
    leftpos = (int(LEFT_POINT[0] - (leftim.size[0]/2)), int(LEFT_POINT[1] - (leftim.size[1]/2)))
    print("Compositing left faction image")
    out.alpha_composite(leftim, leftpos)
    print("Done w/ left faction image")

    # tri = construct_image(cons_gradient_factory(colors), CHART_IMAGE_SIZE)
    # draw = ImageDraw.Draw(tri)
    print("Acquiring background triangle")
    tri = render_triangle({"top": top_settings, "right": right_settings, "left": left_settings})
    print("Compositing background triangle")
    out.alpha_composite(tri, (0,0))
    print("Done compositing background triangle")

    #center = (int(CHART_IMAGE_SIZE[0]/2), int(CHART_IMAGE_SIZE[1]/2))
    #render a triangle? maybe?
    dynamo = awsclient("dynamodb")
    print(f"Scanning Dynamo for Guild ID {CONTEXT['request']['guild_id']}")
    filterexpr = "GuildId = :guildid"
    filtervals = {
        ":guildid": {"S": CONTEXT["request"]["guild_id"]}
    }
    response = dynamo.scan(
        TableName=os.environ.get("DYNAMOTABLE_CHART"),
        FilterExpression=filterexpr,
        ExpressionAttributeValues=filtervals
    )
    print("Looping Dynamo Items")
    msgs = []
    for item in response["Items"]:
        print("Rendering entry")
        print("Making user")
        user = User.from_item(item)
        try:
            im = render_user(user)
        except UserException as e:
            estr = f"Exception with user {user.name}: {e.msg}"
            print(estr)
            msgs.append(estr)
        except UserRenderException as e:
            estr = f"Exception rendering {user.name}: {e.msg}"
            print(estr)
            msgs.append(estr)
        except Exception as e:
            estr = f"Unknown exception rendering {user.name}: {e}"
            print(estr)
            msgs.append(estr)
        else:
            coords = [float(coord["N"]) for coord in item["Coordinates"]["L"]]
            center = compute_pos(coords)
            x = int(center[0]-(AVATAR_SIZE[0])/2)
            y = int(center[1]-(AVATAR_SIZE[1])/2)
            w = int(AVATAR_SIZE[0])
            h = int(AVATAR_SIZE[1])
            box = (x, y, x+w, y+h)
            print("Done rendering entry")
            out.alpha_composite(im, (x,y))
    return out, msgs
