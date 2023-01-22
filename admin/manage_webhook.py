import requests
import json

import adminutils

if __name__ == "__main__":
    import sys
    guild_name = sys.argv[2]
    webhook_name = sys.argv[3]

    local = adminutils.get_local(sys.argv[1])
    secrets = adminutils.get_secrets(sys.argv[1])

    body = {}
    with open(f"webhooks/{webhook_name}.json") as f:
        body = json.load(f)
    
    app_id = secrets["application_id"]
    guild_id = local["guilds"][guild_name]
    
    headers = {
        "Authorization": f"Bot {secrets['discord_bot_token']}"
    }
    url = f"https://discord.com/api/v8/applications/{app_id}/guilds/{guild_id}/commands"
    r = requests.post(url, headers=headers, json=body)

    print(r.status_code)
    print(r.text)
