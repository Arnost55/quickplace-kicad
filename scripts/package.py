"""Build a versioned, offline-installable Action Plugin ZIP."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
dest=root/'dist'/'quickplace-kicad10.zip'
dest.parent.mkdir(exist_ok=True)
with ZipFile(dest,'w',ZIP_DEFLATED) as archive:
    for file in sorted((root/'quickplace').glob('*')):
        if file.is_file() and file.suffix in ('.py','.png'):
            archive.write(file,arcname=f'quickplace/{file.name}')
print(dest)
