from .util import CONTEXT
from .discord import api as discord_api

def populate_member_cache_v2(guild_id):
    if "cache" not in CONTEXT:
        CONTEXT["cache"] = {}
    if "members" not in CONTEXT["cache"]:
        CONTEXT["cache"]["members"] = {}
    CONTEXT["cache"]["members"][guild_id] = {}

    url = f"guilds/{guild_id}/members?limit=250"
    r = discord_api.get(url)
    if r.status_code != 200:
        print(f"Discord API returned: {r.status_code}" + r.text)
        r.raise_for_status()
    else:
        for member in r.json():
            user_id = member["user"]["id"]
            CONTEXT["cache"]["members"][guild_id][user_id] = member