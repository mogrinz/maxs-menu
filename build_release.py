"""Build a clean, reproducible installation ZIP; runtime data is never included."""
import hashlib
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
FILES={'app.py','backups.py','build_release.py','configure.py','hotspot_service.py',
       'install_network_service.py','install_service.py','models.py','network_client.py',
       'network_service.py','prepare_update.py','reset_admin.py','requirements.txt',
       'run.sh','setup.sh','upgrade.sh','sample_menu.json','LICENSE','.gitignore'}
DIRECTORIES={'static','templates','tests','.github'}


def build(output):
    output=Path(output).resolve()
    if output.suffix!='.zip' or output.is_relative_to(ROOT):
        raise ValueError('Write the .zip outside the source directory.')
    selected=[]
    for file in ROOT.rglob('*'):
        relative=file.relative_to(ROOT)
        if file.is_file() and (relative.as_posix() in FILES or (len(relative.parts)==1 and file.suffix=='.md') or relative.parts[0] in DIRECTORIES):
            if file.is_symlink():raise ValueError('Release inputs must not be symlinks: '+str(relative))
            if '__pycache__' in relative.parts or file.suffix in {'.pyc','.log'}:continue
            if relative.parts[0] in DIRECTORIES and file.suffix not in {'.py','.js','.css','.html','.svg','.ttf','.txt','.md','.yml','.yaml'}:continue
            selected.append((relative.as_posix(),file.read_bytes()))
    if not FILES.issubset({name for name,_ in selected}):raise ValueError('Required release source is missing.')
    selected.sort()
    manifest=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in selected)
    selected.append(('SHA256SUMS',manifest.encode()))
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in selected:
            info=zipfile.ZipInfo('maxs-menu/'+name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=((0o100755 if name.endswith('.sh') else 0o100644)<<16)
            archive.writestr(info,data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():raise ValueError('Archive integrity check failed.')
    return output,len(selected)


if __name__=='__main__':
    path,count=build(sys.argv[1] if len(sys.argv)>1 else ROOT.parent/'maxs-menu.zip')
    print(str(path)+' ('+str(count)+' files)')
    print('SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest())
