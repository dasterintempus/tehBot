from tehbot.quotes import Quote, Alias
import random
import traceback
import random
from tehbot.controllerlayout import Game
from tehbot.util import CONTEXT

NUMPAD = [str(n) for n in range(1,10)]
MOTIONS = ["412", "214", "236", "623", "41236", "63214", "612346", "22", "66", "360", "720", "623", "421"]
MODIFIERS = ["cr.", "st.", "j.", "c.", "f.", "dl."]
JOINERS = [" > ", " -> ", ", ", " ~ "]

def get_combo_atom(R: random.Random, game: Game):
    if R.randint(1, 10) >= 7:
        out = R.choice(MOTIONS)
    else:
        out = R.choice(NUMPAD)
    if R.randint(1, 10) >= 7:
        out = out + " " + R.choice(MODIFIERS)
    out = out + R.choice(game.combo_inputs)
    return out

def generate_combo(R: random.Random, guild_id: str, username: str):
    game = R.choice(Game.find_all_with_combos(guild_id))
    
    combo = f"{username} is playing {game.name} and has developed a new combo:\n"
    for n in range(int(R.triangular(2,7))):
        if n > 0:
            combo = combo + R.choice(JOINERS)
        combo = combo + get_combo_atom(R, game)
    return combo

def combo_display(body: dict):
    username = body["member"]["nick"]
    if username is None:
        username = body["member"]["user"]["global_name"]
    guild_id = body["guild_id"]
    R = random.Random()
    
    content = generate_combo(R, guild_id, username)

    return True, {"json": {"content": content}}

if __name__ == "__main__":
    import sys
    username = "TEST"
    R = random.Random(sys.argv[2])
    content = generate_combo(R, sys.argv[1])
    print(content)