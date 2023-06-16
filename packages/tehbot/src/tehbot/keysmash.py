import collections
import math

Vector = collections.namedtuple("Vector", ["x", "y"])
KeyScore = collections.namedtuple("KeyScore", ["v", "shift"])

KEYBOARD_LAYOUT = [
    {
        "offset": Vector(0, 0),
        "chars": ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
        "shift": False
    },
    {
        "offset": Vector(0, 0),
        "chars": ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+"],
        "shift": True
    },
    {
        "offset": Vector(4/3.0, 1),
        "chars": ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
        "shift": False
    },
    {
        "offset": Vector(4/3.0, 1),
        "chars": ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "|"],
        "shift": True
    },
    {
        "offset": Vector(1.5, 2),
        "chars": ["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'"],
        "shift": False
    },
    {
        "offset": Vector(1.5, 2),
        "chars": ["A", "S", "D", "F", "G", "H", "J", "K", "L", ":", '"'],
        "shift": True
    },
    {
        "offset": Vector(2, 3),
        "chars": ["z", "x", "c", "v", "b", "n", "m", ",", ".", "/"],
        "shift": False
    },
    {
        "offset": Vector(2, 3),
        "chars": ["Z", "X", "C", "V", "B", "N", "M", "<", ">", "?"],
        "shift": True
    },
    {
        "offset": Vector(7.5, 4),
        "chars": [" "],
        "shift": False
    }
]

KEYBOARD_MAPPING = {}

for entry in KEYBOARD_LAYOUT:
    for n, char in enumerate(entry["chars"]):
        v = Vector(entry["offset"].x+n, entry["offset"].y)
        score = KeyScore(v, entry["shift"])
        KEYBOARD_MAPPING[char] = score

DEFAULT_SCORE = KeyScore(Vector(7.5, 2.5), False)

def score_pair(a, b):
    try:
        ascore = KEYBOARD_MAPPING[a]
    except:
        ascore = DEFAULT_SCORE
    try:
        bscore = KEYBOARD_MAPPING[b]
    except:
        bscore = DEFAULT_SCORE
    dx = abs(ascore.v.x - bscore.v.x)
    dy = abs(ascore.v.y - bscore.v.y)
    score = dx + (dy*1.75)
    if ascore.shift != bscore.shift:
        score = score * 1.1
    return score

def score_keysmash(s):
    if len(s) < 2:
        raise ValueError
    last = s[0]
    score = -len(s) * 0.25
    for c in s[1:]:
        score += score_pair(last, c)
        last = c
    if score < 0:
        return 0
    return math.floor(score)

if __name__ == "__main__":
    import sys
    print(score_keysmash(sys.argv[1]))