import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from configure import initialize
from app import create_app
from models import Store, make_user, validate_schedule, validate_menu, atomic_json, read_json, Forbidden, Conflict
import backups
from reset_admin import reset

SETTINGS={'site_name':'Example Cafe','timezone':'America/New_York','hotspot_enabled':False,
          'hotspot_ssid':'ExampleWiFi','wifi_interface':'wlan0','country':'US'}


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        initialize(self.root,copy.deepcopy(SETTINGS),'manager','synthetic-admin')
        self.app=create_app(self.root);self.app.testing=True
        self.store=self.app.extensions['store'];self.admin=self.store.user('manager')
        self.client=self.app.test_client();self.login(self.client,'manager','synthetic-admin')

    def login(self,client,name,password):
        client.get('/login')
        with client.session_transaction() as session:csrf=session['csrf']
        return client.post('/login',data={'username':name,'password':password,'csrf':csrf})

    def post(self,path,body,client=None):
        client=client or self.client
        with client.session_transaction() as session:csrf=session['csrf']
        return client.post(path,json=body,headers={'X-CSRF-Token':csrf})

    def employee(self):
        self.store.manage_user(self.admin,'staff','create','synthetic-staff',role='editor')
        client=self.app.test_client();self.login(client,'staff','synthetic-staff');return client

    def rule(self,**kwargs):
        return {'id':'r1','start':420,'end':660,'screen':'screen1','menu':'screen4',**kwargs}

    def test_fresh_setup_has_no_default_or_hidden_account(self):
        self.assertEqual([u['username'] for u in self.store.users()],['manager'])
        self.assertEqual(len(self.store.menu()['menu']['screens']),10)
        self.assertFalse((self.root/'recovery-admin.json').exists())
        self.assertNotIn('synthetic-admin',(self.root/'users.json').read_text())
        self.assertEqual((self.root/'users.json').stat().st_mode&0o777,0o600)

    def test_repeated_setup_refuses_to_overwrite(self):
        before=(self.root/'users.json').read_bytes()
        with self.assertRaises(ValueError):initialize(self.root,SETTINGS,'other','different')
        self.assertEqual(before,(self.root/'users.json').read_bytes())

    def test_restarting_retains_all_settings(self):
        draft=self.store.menu();draft['menu']['screens'][0]['rotation']=90
        self.store.publish(draft['menu'],draft['revision'],self.admin)
        self.store.set_schedule([self.rule()],self.store.schedule()['revision'],self.admin)
        new=Store(self.root)
        self.assertEqual(new.menu()['menu']['screens'][0]['rotation'],90)
        self.assertEqual(new.schedule()['rules'][0]['menu'],'screen4')
        self.assertTrue(new.authenticate('manager','synthetic-admin'))

    def test_all_public_urls_and_case_compatibility(self):
        for i in range(1,11):
            self.assertEqual(self.client.get('/display/Screen'+str(i)).status_code,200)
            self.assertEqual(self.client.get('/api/display/screen'+str(i)).json['menu_id'],'screen'+str(i))
        self.assertEqual(self.client.get('/display/screen11').status_code,404)
        public=json.dumps(self.client.get('/api/display/screen1').json)
        for field in ['password_hash','token','settings','users']:self.assertNotIn(field,public)

    def test_boundary_schedule_default_and_direct_preview(self):
        self.store.set_schedule([self.rule()],self.store.schedule()['revision'],self.admin)
        for hour,minute,expected in [(6,59,'screen1'),(7,0,'screen4'),(10,59,'screen4'),(11,0,'screen1')]:
            instant=datetime(2026,10,15,hour+4,minute,tzinfo=timezone.utc)
            self.assertEqual(self.store.display('screen1',instant)['menu_id'],expected)
            self.assertEqual(self.store.display('screen1',instant,direct=True)['menu_id'],'screen1')
            self.assertEqual(self.store.display('screen2',instant)['menu_id'],'screen2')

    def test_overnight_adjacent_rules_and_overlaps(self):
        night=self.rule(start=1320,end=120)
        validate_schedule([night,self.rule(id='r2',start=120,end=420)])
        for start,end in [(0,30),(1380,0),(90,150)]:
            with self.assertRaises(ValueError):validate_schedule([night,self.rule(id='r2',start=start,end=end)])
        for start,end in [(420,420),(421,660),(False,60),(0,1440)]:
            with self.assertRaises(ValueError):validate_schedule([self.rule(start=start,end=end)])
        self.store.set_schedule([night],self.store.schedule()['revision'],self.admin)
        self.assertEqual(self.store.display('screen1',datetime(2026,10,15,5,tzinfo=timezone.utc))['menu_id'],'screen4')

    def test_rotation_validation_and_employee_permission(self):
        employee=self.employee()
        draft=self.client.get('/api/admin/menu').json
        draft['menu']['screens'][0]['rotation']=90
        self.assertEqual(self.post('/api/admin/menu',{'menu':draft['menu'],'revision':draft['revision']},employee).status_code,403)
        self.assertEqual(self.post('/api/admin/menu',{'menu':draft['menu'],'revision':draft['revision']}).status_code,200)
        draft['menu']['screens'][0]['rotation']=45
        with self.assertRaises(ValueError):validate_menu(draft['menu'])

    def test_employee_can_publish_but_cannot_escalate(self):
        employee=self.employee()
        for path in ['/users','/system','/theme','/schedule','/api/admin/users','/api/admin/schedule','/api/admin/system/backup']:
            self.assertEqual(employee.get(path).status_code,403,path)
        self.assertEqual(self.post('/api/admin/password',{'new_password':'changed','confirm_password':'changed'},employee).status_code,403)
        draft=employee.get('/api/admin/menu').json;draft['menu']['screens'][0]['items'][1]['price']='2.25'
        self.assertEqual(self.post('/api/admin/menu',{'menu':draft['menu'],'revision':draft['revision']},employee).status_code,200)
        self.assertNotIn('name="rotation"',employee.get('/admin').text)

    def test_equal_admins_and_last_admin_guard(self):
        self.store.manage_user(self.admin,'second','create','synthetic-second',role='admin')
        other=self.store.user('second')
        self.store.manage_user(other,'manager','password','reset-by-peer')
        self.assertTrue(self.store.authenticate('manager','reset-by-peer'))
        self.store.manage_user(other,'manager','delete')
        with self.assertRaises(ValueError):self.store.manage_user(other,'second','enabled',enabled=False)
        with self.assertRaises(ValueError):self.store.manage_user(other,'second','role',role='editor')
        with self.assertRaises(ValueError):self.store.manage_user(other,'second','delete')

    def test_local_recovery_resets_and_invalidates_sessions(self):
        reset(self.root,'manager','new-local-password')
        self.assertTrue(self.store.authenticate('manager','new-local-password'))
        self.assertEqual(self.client.get('/api/admin/menu').status_code,401)
        self.assertEqual([u['username'] for u in self.store.users()],['manager'])

    def test_backup_restores_accounts_schedule_site_rotation_and_theme(self):
        draft=self.store.menu();draft['menu']['screens'][3]['rotation']=270
        self.store.publish(draft['menu'],draft['revision'],self.admin)
        self.store.set_schedule([self.rule()],self.store.schedule()['revision'],self.admin)
        self.store.set_theme('seaside-cafe',self.store.menu()['theme_revision'],self.admin)
        value=backups.export_system(self.store,self.admin,{'ssid':'RestoredWiFi','password':'synthetic-wifi'})
        self.assertNotIn('token',json.dumps(value))
        otherdir=self.root/'replacement';initialize(otherdir,SETTINGS,'replacement','synthetic-other')
        target=Store(otherdir);user=target.user('replacement')
        files,summary=backups.prepare_system(target,value,user)
        self.assertEqual(summary['rules'],1);self.assertEqual(summary['login_username'],'manager')
        backups.restore_system(target,value,user,backups.revision(target))
        self.assertTrue(target.authenticate('manager','synthetic-admin'))
        self.assertIsNone(target.user('replacement'))
        self.assertEqual(target.menu()['menu']['screens'][3]['rotation'],270)
        self.assertEqual(target.menu()['theme'],'seaside-cafe')
        self.assertEqual(target.state()['pending_hotspot']['ssid'],'RestoredWiFi')
        self.assertFalse(target.state()['settings']['hotspot_enabled'])

    def test_restore_preview_confirmation_and_stale_revision(self):
        value=backups.export_system(self.store,self.admin,{'ssid':'ExampleWiFi','password':''})
        with patch('app.request_network') as net:
            result=self.post('/api/admin/system/restore/preview',{'backup':value})
            self.assertEqual(result.status_code,200)
            self.assertEqual(self.post('/api/admin/system/restore',{'backup':value,'revision':result.json['revision'],'confirmation':'wrong'}).status_code,400)
            self.store.set_schedule([self.rule()],self.store.schedule()['revision'],self.admin)
            self.assertEqual(self.post('/api/admin/system/restore',{'backup':value,'revision':result.json['revision'],'confirmation':'RESTORE'}).status_code,409)
            net.assert_not_called()

    def test_backup_rejects_missing_admin_and_invalid_schedule(self):
        value=backups.export_system(self.store,self.admin,{'ssid':'ExampleWiFi','password':''})
        invalid=copy.deepcopy(value);invalid['users'][0]['role']='editor'
        with self.assertRaises(ValueError):backups.prepare_system(self.store,invalid,self.admin)
        invalid=copy.deepcopy(value);invalid['state']['schedule']=[self.rule(),self.rule(id='r2')]
        with self.assertRaises(ValueError):backups.prepare_system(self.store,invalid,self.admin)

    def test_system_backup_without_hotspot_needs_no_network_service(self):
        with patch('app.request_network',side_effect=RuntimeError('not installed')):
            result=self.client.get('/api/admin/system/backup')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['format_version'],2)

    def test_authentication_csrf_and_origin(self):
        anonymous=self.app.test_client()
        self.assertEqual(anonymous.get('/api/admin/menu').status_code,401)
        self.assertEqual(self.client.post('/api/admin/schedule',json={}).status_code,403)
        with self.client.session_transaction() as session:csrf=session['csrf']
        self.assertEqual(self.client.post('/api/admin/schedule',json={},headers={'X-CSRF-Token':csrf,'Origin':'https://other.invalid'}).status_code,403)

    def test_history_exports_and_restores_collection(self):
        draft=self.store.menu();draft['menu']['screens'][9]['items']=[]
        self.store.publish(draft['menu'],draft['revision'],self.admin)
        record=self.store.state()['history'][0]
        result=self.client.get('/api/admin/history/'+record['id']+'/download')
        self.assertEqual(result.status_code,200)
        self.assertEqual(len(result.json['menu']['screens']),10)
        self.store.restore(record['id'],self.store.menu()['revision'],self.admin)

    def test_restore_transaction_failure_rolls_back(self):
        value=backups.export_system(self.store,self.admin,{'ssid':'ExampleWiFi','password':''})
        files,_=backups.prepare_system(self.store,value,self.admin)
        before=self.store.state()
        original=self.store._restore_files;calls=[]
        def fail_once(rows):
            calls.append(1)
            if len(calls)==1:
                atomic_json(self.store.users_path,files['users.json'])
                raise OSError('simulated disk failure')
            return original(rows)
        with patch.object(self.store,'_restore_files',side_effect=fail_once):
            with self.assertRaises(OSError):self.store.commit_restore(files)
        self.assertEqual(self.store.state(),before)
        self.assertTrue(self.store.authenticate('manager','synthetic-admin'))
        self.assertFalse(self.store.restore_journal.exists())

    def test_schedule_revision_conflicts(self):
        revision=self.store.schedule()['revision']
        self.store.set_schedule([self.rule()],revision,self.admin)
        with self.assertRaises(Conflict):self.store.set_schedule([],revision,self.admin)

    def test_new_themes_can_be_selected_and_rendered(self):
        for theme in ['starlight-cafe','seaside-cafe','autumn-harvest','winter-hearth','spring-garden']:
            self.store.set_theme(theme,self.store.menu()['theme_revision'],self.admin)
            self.assertEqual(self.client.get('/api/display/screen1').json['theme'],theme)


if __name__=='__main__':unittest.main()
