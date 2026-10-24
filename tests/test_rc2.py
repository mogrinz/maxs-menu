import contextlib
import copy
from datetime import datetime
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models import Store, format_clock, Forbidden, Conflict
from configure import initialize
from test_product import SETTINGS
import install_network_service as installer

ROOT=Path(__file__).resolve().parents[1]


class TimezoneTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        initialize(self.root,copy.deepcopy(SETTINGS),'manager','synthetic-admin')
        self.store=Store(self.root);self.admin=self.store.user('manager')

    def test_clock_format_and_meridiem(self):
        for hour,label in [(7,'7:00AM'),(0,'12:00AM'),(12,'12:00PM'),(19,'7:00PM')]:
            local=datetime(2026,12,18,hour,0,tzinfo=ZoneInfo('America/New_York'))
            self.assertEqual(format_clock(local,'America/New_York'),'Friday, Dec 18 2026 '+label+' America/New York')

    def test_timezone_validation_permissions_and_revision_conflicts(self):
        current=self.store.site_settings()
        self.store.set_timezone('America/Chicago',current['revision'],self.admin)
        with self.assertRaises(Conflict):self.store.set_timezone('America/Denver',current['revision'],self.admin)
        with self.assertRaises(ValueError):self.store.set_timezone('invalid/not-a-zone',self.store.site_settings()['revision'],self.admin)
        with self.assertRaises(Forbidden):self.store.set_timezone('UTC',self.store.site_settings()['revision'],{'role':'editor'})
        self.assertEqual(Store(self.root).site_settings()['timezone'],'America/Chicago')

    def test_timezone_change_affects_mapping_and_keeps_menu_and_rules(self):
        rule={'id':'rule','start':420,'end':660,'screen':'screen1','menu':'screen4'}
        self.store.set_schedule([rule],self.store.schedule()['revision'],self.admin)
        instant=datetime(2026,12,18,12,0,tzinfo=ZoneInfo('UTC'))
        self.assertEqual(self.store.display('screen1',instant)['menu_id'],'screen4')
        before=self.store.menu()['menu']
        self.store.set_timezone('America/Chicago',self.store.site_settings()['revision'],self.admin)
        self.assertEqual(self.store.display('screen1',instant)['menu_id'],'screen1')
        self.assertEqual(before,self.store.menu()['menu']);self.assertEqual(self.store.schedule()['rules'],[rule])

    def test_rc1_backup_restores_timezone(self):
        import backups
        value=backups.export_system(self.store,self.admin,{'ssid':'ExampleWiFi','password':''})
        value['app_version']='1.0.0-rc1'
        self.store.set_timezone('America/Chicago',self.store.site_settings()['revision'],self.admin)
        backups.restore_system(self.store,value,self.admin,backups.revision(self.store))
        self.assertEqual(self.store.site_settings()['timezone'],'America/New_York')

    def test_timezone_endpoint_and_loading_markup(self):
        from app import create_app
        app=create_app(self.root);client=app.test_client();client.get('/login')
        with client.session_transaction() as session:csrf=session['csrf']
        client.post('/login',data={'username':'manager','password':'synthetic-admin','csrf':csrf})
        with client.session_transaction() as session:csrf=session['csrf']
        page=client.get('/system').text
        self.assertIn('class="network-loading" aria-busy="true"',page)
        current=client.get('/api/admin/system/settings').json
        result=client.post('/api/admin/system/settings',json={'timezone':'Europe/London','revision':current['revision']},headers={'X-CSRF-Token':csrf})
        self.assertEqual(result.status_code,200);self.assertEqual(result.json['timezone'],'Europe/London')
        self.assertEqual(client.get('/api/admin/clock').json['timezone'],'Europe/London')


