from steam.webapi import WebAPI

class SteamAPIException(Exception):
    pass

def api(authtoken):
    try:
        steamapi = WebAPI(authtoken)
    except:
        raise SteamAPIException()
    return steamapi