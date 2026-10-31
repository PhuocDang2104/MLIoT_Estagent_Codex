"""Check actual exported pixels move within scene one; save synthetic scene two frame."""
import io
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageChops, ImageStat

results={}
for name in sys.argv[1:]:
    path=Path(name)
    def frame(at):
        data=subprocess.run(['ffmpeg','-v','error','-ss',str(at),'-i',str(path),'-frames:v','1','-f','image2pipe','-vcodec','png','pipe:1'],capture_output=True,check=True).stdout
        return Image.open(io.BytesIO(data)).convert('RGB')
    a,b=frame(.5),frame(2.5)
    box=(int(a.width*.2),int(a.height*.2),int(a.width*.8),int(a.height*.6))
    difference=sum(ImageStat.Stat(ImageChops.difference(a.crop(box),b.crop(box))).mean)/3
    assert difference>1, 'Expected real crop motion, found static output'
    frame(3.5).save(Path(__file__).parent/'evidence'/(path.stem+'-scene-two.png'))
    results[path.name]={'real_pixel_motion_mean_difference':round(difference,3),'second_scene_frame_seconds':3.5}
print(json.dumps(results,indent=2))
