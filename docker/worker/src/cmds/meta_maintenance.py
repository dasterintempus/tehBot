from tehbot.discord import api as discord_api
from tehbot.settings import get_settings, upsert_settings, delete_settings

def meta_maintenance_start(body):
    guildid = body["guildid"]
    try:
        lobby_settings = get_settings(guildid, "lobby_tracker")
    except:
        return
    if lobby_settings["status_channel"]["S"] == "":
        return
    status_channel = lobby_settings["status_channel"]["S"]
    try:
        maintenance_status = get_settings(guildid, "maintenance_status")
        maintenance_message_id = maintenance_status["message_id"]["S"]
    except:
        maintenance_status = {}
        maintenance_message_id = None
    

    msg = f"Beep boop! tehBot is currently undergoing maintenance. During this, some features may be delayed, malfunctioning, or unavailable. Please hold!"
    if len(body["msg"]) > 0:
        msg = msg + "\n" + body["msg"]
    msg_body = {"content": msg}
    if maintenance_message_id is not None:
        r = discord_api.patch(f"/channels/{status_channel}/messages/{maintenance_message_id}", json=msg_body)
        r.raise_for_status()
    else:
        r = discord_api.post(f"/channels/{status_channel}/messages", json=msg_body)
        r.raise_for_status()
        maintenance_message_id = r.json()["id"]

    upsert_settings(guildid, "maintenance_status", message_id=maintenance_message_id)
    return True

def meta_maintenance_end(body):
    guildid = body["guildid"]
    try:
        lobby_settings = get_settings(guildid, "lobby_tracker")
    except:
        return
    if lobby_settings["status_channel"]["S"] == "":
        return
    status_channel = lobby_settings["status_channel"]["S"]
    try:
        maintenance_status = get_settings(guildid, "maintenance_status")
        maintenance_message_id = maintenance_status["message_id"]["S"]
    except:
        maintenance_status = {}
        maintenance_message_id = None
    
    if maintenance_message_id is not None:
        r = discord_api.delete(f"/channels/{status_channel}/messages/{maintenance_message_id}")
        r.raise_for_status()
    delete_settings(guildid, "maintenance_status", "message_id")
    return True