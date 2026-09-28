"""Contact sheet of downloaded images (for eyeballing): python contact_sheet.py out.jpg [type/slug ...]"""
import sys
from PIL import Image, ImageDraw
from common import IMAGES
out=sys.argv[1]; pats=sys.argv[2:]
files=sorted(p for p in IMAGES.rglob("*.jpg") if not pats or any(x in p.as_posix() for x in pats))[:60]
W=200; cols=6; rows=(len(files)+cols-1)//cols
sheet=Image.new("RGB",(cols*W,rows*(W+16)),"white"); d=ImageDraw.Draw(sheet)
for i,f in enumerate(files):
    im=Image.open(f); im.thumbnail((W,W)); x=(i%cols)*W; y=(i//cols)*(W+16)
    sheet.paste(im,(x,y)); d.text((x+2,y+W+2),f"{f.parent.name[:18]}/{f.stem}",fill="black")
sheet.save(out,quality=80)
