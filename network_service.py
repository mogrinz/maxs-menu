"""Root-owned, narrow network controller. No shell or caller-selected commands."""
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading
import time

STATE = Path('/var/lib/maxs-menu-network/state.json')
CONFIG = Path('/etc/maxs-menu-network.json')
SOCKET = '/run/maxs-menu-network/control.sock'
HOTSPOT_NAME = 'maxs-menu-hotspot'
DEFAULT_SSID = 'MenuWiFi'
ADDRESS = '192.168.50.1'
TRIAL_SECONDS = 180
HOTSPOT_SERVICE = 'maxs-menu-hotspot.service'


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def network_config(value=None):
    if value is None:
        value=json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    result={'ssid':value.get('ssid',DEFAULT_SSID),'interface':value.get('interface','wlan0'),
            'country':value.get('country','US'),'enabled':value.get('enabled',False)}
    if (not isinstance(result['ssid'],str) or not re.fullmatch(r'[\x20-\x7e]{1,32}',result['ssid']) or not result['ssid'].strip()
        or not isinstance(result['interface'],str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}',result['interface'])
        or not isinstance(result['country'],str) or not re.fullmatch(r'[A-Z]{2}',result['country'])
        or type(result['enabled']) is not bool):
        raise ValueError('Invalid network installation settings.')
    return result


