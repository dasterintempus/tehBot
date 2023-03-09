import os
from tehbot.aws import from_dynamo_item
import adminutils
from typing import Optional

if __name__ == "__main__":
    import sys
    env:str = sys.argv[1]
    operation:str = sys.argv[2]
    settings_table:str = adminutils.get_cft_resource(env, "DynamoTables", "SettingsTable")
    os.environ["DYNAMOTABLE_SETTINGS"] = settings_table
    from tehbot.settings import get_settings, upsert_settings
    if operation == "add":
        guild_name:str = sys.argv[3]
        guild_id:str = sys.argv[4]
        try:
            status: Optional[dict] = get_settings(guild_id, "guild_status")
        except IndexError:
            status = {}
        status["GuildName"] = guild_name
        upsert_settings(guild_id, "guild_status", **status)