class Rc1UpgradeTests(unittest.TestCase):
    def test_rc1_fixture_survives_upgrade_in_version_named_folder(self):
        # Fixture schema/version matches the shipped RC1. Retain opaque values byte-for-byte.
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'maxs-menu-v1.0.0-rc1';target.mkdir()
            initialize(target/'data',copy.deepcopy(SETTINGS),'existing-admin','synthetic-existing')
            old=Store(target/'data');admin=old.user('existing-admin')
            old.manage_user(admin,'existing-staff','create','synthetic-staff',role='editor')
            draft=old.menu();draft['menu']['screens'][0]['rotation']=270
            draft['menu']['screens'][0]['items'][1]['price']='8.75'
            old.publish(draft['menu'],draft['revision'],admin)
            old.set_theme('spring-garden',old.menu()['theme_revision'],admin)
            rule={'id':'keep-rule','start':420,'end':660,'screen':'screen1','menu':'screen4'}
            old.set_schedule([rule],old.schedule()['revision'],admin)
            (target/'app.py').write_text('# RC1 existing service target\n')
            (target/'.menu.env').write_text('MENU_PORT=8090\n')
            before={p.name:p.read_bytes() for p in (target/'data').iterdir()}
            with patch.object(sys,'argv',['prepare_update.py',str(target)]),patch('os.geteuid',return_value=1000),patch('shutil.which',return_value=None),contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT/'prepare_update.py'),run_name='__main__')
            for name,data in before.items():self.assertEqual(data,(target/'data'/name).read_bytes(),name)
            updated=Store(target/'data')
            self.assertTrue(updated.authenticate('existing-admin','synthetic-existing'))
            self.assertTrue(updated.authenticate('existing-staff','synthetic-staff'))
            self.assertEqual(updated.menu()['menu']['screens'][0]['rotation'],270)
            self.assertEqual(updated.menu()['theme'],'spring-garden')
            self.assertEqual(updated.schedule()['rules'],[rule])
            self.assertEqual((target/'.menu.env').read_text(),'MENU_PORT=8090\n')

    def test_upgrade_script_uses_existing_service_directory(self):
        # Stubs execute the real shell flow without touching system services or installing packages.
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);stubs=base/'bin';stubs.mkdir();target=base/'old rc1';(target/'data').mkdir(parents=True)
            for name in ['users.json','menu-state.json']:(target/'data'/name).write_text('{}')
            log=base/'calls';release=base/'release';release.mkdir()
            for name in ['upgrade.sh','install_network_service.py','prepare_update.py']:(release/name).write_bytes((ROOT/name).read_bytes())
            (target/'setup.sh').write_text('echo setup >> "$CALLS"\n')
            for name,body in {
                'systemctl':'printf "%s\\n" "$TARGET"',
                'sudo':'printf "sudo:" >> "$CALLS"; printf "<%s>" "$@" >> "$CALLS"; echo >> "$CALLS"',
                'python3':'printf "python:" >> "$CALLS"; printf "<%s>" "$@" >> "$CALLS"; echo >> "$CALLS"',
            }.items():
                p=stubs/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
            import os
            env={**os.environ,'PATH':str(stubs)+':'+os.environ['PATH'],'TARGET':str(target),'CALLS':str(log)}
            result=subprocess.run(['bash',str(release/'upgrade.sh')],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            calls=log.read_text();self.assertIn('<'+str(target)+'>',calls)
            self.assertIn('setup',calls);self.assertIn('<install_service.py>',calls)

    def test_existing_rc1_network_config_is_preserved(self):
        from types import SimpleNamespace
        from test_network import FakeNM,HOME,AP
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);appdir=root/'app';appdir.mkdir()
            site={**SETTINGS,'hotspot_enabled':True,'hotspot_ssid':'Chosen Cafe WiFi'}
            initialize(appdir/'data',site,'existing-admin','synthetic-pass','synthetic-wifi')
            state=json.loads((appdir/'data/menu-state.json').read_text());state.pop('initial_hotspot')
            (appdir/'data/menu-state.json').write_text(json.dumps(state))
            for name in ['network_service.py','hotspot_service.py']:(appdir/name).write_bytes((ROOT/name).read_bytes())
            for name in ['etc/systemd/system','var/lib/maxs-menu-network','usr/local/lib']:(root/name).mkdir(parents=True,exist_ok=True)
            config={'user':'chosen-os-user','enabled':True,'ssid':'Chosen Cafe WiFi','interface':'wlan0','country':'US'}
            (root/'etc/maxs-menu-network.json').write_text(json.dumps(config))
            (root/'var/lib/maxs-menu-network/state.json').write_text(json.dumps({'hotspot':AP,'ssid':'Chosen Cafe WiFi','confirmed':HOME,'internet':HOME}))
            def mapped(value):
                value=str(value);return root/value.lstrip('/') if value.startswith(('/etc/','/var/lib/','/usr/local/lib/')) else Path(value)
            nm=FakeNM();nm.run=lambda *args:None;nm.saved_password='keep-existing-wifi'
            # This test simulates root services even when CI itself is unprivileged.
            # Preserve the production ownership check; fake only our private state dir.
            original_stat=Path.stat
            def root_stat(path,*args,**kwargs):
                result=original_stat(path,*args,**kwargs)
                if path==root/'var/lib/maxs-menu-network':
                    import os
                    values=list(result);values[4]=0
                    return os.stat_result(values)
                return result
            with patch.object(Path,'stat',autospec=True,side_effect=root_stat),patch.object(installer,'Path',side_effect=mapped),patch.object(installer,'DESTINATION',root/'usr/local/lib/maxs-menu-network'),patch.object(installer,'STATE_DIR',root/'var/lib/maxs-menu-network'),patch.object(installer,'preflight',return_value=(nm,HOME)),patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.pwd,'getpwuid',return_value=SimpleNamespace(pw_name='chosen-os-user',pw_uid=1000,pw_gid=1000)),patch.object(installer.os,'chown'),patch.object(installer.subprocess,'run'):
                installer.install(appdir)
            self.assertEqual(json.loads((root/'etc/maxs-menu-network.json').read_text()),config)
            self.assertFalse(nm.configured);self.assertEqual(nm.saved_password,'keep-existing-wifi')
            self.assertEqual(json.loads((root/'var/lib/maxs-menu-network/state.json').read_text())['hotspot'],AP)

class PackagingTests(unittest.TestCase):
    def test_archive_layout_manifest_exclusions_and_reproducibility(self):
        import hashlib
        import shutil
        import zipfile
        import build_release
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);source=base/'source'
            shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('__pycache__','.venv'))
            import secrets
            marker=secrets.token_hex(24)
            (source/'data').mkdir();(source/'data/users.json').write_text(marker)
            (source/'.menu.env').write_text(marker)
            (source/'private-backup.json').write_text(marker)
            with patch.object(build_release,'ROOT',source):
                first,_=build_release.build(base/'first.zip')
                second,_=build_release.build(base/'second.zip')
            self.assertEqual(first.read_bytes(),second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertTrue(all(n.startswith('maxs-menu/') for n in archive.namelist()))
                manifest=archive.read('maxs-menu/SHA256SUMS').decode().splitlines()
                for line in manifest:
                    checksum,name=line.split('  ',1)
                    data=archive.read('maxs-menu/'+name)
                    self.assertEqual(checksum,hashlib.sha256(data).hexdigest())
                    self.assertNotIn(marker.encode(),data)
                self.assertIn('maxs-menu/LICENSE',archive.namelist())
                self.assertNotIn('maxs-menu/data/users.json',archive.namelist())
                self.assertNotIn('maxs-menu/.menu.env',archive.namelist())


if __name__=='__main__':unittest.main()
