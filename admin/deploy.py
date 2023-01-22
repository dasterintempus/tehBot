#!/usr/bin/env python
import boto3
import json
import argparse
import traceback
import os, os.path
import glob
import sys
import botocore.exceptions
import time
import datetime
import subprocess
import shlex
import pprint
import requests
import io
import jinja2
import docker

import adminutils

ALL_STACKS = ["buckets", "cloudfront", "dynamotables", "secrets", "roles", "queues", "lambdas", "apigateway", "backups"]

STACK_HANDLERS = {}

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("../web/"))

def wait_stack_status(ctx, stackname, okstatus, errstatus):
    cfn = ctx["aws"].client("cloudformation")
    while True:
        r = cfn.describe_stacks(StackName=stackname)
        status = r["Stacks"][0]["StackStatus"]
        print(f"{datetime.datetime.now().isoformat()} - Stack {stackname} is {status}")
        if "CLEANUP_IN_PROGRESS" not in status:
            for err in errstatus:
                if err in status:
                    print(f"{datetime.datetime.now().isoformat()} - Stack {stackname} has failed!")
                    # pprint.pprint(r)
                    return False, r.get("StackStatusReason")
            for ok in okstatus:
                if ok in status:
                    print(f"{datetime.datetime.now().isoformat()} - Stack {stackname} is ok!")
                    return True, None
        time.sleep(10)

def create_stack(ctx, stackname, templatepath, args, **kwargs):
    print(f"{datetime.datetime.now().isoformat()} - Creating stack {stackname}")
    cfn = ctx["aws"].client("cloudformation")
    with open(templatepath) as f:
        templatebody = f.read()
    args["EnvPrefix"] = ctx["args"].env
    cfn.create_stack(StackName=stackname, TemplateBody=templatebody, Parameters=[{"ParameterKey": k, "ParameterValue": v} for k,v in args.items()], **kwargs)
    ok, reason = wait_stack_status(ctx, stackname, ("CREATE_COMPLETE",), ("_FAILED", "ROLLBACK_COMPLETE"))
    if not ok:
        raise Exception(f"Stack creation failed: {reason}")
    return cfn.describe_stacks(StackName=stackname)["Stacks"][0]

def update_stack(ctx, stackname, templatepath, args, **kwargs):
    print(f"{datetime.datetime.now().isoformat()} - Updating stack {stackname}, checking for ok status first")
    ok, reason = wait_stack_status(ctx, stackname, ("_COMPLETE"), ("_FAILED", "DELETE_COMPLETE", "IMPORT_ROLLBACK_COMPLETE"))
    if not ok:
        raise Exception(f"Stack not updateable: {reason}")

    cfn = ctx["aws"].client("cloudformation")
    with open(templatepath) as f:
        templatebody = f.read()
    args["EnvPrefix"] = ctx["args"].env
    try:
        cfn.update_stack(StackName=stackname, TemplateBody=templatebody, Parameters=[{"ParameterKey": k, "ParameterValue": v} for k,v in args.items()], **kwargs)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Message"] == "No updates are to be performed.":
            print(f"{datetime.datetime.now().isoformat()} - Stack {stackname} has no updates to be performed.")
            return cfn.describe_stacks(StackName=stackname)["Stacks"][0]
        else:
            raise
    ok, reason = wait_stack_status(ctx, stackname, ("UPDATE_COMPLETE",), ("_FAILED", "UPDATE_ROLLBACK_COMPLETE"))
    if not ok:
        raise Exception(f"Stack update failed: {reason}")
    return cfn.describe_stacks(StackName=stackname)["Stacks"][0]

def upsert_stack(ctx, stackname, templatepath, args, **kwargs):
    print(f"{datetime.datetime.now().isoformat()} - Upserting stack {stackname}")
    cfn = ctx["aws"].client("cloudformation")
    try:
        cfn.describe_stacks(StackName=stackname)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ValidationError":
            return create_stack(ctx, stackname, templatepath, args, **kwargs)
        else:
            raise
    else:
        return update_stack(ctx, stackname, templatepath, args, **kwargs)

def stack_handler(name):
    def decorator(func):
        STACK_HANDLERS[name] = func
        return func
    return decorator


