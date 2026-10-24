"""Recover access locally or over SSH. There is no hidden recovery account."""
import getpass
import os
from pathlib import Path
import subprocess
from models import ROOT, make_user, valid_username, atomic_json, read_json


def reset(directory, username, password):
    root=Path(directory)
    rows=read_json(root/"users.json")["users"]
    current=next((u for u in rows if u['username']==valid_username(username)),None)
    if current is None or current['role']!='admin':
        raise ValueError('Choose an existing administrator listed by this command.')
    replacement=make_user(username,password,'admin')
    rows=[replacement if u['username']==replacement['username'] else u for u in rows]
    atomic_json(root/'users.json',{'users':rows})


if __name__=='__main__':
    if os.geteuid()==0:raise SystemExit('Run this command as the Pi user who owns the installation, without sudo.')
    directory=Path(os.environ.get('MENU_DATA_DIR',ROOT/'data'))
    # Stop the web writer while changing its account file.
    if subprocess.run(['systemctl','is-active','--quiet','bagel-menu.service'],capture_output=True).returncode==0:
        raise SystemExit('First run: sudo systemctl stop bagel-menu.service. Restart it after resetting.')
    try:
        rows=read_json(directory/"users.json")["users"]
        print('Administrators: '+', '.join(u['username'] for u in rows if u['role']=='admin'))
        name=input('Administrator to reset: ').strip()
        password=getpass.getpass('New password: ')
        if password!=getpass.getpass('Repeat password: '):raise ValueError('Passwords do not match.')
        reset(directory,name,password)
        print('Administrator enabled and password reset. Restart bagel-menu.service.')
    except (ValueError,RuntimeError) as error:raise SystemExit(str(error))
