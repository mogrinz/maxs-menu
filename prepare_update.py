"""Back up the existing project and install code without replacing live data."""
from datetime import datetime
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

source=Path(__file__).resolve().parent
target=Path(sys.argv[1] if len(sys.argv)>1 else Path.home()/'maxs-menu').resolve()
if os.geteuid()==0:
    raise SystemExit('Run the update as your regular Pi user, without sudo.')
if source==target:
    raise SystemExit('Extract the release into a separate temporary directory before upgrading.')
if target.exists() and (target/'data/recovery-admin.json').exists():
    raise SystemExit('Private prototype detected. This release requires a fresh installation; export menu content separately if needed.')
if target.exists() and (not (target/'app.py').is_file() or target.stat().st_uid!=os.getuid()):
    raise SystemExit('The target must be your existing menu project, owned by your Pi user.')
if target.is_relative_to(source):
    raise SystemExit('The target must be outside the release folder.')
if shutil.which('systemctl'):
    active=subprocess.run(['systemctl','is-active','--quiet','bagel-menu.service'],capture_output=True).returncode==0
    if active:
        subprocess.run(['sudo','systemctl','stop','bagel-menu.service'],check=True)
# Stop this user's manual server only when its working directory matches the target.
stopped=[]
for directory in Path('/proc').iterdir():
    if not directory.name.isdigit():
        continue
    try:
        if directory.stat().st_uid!=os.getuid() or (directory/'cwd').resolve()!=target:
            continue
        args=(directory/'cmdline').read_bytes().decode().split('\0')
        if any(Path(arg).name=='app.py' for arg in args[1:] if arg):
            pid=int(directory.name)
            os.kill(pid,signal.SIGTERM)
            stopped.append(pid)
    except (OSError,UnicodeError):
        continue
for _ in range(50):
    if all(not Path('/proc',str(pid)).exists() for pid in stopped):
        break
    time.sleep(.1)
else:
    raise SystemExit('The old manual server has not stopped. Stop it before updating.')
excluded={'.venv','__pycache__','.git'}
if target.exists():
    backup=target.parent/'maxs-menu-backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True,mode=0o700)
    backup.parent.chmod(0o700)
    for entry in target.iterdir():
        if entry.name in excluded:
            continue
        destination=backup/entry.name
        if entry.is_dir():
            shutil.copytree(entry,destination,ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(entry,destination)
    print('Backup saved at: '+str(backup))
target.mkdir(parents=True,exist_ok=True)
for entry in source.iterdir():
    if entry.name in excluded|{'data','.menu.env'}:
        continue
    destination=target/entry.name
    if entry.is_dir():
        shutil.copytree(entry,destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    else:
        shutil.copy2(entry,destination)
print('Code installed in: '+str(target))