@stack_handler("buckets")
def stack_buckets(ctx):
    stackname = f"tehBot-{ctx['args'].env}Buckets"
    upsert_stack(ctx, stackname, "../cft/buckets.yml", {})


# @stack_handler("waf")
# def stack_waf(ctx):
#     stackname = f"tehBot-{ctx['args'].env}WAF"
#     params = {}
#     r = requests.get("http://ipecho.net/plain")
#     r.raise_for_status()
#     ip = r.text
#     params["HomeIPCIDR"] = f"{ip}/32"
#     #us-east-1 trickery :(
#     old_aws = ctx["aws"]
#     ctx["aws"] = boto3.Session(region_name="us-east-1")
#     upsert_stack(ctx, stackname, "../cft/waf.yml", params)
#     ctx["aws"] = old_aws


def invalidate_web_file_cache(ctx):
    cdn = ctx["aws"].client("cloudfront")
    distribution_id = adminutils.get_cft_resource(ctx["args"].env, "Cloudfront", "Distribution")
    print(f"{datetime.datetime.now().isoformat()} - Invalidating CloudFront cache.")
    r = cdn.create_invalidation(DistributionId=distribution_id, InvalidationBatch={"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": ctx["now"]})
    invalidation_id = r["Invalidation"]["Id"]
    while True:
        status = cdn.get_invalidation(DistributionId=distribution_id, Id=invalidation_id)["Invalidation"]["Status"]
        if status == "Completed":
            break
        print(f"{datetime.datetime.now().isoformat()} - Waiting for CloudFront cache invalidation to complete.")
        time.sleep(10)


def push_web_files(ctx):
    print(f"{datetime.datetime.now().isoformat()} - Pushing web files to bucket")
    web_bucket = adminutils.get_cft_resource(ctx["args"].env, "Buckets", "WebBucket")
    for root, dirs, files in os.walk("../web/"):
        for n in range(len(dirs)):
            if dirs[n].startswith("."):
                del dirs[n]
        for name in files:
            if not name.startswith("."):
                file_name = os.path.join(root, name)
                push_web_file(ctx, file_name, web_bucket)


def get_web_template_view(ctx):
    view = {}
    view.update(ctx["local"])
    view.update(ctx["secrets"])
    return view

def push_web_file(ctx, file_name:str, web_bucket:str):
    s3 = ctx["aws"].client("s3")
    print(f"{datetime.datetime.now().isoformat()} - Pushing file {file_name} to bucket")
    file_name = os.path.join(*(file_name.split("/")[2:]))
    view = get_web_template_view(ctx)
    out_body = jinja_env.get_template(file_name).render(**view)
    bio = io.BytesIO()
    bio.write(out_body.encode("utf-8"))
    bio.seek(0)
    if file_name.endswith(".html"):
        content_type = "text/html"
    elif file_name.endswith(".css"):
        content_type = "text/css"
    elif file_name.endswith(".js"):
        content_type = "text/javascript"
    elif file_name.endswith(".png"):
        content_type = "image/png"
    else:
        content_type = "binary/octet-stream"
        print(f"{datetime.datetime.now().isoformat()} - Unknown Content Type for {file_name}")

    s3.put_object(Bucket=web_bucket, Key=file_name, ContentType=content_type, Body=bio)

@stack_handler("cloudfront")
def stack_cloudfront(ctx):
    stackname = f"tehBot-{ctx['args'].env}Cloudfront"
    params = {}
    params["UsEastOneCertificateArn"] = ctx["local"]["us-east-1_cert_arn"]
    # params["WebACLArn"] = adminutils.get_cft_output(ctx["args"].env, "WAF", "WebACLArn", region="us-east-1")
    upsert_stack(ctx, stackname, "../cft/cloudfront.yml", params)
    push_web_files(ctx)
    invalidate_web_file_cache(ctx)

def build_lambdabuilder_docker(ctx):
    if "docker_lambdabuilder_image" not in ctx:
        print(f"{datetime.datetime.now().isoformat()} - Building lambdabuilder docker image")
        try:
            image, buildlogs = ctx["docker"].images.build(path="../docker/lambda_builder/")
        except docker.errors.BuildError:
            print("Failure with building docker image for lambda builds")
            raise
        ctx["docker_lambdabuilder_image"] = image
        print(f"{datetime.datetime.now().isoformat()} - Completed building lambdabuilder docker image")

