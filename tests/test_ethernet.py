import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from network_service import NM, Controller
from test_network import AP, HOME, FakeNM
import install_network_service as installer


class WiredNM(FakeNM):
    def capabilities(self):
        return {'wifi_control':False,'hotspot_supported':False,'ethernet_interfaces':['eth0'],'hotspot_reason':'No Wi-Fi interface.'}
    def wired_info(self):
        return [{'interface':'eth0','addresses':['10.0.0.76'],'profile':'33333333-3333-3333-3333-333333333333'}]
    def active(self):raise AssertionError('Must not query wlan0 on Ethernet-only hardware')
    def addresses(self):raise AssertionError('Must not query wlan0 on Ethernet-only hardware')
    def profiles(self):raise AssertionError('Must not scan Wi-Fi profiles on Ethernet-only hardware')
    def activate(self,uuid):raise AssertionError('Must not activate a saved Wi-Fi mode')
    def preference(self,uuid,enabled):raise AssertionError('Must not change network preferences')


class EthernetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'state.json'

    def test_ethernet_capabilities_do_not_query_absent_wifi(self):
        nm=NM({'enabled':True})
        with patch.object(nm,'run',return_value='eth0:ethernet\nlo:loopback') as run:
            caps=nm.capabilities();again=nm.capabilities()
        self.assertFalse(caps['wifi_control']);self.assertFalse(caps['hotspot_supported'])
        self.assertEqual(caps['ethernet_interfaces'],['eth0'])
        self.assertEqual(caps,again);self.assertEqual(run.call_count,1)

    def test_wifi_present_without_ap_support(self):
        nm=NM({'enabled':True})
        with patch.object(nm,'run',side_effect=['wlan0:wifi\neth0:ethernet','no']):caps=nm.capabilities()
        self.assertTrue(caps['wifi_control']);self.assertFalse(caps['hotspot_supported'])

    def test_wifi_ap_capability_preserved(self):
        nm=NM({'enabled':True})
        with patch.object(nm,'run',side_effect=['wlan0:wifi\nlo:loopback','yes']):caps=nm.capabilities()
        self.assertTrue(caps['hotspot_supported'])

    def test_moved_sd_saved_hotspot_does_not_activate_or_retry(self):
        controller=Controller(WiredNM(),self.path,clock=lambda:1000)
        controller.state={'hotspot':AP,'confirmed':AP,'internet':HOME,
                          'pending':{'prior':HOME,'target':AP,'deadline':900}}
        controller.recover_startup();controller.tick()
        result=controller.status()
        self.assertEqual(result['mode'],'ethernet')
        self.assertEqual(result['addresses'],['10.0.0.76'])
        self.assertFalse(result['hotspot_ready']);self.assertFalse(result['can_switch'])
        self.assertEqual(result['internet_profiles'],[])
        self.assertIsNone(result['pending'])
        self.assertEqual(controller.state['confirmed'],AP)
        self.assertEqual(controller.state['hotspot'],AP)

    def test_unsupported_actions_refused_without_mutation(self):
        controller=Controller(WiredNM(),self.path)
        for body in [{'action':'configure','ssid':'TestMenu','password':'synthetic-test'},
                     {'action':'switch','mode':'hotspot','profile':''},
                     {'action':'switch','mode':'internet','profile':HOME}]:
            with self.assertRaises(ValueError):controller.dispatch(body)
        self.assertFalse(self.path.exists())

    def test_wired_preflight_does_not_require_hostapd_or_confirmed_wifi(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'state.json').write_text(json.dumps({'confirmed':AP,'pending':{'target':AP}}))
            with patch.object(installer,'STATE_DIR',Path(d)),patch('install_network_service.os.geteuid',return_value=0),patch('install_network_service.Path.exists',return_value=True) as exists,patch.object(installer,'NM',return_value=WiredNM()),patch('install_network_service.subprocess.run') as command:
                nm,active=installer.preflight()
        self.assertEqual(active,'');self.assertIsInstance(nm,WiredNM)
        command.assert_not_called()
        self.assertFalse(any('hostapd' in str(c) for c in exists.call_args_list))


if __name__=='__main__':unittest.main()
