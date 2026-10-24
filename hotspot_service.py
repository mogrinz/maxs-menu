"""Root-owned hostapd/DHCP service. Fixed interface and configuration only."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

RUNTIME = Path('/run/maxs-menu-hotspot')
STATE = Path('/var/lib/maxs-menu-network/state.json')
CONFIG = Path('/etc/maxs-menu-network.json')
from network_service import network_config
ADDRESS = '192.168.50.1/24'


def command(*args, check=True, timeout=30):
    try:
        result = subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError('A hotspot system command did not respond.') from None
    if check and result.returncode:
        # Never echo command output or credentials into the journal.
        raise RuntimeError('A hotspot system command failed. Check NetworkManager and the Wi-Fi driver.')
    return result


def nm(*args, check=True):
    return command('/usr/bin/nmcli','--wait','20',*args,check=check).stdout.rstrip('\n')


def configuration(password, ssid, interface, country):
    if not isinstance(password,str) or not re.fullmatch(r'[\x20-\x7e]{8,63}',password):
        raise RuntimeError('The saved hotspot passphrase must contain 8-63 printable ASCII characters.')
    key=hashlib.pbkdf2_hmac('sha1',password.encode('ascii'),ssid.encode('ascii'),4096,32).hex()
    return (
        'interface='+interface+'\ndriver=nl80211\nssid2='+ssid.encode('ascii').hex()+'\n'
        'country_code='+country+'\nieee80211d=1\nhw_mode=g\nchannel=6\n'
        'auth_algs=1\nwpa=2\nwpa_key_mgmt=WPA-PSK\n'
        'rsn_pairwise=CCMP\nieee80211w=0\nwps_state=0\n'
        'ctrl_interface='+str(RUNTIME/'hostapd')+'\n'
        'wpa_psk='+key+'\n'
    )


def ready():
    address=os.environ.get('NOTIFY_SOCKET')
    if not address:
        raise RuntimeError('Start this helper using its installed systemd service.')
    if address.startswith('@'):
        address='\0'+address[1:]
    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as sock:
        sock.connect(address)
        sock.sendall(b'READY=1\nSTATUS=Menu hotspot and DHCP are ready')


def cleanup():
    interface=network_config()["interface"]
    # ExecStopPost runs after systemd has killed both child processes, including
    # after partial startup or a crash. Normal Wi-Fi credentials are untouched.
    if (RUNTIME/'radio-owned').exists():
        try:
            command('/usr/sbin/ip','address','del',ADDRESS,'dev',interface,check=False)
        finally:
            nm('device','set',interface,'managed','yes')
            (RUNTIME/'radio-owned').unlink(missing_ok=True)
    (RUNTIME/'hostapd.conf').unlink(missing_ok=True)


def start():
    settings=network_config()
    if not settings["enabled"]:raise RuntimeError("Hotspot support is disabled.")
    interface=settings["interface"]
    state=json.loads(STATE.read_text())
    uuid=state.get('hotspot','')
    if not re.fullmatch(r'[a-fA-F0-9-]{36}',uuid):
        raise RuntimeError('No saved hotspot profile. Configure it in System first.')
    if nm('-g','connection.id','connection','show','uuid',uuid)!='maxs-menu-hotspot':
        raise RuntimeError('The saved hotspot profile does not match Max\'s Menu.')
    password=nm('--show-secrets','-g','802-11-wireless-security.psk','connection','show','uuid',uuid)
    config=configuration(password,state.get('ssid',settings['ssid']),interface,settings['country'])
    del password
    (RUNTIME/'hostapd.conf').write_text(config)
    # Mark ownership before the first radio mutation so partial startup cleans up.
    (RUNTIME/'radio-owned').touch()
    nm('device','disconnect',interface,check=False)
    nm('device','set',interface,'managed','no')
    time.sleep(2)
    command('/usr/sbin/ip','link','set',interface,'up')
    command('/usr/sbin/ip','address','replace',ADDRESS,'dev',interface)
    host=subprocess.Popen(['/usr/sbin/hostapd',str(RUNTIME/'hostapd.conf')])
    deadline=time.monotonic()+20
    while True:
        if host.poll() is not None or time.monotonic()>=deadline:
            raise RuntimeError('hostapd did not enable the access point.')
        status=command('/usr/sbin/hostapd_cli','-p',str(RUNTIME/'hostapd'),'-i',interface,'status',check=False,timeout=3)
        if 'state=ENABLED' in status.stdout.splitlines():
            break
        time.sleep(.5)
    # Match the successful isolated test: DHCP, no upstream DNS or routing.
    dhcp=subprocess.Popen([
        '/usr/sbin/dnsmasq','--no-daemon','--conf-file=/dev/null','--port=0',
        '--interface='+interface,'--except-interface=lo','--bind-interfaces',
        '--dhcp-authoritative',
        '--dhcp-range=192.168.50.10,192.168.50.254,255.255.255.0,12h',
        '--dhcp-option=6','--dhcp-leasefile='+str(RUNTIME/'leases'),'--log-dhcp',
    ])
    time.sleep(1)
    if host.poll() is not None or dhcp.poll() is not None:
        raise RuntimeError('Hotspot or DHCP service failed during startup.')
    ready()
    print('Menu hotspot ready at 192.168.50.1. WPA2/AES, hostapd backend.',flush=True)
    while True:
        if host.poll() is not None or dhcp.poll() is not None:
            raise RuntimeError('A hotspot process exited. systemd will clean up and retry.')
        time.sleep(1)


if __name__=='__main__':
    os.umask(0o077)
    os.environ['LC_ALL']='C'
    if os.geteuid()!=0:
        raise SystemExit('This helper runs only through the installed root service.')
    try:
        if sys.argv[1:]==['cleanup']:
            cleanup()
        elif sys.argv[1:]==['start']:
            start()
        else:
            raise RuntimeError('Use the installed maxs-menu-hotspot.service.')
    except Exception as error:
        # Only our controlled errors carry details; unexpected exceptions may
        # include file contents, so keep them out of logs.
        print(str(error) if type(error) is RuntimeError else 'Hotspot helper failed.',file=sys.stderr,flush=True)
        sys.exit(1)
