from tehbot.discord import api as discord_api
from tehbot.keysmash import score_keysmash
from tehbot.settings import get_settings
from tehbot.util import CONTEXT
import traceback

def keysmash_score(body):
    guild_id = body["guild_id"]
    channel_id = body["channel_id"]
    message_id = body["data"]["target_id"]

    # suggestor_username = body["member"]["nick"]
    # if suggestor_username is None:
    #     suggestor_username = body["member"]["user"]["global_name"]
    author: dict = list(body["data"]["resolved"]["messages"].values())[0]["author"]

    message_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
    if author.get("bot"):
        return True, {"json": {"content": f"{message_url}\nBots lack the emotional capacity to *truly* keysmash."}}

    author_username = author["global_name"]
    if author_username is None:
        author_username = author["username"]
    
    msg = list(body["data"]["resolved"]["messages"].values())[0]["content"]
    if len(msg) < 5:
        return True, {"json": {"content": f"{message_url}\nYou and I both know that is *not* a proper keysmash."}}
    
    try:
        score = score_keysmash(msg)
    except:
        traceback.print_exc()
        return True, {"json": {"content": f"{message_url}\nThis keysmash was so powerful it caused an error in the bot. Good work!"}}

    message_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    content = f"{message_url}\n**{author_username}**'s keysmash scored a **{score}**!"

    # discord_api.post(f"channels/{suggest_to_channel_id}/messages", json=msg)
    return True, {"json": {"content": content}}