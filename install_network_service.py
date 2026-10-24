"""Install root-owned hotspot services while connected to confirmed normal Wi-Fi."""
import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile
from network_service import NM, write_json, network_config

DESTINATION = Path('/usr/local/lib/maxs-menu-network')
STATE_DIR = Path('/var/lib/maxs-menu-network')


def preflight(settings=None):
    if os.geteuid()!=0:
        raise SystemExit('Run network installation with sudo.')
    if not Path('/usr/bin/nmcli').exists():
        raise SystemExit('NetworkManager is required for System network status.')
    nm=NM(settings)
    caps=nm.capabilities()
    if caps['hotspot_supported']:
        for binary in ['/usr/sbin/hostapd','/usr/sbin/hostapd_cli','/usr/sbin/dnsmasq','/usr/sbin/ip']:
            if not Path(binary).exists():
                raise SystemExit('Install hotspot dependencies: sudo apt install -y hostapd dnsmasq-base')
    if caps['wifi_control']:
        for unit in ['maxs-menu-hostapd-test.service','hostapd.service','dnsmasq.service','maxs-menu-hotspot.service']:
            result=subprocess.run(['systemctl','show',unit,'-p','ActiveState','--value'],capture_output=True,text=True)
            if result.stdout.strip() in {'active','activating','deactivating','reloading'}:
                raise SystemExit('Wait for any diagnostic to finish, and switch to normal Wi-Fi before installing. Conflicting unit: '+unit)
    active=nm.active() if caps['wifi_control'] else ''
    profiles=[p for p in nm.profiles() if p['mode'] in {'infrastructure','','--'}] if caps['wifi_control'] else []
    wired=nm.wired_info()
    wifi_active=active in {p['uuid'] for p in profiles}
    if not wifi_active and not wired:
        raise SystemExit('Connect to Ethernet or a saved normal Wi-Fi network before installing.')
    state=STATE_DIR/'state.json'
    if state.exists() and caps['wifi_control']:
        saved=json.loads(state.read_text())
        if saved.get('pending') or (wifi_active and saved.get('confirmed') and saved['confirmed']!=active):
            raise SystemExit('Confirm the current normal Wi-Fi connection in System before installing.')
    if not wifi_active:active=''

    return nm,active


