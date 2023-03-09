import sys
import json
import boto3
import os
from tehbot.settings import get_guildid, list_guilds
from typing import Optional, Iterable, Tuple

def get_env_guildid(env:str, guild_name:str) -> str:
    settings_table:str = get_cft_resource(env, "DynamoTables", "SettingsTable")
    os.environ["DYNAMOTABLE_SETTINGS"] = settings_table
    return get_guildid(guild_name)

def get_env_guilds(env:str) -> Iterable[Tuple[str, str]]:
    settings_table:str = get_cft_resource(env, "DynamoTables", "SettingsTable")
    os.environ["DYNAMOTABLE_SETTINGS"] = settings_table
    return list_guilds()

def get_cft_resource(env, stack, resource):
    if env == "prod":
        env = ""
    stackname = f"tehBot-{env}{stack}"
    cfn = boto3.client("cloudformation")
    r = cfn.describe_stack_resource(StackName=stackname, LogicalResourceId=resource)
    return r["StackResourceDetail"]["PhysicalResourceId"]

def get_cft_output(env, stack, outputkey, region="us-east-2"):
    if env == "prod":
        env = ""
    stackname = f"tehBot-{env}{stack}"
    botosession = boto3.Session(region_name=region)
    cfn = botosession.client("cloudformation")
    r = cfn.describe_stacks(StackName=stackname)
    stack = r["Stacks"][0]
    output = [output for output in stack["Outputs"] if output["OutputKey"] == outputkey][0]
    return output["OutputValue"]

def get_local(env):
    if env == "prod":
        env = ""
    local = {}
    with open("../local.json") as f:
        local = json.load(f)[env]
    
    return local

def get_secrets(env):
    if env == "prod":
        env = ""
    secrets = {}
    with open("../secrets.json") as f:
        secrets = json.load(f)[env]
    
    return secrets
    