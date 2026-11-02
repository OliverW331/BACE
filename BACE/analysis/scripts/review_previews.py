"""Render final-size PDF proofs and colour-vision/grayscale QA previews."""
from pathlib import Path
import sys
import numpy as np
import pymupdf
from PIL import Image
from colorspacious import cspace_convert
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis_data import OUT, save_json, sha
review=OUT/'review';review.mkdir(exist_ok=True)
manifest=[]
for path in sorted((OUT/'figures').rglob('*.pdf')):
    with pymupdf.open(path) as doc:
        pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),alpha=False)
    rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)/255
    Image.fromarray((rgb*255).astype('uint8')).save(review/(path.stem+'.png'))
    for kind in ['deuteranomaly','protanomaly']:
        transformed=cspace_convert(rgb,{'name':'sRGB1+CVD','cvd_type':kind,'severity':100},'sRGB1')
        Image.fromarray((np.clip(transformed,0,1)*255).astype('uint8')).save(review/(path.stem+'__'+kind+'.png'))
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    luminance=linear@np.array([.2126,.7152,.0722])
    gray=np.where(luminance<=.0031308,luminance*12.92,1.055*luminance**(1/2.4)-.055)
    Image.fromarray((np.clip(gray,0,1)*255).astype('uint8')).save(review/(path.stem+'__grayscale.png'))
    manifest.append({'figure':path.stem,'pdf_sha256':sha(path),'proof_pixels_per_pt':1.6,'cvd_severity':100})
save_json(review/'preview_manifest.json',manifest)
print(f'Created final PDF proofs and colour-vision previews for {len(manifest)} figures.')
