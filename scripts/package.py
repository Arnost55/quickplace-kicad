"""Build manual-install and KiCad PCM plugin ZIPs."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json

root=Path(__file__).resolve().parents[1]
source=root/'quickplace'
dist=root/'dist'
dist.mkdir(exist_ok=True)
plugin_files=sorted(p for p in source.iterdir() if p.is_file() and p.suffix in ('.py','.png'))
metadata=json.loads((root/'metadata.json').read_text(encoding='utf-8'))

# Manual Action Plugin folder for the pcbnew scripting/plugins directory.
manual=dist/'quickplace-kicad10.zip'
with ZipFile(manual,'w',ZIP_DEFLATED) as archive:
    for file in plugin_files:
        archive.write(file,arcname=f'quickplace/{file.name}')

# PCM ZIP has the mandated archive-root paths and excludes repository download_* fields.
pcm_metadata=json.loads(json.dumps(metadata))
for version in pcm_metadata['versions']:
    for key in ('download_url','download_sha256','download_size','install_size'):
        version.pop(key,None)
pcm=dist/'quickplace-pcm.zip'
with ZipFile(pcm,'w',ZIP_DEFLATED) as archive:
    archive.writestr('metadata.json',json.dumps(pcm_metadata,indent=2)+'\n')
    for file in plugin_files:
        archive.write(file,arcname=f'plugins/{file.name}')
    archive.write(source/'icon.png',arcname='resources/icon.png')

print(f'Manual Action Plugin: {manual}')
print(f'KiCad PCM package: {pcm}')
