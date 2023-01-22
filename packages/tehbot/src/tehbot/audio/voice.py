from io import BytesIO
import sys
import wave
import random
import copy
import hashlib
from gensound import Sine, Gain, Sawtooth, Silence, Triangle, WhiteNoise, Square, ADSR

WAVES = [Sine, Sawtooth, Sawtooth, Square, Triangle]
LETTERS = list("abcdefghijklmnopqrstuvwxyz")

def scale_byte(b, lower, upper):
    return round((b/255.0 * (upper-lower)) + lower)

def scale_byte_float(b, lower, upper):
    return (b/255.0 * (upper-lower)) + lower

class Voice:
    @staticmethod
    def generate_from_hash(bs):
        bs = list(bytearray(bs))
        adsrparams = [
            scale_byte(bs[0], 20.0, 40.0),
            scale_byte(bs[1], 15.0, 30.0),
            scale_byte_float(bs[2], 0.2, 0.8),
            scale_byte(bs[3], 15.0, 30.0)
        ]
        wave = WAVES[int(round(scale_byte(bs[4], 0, len(WAVES)-1)))]
        durations = [
            sum(adsrparams) + scale_byte(bs[5], 15.0, 35.0)
        ]
        durations.append(durations[0] + scale_byte(bs[6], 10.0, 25.0))
        durations.append(durations[1] + scale_byte(bs[7], 10.0, 25.0))
        gain = scale_byte_float(bs[8], -4.0, -6.0)
        freqparams = [
            scale_byte(bs[9], 160, 200),
            scale_byte(bs[10], 8, 15)
        ]
        r = random.Random(bs[11])
        letters = copy.copy(LETTERS)
        r.shuffle(letters)
        print(adsrparams, wave, durations, gain, freqparams, letters)
        return Voice(adsrparams, wave, durations, gain, freqparams, letters)

    def __init__(self, adsrparams, wave, durations, gain, freqparams, letters):
        self.adsr = ADSR(*adsrparams)
        self.wave = wave
        self.durations = durations
        self.gain = gain
        self.freqparams = freqparams
        self.letters = letters
    
    def _generate_blip(self, c):
        num = self.letters.index(c)
        return self.wave(frequency=self.freqparams[0]+(self.freqparams[1]*num), duration=self.durations[0]) * self.adsr

    def _process(self, line):
        wav = Silence(self.durations[2]*len(line))
        wavpos = 0.0
        for c in line:
            if c in self.letters:
                wav[wavpos:wavpos+self.durations[0]] = self._generate_blip(c) * Gain(self.gain)
                wavpos += self.durations[1]
            else:
                wavpos += self.durations[2]
        return wav

    def say(self, line):
        line = line.lower()
        wav = self._process(line)
        bio = BytesIO()
        a = wav.realise(44100)
        a._prepare_buffer(2, 0.9)
        w = wave.open(bio, "wb")
        w.setnchannels(a.num_channels)
        w.setsampwidth(a.byte_width)
        w.setframerate(a.sample_rate)
        w.setnframes(a.length)
        w.writeframes(a.buffer)
        w.close()
        bio.seek(0)
        return bio

if __name__ == "__main__":
    line = sys.argv[1]
    userid = sys.argv[2]
    outfile = sys.argv[3]
    v = Voice.generate_from_hash(hashlib.sha256(userid.encode("utf-8")).digest())
    with open(outfile, "wb") as f:
        f.write(v.say(line).read())
