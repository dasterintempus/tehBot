#!/usr/bin/env python

import cfscrape
import boto3
import json
# from bs4 import BeautifulSoup
import sys
import io
from PIL import Image, ImageDraw, ImageFont
import re
import hashlib
import os
import random
import math

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

env_prefix = os.environ["ENV_PREFIX"]
# print(env_prefix)
QUEUE_URL = get_cft_output(env_prefix, "Queues", "InteractionDaemonQueueUrl")
CACHE_BUCKET = get_cft_output(env_prefix, "Buckets", "CacheBucket")
SECRETS_ARN = get_cft_output(env_prefix, "Secrets", "LambdaSecretsArn")
secrets = boto3.client("secretsmanager")
SECRET_BLOB = json.loads(secrets.get_secret_value(SecretId=SECRETS_ARN)["SecretString"])
os.environ["SECRETS_ARN"] = SECRETS_ARN

from tehbot.discord import api as discord_api

RANDOM_TIERLISTS = [
    "https://tiermaker.com/create/guilty-gear-xrd-rev-2--tier-list-15358858",
    "https://tiermaker.com/create/guilty-gear-strive-characters-2",
    "https://tiermaker.com/create/guilty-gear-xx-accent-core-r-1704"
]
CHARACTER_IMAGE_SIZE = (70, 70)

RANDOM_TIERS = ["S", "A", "B", "C", "D"]
RANDOM_RARE_TIERS = ["God", "Trash", "OP", "UP"]
SORT_ORDER = ["God", "OP", "S", "A", "B", "C", "D", "UP", "Trash"]
TIER_COLORS = [(1.0, 0.5, 0.5), (1.0, 0.75, 0.5), (1.0, 0.875, 0.5), (1.0, 1.0, 0.5), (.75, 1.0, 0.5)]


def handle_queue_event(body):
    interaction_token = body["token"]
    if "options" in body["data"] and len(body["data"]["options"]) > 0:
        url = body["data"]["options"][0]["value"].lower()
    else:
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
            apir = scraper.get(url)
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
    random.shuffle(images)

    tiers = {}
    tiernames = set()
    character_count = len(images)
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
    if len(images) + len(tier) > max_assign_count:
        max_assign_count = len(images) + len(tier)
    tier.extend(images)

    # print(tiers.keys())
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

    out_body = io.BytesIO()
    out_im.save(out_body, "png")
    out_body.seek(0)
    url = f"webhooks/{SECRET_BLOB['application_id']}/{interaction_token}/messages/@original"
    files = {}
    files["file[0]"] = ("tierlist.png", out_body)
    outbody = {
        "embeds": [{
            "image": {
                "url": "attachment://tierlist.png"
            }
        }]
    }
    files["payload_json"] = ("", json.dumps(outbody), "application/json")
    r = discord_api.patch(url, files=files)

    # out_im.save("out.png")


if __name__ == "__main__":
    sqs = boto3.client("sqs")
    while True:
        r = sqs.receive_message(QueueUrl=QUEUE_URL, WaitTimeSeconds=20, VisibilityTimeout=60)
        # print(r)
        if "Messages" in r:
            for msg in r["Messages"]:
                handle_queue_event(json.loads(msg["Body"]))
        # time.sleep(5)