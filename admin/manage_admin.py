import boto3
import adminutils
import os
if __name__ == "__main__":
    import sys
    
    env = sys.argv[1]
    local = adminutils.get_local(env)

    guild_name = sys.argv[2]
    guild_id = adminutils.get_env_guildid(env, guild_name)

    roletype = sys.argv[3]

    settings_table = adminutils.get_cft_resource(sys.argv[1], "DynamoTables", "SettingsTable")
    os.environ["DYNAMOTABLE_SETTINGS"] = settings_table
    from tehbot.settings import upsert_settings
    kwargs = {}
    kwargs[roletype+"_roles"] = ",".join(sys.argv[4:])
    upsert_settings(guild_id, "admin_settings", **kwargs)