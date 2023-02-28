import os
os.environ["SECRETS_ARN"] = "arn:aws:secretsmanager:us-east-2:105824585986:secret:tehBot/devlambdas-aJPvrC"
from tehbot.discord import api as discord_api
# from tehbot.discord import is_quoteadmin_issuer
# from tehbot.quotes import Quote, Alias
# from tehbot.settings import get_settings
from tehbot.util import CONTEXT
from bs4 import BeautifulSoup
import requests
import random
import traceback
import re
import math
import io
import json
from PIL import Image, ImageDraw, ImageFont

RANDOM_TIERLISTS = [
    "https://tiermaker.com/create/guilty-gear-xrd-rev-2--tier-list-15358858",
    "https://tiermaker.com/create/guilty-gear-strive-characters-2",
    "https://tiermaker.com/create/guilty-gear-xx-accent-core-r-1704"
]
CHARACTER_IMAGE_SIZE = (200, 200)

RANDOM_TIERS = ["S", "A", "B", "C", "D"]
RANDOM_RARE_TIERS = ["God", "Trash", "OP", "UP"]
TIER_COLORS = [(1.0, 0.5, 0.5), (1.0, 0.75, 0.5), (1.0, 0.875, 0.5), (1.0, 1.0, 0.5), (.75, 1.0, 0.5)]

def extract_bg_image(img):
    style = img["style"]
    match = re.search(r'''url\((.*?)\)''', style)
    if match:
        return match.group(1)
    else:
        return None

def generate_tierlist(body):
    # if "options" in body["data"] and len(body["data"]["options"]) > 0:
    #     tierlist_url = body["data"]["options"][0]["value"].lower()
    # else:
    tierlist_url = random.choice(RANDOM_TIERLISTS)

    # interaction_token = CONTEXT["request"]["token"]
    # url = f"webhooks/{CONTEXT['secrets']['application_id']}/{interaction_token}/messages/@original"
    # print("Sending temporary status")
    # r = discord_api.patch(url, json={"content": f"Preparing tier list! Please hold."})
    # print("Done sending temporary status")

    # r = requests.get(tierlist_url, headers={
    #     "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    #     "accept-encoding": "gzip, deflate, br",
    #     "accept-language": "en-US,en;q=0.9",
    #     "referer": "https://tiermaker.com",
    #     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.50",
    #     "sec-ch-ua": '''"Chromium";v="110", "Not A(Brand";v="24", "Microsoft Edge";v="110"'''
    # },
    # cookies={"cookiePolicyAgreement": "true"})
    # print(r.headers)
    # # try:
    # r.raise_for_status()
    # except:
    #     return True, {"json": {"content": "Invalid Tierlist URL"}}


    # soup = BeautifulSoup(r.text, "html.parser")
    # images = soup.select("#create-image-carousel > div#character")
    # image_urls = [extract_bg_image(i) for i in images if extract_bg_image(i) is not None]


    image_urls = []
    for filename in os.listdir("./icons"):
        image_urls.append(filename)
    random.shuffle(image_urls)
    tiers = {}
    tiernames = set()
    character_count = len(image_urls)
    max_assign_count = 0
    for n in range(5):
        tier = []
        if random.randint(1,10) == 10:
            while tiername := random.choice(RANDOM_RARE_TIERS):
                if tiername not in tiernames:
                    break
            tiernames.add(tiername)
            tiers[tiername] = tier
        else:
            while tiername := random.choice(RANDOM_TIERS):
                if tiername not in tiernames:
                    break
            tiernames.add(tiername)
            tiers[tiername] = tier
        assign_count = math.ceil(random.triangular(0.0, 1.0, 0.05*(n+1))*character_count)
        if assign_count > len(image_urls):
            assign_count = len(image_urls)
        if assign_count > max_assign_count:
            max_assign_count = assign_count
        tier.extend(image_urls[:assign_count])
        del image_urls[:assign_count]
    
    # print((300+CHARACTER_IMAGE_SIZE[0]*character_count, 1000))
    # print((0.0, 0.0, 0.0, 1.0))
    out_im = Image.new("RGBA", (300+(CHARACTER_IMAGE_SIZE[0]*max_assign_count), 1000), (0, 0, 0, 255))

    out_draw = ImageDraw.Draw(out_im)
    font = ImageFont.truetype("OpenSans-VariableFont_wdth,wght.ttf", 80)
    for tier_n, tiername in enumerate(tiers):
        print(tier_n, tiername)
        out_draw.rectangle((0, (CHARACTER_IMAGE_SIZE[1]*tier_n), 300, (CHARACTER_IMAGE_SIZE[1]*(1+tier_n))), tuple([int(i*255) for i in TIER_COLORS[tier_n]]), (0, 0, 0, 255))
        out_draw.text((10, 50+(CHARACTER_IMAGE_SIZE[1]*tier_n)), tiername, (20, 20, 20, 255), font)
        for char_n, character_image_url in enumerate(tiers[tiername]):
            # r = requests.get(f"https://tiermaker.com/{character_image_url}")
            # char_io = io.BytesIO()
            # char_io.write(r.content)
            # char_io.seek(0)
            # char_im = Image.open(char_io)
            char_im = Image.open(f"icons/{character_image_url}")
            char_im = char_im.resize(CHARACTER_IMAGE_SIZE)
            out_im.paste(char_im, (300+(char_n*CHARACTER_IMAGE_SIZE[0]), tier_n*CHARACTER_IMAGE_SIZE[1]))

    
    out_im.save("out.png")

    # filebody = io.BytesIO()
    # print("Rendering tier list")
    # out_im.save(filebody, "PNG")
    # print("Done rendering tierlist")
    # filebody.seek(0)
    # print("Done seek(0)ing tierlist filebody")
    # files = {}
    # files["file[0]"] = ("tierlist.png", filebody)

    # outbody = {
    #     "embeds": [{
    #         "image": {
    #             "url": "attachment://tierlist.png"
    #         }
    #     }]
    # }
    # files["payload_json"] = ("", json.dumps(outbody), "application/json")
    # return True, {"files": files}