class NM:
    def __init__(self, settings=None):
        self.settings=network_config(settings)
        self.interface=self.settings['interface']
        self.ssid=self.settings['ssid']

    def capabilities(self):
        cached=getattr(self,'_capabilities',None)
        if cached and time.monotonic()-cached[0]<15:
            return cached[1]
        devices={}
        for line in self.run('-t','-f','DEVICE,TYPE','device','status').splitlines():
            parts=line.split(':')
            if len(parts)==2 and re.fullmatch(r'[a-zA-Z0-9_.-]+',parts[0]):
                devices[parts[0]]=parts[1]
        wifi_control=devices.get(self.interface)=='wifi'
        hotspot=self.settings['enabled'] and wifi_control and self.run('-g','WIFI-PROPERTIES.AP','device','show',self.interface)=='yes'
        result={'network_enabled':self.settings['enabled'],'wifi_control':wifi_control,'hotspot_supported':bool(hotspot),
                'ethernet_interfaces':[name for name,kind in devices.items() if kind=='ethernet'],
                'hotspot_reason':'' if hotspot else 'Optional hotspot support was not enabled during setup.' if not self.settings['enabled'] else 'This Pi has no supported Wi-Fi interface.' if not wifi_control else 'The Wi-Fi interface does not support access-point mode.'}
        self._capabilities=(time.monotonic(),result)
        return result

    def wired_info(self):
        rows=[]
        for interface in self.capabilities()['ethernet_interfaces']:
            addresses=[v.split('/')[0] for v in self.run('-g','IP4.ADDRESS','device','show',interface).splitlines() if v]
            if addresses:
                rows.append({'interface':interface,'addresses':addresses,
                             'profile':self.run('-g','GENERAL.CON-UUID','device','show',interface)})
        return rows

    def run(self, *args):
        try:
            result = subprocess.run(['/usr/bin/nmcli', '--wait', '25', *args],
                                    capture_output=True, text=True, timeout=35,
                                    env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL':'C'})
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError('NetworkManager did not respond. The previous network will be retried.') from None
        if result.returncode:
            # Never return argv or nmcli errors: configuration commands can contain a PSK.
            raise ValueError('NetworkManager could not complete the operation. Check Wi-Fi signal, saved credentials and hotspot capability.')
        return result.stdout.rstrip('\n')

    def get(self, uuid, field):
        return self.run('-g', field, 'connection', 'show', 'uuid', uuid)

    def profiles(self):
        ids = self.run('-g', 'UUID', 'connection', 'show').splitlines()
        rows = []
        for uuid in ids:
            if not re.fullmatch(r'[0-9a-fA-F-]{36}', uuid):
                continue
            if self.get(uuid, 'connection.type') != '802-11-wireless':
                continue
            interface = self.get(uuid, 'connection.interface-name')
            if interface not in {'', '--', self.interface}:
                continue
            rows.append({'uuid':uuid, 'name':self.get(uuid, 'connection.id'),
                         'mode':self.get(uuid, '802-11-wireless.mode')})
        return rows

    def active(self):
        # Device GENERAL.CON-UUID is the current connection on wlan0 only.
        return self.run('-g', 'GENERAL.CON-UUID', 'device', 'show', self.interface)

    def addresses(self):
        return [v.split('/')[0] for v in self.run('-g', 'IP4.ADDRESS', 'device', 'show', self.interface).splitlines() if v]

    def activate(self, uuid):
        self.run('connection', 'up', 'uuid', uuid, 'ifname', self.interface)

    def preference(self, uuid, enabled):
        self.run('connection', 'modify', 'uuid', uuid, 'connection.autoconnect', 'yes' if enabled else 'no',
                 'connection.autoconnect-priority', '999' if enabled else '0')

    def configure(self, uuid, password, ssid=None):
        if ssid is not None:self.ssid=network_config({**self.settings,"ssid":ssid})["ssid"]
        properties = ['802-11-wireless.mode','ap','802-11-wireless.ssid',self.ssid,
                      '802-11-wireless.band','bg','802-11-wireless.channel','6',
                      '802-11-wireless.powersave','2','802-11-wireless-security.key-mgmt','wpa-psk',
                      '802-11-wireless-security.proto','rsn','802-11-wireless-security.pairwise','ccmp',
                      '802-11-wireless-security.group','ccmp','802-11-wireless-security.pmf','disable',
                      '802-11-wireless-security.psk',password,
                      'ipv4.method','shared','ipv4.addresses',ADDRESS+'/24','ipv6.method','disabled',
                      'connection.autoconnect','no']
        if uuid:
            self.run('connection','modify','uuid',uuid,*properties)
        else:
            existing = [p for p in self.profiles() if p['name'] == HOTSPOT_NAME]
            if existing:
                if len(existing) != 1 or existing[0]['mode'] != 'ap':
                    raise ValueError('A conflicting hotspot profile exists. Review it on the Pi.')
                return self.configure(existing[0]['uuid'], password, self.ssid)
            self.run('connection','add','type','wifi','ifname',self.interface,'con-name',HOTSPOT_NAME,*properties)
            matches = [p for p in self.profiles() if p['name'] == HOTSPOT_NAME and p['mode'] == 'ap']
            if len(matches) != 1:
                raise ValueError('Could not identify the new hotspot profile.')
            uuid = matches[0]['uuid']
        return uuid

    def password(self, uuid):
        return self.run('--show-secrets','-g','802-11-wireless-security.psk',
                        'connection','show','uuid',uuid)


class HostapdNM(NM):
    """NetworkManager owns client Wi-Fi; a separate service owns the AP radio."""
    def service(self, operation, check=True):
        try:
            result = subprocess.run(['/usr/bin/systemctl',operation,HOTSPOT_SERVICE],
                                    capture_output=True,text=True,timeout=100)
        except (OSError,subprocess.TimeoutExpired):
            raise ValueError('Hotspot service did not respond. The previous network will be retried.') from None
        if check and result.returncode:
            raise ValueError('Hotspot service could not start or stop. Check journalctl -u maxs-menu-hotspot.service.')
        return result.returncode == 0

    def active(self):
        if self.service('is-active',False):
            return self.run('-g','connection.uuid','connection','show',HOTSPOT_NAME)
        return super().active()

    def addresses(self):
        if self.service('is-active',False):
            return [ADDRESS]
        return super().addresses()

    def activate(self, uuid):
        if self.get(uuid,'connection.id') == HOTSPOT_NAME:
            # Keep the saved profile only as credential storage. NetworkManager
            # must never start its own AP at boot or after a backend restart.
            self.preference(uuid,False)
            self.service('start')
        else:
            self.service('stop')
            self.run('device','set',self.interface,'managed','yes')
            super().activate(uuid)

    def preference(self, uuid, enabled):
        if self.get(uuid,'connection.id') == HOTSPOT_NAME:
            enabled = False
        super().preference(uuid,enabled)


class Controller:
    def __init__(self, nm=None, path=STATE, clock=time.time, schedule=None):
        self.nm = nm or HostapdNM()
        self.path = Path(path)
        self.clock = clock
        self.lock = threading.RLock()
        self.schedule = schedule or self._schedule
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.busy = False
        self.retry_after = 0

    @staticmethod
    def _schedule(function):
        timer = threading.Timer(3, function)
        timer.daemon = True
        timer.start()

    def save(self):
        write_json(self.path, self.state)

    def internet_profiles(self):
        return [p for p in self.nm.profiles() if p['mode'] in {'infrastructure','', '--'} and p['uuid'] != self.state.get('hotspot')]

    def status(self):
        with self.lock:
            caps=self.nm.capabilities()
            wired=self.nm.wired_info()
            active = self.nm.active() if caps['wifi_control'] else ''
            profiles = self.internet_profiles() if caps['wifi_control'] else []
            pending = self.state.get('pending')
            addresses = self.nm.addresses() if caps['wifi_control'] else []
            addresses=list(dict.fromkeys(addresses+[a for row in wired for a in row['addresses']]))
            mode='hotspot' if active and active == self.state.get('hotspot') else 'internet' if active in {p['uuid'] for p in profiles} else 'ethernet' if wired else 'disconnected'
            return {'mode':mode, 'capabilities':caps,'ethernet':wired,
                    'ssid':self.state.get('ssid',self.nm.ssid), 'hotspot_address':ADDRESS, 'addresses':addresses, 'active_profile':active,
                    'internet_profiles':profiles, 'internet_profile':self.state.get('internet', ''),
                    'hotspot_ready':caps['hotspot_supported'] and bool(self.state.get('hotspot')), 'busy':self.busy,
                    'can_switch':caps['wifi_control'] and bool(active) and active in ({p['uuid'] for p in profiles}|{self.state.get('hotspot')}),
                    'pending':None if not pending else {'id':pending['id'], 'mode':pending['mode'],
                        'remaining':max(0,int(pending['deadline']-self.clock())), 'target':pending['target'],
                        'active':active == pending['target'] and not self.busy},
                    'message':self.state.get('message','')}

    def dispatch(self, body):
        if not isinstance(body, dict) or not isinstance(body.get('action'), str):
            raise ValueError('Invalid network request.')
        fields = {'status':{'action'}, 'credentials':{'action'}, 'configure':{'action','password','ssid'}, 'switch':{'action','mode','profile'},
                  'confirm':{'action','id'}, 'cancel':{'action','id'}}
        action = body['action']
        if action not in fields or set(body) != fields[action]:
            raise ValueError('Unsupported network operation or fields.')
        if action == 'status':
            return self.status()
        if action == 'credentials':
            with self.lock:
                uuid = self.state.get('hotspot')
                return {'password':self.nm.password(uuid) if uuid else '', 'ssid':self.state.get('ssid',self.nm.ssid)}
        with self.lock:
            caps=self.nm.capabilities()
            if not self.nm.settings['enabled']:
                raise ValueError('Optional hotspot networking is disabled for this installation.')
            if action=='configure' and not caps['hotspot_supported']:
                raise ValueError('Hotspot configuration is unavailable on this Pi.')
            if action in {'switch','confirm','cancel'} and not caps['wifi_control']:
                raise ValueError('Wi-Fi switching is unavailable on this Pi. Its Ethernet connection is unchanged.')
            if action=='switch' and body['mode']=='hotspot' and not caps['hotspot_supported']:
                raise ValueError('This Pi does not support hotspot mode.')
            if self.busy:
                raise ValueError('A network operation is in progress. Wait a moment.')
            pending = self.state.get('pending')
            if action == 'configure':
                password = body['password']
                if not isinstance(password,str) or not re.fullmatch(r'[\x20-\x7e]{8,63}', password):
                    raise ValueError('Hotspot password needs 8–63 printable characters.')
                if pending or self.nm.active() == self.state.get('hotspot'):
                    raise ValueError('Configure the hotspot while connected to Internet Wi-Fi, with no trial pending.')
                self.state['hotspot'] = self.nm.configure(self.state.get('hotspot'),password,body['ssid'])
                self.state['ssid']=self.nm.ssid
                self.state['message'] = 'Hotspot configured. The current network has not changed.'
                self.save()
            elif action == 'switch':
                if pending:
                    raise ValueError('Confirm or cancel the current trial first.')
                profiles = self.internet_profiles()
                mode = body['mode']
                if mode == 'hotspot':
                    target = self.state.get('hotspot')
                    if not target or body['profile'] != '':
                        raise ValueError('Configure the hotspot first.')
                elif mode == 'internet' and body['profile'] in {p['uuid'] for p in profiles}:
                    target = body['profile']
                else:
                    raise ValueError('Choose a saved Internet Wi-Fi profile.')
                prior = self.nm.active()
                allowed = {p['uuid'] for p in profiles} | {self.state.get('hotspot')}
                if prior not in allowed or not prior:
                    raise ValueError('A working Wi-Fi connection is required for a recoverable trial switch.')
                if target == prior:
                    raise ValueError('That network is already active.')
                if mode == 'hotspot' and prior in {p['uuid'] for p in profiles}:
                    self.state['internet'] = prior
                self.state['pending'] = {'id':secrets.token_hex(16),'prior':prior,'target':target,
                                         'mode':mode,'deadline':self.clock()+TRIAL_SECONDS}
                self.state['message'] = 'Trial scheduled. Reconnect and confirm within three minutes.'
                self.save()
                self.busy = True
                self.schedule(self.activate_trial)
            elif action in {'confirm','cancel'}:
                if not pending or body['id'] != pending['id']:
                    raise ValueError('That trial is no longer pending. Reload System.')
                if action == 'confirm':
                    if self.clock() >= pending['deadline']:
                        raise ValueError('The trial expired; the previous network will be restored.')
                    if self.nm.active() != pending['target']:
                        raise ValueError('The requested network is not active yet.')
                    # Persist only after the administrator can access the target network.
                    self.nm.preference(pending['target'], True)
                    self.nm.preference(pending['prior'], False)
                    self.state['confirmed'] = pending['target']
                    if pending['mode'] == 'internet':
                        self.state['internet'] = pending['target']
                    self.state.pop('pending')
                    self.state['message'] = 'Network mode confirmed and saved for reboot.'
                    self.save()
                else:
                    self.busy = True
                    self.schedule(self.rollback)
        # Do not run status (slow nmcli reads) before a deferred network switch.
        return {'message':self.state['message'], 'scheduled':action in {'switch','cancel'}}

    def activate_trial(self):
        with self.lock:
            pending = self.state.get('pending')
            if not pending:
                self.busy = False
                return
            try:
                if self.clock() >= pending['deadline']:
                    self.rollback()
                    return
                self.nm.activate(pending['target'])
                self.state['message'] = 'Trial active. Reconnect and choose Keep this mode.'
                self.save()
            except ValueError:
                self.rollback()
            finally:
                self.busy = False

    def rollback(self):
        with self.lock:
            pending = self.state.get('pending')
            if not pending:
                self.busy = False
                return
            try:
                self.nm.preference(pending['prior'],True)
                self.nm.preference(pending['target'],False)
                self.nm.activate(pending['prior'])
                self.state['confirmed'] = pending['prior']
                self.state.pop('pending')
                self.state['message'] = 'Previous network restored. The trial was not kept.'
            except ValueError:
                self.state['message'] = 'Could not restore the previous network yet. Retrying; check its signal.'
                pending['deadline'] = self.clock()
            finally:
                self.busy = False
                self.save()

    def recover_startup(self):
        if not self.nm.settings['enabled']:return
        caps=self.nm.capabilities()
        if not caps['wifi_control']:
            self.state.pop('pending',None)
            self.state['message']='Ethernet networking is managed by the operating system. Saved Wi-Fi settings are retained.'
            self.save()
            return
        if not caps['hotspot_supported'] and self.state.get('hotspot') and self.state.get('confirmed')==self.state.get('hotspot'):
            self.state.pop('pending',None)
            self.state['message']='Hotspot mode is unavailable on this Pi. Saved settings are retained.'
            self.save()
            return
        # Always roll back an unfinished trial after a service restart/power failure.
        if self.state.get('pending'):
            self.rollback()
        elif self.state.get('confirmed') and self.nm.active() != self.state['confirmed']:
            self.nm.activate(self.state['confirmed'])

    def tick(self):
        if not self.nm.settings['enabled']:return
        with self.lock:
            if self.state.get('pending') and self.clock() >= self.state['pending']['deadline'] and not self.busy:
                if self.nm.capabilities()['wifi_control']:
                    self.rollback()
                else:
                    self.state.pop('pending',None)
                    self.save()
            elif not self.state.get('pending') and not self.busy and self.state.get('confirmed') and self.clock() >= self.retry_after:
                self.retry_after = self.clock() + 30
                caps=self.nm.capabilities()
                if not caps['wifi_control'] or (not caps['hotspot_supported'] and self.state['confirmed']==self.state.get('hotspot')):
                    return
                try:
                    if self.nm.active() != self.state['confirmed']:
                        self.nm.activate(self.state['confirmed'])
                        self.state['message'] = 'Saved network connection restored.'
                        self.save()
                except ValueError:
                    self.state['message'] = 'Saved network unavailable. Retrying automatically.'
                    self.save()


def serve():
    config = json.loads(CONFIG.read_text())
    account = pwd.getpwnam(config['user'])
    controller = Controller()
    try:
        controller.recover_startup()
    except ValueError:
        controller.state['message'] = 'Saved network unavailable. Check Wi-Fi signal.'
        controller.save()
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(5)
            _,uid,_ = struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid not in {0,account.pw_uid}:
                return
            try:
                line = self.rfile.readline(4097)
                if len(line)>4096 or not line.endswith(b'\n'):
                    raise ValueError('Network request is too large.')
                result = controller.dispatch(json.loads(line))
            except (ValueError,TypeError,KeyError,json.JSONDecodeError):
                result = {'error':'Invalid request or network operation failed.'}
                # ValueError messages are controlled and never include the PSK.
                import sys
                error = sys.exc_info()[1]
                if type(error) is ValueError:
                    result['error'] = str(error)
            except Exception:
                result = {'error':'Network service could not complete the operation.'}
            self.wfile.write(json.dumps(result).encode()+b'\n')
    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True
    Path(SOCKET).unlink(missing_ok=True)
    with Server(SOCKET,Handler) as server:
        os.chown(SOCKET,0,account.pw_gid)
        os.chmod(SOCKET,0o660)
        server.timeout = 1
        while True:
            server.handle_request()
            controller.tick()


if __name__ == '__main__':
    if os.geteuid()!=0:
        raise SystemExit('The network controller must run as its installed root-owned service.')
    serve()
