"""Interactive first-install setup. Passwords are prompted, never command arguments."""
import getpass
import os
from pathlib import Path
from models import ROOT, Store, atomic_json, read_json, make_user, validate_settings, valid_username, valid_password


def initialize(directory, settings, username, password, hotspot_password=''):
    validate_settings(settings)
    username=valid_username(username);valid_password(password)
    if settings['hotspot_enabled']:
        import re
        if not re.fullmatch(r'[\x20-\x7e]{8,63}',hotspot_password):
            raise ValueError('Hotspot password needs 8–63 printable ASCII characters.')
    root=Path(directory)
    root.mkdir(mode=0o700,parents=True,exist_ok=True);root.chmod(0o700)
    if any((root/name).exists() for name in ['users.json','menu-state.json','menu.json']):
        raise ValueError('An installation already exists. Setup will not overwrite it. Use the editor or reset_admin.py.')
    menu=read_json(ROOT/'sample_menu.json')
    state={'menu':menu,'history':[],'audit':[],'theme':'classic-bagel-shop','schedule':[],'settings':settings}
    if settings['hotspot_enabled']:state['initial_hotspot']={'ssid':settings['hotspot_ssid'],'password':hotspot_password}
    atomic_json(root/'menu.json',menu)
    atomic_json(root/'menu-state.json',state)
    atomic_json(root/'users.json',{'users':[make_user(username,password,'admin')]})
    Store(root)


def ask(label, default=''):
    result=input(label+(' ['+default+']' if default else '')+': ').strip()
    return result or default


def secret(label, minimum):
    while True:
        value=getpass.getpass(label+': ')
        if len(value)<minimum:print('Use at least '+str(minimum)+' characters.');continue
        if value!=getpass.getpass('Repeat '+label.lower()+': '):print('Passwords did not match.');continue
        return value


def main():
    if os.geteuid()==0:raise SystemExit('Run setup as your regular Pi user, without sudo.')
    directory=Path(os.environ.get('MENU_DATA_DIR',ROOT/'data'))
    if (directory/'users.json').exists():
        Store(directory)
        print('Existing settings and accounts retained. Setup was not repeated.')
        return
    print("Max's Menu first-time setup. The application login is separate from the Pi SSH login.")
    settings={'site_name':ask('Site name'), 'timezone':ask('IANA timezone','America/New_York'),
              'hotspot_enabled':ask('Set up optional offline hotspot? (yes/no)','no').lower() in {'y','yes'},
              'hotspot_ssid':'MenuWiFi','wifi_interface':'wlan0','country':'US'}
    username=ask('Application administrator username')
    password=secret('Administrator password',4)
    hotspot_password=''
    if settings['hotspot_enabled']:
        settings['hotspot_ssid']=ask('Hotspot network name','MenuWiFi')
        settings['wifi_interface']=ask('Wi-Fi interface for the existing 2.4 GHz hotspot backend','wlan0')
        settings['country']=ask('Two-letter country code','US').upper()
        hotspot_password=secret('Hotspot Wi-Fi password',8)
    initialize(directory,settings,username,password,hotspot_password)
    print('Settings saved. Sample menus loaded; Menus 4–10 are empty placeholders.')
    print('No hotspot switch has occurred. Complete service installation, then use System if needed.')


if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError) as error:raise SystemExit(str(error))
