"""Measure synthetic source frequencies in the actual encoded MP4 (not listening QA)."""
import array
import cmath
import json
from pathlib import Path
import subprocess
import sys


def measure(path):
    result=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-vn','-f','s16le','-ac','1','-ar','8000','pipe:1'],capture_output=True,check=True)
    samples=array.array('h');samples.frombytes(result.stdout)
    if sys.byteorder!='little':samples.byteswap()
    def amplitude(frequency,start,end):
        signal=samples[int(start*8000):int(end*8000)]
        return 2*abs(sum(v*cmath.exp(-2j*cmath.pi*frequency*i/8000) for i,v in enumerate(signal)))/len(signal)
    music_under=amplitude(220,.2,.8);music_between=amplitude(220,1.5,2.2)
    voice_one=amplitude(440,.2,.8);wrong_one=amplitude(660,.2,.8)
    voice_two=amplitude(660,3.2,3.8);wrong_two=amplitude(440,3.2,3.8)
    assert .12<music_under/music_between<.30,(music_under,music_between)
    assert voice_one>1000 and voice_two>1000
    assert wrong_one<voice_one*.05 and wrong_two<voice_two*.05
    return {'music_under_voice':round(music_under,2),'music_between_voice':round(music_between,2),'duck_ratio':round(music_under/music_between,3),'scene_one_440Hz':round(voice_one,2),'scene_two_660Hz':round(voice_two,2),'wrong_scene_frequency_below_5_percent':True}

if __name__=='__main__':
    print(json.dumps({Path(p).name:measure(Path(p)) for p in sys.argv[1:]},indent=2))
