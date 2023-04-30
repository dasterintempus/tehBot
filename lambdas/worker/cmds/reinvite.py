import os

from tehbot.settings import get_settings, upsert_settings, remove_settings_key

def reinvite_allow(body):
    #now using Discord built-in permission management for new commands
    # if not is_admin_issuer():
    #     return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    memberobj = body["data"]["resolved"]["members"][userval]

    display_name = f"{userobj['username']}#{userobj['discriminator']}"
    
    settings_key = f"reinvite:{userobj['id']}"
    try:
        get_settings(guild_id, settings_key)
    except IndexError:
        roleids = set()
        for roleid in memberobj["roles"]:
            roleids.add(roleid)
        upsert_settings(guild_id, settings_key, RoleIds=roleids)
        return True, {"json": {"content": f"Access granted to user {display_name}"}}
    else:
        return True, {"json": {"content": f"User {display_name} already has access."}}
    
def reinvite_disallow(body):
    #now using Discord built-in permission management for new commands
    # if not is_admin_issuer():
    #     return False, {"json": {"content": "Access Denied."}}
    guild_id = body["guild_id"]
    userval = body["data"]["options"][0]["options"][0]["value"]
    userobj = body["data"]["resolved"]["users"][userval]
    # memberobj = body["data"]["resolved"]["members"][userval]
    display_name = f"{userobj['username']}#{userobj['discriminator']}"
    
    settings_key = f"reinvite:{userobj['id']}"
    try:
        remove_settings_key(guild_id, settings_key)
    except IndexError:
        return True, {"json": {"content": f"User {display_name} did not have access. No changes made."}}
    else:
        return True, {"json": {"content": f"Access removed from user {display_name}."}}