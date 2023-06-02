from tehbot.discord import api as discord_api
from tehbot.discord import is_quoteadmin_issuer
from tehbot.quotes import Quote, Alias
from tehbot.settings import get_settings
import random
import traceback
from tehbot.util import CONTEXT

def quote_search(body):
    guild_id = body["guild_id"]
    if "options" in body["data"] and len(body["data"]["options"]) > 0:
        termstr = body["data"]["options"][0]["value"].lower()
        terms = termstr.split(",")
        quotes = Quote.search(terms, guild_id)
        content = f"Quote: {' '.join(terms)}"
    else:
        quotes = Quote.find_all(guild_id)
        content = f"Random Quote"
    if len(quotes) == 0:
        return True, {"json": {"content": f"No matching quotes found."}}
    
    quote = random.choice(quotes)
    print(f"Quote found: {quote.name} {quote.url} {quote.tags}")

    #return True, {"json": {"content": f"{content}\n{quote.url}"}}
    outbody = {
        "content": content,
        "embeds": [{
            "image": {
                "url": quote.url
            }
        }]
    }

    #return True, {"json": outbody}
    #DISCORD WORKAROUND
    interaction_token = body["token"]
    discord_api.post(f"webhooks/{CONTEXT['secrets']['application_id']}/{interaction_token}", json=outbody)

    return True, {"json": {"content": content}}

def quote_suggest(body):
    guild_id = body["guild_id"]

    admin_settings = get_settings(guild_id, "admin_settings")
    suggest_to_channel_id = admin_settings["quote_suggest_channel_id"]["S"]


    channel_id = body["channel_id"]
    message_id = body["data"]["target_id"]
    suggestor = body["member"]["user"]
    suggestor_display_name = f"{suggestor['username']}#{suggestor['discriminator']}"
    author = list(body["data"]["resolved"]["messages"].values())[0]["author"]
    author_display_name = f"{author['username']}#{author['discriminator']}"
    message_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    msg = {}
    msg["content"] = f"**{suggestor_display_name}** has submitted a post by **{author_display_name}**\n{message_url}"

    discord_api.post(f"channels/{suggest_to_channel_id}/messages", json=msg)
    return True, "__DELETE"

