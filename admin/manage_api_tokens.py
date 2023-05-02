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
    parser_create.add_argument("--perm", dest="perms", action="append")
    
    args = parser.parse_args()

    env = args.env
    local = adminutils.get_local(env)

    env_guilds = adminutils.get_env_guilds(args.env)

    api_table = adminutils.get_cft_resource(env, "DynamoTables", "ApiTable")
    os.environ["DYNAMOTABLE_API"] = api_table
    from tehbot.api.token import Token

    if args.action == "create":
        guild_perms = {}
        for guild_name in args.guilds:
            for guild_entry in env_guilds:
                if guild_name == guild_entry[0]:
                    guild_perms[guild_entry[1]] = set(args.perms)
        
        user_id = args.user_id
        user_display_name = args.user_display_name

        token = Token(user_id, user_display_name, guild_perms)
        token.save()
        print(str(token))
    else:
        print("Invalid Action", file=sys.stderr)
        sys.exit(2)
    