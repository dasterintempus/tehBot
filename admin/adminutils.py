import sys
import json
import boto3

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
    