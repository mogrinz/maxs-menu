import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch, call

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from network_service import HostapdNM, HOTSPOT_SERVICE, NM
import hotspot_service as driver
import install_network_service as installer

AP='22222222-2222-2222-2222-222222222222'
HOME='11111111-1111-1111-1111-111111111111'


class HostapdTests(unittest.TestCase):
    def setUp(self):
        self.config_patch=patch.object(driver,'network_config',return_value={'enabled':True,'interface':'wlan0','country':'US','ssid':'TestMenu'})
        self.config_patch.start();self.addCleanup(self.config_patch.stop)

    def test_ap_activation_never_invokes_nm_connection_up(self):
        nm=HostapdNM({'enabled':True})
        with patch.object(nm,'get',return_value='maxs-menu-hotspot'),patch.object(nm,'run') as run,patch.object(nm,'service') as service:
            nm.activate(AP)
        service.assert_called_once_with('start')
        self.assertIn(call('connection','modify','uuid',AP,'connection.autoconnect','no','connection.autoconnect-priority','0'),run.call_args_list)
        self.assertFalse(any(c.args[:2]==('connection','up') for c in run.call_args_list))

    def test_home_activation_stops_ap_before_networkmanager(self):
        nm=HostapdNM({'enabled':True});events=[]
        with patch.object(nm,'get',return_value='home'),patch.object(nm,'service',side_effect=lambda op:events.append(('service',op))),patch.object(nm,'run',side_effect=lambda *args:events.append(args)):
            nm.activate(HOME)
        self.assertEqual(events[0],('service','stop'))
        self.assertEqual(events[1],('device','set','wlan0','managed','yes'))
        self.assertEqual(events[2],('connection','up','uuid',HOME,'ifname','wlan0'))

    def test_confirmed_hotspot_cannot_autostart_networkmanager_ap(self):
        nm=HostapdNM({'enabled':True})
        with patch.object(nm,'get',return_value='maxs-menu-hotspot'),patch.object(nm,'run') as run:
            nm.preference(AP,True)
        self.assertIn('no',run.call_args.args)

    def test_service_timeout_redacted_and_reported(self):
        import subprocess
        with patch('network_service.subprocess.run',side_effect=subprocess.TimeoutExpired('private',100)):
            with self.assertRaisesRegex(ValueError,'did not respond'):
                HostapdNM({'enabled':True}).activate(AP)

    def test_active_ap_and_ip_are_reported_even_with_unmanaged_radio(self):
        nm=HostapdNM({'enabled':True})
        with patch.object(nm,'service',return_value=True),patch.object(nm,'run',return_value=AP):
            self.assertEqual(nm.active(),AP)
            self.assertEqual(nm.addresses(),['192.168.50.1'])

    def test_password_spaces_preserved(self):
        with patch('network_service.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=' password with spaces \n')):
            self.assertEqual(NM({'enabled':True}).password(AP),' password with spaces ')

    def test_generated_config_matches_successful_security_and_ssid(self):
        password=' synthetic test '
        result=driver.configuration(password,'TestMenu','wlan0','US')
        digest=hashlib.pbkdf2_hmac('sha1',password.encode(),b'TestMenu',4096,32).hex()
        for value in ['ssid2='+b'TestMenu'.hex(),'wpa=2','wpa_key_mgmt=WPA-PSK','rsn_pairwise=CCMP','ieee80211w=0','wpa_psk='+digest]:
            self.assertIn(value,result.splitlines())
        self.assertNotIn(password,result)
        for invalid in ['short','abcdefgh\ninjected=1','é'*8,'x'*64]:
            with self.assertRaises(RuntimeError):driver.configuration(invalid,'TestMenu','wlan0','US')

    def test_cleanup_releases_radio_even_if_address_removal_fails(self):
        with tempfile.TemporaryDirectory() as d,patch.object(driver,'RUNTIME',Path(d)):
            (Path(d)/'radio-owned').touch()
            with patch.object(driver,'command',side_effect=RuntimeError('ip unavailable')),patch.object(driver,'nm') as nm:
                with self.assertRaises(RuntimeError):driver.cleanup()
            nm.assert_called_once_with('device','set','wlan0','managed','yes')

    def test_cleanup_without_ownership_does_not_change_wifi(self):
        with tempfile.TemporaryDirectory() as d,patch.object(driver,'RUNTIME',Path(d)),patch.object(driver,'nm') as nm,patch.object(driver,'command') as command:
            driver.cleanup()
            nm.assert_not_called();command.assert_not_called()

    def test_invalid_credentials_rejected_before_radio_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.json';state.write_text(json.dumps({'hotspot':AP}))
            with patch.object(driver,'STATE',state),patch.object(driver,'RUNTIME',Path(d)),patch.object(driver,'nm',side_effect=['maxs-menu-hotspot','bad']) as nm:
                with self.assertRaises(RuntimeError):driver.start()
            self.assertEqual(nm.call_count,2)
            self.assertFalse((Path(d)/'radio-owned').exists())

    def test_ready_only_after_ap_enabled_and_dhcp_alive(self):
        class EndTest(BaseException):pass
        events=[]
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.json';state.write_text(json.dumps({'hotspot':AP}))
            def spawn(args):
                events.append(Path(args[0]).name)
                return SimpleNamespace(poll=lambda:None)
            with patch.object(driver,'STATE',state),patch.object(driver,'RUNTIME',Path(d)),patch.object(driver,'nm',side_effect=['maxs-menu-hotspot','synthetic-test','','']),patch.object(driver,'command',return_value=SimpleNamespace(stdout='state=ENABLED\n')),patch.object(driver.subprocess,'Popen',side_effect=spawn),patch.object(driver,'ready',side_effect=lambda:events.append('ready')),patch.object(driver.time,'sleep',side_effect=[None,None,EndTest()]):
                with self.assertRaises(EndTest):driver.start()
            self.assertEqual(events,['hostapd','dnsmasq','ready'])
            self.assertTrue((Path(d)/'radio-owned').exists())

    def test_dhcp_start_failure_does_not_report_ready(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.json';state.write_text(json.dumps({'hotspot':AP}))
            children=[SimpleNamespace(poll=lambda:None),SimpleNamespace(poll=lambda:1)]
            with patch.object(driver,'STATE',state),patch.object(driver,'RUNTIME',Path(d)),patch.object(driver,'nm',side_effect=['maxs-menu-hotspot','synthetic-test','','']),patch.object(driver,'command',return_value=SimpleNamespace(stdout='state=ENABLED\n')),patch.object(driver.subprocess,'Popen',side_effect=children),patch.object(driver,'ready') as ready,patch.object(driver.time,'sleep'):
                with self.assertRaisesRegex(RuntimeError,'DHCP'):driver.start()
            ready.assert_not_called()

    def test_preflight_refuses_unfinished_trial_before_any_write(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'state.json').write_text(json.dumps({'pending':{'target':AP},'confirmed':HOME}))
            with patch.object(installer,'STATE_DIR',Path(d)),patch('install_network_service.os.geteuid',return_value=0),patch('install_network_service.Path.exists',return_value=True),patch('install_network_service.subprocess.run',return_value=SimpleNamespace(stdout='inactive')),patch.object(installer,'NM') as ctor:
                ctor.return_value.run.return_value='yes'
                ctor.return_value.capabilities.return_value={'wifi_control':True,'hotspot_supported':True,'ethernet_interfaces':[]}
                ctor.return_value.wired_info.return_value=[]
                ctor.return_value.active.return_value=HOME
                ctor.return_value.profiles.return_value=[{'uuid':HOME,'mode':'infrastructure'}]
                with self.assertRaisesRegex(SystemExit,'Confirm'):installer.preflight()


if __name__=='__main__':unittest.main()