def install(root):
    owner=pwd.getpwuid(root.stat().st_uid)
    if os.geteuid()!=0 or owner.pw_uid==0:
        raise SystemExit('Install as the regular Pi user, then invoke install_service.py with sudo.')
    site=json.loads((root/'data/menu-state.json').read_text())['settings']
    previous=Path('/etc/maxs-menu-network.json')
    config_value=json.loads(previous.read_text()) if previous.exists() else {
        'user':owner.pw_name,'ssid':site['hotspot_ssid'],'interface':site['wifi_interface'],
        'country':site['country'],'enabled':site['hotspot_enabled']}
    settings=network_config(config_value)
    nm,active=preflight(settings)
    caps=nm.capabilities()
    if not caps['wifi_control']:
        # Old images may have a saved hotspot mode and a retrying AP service.
        # Stop our own service only, without altering Ethernet or other daemons.
        path=Path('/etc/systemd/system/maxs-menu-hotspot.service')
        if path.exists() and '/usr/local/lib/maxs-menu-network/hotspot_service.py' in path.read_text():
            subprocess.run(['systemctl','stop','maxs-menu-network.service'],check=False)
            subprocess.run(['systemctl','stop','maxs-menu-hotspot.service'],check=False)
    destination=DESTINATION
    state_dir=STATE_DIR
    config=Path('/etc/maxs-menu-network.json')
    for directory in [destination,state_dir]:
        if directory.is_symlink() or (directory.exists() and directory.stat().st_uid!=0):
            raise SystemExit('Network controller directory is not root-owned.')
        directory.mkdir(exist_ok=True)
        directory.chmod(0o755 if directory==destination else 0o700)
    if config.exists() and json.loads(config.read_text()).get('user')!=owner.pw_name:
        raise SystemExit('A network controller for another user already exists.')
    write_json(config,{'user':owner.pw_name,**settings})
    for filename in ['network_service.py','hotspot_service.py']:
        fd,temporary=tempfile.mkstemp(dir=destination)
        with os.fdopen(fd,'wb') as stream:
            stream.write((root/filename).read_bytes())
        os.chmod(temporary,0o644)
        os.replace(temporary,destination/filename)
    state=state_dir/'state.json'
    saved=json.loads(state.read_text()) if state.exists() else {}
    if saved.get('hotspot') and caps['wifi_control']:
        nm.run('connection','modify','uuid',saved['hotspot'],
               'connection.autoconnect','no','connection.autoconnect-priority','0',
               '802-11-wireless.ssid',saved.get('ssid',settings['ssid']),'802-11-wireless-security.pmf','disable')
    app_state_path=root/'data/menu-state.json'
    app_state=json.loads(app_state_path.read_text())
    pending=app_state.get('initial_hotspot')
    if pending and caps['hotspot_supported']:
        saved['hotspot']=nm.configure(saved.get('hotspot'),pending['password'],pending['ssid'])
        saved['ssid']=pending['ssid']
        app_state['settings']['hotspot_ssid']=pending['ssid']
        app_state.pop('initial_hotspot')
        write_json(app_state_path,app_state)
        os.chown(app_state_path,owner.pw_uid,owner.pw_gid)
    if active:
        saved.update(internet=active,confirmed=active,message='Network controller installed. Your current Wi-Fi is unchanged.')
    else:
        saved.pop('pending',None)
        if caps['wifi_control']:saved.pop('confirmed',None)
        saved['message']='Ethernet connection retained. Hotspot controls are hidden when unsupported.'
    write_json(state,saved)
    controller='''[Unit]
Description=Max's Menu restricted network controller
After=NetworkManager.service
Requires=NetworkManager.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/lib/maxs-menu-network/network_service.py
Restart=on-failure
RestartSec=3
RuntimeDirectory=maxs-menu-network
RuntimeDirectoryMode=0755
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/maxs-menu-network /run/maxs-menu-network
RestrictAddressFamilies=AF_UNIX

[Install]
WantedBy=multi-user.target
'''
    hotspot='''[Unit]
Description=Max's Menu WPA2 hotspot and DHCP
After=NetworkManager.service
Requires=NetworkManager.service
StartLimitIntervalSec=0

[Service]
Type=notify
NotifyAccess=main
ExecStart=/usr/bin/python3 /usr/local/lib/maxs-menu-network/hotspot_service.py start
ExecStopPost=/usr/bin/python3 /usr/local/lib/maxs-menu-network/hotspot_service.py cleanup
Restart=on-failure
RestartSec=5
TimeoutStartSec=90
TimeoutStopSec=60
KillMode=control-group
RuntimeDirectory=maxs-menu-hotspot
RuntimeDirectoryMode=0700
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/run/maxs-menu-hotspot
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK AF_PACKET
'''
    paths=[]
    for name,content,marker in [
        ('maxs-menu-network.service',controller,'/usr/local/lib/maxs-menu-network/network_service.py'),
        ('maxs-menu-hotspot.service',hotspot,'/usr/local/lib/maxs-menu-network/hotspot_service.py')]:
        path=Path('/etc/systemd/system')/name
        if path.is_symlink() or (path.exists() and marker not in path.read_text()):
            raise SystemExit('An unrelated service exists: '+name)
        path.write_text(content)
        paths.append(str(path))
    subprocess.run(['systemd-analyze','verify',*paths],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','maxs-menu-network.service'],check=True)
    # Only the controller is enabled. It starts hostapd at boot when hotspot mode
    # was confirmed. Never enable a competing generic hostapd/dnsmasq service.
    subprocess.run(['systemctl','restart','maxs-menu-network.service'],check=True)


if __name__=='__main__':
    preflight()
    print('Network preflight passed. Ethernet or normal Wi-Fi is connected.')
