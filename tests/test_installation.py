import contextlib
import copy
import io
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from configure import initialize, main
from models import Store
from test_product import SETTINGS
from network_service import NM, network_config
import install_network_service as installer

ROOT=Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def test_unconfigured_server_does_not_create_partial_installation(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):Store(d)
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_interactive_setup_and_repeat_preserves_existing_login(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict('os.environ',{'MENU_DATA_DIR':d}),patch('configure.os.geteuid',return_value=1000),patch('builtins.input',side_effect=['New Site','America/Chicago','no','chosen-admin']),patch('configure.getpass.getpass',side_effect=['synthetic-pass','synthetic-pass']),contextlib.redirect_stdout(io.StringIO()):main()
            store=Store(d)
            self.assertTrue(store.authenticate('chosen-admin','synthetic-pass'))
            self.assertEqual(store.state()['settings']['timezone'],'America/Chicago')
            with patch.dict('os.environ',{'MENU_DATA_DIR':d}),patch('configure.os.geteuid',return_value=1000),patch('builtins.input',side_effect=AssertionError('Must not prompt again')),contextlib.redirect_stdout(io.StringIO()):main()
            self.assertTrue(Store(d).authenticate('chosen-admin','synthetic-pass'))

    def test_code_upgrade_preserves_data_environment_and_existing_login(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'installation';target.mkdir();(target/'app.py').write_text('# older code\n')
            initialize(target/'data',copy.deepcopy(SETTINGS),'chosen-admin','synthetic-pass')
            (target/'.menu.env').write_text('MENU_PORT=8090\n')
            before={p.name:p.read_bytes() for p in (target/'data').iterdir()}
            with patch.object(sys,'argv',['prepare_update.py',str(target)]),patch('os.geteuid',return_value=1000),patch('shutil.which',return_value=None),contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(ROOT/'prepare_update.py'),run_name='__main__')
            self.assertEqual((target/'.menu.env').read_text(),'MENU_PORT=8090\n')
            for name,value in before.items():self.assertEqual((target/'data'/name).read_bytes(),value)
            self.assertTrue(Store(target/'data').authenticate('chosen-admin','synthetic-pass'))
            self.assertIn('def create_app',(target/'app.py').read_text())
            backups=list((Path(d)/'maxs-menu-backups').iterdir())
            self.assertEqual(len(backups),1)
            self.assertEqual((backups[0]/'app.py').read_text(),'# older code\n')

    def test_custom_hotspot_and_interface_use_argument_values(self):
        nm=NM({'ssid':'My Cafe WiFi','interface':'wlx1234','enabled':True,'country':'CA'})
        with patch.object(nm,'run') as run:nm.configure('11111111-1111-1111-1111-111111111111','synthetic-wifi')
        args=run.call_args.args
        self.assertEqual(args[args.index('802-11-wireless.ssid')+1],'My Cafe WiFi')
        with patch.object(nm,'run',side_effect=['wlx1234:wifi','yes']):self.assertTrue(nm.capabilities()['hotspot_supported'])
        with self.assertRaises(ValueError):network_config({'ssid':'bad\nssid','enabled':True})
        with self.assertRaises(ValueError):network_config({'interface':'bad;name','enabled':True})

    def test_disabled_hotspot_does_not_probe_ap_support(self):
        nm=NM({'enabled':False})
        with patch.object(nm,'run',return_value='wlan0:wifi') as run:
            caps=nm.capabilities()
        self.assertFalse(caps['hotspot_supported'])
        self.assertEqual(run.call_count,1)

class ServiceInstallTests(unittest.TestCase):
    def test_fresh_hotspot_install_uses_chosen_identity_without_switching(self):
        import json
        from types import SimpleNamespace
        from test_network import FakeNM,HOME,AP
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);appdir=root/'app';appdir.mkdir()
            site={**SETTINGS,'hotspot_enabled':True,'hotspot_ssid':'Chosen Cafe WiFi'}
            initialize(appdir/'data',site,'chosen-admin','synthetic-pass','synthetic-wifi')
            for name in ['network_service.py','hotspot_service.py']:(appdir/name).write_bytes((ROOT/name).read_bytes())
            for name in ['etc/systemd/system','var/lib','usr/local/lib']:(root/name).mkdir(parents=True,exist_ok=True)
            def mapped(value):
                value=str(value)
                return root/value.lstrip('/') if value.startswith(('/etc/','/var/lib/','/usr/local/lib/')) else Path(value)
            nm=FakeNM()
            with patch.object(installer,'Path',side_effect=mapped),patch.object(installer,'DESTINATION',root/'usr/local/lib/maxs-menu-network'),patch.object(installer,'STATE_DIR',root/'var/lib/maxs-menu-network'),patch.object(installer,'preflight',return_value=(nm,HOME)),patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.pwd,'getpwuid',return_value=SimpleNamespace(pw_name='chosen-os-user',pw_uid=1000,pw_gid=1000)),patch.object(installer.os,'chown'),patch.object(installer.subprocess,'run') as run:
                installer.install(appdir)
            self.assertEqual(nm.current,HOME)
            self.assertEqual(nm.ssid,'Chosen Cafe WiFi')
            self.assertEqual(nm.saved_password,'synthetic-wifi')
            config=json.loads((root/'etc/maxs-menu-network.json').read_text())
            self.assertEqual(config['user'],'chosen-os-user');self.assertEqual(config['ssid'],'Chosen Cafe WiFi')
            state=json.loads((root/'var/lib/maxs-menu-network/state.json').read_text())
            self.assertEqual(state['confirmed'],HOME);self.assertEqual(state['hotspot'],AP)
            self.assertNotIn('initial_hotspot',json.loads((appdir/'data/menu-state.json').read_text()))
            self.assertFalse(any('start' in c.args[0] and 'maxs-menu-hotspot.service' in c.args[0] for c in run.call_args_list))
            for unit in ['maxs-menu-network.service','maxs-menu-hotspot.service']:
                text=(root/'etc/systemd/system'/unit).read_text()
                self.assertIn('ExecStart=/usr/bin/python3 /usr/local/lib/maxs-menu-network/',text)
            self.assertNotIn('synthetic-wifi',(root/'etc/maxs-menu-network.json').read_text())


if __name__=='__main__':unittest.main()
