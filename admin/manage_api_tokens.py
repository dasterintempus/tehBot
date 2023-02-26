import adminutils
import os
import argparse


if __name__ == "__main__":
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("env")
    subparsers = parser.add_subparsers(help="subcommands help", required=True)
    parser_create = subparsers.add_parser("create")
    parser_create.set_defaults(action="create")
    parser_create.add_argument("user_id")
    parser_create.add_argument("user_display_name")
    parser_create.add_argument("--guild", dest="guilds", action="append")
    
    args = parser.parse_args()

    env = args.env
    local = adminutils.get_local(env)

    api_table = adminutils.get_cft_resource(env, "DynamoTables", "ApiTable")
    os.environ["DYNAMOTABLE_API"] = api_table
    from tehbot.api.token import Token

    if args.action == "create":
        guild_ids = set()
        for guild_name in args.guilds:
            guild_ids.add(local["guilds"][guild_name])
        
        user_id = args.user_id
        user_display_name = args.user_display_name

        token = Token(user_id, user_display_name, guild_ids)
        token.save()
        print(str(token))
    else:
        print("Invalid Action", file=sys.stderr)
        sys.exit(2)
    