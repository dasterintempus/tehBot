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
import base64
import io
import jinja2
import docker
import shutil

import adminutils

ALL_STACKS = ["buckets", "cloudfront", "dynamotables", "secrets", "roles", "queues", "lambdas", "apigateway", "backups"]

STACK_HANDLERS = {}

jinja_web_env = jinja2.Environment(loader=jinja2.FileSystemLoader("../web/"))
jinja_api_env = jinja2.Environment(loader=jinja2.FileSystemLoader("../api/"))

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
            exists = False
        else:
            raise
    else:
        exists = True
    if exists is True:
        return update_stack(ctx, stackname, templatepath, args, **kwargs)
    elif exists is False:
        return create_stack(ctx, stackname, templatepath, args, **kwargs)

def delete_stack(ctx, stackname):
    cfn = ctx["aws"].client("cloudformation")
    try:
        cfn.describe_stacks(StackName=stackname)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ValidationError":
            exists = False
        else:
            raise
    else:
        exists = True
    if exists:
        print(f"{datetime.datetime.now().isoformat()} - Deleting stack {stackname}")
        cfn.delete_stack(StackName=stackname)
        ok, reason = wait_stack_status(ctx, stackname, ("DELETE_COMPLETE",), ("_FAILED", "_ROLLBACK_"))
        if not ok:
            raise Exception(f"Stack update failed: {reason}")
    else:
        print(f"{datetime.datetime.now().isoformat()} - Told to delete Stack {stackname} but it does not exist")

def stack_handler(name):
    def decorator(func):
        STACK_HANDLERS[name] = func
        return func
    return decorator


@stack_handler("buckets")
def stack_buckets(ctx):
    stackname = f"tehBot-{ctx['args'].env}Buckets"
    if ctx["args"].action == "upsert":
        upsert_stack(ctx, stackname, "../cft/buckets.yml", {})
    elif ctx["args"].action == "delete":
        delete_stack(ctx, stackname)



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
    out_body = jinja_web_env.get_template(file_name).render(**view)
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
    if ctx["args"].action == "upsert":
        params = {}
        params["UsEastOneCertificateArn"] = ctx["local"]["us-east-1_cert_arn"]
        params["HostedZoneName"] = ctx["local"]["domain"]
        # params["WebACLArn"] = adminutils.get_cft_output(ctx["args"].env, "WAF", "WebACLArn", region="us-east-1")
        upsert_stack(ctx, stackname, "../cft/cloudfront.yml", params)
        push_web_files(ctx)
        # invalidate_web_file_cache(ctx)
    elif ctx["args"].action == "delete":
        delete_stack(ctx, stackname)

def build_lambdabuilder_docker(ctx):
    dockerc: docker.DockerClient = ctx["docker"]
    if "docker_lambdabuilder_image" not in ctx:
        print(f"{datetime.datetime.now().isoformat()} - Building lambdabuilder docker image")
        try:
            image, buildlogs = dockerc.images.build(path="../docker/lambda_builder/")
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
        deps_path = "../lambdas/shared_deps_" + ctx["now"].replace(":","_")
        if os.path.exists(deps_path):
            shutil.rmtree(deps_path) #clear the shared deps dir if it already exists.
        os.mkdir(deps_path) #remake the folder