def build_tehbot_package(ctx):
    if not ctx.get("tehbot_package_built"):
        print(f"{datetime.datetime.now().isoformat()} - Building tehbot python package")
        try:
            subprocess.check_call(shlex.split("python3 -m build ."), cwd="../packages/tehbot")
        except:
            print("Failure with building tehbot package")
            sys.exit(1)
        
        ctx["tehbot_package_built"] = True
        print(f"{datetime.datetime.now().isoformat()} - Completed building tehbot python package")

def package_lambda(ctx, lambda_name, lambda_bucket, lambda_version):
    s3 = ctx["aws"].client("s3")
    try:
        os.remove(f"../lambdas/{lambda_name}_package_{lambda_version}.zip")
    except:
        pass
    try:
        logs = ctx["docker"].containers.run(ctx["docker_lambdabuilder_image"],
            command=[f"{lambda_name}_package_{lambda_version}", "/usr/src/pylib/tehbot/tehbot-0.0.1-py3-none-any.whl"],
            volumes=[os.path.abspath(f"../lambdas/{lambda_name}")+":/usr/src/app", os.path.abspath("../packages/tehbot/dist")+":/usr/src/pylib/tehbot"],
            remove=True
        )
    except docker.errors.ContainerError:
        print(f"{datetime.datetime.now().isoformat()} - Error building {lambda_name}")
        print(logs, file=sys.stderr)
        raise

    # try:
    #     subprocess.check_call(shlex.split(f'''../lambdas/package.bash "{lambda_name}"'''))
    # except:
    #     print(f"Failure with packaging {lambda_name} Lambda")
    #     sys.exit(1)
    with open(f"../lambdas/{lambda_name}/{lambda_name}_package_{lambda_version}.zip", "rb") as f:
        s3.put_object(Bucket=lambda_bucket, Key=f"{lambda_name}_package_{lambda_version}.zip", Body=f)

@stack_handler("lambdas")
def stack_lambdas(ctx):
    build_tehbot_package(ctx)
    build_lambdabuilder_docker(ctx)
    
    lambda_bucket = adminutils.get_cft_resource(ctx["args"].env, "Buckets", "LambdaBucket")
    lambda_version = ctx["now"]
    for lambda_name in ("worker", "webhook", "cron"):
        package_lambda(ctx, lambda_name, lambda_bucket, lambda_version)

    stackname = f"tehBot-{ctx['args'].env}Lambdas"
    params = {}
    params["WebhookVersion"] = lambda_version
    params["WorkerVersion"] = lambda_version
    params["CronVersion"] = lambda_version
    params["RootDiscordUserId"] = ctx["local"]["root_discord_user_id"]
    upsert_stack(ctx, stackname, "../cft/lambdas.yml", params)

    for guildname in ctx["local"]["guilds"]:
        guildid = ctx["local"]["guilds"][guildname]
        stackname = f"tehBot-{ctx['args'].env}LambdaSchedules{guildname}"
        upsert_stack(ctx, stackname, "../cft/lambda_schedules.yml", {"GuildName": guildname, "GuildId": guildid})


@stack_handler("dynamotables")
def stack_dynamotables(ctx):
    stackname = f"tehBot-{ctx['args'].env}DynamoTables"
    upsert_stack(ctx, stackname, "../cft/dynamotables.yml", {})


@stack_handler("secrets")
def stack_secrets(ctx):
    stackname = f"tehBot-{ctx['args'].env}Secrets"
    upsert_stack(ctx, stackname, "../cft/secrets.yml", {})
    ctx["secret_arn"] = adminutils.get_cft_resource(ctx["args"].env, "Secrets", "LambdaSecrets")
    secretsmanager = ctx["aws"].client("secretsmanager")
    secretsmanager.put_secret_value(SecretId=ctx["secret_arn"], SecretString=json.dumps(ctx["secrets"]))


@stack_handler("roles")
def stack_roles(ctx):
    stackname = f"tehBot-{ctx['args'].env}Roles"
    upsert_stack(ctx, stackname, "../cft/roles.yml", {}, Capabilities=["CAPABILITY_IAM"])