def quotemod_add(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    quotename = body["data"]["options"][0]["options"][0]["value"].lower()
    tagstr = body["data"]["options"][0]["options"][1]["value"].lower()
    tags = tagstr.split(",")
    quoteimgurl = body["data"]["options"][0]["options"][2]["value"]
    oldquote = Quote.find_by_name(quotename, guild_id)
    if oldquote is not None:
        return True, {"json": {"content": f"Quote with that name already exists: {oldquote.url}"}}

    quote = Quote(quoteimgurl, quotename, set(tags), guild_id)
    quote.save()
    
    print(f"Quote created: {quote.name} {quote.url} {quote.tags}")

    return True, {"json": {"content": f"Quote added! {quote.name} {quote.tags} {quote.url}"}}
    
def quotemod_delete(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    quotename = body["data"]["options"][0]["options"][0]["value"].lower()
    quote = Quote.find_by_name(quotename, guild_id)
    if quote is None:
        return True, {"json": {"content": f"Quote with that name does not exist"}}

    quote.drop()
    
    print(f"Quote deleted: {quote.name} {quote.url} {quote.tags}")

    return True, {"json": {"content": "Deleted."}}
    
def quotemod_print(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    quotename = body["data"]["options"][0]["options"][0]["value"].lower()
    quote = Quote.find_by_name(quotename, guild_id)
    if quote is None:
        return True, {"json": {"content": f"Quote with that name does not exist"}}
    
    print(f"Quote printed: {quote.name} {quote.url} {quote.tags}")

    return True, {"json": {"content": f"{quote.name} {quote.tags} {quote.url}"}}

def quotemod_list(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    if len(body["data"]["options"][0]["options"]) > 0:
        termstr = body["data"]["options"][0]["options"][0]["value"].lower()
        terms = termstr.split(",")
        quotes = Quote.search(terms, guild_id)
    else:
        quotes = Quote.find_all(guild_id)
    if len(quotes) == 0:
        return True, {"json": {"content": f"No matching quotes found."}}

    count = 0
    content = ""
    content = content + "```"
    for quote in quotes:
        if len(content) >= 1500:
            content = f"Only returning the first {count} results!" + content
            break
        content = content + f"{quote.name} {quote.tags}\n"
        count += 1
    content = content + "```"

    return True, {"json": {"content": content}}

def quotemod_modify_tags(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    quotename = body["data"]["options"][0]["options"][0]["value"].lower()
    tagstr = body["data"]["options"][0]["options"][1]["value"].lower()
    tags = tagstr.split(",")
    quote = Quote.find_by_name(quotename, guild_id)
    if quote is None:
        return True, {"json": {"content": f"Quote with that name does not exist"}}

    oldtags = quote.tags

    quote.tags = set(tags)

    quote.save()
    
    print(f"Quote modified: {quote.name} {quote.url} {oldtags} -> {quote.tags}")

    return True, {"json": {"content": f"Modified tags! {oldtags} -> {quote.tags}"}}


def quotemod_alias_add(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    aliaskey = body["data"]["options"][0]["options"][0]["options"][0]["value"].lower()
    valuestr = body["data"]["options"][0]["options"][0]["options"][1]["value"].lower()
    values = valuestr.split(",")
    oldalias = Alias.find_by_key(aliaskey, guild_id)
    if oldalias is not None:
        return True, {"json": {"content": f"Quote with that key already exists: {oldalias.values}"}}

    alias = Alias(aliaskey, set(values), guild_id)
    alias.save()
    
    print(f"Alias created: {alias.key} {alias.values}")

    return True, {"json": {"content": f"Alias added! {alias.key} {alias.values}"}}
    
def quotemod_alias_delete(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    aliaskey = body["data"]["options"][0]["options"][0]["options"][0]["value"].lower()
    alias = Alias.find_by_key(aliaskey, guild_id)
    if alias is None:
        return True, {"json": {"content": f"Alias with that key does not exist"}}

    alias.drop()
    
    print(f"Alias deleted: {alias.key} {alias.values}")

    return True, {"json": {"content": "Deleted."}}
    
def quotemod_alias_print(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    aliaskey = body["data"]["options"][0]["options"][0]["options"][0]["value"].lower()
    alias = Alias.find_by_key(aliaskey, guild_id)
    if alias is None:
        return True, {"json": {"content": f"Alias with that key does not exist"}}
    
    print(f"Alias printed: {alias.key} {alias.values}")

    return True, {"json": {"content": f"{alias.key} {alias.values}"}}

def quotemod_alias_list(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    if len(body["data"]["options"][0]["options"][0]["options"]) > 0:
        valuestr = body["data"]["options"][0]["options"][0]["options"][0]["value"].lower()
        values = valuestr.split(",")
        aliases = []
        for value in values:
            aliases.extend(Alias.find_by_value(value, guild_id))
    else:
        aliases = Alias.find_all(guild_id)
    if len(aliases) == 0:
        return True, {"json": {"content": f"No matching aliases found."}}

    count = 0
    content = ""
    content = content + "```"
    for alias in aliases:
        if len(content) >= 1500:
            content = f"Only returning the first {count} results!" + content
            break
        content = content + f"{alias.key} {alias.values}\n"
        count += 1
    content = content + "```"

    return True, {"json": {"content": content}}

def quotemod_alias_modify_values(body):
    if not is_quoteadmin_issuer():
        return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    aliaskey = body["data"]["options"][0]["options"][0]["options"][0]["value"].lower()
    valuestr = body["data"]["options"][0]["options"][0]["options"][1]["value"].lower()
    values = valuestr.split(",")
    alias = Alias.find_by_key(aliaskey, guild_id)
    if alias is None:
        return True, {"json": {"content": f"Alias with that key does not exist"}}

    oldvalues = alias.values

    alias.values = set(values)

    alias.save()
    
    print(f"Alias modified: {alias.key} {oldvalues} -> {alias.values}")

    return True, {"json": {"content": f"Modified values! {oldvalues} -> {alias.values}"}}