#!/usr/bin/env python

import cfscrape
import boto3
import json
# from bs4 import BeautifulSoup
import sys
import io
from PIL import Image, ImageDraw, ImageFont
import re
import traceback
import hashlib
import os
import random
import math

from tehbot.util import BUCKET_NAME as CACHE_BUCKET

def get_cft_output(env, stack, outputkey, region="us-east-2"):
    if env == "prod":
        env = ""
    stackname = f"tehBot-{env}{stack}"
    botosession = boto3.Session(region_name=region)
    cfn = botosession.client("cloudformation")
    r = cfn.describe_stacks(StackName=stackname)
    stack = r["Stacks"][0]
    # print(stack)
    output = [output for output in stack["Outputs"] if output["OutputKey"] == outputkey][0]
    return output["OutputValue"]

RANDOM_TIERLISTS = [
    "https://tiermaker.com/create/guilty-gear-xrd-rev-2--tier-list-15358858",
    "https://tiermaker.com/create/guilty-gear-strive-characters-2",
    "https://tiermaker.com/create/guilty-gear-xx-accent-core-r-1704"
]
CHARACTER_IMAGE_SIZE = (70, 70)

RANDOM_TIERS = ["S", "A", "B", "C", "D"]
RANDOM_RARE_TIERS = ["God", "Trash", "OP", "UP", "Joke"]
SORT_ORDER = ["God", "OP", "S", "A", "B", "C", "D", "UP", "Trash", "Joke"]
TIER_COLORS = [(1.0, 0.5, 0.5), (1.0, 0.75, 0.5), (1.0, 0.875, 0.5), (1.0, 1.0, 0.5), (.75, 1.0, 0.5)]

def generate_tierlist(url=None):
    # interaction_token = body["token"]
    if url is None:
        url = random.choice(RANDOM_TIERLISTS)

    category = url.rsplit("/", 1)[-1]
    hashed_category = hashlib.sha256(category.encode()).hexdigest()
    s3 = boto3.client("s3")

    
    try:
        s3.get_object(Bucket=CACHE_BUCKET, Key=f"/tiermakers/{hashed_category}/done")
    except:
        cached = False
    else:
        cached = True

    images = []

    if not cached:
        scraper = cfscrape.create_scraper()
        r = scraper.get(url)
        r.raise_for_status()
        # except:
        #     sys.stderr.write("")
        # print(r.text)

        path_match = re.search(r'''baseTierImagePath\s+\=\s+"(.+?)";''', r.text)
        edited_date_match = re.search(r'''dateLastEdited\s+\=\s+"(.+?)";''', r.text)
        if path_match and edited_date_match:
            baseImagePath = path_match.group(1)
            dateLastEdited = edited_date_match.group(1)
            url = f"https://tiermaker.com/api/?type=templates-v2&id={category}&lastEdited={dateLastEdited}"
            # print(url)
            try:
                apir = scraper.get(url)
            except:
                traceback.print_exc()
                return None
            for imagename in apir.json()[1:]:
                url = f"https://tiermaker.com/{baseImagePath}/{imagename}"
                # print(url)
                imager = scraper.get(url)
                char_io = io.BytesIO()
                char_io.write(imager.content)
                char_io.seek(0)
                char_im = Image.open(char_io)
                # char_io.close()
                # char_im = Image.open(f"icons/{image_url}")
                char_im = char_im.resize(CHARACTER_IMAGE_SIZE)
                images.append(char_im)
                # char_im.save(f"{imagename}.png")
                char_png_io = io.BytesIO()
                char_im.save(char_png_io, "png")
                char_png_io.seek(0)
                s3.put_object(Bucket=CACHE_BUCKET, Key=f"/tiermakers/{hashed_category}/{imagename}.png", ContentType="image/png", Body=char_png_io)
                # char_png_io.close()
        else:
            print(":(")
            print(path_match)
            print(edited_date_match)
        dummy = io.BytesIO()
        s3.put_object(Bucket=CACHE_BUCKET, Key=f"/tiermakers/{hashed_category}/done", ContentType="test/plain", Body=dummy)
    else:
        aws_r = s3.list_objects_v2(Bucket=CACHE_BUCKET, Prefix=f"/tiermakers/{hashed_category}/")
        for obj in aws_r["Contents"]:
            # print("key", obj["Key"])
            if obj["Key"].endswith(".png"):
                im = Image.open(s3.get_object(Bucket=CACHE_BUCKET, Key=obj["Key"])["Body"])
                images.append(im)
    #ADVANCED ML WORK HERE
    random.shuffle(images)

    #assign characters to tiers
    tiers = {}
    tiernames = set()
    character_count = len(images)
    max_assign_count = 0
    for n in range(5):
        tier = []
        if random.randint(1,10) == 10:
            #pick a rarer tier name
            while tiername := random.choice(RANDOM_RARE_TIERS):
                if tiername not in tiernames:
                    break
            tiernames.add(tiername)
            tiers[tiername] = tier
        else:
            #pick a normal tier name
            while tiername := random.choice(RANDOM_TIERS):
                if tiername not in tiernames:
                    break
            tiernames.add(tiername)
            tiers[tiername] = tier
        #how many characters in this tier?
	    #formula figured out by advanced process of "trial and error until it looks right"
        assign_count = math.ceil(random.triangular(0.0, 1.0, 0.01*(n+1))*character_count/3)
        if assign_count > len(images):
            assign_count = len(images)
        if assign_count > max_assign_count:
            max_assign_count = assign_count
        # print("assign_count", assign_count)
        # print("max_assign_count", max_assign_count)
        # print("pre_assign_len", len(images))
        tier.extend(images[:assign_count])
        del images[:assign_count]
        # print("post_assign_len", len(images))
    #any remaining characters are also dumped into the last tier
    if len(images) + len(tier) > max_assign_count:
        max_assign_count = len(images) + len(tier)
    tier.extend(images)

    #sort so tier names appear in order
    sorted_tiernames = list(tiers.keys())
    sorted_tiernames.sort(key=lambda i: SORT_ORDER.index(i))
    # print(sorted_tiernames)

    out_im = Image.new("RGBA", (100+(CHARACTER_IMAGE_SIZE[0]*max_assign_count), 70*5), (0, 0, 0, 255))

    out_draw = ImageDraw.Draw(out_im)
    font = ImageFont.truetype("OpenSans-VariableFont_wdth,wght.ttf", 30)
    for tier_n, tiername in enumerate(sorted_tiernames):
        # print(tier_n, tiername)
        out_draw.rectangle((0, (CHARACTER_IMAGE_SIZE[1]*tier_n), 100, (CHARACTER_IMAGE_SIZE[1]*(1+tier_n))), tuple([int(i*255) for i in TIER_COLORS[tier_n]]), (0, 0, 0, 255))
        out_draw.text((10, 20+(CHARACTER_IMAGE_SIZE[1]*tier_n)), tiername, (20, 20, 20, 255), font)
        for char_n, char_im in enumerate(tiers[tiername]):
            # r = requests.get(f"https://tiermaker.com/{character_image_url}")
            # char_io = io.BytesIO()
            # char_io.write(r.content)
            # char_io.seek(0)
            # char_im = Image.open(char_io)
            # char_im = Image.open(f"icons/{character_image_url}")
            # char_im = char_im.resize(CHARACTER_IMAGE_SIZE)
            out_im.paste(char_im, (100+(char_n*CHARACTER_IMAGE_SIZE[0]), tier_n*CHARACTER_IMAGE_SIZE[1]))

    return out_im

    # out_im.save("out.png")