def package_lambda(ctx, lambda_name, lambda_bucket, lambda_version):
    dockerc: docker.DockerClient = ctx["docker"]
    s3 = ctx["aws"].client("s3")

    try:
        os.remove(f"../lambdas/{lambda_name}/{lambda_name}_package_{lambda_version}.zip")
    except:
        pass

    try:
        deps_path = "../lambdas/shared_deps_" + ctx["now"].replace(":","_")
        logs = dockerc.containers.run(ctx["docker_lambdabuilder_image"],
            command=[f"{lambda_name}_package_{lambda_version}", "/usr/src/pylib/tehbot/tehbot-0.0.1-py3-none-any.whl"],
            volumes=[
                os.path.abspath(f"../lambdas/{lambda_name}")+":/usr/src/app",
                os.path.abspath("../packages/tehbot/dist")+":/usr/src/pylib/tehbot",
                os.path.abspath(deps_path)+":/usr/src/shared_deps"
            ],
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
    
    os.remove(f"../lambdas/{lambda_name}/{lambda_name}_package_{lambda_version}.zip")

"""aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 105824585986.dkr.ecr.us-east-2.amazonaws.com"""
def package_heavy_lambda(ctx, lambda_name, lambda_version):
    shutil.copy("../packages/tehbot/dist/tehbot-0.0.1-py3-none-any.whl", "../docker/heavyworker/tehbot-0.0.1-py3-none-any.whl")
    dockerc: docker.DockerClient = ctx["docker"]
    try:
        image, buildlogs = dockerc.images.build(path="../docker/heavyworker/")
    except docker.errors.BuildError:
        print(f"Failure with building docker image for heavy lambda {lambda_name}")
        raise
    image.tag(ctx['local']['heavyworker_ecrimage_uri'], lambda_version)
    response = dockerc.images.push(ctx['local']['heavyworker_ecrimage_uri'], lambda_version, stream=True, decode=True)
    for responserow in response:
        if "error" in responserow:
            print(f"Failure with pushing docker image for heavy lambda {lambda_name}")
            print(responserow["error"])
            sys.exit(1)

@stack_handler("lambdas")
def stack_lambdas(ctx):
    if ctx["args"].action == "upsert":
        lambda_bucket = adminutils.get_cft_resource(ctx["args"].env, "Buckets", "LambdaBucket")
        if ctx["args"].lambda_version is None:
            build_tehbot_package(ctx)
            build_lambdabuilder_docker(ctx)
            
            lambda_version = ctx["now"]
            for lambda_name in ("webhook", "cron", "worker"):
                package_lambda(ctx, lambda_name, lambda_bucket, lambda_version)
            for heavy_lambda_name in ("heavyworker",):
                package_heavy_lambda(ctx, heavy_lambda_name, lambda_version)
            time.sleep(1)

        else:
            lambda_version = ctx["args"].lambda_version
        params = {}
        params["WebhookVersion"] = lambda_version
        params["WorkerVersion"] = lambda_version
        params["HeavyWorkerDockerImageUri"] = f"{ctx['local']['heavyworker_ecrimage_uri']}:{lambda_version}"
        params["CronVersion"] = lambda_version
        params["RootDiscordUserId"] = ctx["local"]["root_discord_user_id"]
        params["HostedZoneName"] = ctx["local"]["domain"]
        stackname = f"tehBot-{ctx['args'].env}Lambdas"
        upsert_stack(ctx, stackname, "../cft/lambdas.yml", params)

        # for guildname in ctx["local"]["guilds"]:
        #     guildid = ctx["local"]["guilds"][guildname]
        #     stackname = f"tehBot-{ctx['args'].env}LambdaSchedules{guildname}"
        #     upsert_stack(ctx, stackname, "../cft/lambda_schedules.yml", {"GuildName": guildname, "GuildId": guildid})
        
    elif ctx["args"].action == "delete":
        # for guildname in ctx["local"]["guilds"]:
        #     guildid = ctx["local"]["guilds"][guildname]
        #     stackname = f"tehBot-{ctx['args'].env}LambdaSchedules{guildname}"
        #     delete_stack(ctx, stackname)
        stackname = f"tehBot-{ctx['args'].env}Lambdas"
        delete_stack(ctx, stackname)


@stack_handler("dynamotables")
def stack_dynamotables(ctx):
    stackname = f"tehBot-{ctx['args'].env}DynamoTables"
    if ctx["args"].action == "upsert":
        upsert_stack(ctx, stackname, "../cft/dynamotables.yml", {})
    elif ctx["args"].action == "delete":
        delete_stack(ctx, stackname)


@stack_handler("secrets")
def stack_secrets(ctx):
    stackname = f"tehBot-{ctx['args'].env}Secrets"
    if ctx["args"].action == "upsert":
        upsert_stack(ctx, stackname, "../cft/secrets.yml", {})
        ctx["secret_arn"] = adminutils.get_cft_resource(ctx["args"].env, "Secrets", "LambdaSecrets")
        secretsmanager = ctx["aws"].client("secretsmanager")
        secretsmanager.put_secret_value(SecretId=ctx["secret_arn"], SecretString=json.dumps(ctx["secrets"]))
    elif ctx["args"].action == "delete":
        delete_stack(ctx, stackname)


@stack_handler("roles")
def stack_roles(ctx):
    stackname = f"tehBot-{ctx['args'].env}Roles"
    if ctx["args"].action == "upsert":
        upsert_stack(ctx, stackname, "../cft/roles.yml", {}, Capabilities=["CAPABILITY_IAM"])
    elif ctx["args"].action == "delete":
        delete_stack(ctx, stackname)


@stack_handler("queues")
def stack_queues(ctx):
    stackname = f"tehBot-{ctx['args'].env}Queues"
    if ctx["args"].action == "upsert":
        params = {}
        # params["DaemonRoleArn"] = ctx["local"]["daemon_role_arn"]
        upsert_stack(ctx, stackname, "../cft/queues.yml", params)
    elif ctx["args"].action == "delete":
        delete_stack(ctx, stackname)


def deploy_api(ctx):
    api_id = adminutils.get_cft_resource(ctx["args"].env, "ApiGateway", "ApiGateway")
    apigateway = ctx["aws"].client("apigatewayv2")
    domain_name = "api." + ctx["local"]["domain"]
    if len(ctx["args"].env) > 0:
        domain_name = ctx["args"].env + "-" + domain_name
    try:
        mappings = apigateway.get_api_mappings(DomainName=domain_name)["Items"]
        for mapping in mappings:
            if mapping["ApiId"] == api_id:
                apigateway.delete_api_mapping(ApiMappingId=mapping["ApiMappingId"], DomainName=domain_name)
    except:
        pass

    stages = apigateway.get_stages(ApiId=api_id)["Items"]
    for stage in stages:
        apigateway.delete_stage(ApiId=api_id, StageName=stage["StageName"])
    # deployments = apigateway.get_deployments(ApiId=api_id)["Items"]
    # for deployment in deployments:
    #     apigateway.delete_deployment(ApiId=api_id, deploymentId=deployment["DeploymentId"])

    new_stage = apigateway.create_stage(ApiId=api_id, StageName="live")
    apigateway.create_api_mapping(DomainName=domain_name, ApiId=api_id, Stage="live")

def delete_api_deployment(ctx):
    api_id = adminutils.get_cft_resource(ctx["args"].env, "ApiGateway", "ApiGateway")
    apigateway = ctx["aws"].client("apigatewayv2")
    domain_name = "api." + ctx["local"]["domain"]
    if len(ctx["args"].env) > 0:
        domain_name = ctx["args"].env + "-" + domain_name
    apigateway.delete_stage(ApiId=api_id, StageName="live")
    mappings = apigateway.get_api_mappings(DomainName=domain_name)["Items"]
    try:
        for mapping in mappings:
            if mapping["ApiId"] == api_id:
                apigateway.delete_api_mapping(ApiMappingId=mapping["ApiMappingId"], DomainName=domain_name)
    except:
        pass

@stack_handler("apigateway")
def stack_apigateway(ctx):
    gateway_stackname = f"tehBot-{ctx['args'].env}ApiGateway"
    components_stackname = f"tehBot-{ctx['args'].env}ApiComponents"
    if ctx["args"].action == "upsert":
        lambda_bucket = adminutils.get_cft_resource(ctx["args"].env, "Buckets", "LambdaBucket")
        if ctx["args"].lambda_version is None:
            build_tehbot_package(ctx)
            build_lambdabuilder_docker(ctx)

            lambda_version = ctx["now"]
            for lambda_dir in glob.glob("../lambdas/api_*"):
                lambda_name = os.path.basename(lambda_dir)
                package_lambda(ctx, lambda_name, lambda_bucket, lambda_version) 
        else:
            lambda_version = ctx["args"].lambda_version
        
        

        s3 = ctx["aws"].client("s3")
        with open(f"../cft/apilambda.yml", "rb") as f:
            s3.put_object(Bucket=lambda_bucket, Key=f"apilambda_cft_{lambda_version}.yml", Body=f)
        with open(f"../cft/apimethod.yml", "rb") as f:
            s3.put_object(Bucket=lambda_bucket, Key=f"apimethod_cft_{lambda_version}.yml", Body=f)
        time.sleep(1)

        components_stackname = f"tehBot-{ctx['args'].env}ApiComponents"
        params = {}
        # params["CertificateArn"] = ctx["local"]["cert_arn"]
        params["HostedZoneName"] = ctx["local"]["domain"]
        params["LambdaVersion"] = lambda_version
        params["RootDiscordUserId"] = ctx["local"]["root_discord_user_id"]
        upsert_stack(ctx, components_stackname, "../cft/apicomponents.yml", params)#, Capabilities=["CAPABILITY_IAM"])

        #Render OpenAPI template
        template = jinja_api_env.get_template("openapi.yaml")
        view = {}
        view.update(ctx["local"])
        view["env_prefix"] = ctx["args"].env
        sanitized_view = {}
        sanitized_view.update(view)
        cfn = boto3.client("cloudformation")
        resources = cfn.describe_stack_resources(StackName=components_stackname)["StackResources"]
        for resource in resources:
            if resource["ResourceType"] == "AWS::CloudFormation::Stack":
                nested_stack = cfn.describe_stacks(StackName=resource["PhysicalResourceId"])["Stacks"][0]
                nested_lambda_name = [out["OutputValue"] for out in nested_stack["Outputs"] if out["OutputKey"] == "LambdaName"][0]
                nested_lambda_arn = [out["OutputValue"] for out in nested_stack["Outputs"] if out["OutputKey"] == "LambdaArn"][0]
                view[f"lambda_{nested_lambda_name}"] = f"arn:aws:apigateway:us-east-2:lambda:path/2015-03-31/functions/{nested_lambda_arn}/invocations"
                sanitized_view[f"lambda_{nested_lambda_name}"] = "REDACTED"
        lambda_stackname = f"tehBot-{ctx['args'].env}Lambdas"
        stack = cfn.describe_stacks(StackName=lambda_stackname)["Stacks"][0]
        webhook_lambda_arn = [out["OutputValue"] for out in stack["Outputs"] if out["OutputKey"] == "WebhookLambdaArn"][0]
        view["lambda_discord_webhook"] = f"arn:aws:apigateway:us-east-2:lambda:path/2015-03-31/functions/{webhook_lambda_arn}/invocations"
        sanitized_view["lambda_discord_webhook"] = "REDACTED"

        openapi_bodystr = template.render(**view)
        openapi_body = io.BytesIO()
        openapi_body.write(openapi_bodystr.encode())
        openapi_body.seek(0)
        s3.put_object(Bucket=lambda_bucket, Key=f"openapi_{lambda_version}.yml", Body=openapi_body)
        # openapi_body.seek(0)
        # time.sleep(0.1)
        # s3.put_object_acl(Bucket=lambda_bucket, Key=f"openapi_{lambda_version}.yml", ACL="public-read")

        #push docs!
        web_bucket = adminutils.get_cft_resource(ctx["args"].env, "Buckets", "WebBucket")
        openapi_sanitized_bodystr = template.render(**sanitized_view)
        openapi_sanitized_body = io.BytesIO()
        openapi_sanitized_body.write(openapi_sanitized_bodystr.encode())
        openapi_sanitized_body.seek(0)
        # s3.put_object(Bucket=lambda_bucket, Key=f"openapi_{lambda_version}.yml", Body=openapi_sanitized_body)
        s3.put_object(Bucket=web_bucket, Key=f"docs/openapi_{lambda_version}.yml", ContentType="text/plain", Body=openapi_sanitized_body)
        view["openapi_url"] = f"{ctx['local']['tehbot_web_url']}/docs/openapi_{lambda_version}.yml"
        docstemplate = jinja_api_env.get_template("docs.html")
        apidocs_bodystr = docstemplate.render(**view)
        apidocs_body = io.BytesIO()
        apidocs_body.write(apidocs_bodystr.encode())
        apidocs_body.seek(0)
        s3.put_object(Bucket=web_bucket, Key=f"docs/redoc.html", ContentType="text/html", Body=apidocs_body)
        
        params = {}
        params["CertificateArn"] = ctx["local"]["cert_arn"]
        params["HostedZoneName"] = ctx["local"]["domain"]
        params["OpenApiFileKey"] = f"openapi_{lambda_version}.yml"
        # params["LambdaVersion"] = lambda_version
        # params["RootDiscordUserId"] = ctx["local"]["root_discord_user_id"]
        upsert_stack(ctx, gateway_stackname, "../cft/apigateway.yml", params, Capabilities=["CAPABILITY_IAM"])
        # deploy_api(ctx)

    elif ctx["args"].action == "delete":
        # delete_api_deployment(ctx)
        delete_stack(ctx, gateway_stackname)
        delete_stack(ctx, components_stackname)


@stack_handler("backups")
def stack_backups(ctx):
    stackname = f"tehBot-{ctx['args'].env}Backups"
    #west trickery
    old_aws = ctx["aws"]
    ctx["aws"] = boto3.Session(region_name="us-west-1")
    if ctx["args"].action == "upsert":
        upsert_stack(ctx, stackname, "../cft/backups.yml", {})
    elif ctx["args"].action == "delete":
        upsert_stack(ctx, stackname)
    ctx["aws"] = old_aws
    if ctx["args"].action == "upsert":
        upsert_stack(ctx, stackname, "../cft/backups.yml", {})
    elif ctx["args"].action == "delete":
        upsert_stack(ctx, stackname)
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("env")
    parser.add_argument("action")
    parser.add_argument("--stack", dest="stacks", action="append", default=[])
    parser.add_argument("--lambda-version", dest="lambda_version", action="store", default=None)
    args = parser.parse_args()

    if args.action not in ("upsert", "delete"):
        print("Invalid action.")
        sys.exit(2)

    local = adminutils.get_local(args.env)
    secrets = adminutils.get_secrets(args.env)

    if len(args.stacks) == 0:
        stacks = ALL_STACKS
    else:
        stacks = [stack for stack in ALL_STACKS if stack in args.stacks] #stay in correct order, NOT arg order!

    if args.action == "delete":
        stacks.reverse()

    ctx = {}
    ctx["now"] = datetime.datetime.now().strftime("%Y-%m-%dT%H_%M_%S")
    ctx["local"] = local
    ctx["secrets"] = secrets
    ctx["args"] = args
    ctx["aws"] = boto3.Session(region_name="us-east-2")
    ctx["docker"] = docker.from_env()

    for stack in stacks:
        f = STACK_HANDLERS[stack]
        try:
            f(ctx)
        except:
            print(f"Error in stack: {stack}")
            traceback.print_exc()
            sys.exit(1)

    deps_path = "../lambdas/shared_deps_" + ctx["now"].replace(":","_")
    if os.path.exists(deps_path):
        shutil.rmtree(deps_path) #clear the shared deps dir when done.
    if "apigateway" in stacks or "cloudfront" in stacks:
        invalidate_web_file_cache(ctx)
