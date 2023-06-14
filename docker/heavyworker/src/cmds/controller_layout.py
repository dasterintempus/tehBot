import io
import json
import copy
from PIL import Image, ImageDraw, ImageFont
import random
import io
import os.path
from typing import Iterable, Optional
from tehbot.aws import client as awsclient
from tehbot.controllerlayout import Controller, Game
from tehbot.util import BUCKET_NAME

# CONTROLLERS: "dict[str, Controller]" = {}
# GAMES: "dict[str, Game]" = {}

# BUCKET_NAME = 

def render_layout(guild_id:str, seed:Optional[str]=None):
    R = random.Random(seed)
    controller = R.choice(Controller.find_all(guild_id))
    # print(controller.buttons)
    buttons = copy.copy(list(controller.buttons))
    R.shuffle(buttons)
    num_buttons = len(buttons)
    game = R.choice(Game.find_all(guild_id))
    inputs = copy.copy(list(game.inputs))
    inputs.extend([""]*R.randint(0,2))
    if num_buttons > len(game.inputs):
        R.shuffle(inputs)
    else:
        inputs = R.sample(list(inputs), num_buttons)
    s3 = awsclient("s3")
    imio = s3.get_object(Bucket=BUCKET_NAME, Key=f"controllers/{controller.entryid}.{controller.imagepath}")["Body"]
    # print("Reading right faction image")
    im = Image.open(imio).convert("RGBA")
    # im = Image.open(controller.imagepath).convert("RGBA")
    color = tuple([0,0,0,255])
    font_size = int(16.0/600.0*im.width)
    font = ImageFont.truetype("OpenSans-VariableFont_wdth,wght.ttf", font_size)
    im_draw = ImageDraw.ImageDraw(im)
    for input in inputs:
        if len(buttons) <= 0:
            break
        button = tuple(buttons.pop(0))
        im_draw.point(button, (0,0,0,255))
        im_draw.text(button, input, color, font, "ld", stroke_fill=(255,255,255,255), stroke_width=2)
    return game.name, controller.name, im

def process_controller_map(im: Image.Image):
    x = 0
    y = 0
    out = []
    for pixel in im.getdata():
        if pixel[0] == 255 and pixel[1] == 0 and pixel[2] == 255:
            out.append([x,y])
        x += 1
        if x >= im.width:
            x = 0
            y += 1
    return out

def controller_layout(body: dict):
    username = body["member"]["nick"]
    if username is None:
        username = body["member"]["user"]["global_name"]
    filebody = io.BytesIO()
    print("Rendering Layout")
    gamename, controllername, layout_image = render_layout(body["guild_id"])
    print("Saving Layout")
    layout_image.save(filebody, "PNG")
    print("Done Saving Layout")
    filebody.seek(0)
    print("Done seek(0)ing Layout filebody")
    files = {}
    files["file[0]"] = ("layout.png", filebody)
    content = f"{username} is playing {gamename} using the {controllername}!"
    outbody = {
        "content": content,
        "embeds": [{
            "image": {
                "url": "attachment://layout.png"
            }
        }]
    }
    files["payload_json"] = ("", json.dumps(outbody), "application/json")
    return True, {"files": files}


if __name__ == "__main__":
    import sys
    if sys.argv[2] == "addgame":
        gamedef = json.load(sys.stdin)
        g = Game(sys.argv[3], sys.argv[4], gamedef, sys.argv[1])
        g.save()
    elif sys.argv[2] == "addcontroller":
        # controllerdef = json.load(sys.stdin)
        imgpath = os.path.basename(sys.argv[5])
        im = Image.open(sys.argv[5])
        controllerdef = process_controller_map(im)
        c = Controller(sys.argv[3], sys.argv[4], imgpath, controllerdef, sys.argv[1])
        c.save()
        s3 = awsclient("s3")
        imio = io.BytesIO()
        im.save(imio, "PNG")
        imio.seek(0)
        s3.put_object(Bucket=BUCKET_NAME, Key=f"controllers/{c.entryid}.{c.imagepath}", Body=imio)
    elif sys.argv[2] == "render":
        # CONTROLLERS = {c.name: c for c in Controller.find_all(sys.argv[1])}
        # print(CONTROLLERS)
        # GAMES = {g.name: g for g in Game.find_all(sys.argv[1])}
        # print(GAMES)
        gamename, controllername, im = render_layout(sys.argv[1], sys.argv[3])
        print(gamename, "-", controllername)
        im.save("out.png")