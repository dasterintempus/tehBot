import adminutils
import os

if __name__ == "__main__":
    import sys
    
    env = sys.argv[1]
    local = adminutils.get_local(env)

    quotes_table = adminutils.get_cft_resource(sys.argv[1], "DynamoTables", "QuotesTable")
    os.environ["DYNAMOTABLE_QUOTES"] = quotes_table
    from tehbot.quotes import Quote

    guild_name = sys.argv[2]
    guild_id = local["guilds"][guild_name]
    
    quotes = []
    quotes.extend(Quote.find_all(guild_id))

    with open(sys.argv[3]) as f:
        for line in f:
            key = line.split(":", 1)[0]
            tags = set(key.split("_")[:-1])
            name = key.split("_")[-1]
            url = line.split("'", 2)[1].strip()
            q = Quote(url, name, tags, guild_id)
            count = 0
            while True:
                name_ok = q.name not in [quote.name for quote in quotes]
                if not name_ok:
                    count += 1
                    q.name = f"{q.name}{count}"
                else:
                    break
            quotes.append(q)
            q.save()
            print("added", q.name, q.url, q.tags)