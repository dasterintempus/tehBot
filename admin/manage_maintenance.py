import boto3
import json
import sys
import adminutils

if __name__ == "__main__":
    env = sys.argv[1]
    local = adminutils.get_local(env)
    if sys.argv[2] == "start":
        message = {"_meta": "maintenance-start"}
        if len(sys.argv) > 3:
            message["msg"] = sys.argv[3]
    elif sys.argv[2] == "end":
        message = {"_meta": "maintenance-end"}
    else:
        print("Invalid args.")
        sys.exit(2)
    
    queue_url = adminutils.get_cft_resource(env, "Queues", "InteractionQueue")

    sqs = boto3.client("sqs")
    
    for guildname in local["guilds"]:
        guildid = local["guilds"][guildname]
        message["guildid"] = guildid
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))