@stack_handler("queues")
def stack_queues(ctx):
    stackname = f"tehBot-{ctx['args'].env}Queues"
    upsert_stack(ctx, stackname, "../cft/queues.yml", {})



def deploy_api(ctx):
    gateway_id = adminutils.get_cft_resource(ctx["args"].env, "ApiGateway", "ApiGateway")
    apigateway = ctx["aws"].client("apigateway")
    domain_name = "api." + ctx["local"]["domain"]
    if len(ctx["args"].env) > 0:
        domain_name = ctx["args"].env + "-" + domain_name
    try:
        apigateway.delete_base_path_mapping(domainName=domain_name, basePath='(none)')
    except:
        pass
    deployments = apigateway.get_deployments(restApiId=gateway_id)["items"]
    for deployment in deployments:
        stages = apigateway.get_stages(restApiId=gateway_id, deploymentId=deployment["id"])["item"]
        for stage in stages:
            apigateway.delete_stage(restApiId=gateway_id, stageName=stage["stageName"])
        apigateway.delete_deployment(restApiId=gateway_id, deploymentId=deployment["id"])

    new_deployment = apigateway.create_deployment(restApiId=gateway_id, stageName="live", stageDescription=datetime.datetime.now().isoformat())
    apigateway.create_base_path_mapping(domainName=domain_name, restApiId=gateway_id, stage="live")

@stack_handler("apigateway")
def stack_apigateway(ctx):
    build_tehbot_package(ctx)
    build_lambdabuilder_docker(ctx)

    lambda_bucket = adminutils.get_cft_resource(ctx["args"].env, "Buckets", "LambdaBucket")
    lambda_version = ctx["now"]
    for lambda_dir in glob.glob("../lambdas/api_*"):
        lambda_name = os.path.basename(lambda_dir)
        package_lambda(ctx, lambda_name, lambda_bucket, lambda_version) 
    s3 = ctx["aws"].client("s3")
    with open(f"../cft/apilambda.yml", "rb") as f:
        s3.put_object(Bucket=lambda_bucket, Key=f"apilambda_cft_{lambda_version}.yml", Body=f)
    with open(f"../cft/apimethod.yml", "rb") as f:
        s3.put_object(Bucket=lambda_bucket, Key=f"apimethod_cft_{lambda_version}.yml", Body=f)


    stackname = f"tehBot-{ctx['args'].env}ApiGateway"
    params = {}
    params["CertificateArn"] = ctx["local"]["cert_arn"]
    params["HostedZoneName"] = ctx["local"]["domain"]
    params["LambdaVersion"] = lambda_version
    params["RootDiscordUserId"] = ctx["local"]["root_discord_user_id"]
    upsert_stack(ctx, stackname, "../cft/apigateway.yml", params, Capabilities=["CAPABILITY_IAM"])
    deploy_api(ctx)



@stack_handler("backups")
def stack_backups(ctx):
    stackname = f"tehBot-{ctx['args'].env}Backups"
    #west trickery
    old_aws = ctx["aws"]
    ctx["aws"] = boto3.Session(region_name="us-west-1")
    upsert_stack(ctx, stackname, "../cft/backups.yml", {})
    ctx["aws"] = old_aws
    upsert_stack(ctx, stackname, "../cft/backups.yml", {})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("env")
    parser.add_argument("action")
    parser.add_argument("--stack", dest="stacks", action="append", default=[])
    args = parser.parse_args()

    if args.action != "upsert":
        print("Invalid action.")
        sys.exit(2)

    local = adminutils.get_local(args.env)
    secrets = adminutils.get_secrets(args.env)

    if len(args.stacks) == 0:
        stacks = ALL_STACKS
    else:
        stacks = [stack for stack in ALL_STACKS if stack in args.stacks] #stay in correct order, NOT arg order!

    ctx = {}
    ctx["now"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    ctx["local"] = local
    ctx["secrets"] = secrets
    ctx["args"] = args
    ctx["aws"] = boto3.Session()
    ctx["docker"] = docker.from_env()

    for stack in stacks:
        f = STACK_HANDLERS[stack]
        try:
            f(ctx)
        except:
            print(f"Error in stack: {stack}")
            traceback.print_exc()
            sys.exit(1)