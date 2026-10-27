import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from configure import initialize
from app import create_app
from models import Store, validate_menu, validate_settings, DEFAULT_PRICING, Forbidden, Conflict, atomic_json
from test_product import SETTINGS
import backups


class ReleaseThreeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        initialize(self.root,copy.deepcopy(SETTINGS),'manager','synthetic-admin')
        self.app=create_app(self.root);self.store=self.app.extensions['store']
        self.admin=self.store.user('manager');self.client=self.app.test_client()
        self.client.get('/login')
        with self.client.session_transaction() as session:csrf=session['csrf']
        self.client.post('/login',data={'username':'manager','password':'synthetic-admin','csrf':csrf})
        with self.client.session_transaction() as session:self.csrf=session['csrf']

    def post(self,path,value):
        return self.client.post(path,json=value,headers={'X-CSRF-Token':self.csrf})

    def test_samples_have_three_columns_unique_ids_and_positive_prices(self):
        menu=self.store.menu()['menu'];validate_menu(menu)
        for n in [3,4]:
            rows=menu['screens'][n]['items']
            self.assertEqual({r['column'] for r in rows},{1,2,3})
            self.assertTrue(rows[0]['starts_section']);self.assertEqual(rows[0]['layout'],'three')
            self.assertEqual(sum(bool(r.get('starts_section')) for r in rows),1)
            self.assertTrue(all(float(r['price'])>0 for r in rows if r['kind']=='item'))
            self.assertGreater(sum(r['kind']=='header' for r in rows),3)

    def test_price_precision_layout_and_column_validation(self):
        base=self.store.menu()['menu']
        for amount in ['1.234','9999999.999','','0.00','-1.50',None]:
            value=copy.deepcopy(base);value['screens'][3]['items'][1]['price']=amount
            validate_menu(value)
        for amount in ['1.2345','nan','1e3',5.0,'10000000.00']:
            value=copy.deepcopy(base);value['screens'][3]['items'][1]['price']=amount
            with self.assertRaises(ValueError):validate_menu(value)
        for key,value in [('column',4),('column',True),('layout','four')]:
            menu=copy.deepcopy(base);menu['screens'][3]['items'][0][key]=value
            with self.assertRaises(ValueError):validate_menu(menu)

    def test_pricing_permissions_validation_and_independent_revision(self):
        before=self.store.menu()['menu'];clock=self.store.site_settings();current=self.store.pricing()
        self.assertEqual(current['pricing'],DEFAULT_PRICING)
        selected={'currency':'EUR','locale':'de-DE'}
        self.store.set_timezone('UTC',clock['revision'],self.admin)
        self.store.set_pricing(selected,current['revision'],self.admin)
        self.assertEqual(self.store.menu()['menu'],before)
        self.assertEqual(Store(self.root).pricing()['pricing'],selected)
        self.assertEqual(self.store.site_settings()['timezone'],'UTC')
        with self.assertRaises(Conflict):self.store.set_pricing(DEFAULT_PRICING,current['revision'],self.admin)
        with self.assertRaises(Forbidden):self.store.set_pricing(selected,self.store.pricing()['revision'],{'role':'editor'})
        for bad in [{'currency':'BAD','locale':'de-DE'},{'currency':'EUR','locale':'bad'}, {'currency':[],'locale':'de-DE'}, {'currency':'EUR'}]:
            with self.assertRaises(ValueError):self.store.set_pricing(bad,self.store.pricing()['revision'],self.admin)

    def test_pricing_refreshes_all_public_displays_and_no_private_data(self):
        before=[self.store.display('screen'+str(n))['revision'] for n in range(1,11)]
        value={'currency':'KWD','locale':'en-GB'}
        response=self.post('/api/admin/system/pricing',{'pricing':value,'revision':self.store.pricing()['revision']})
        self.assertEqual(response.status_code,200)
        for n in range(1,11):
            data=self.client.get('/api/display/screen'+str(n)).json
            self.assertNotEqual(data['revision'],before[n-1]);self.assertEqual(data['pricing'],value)
            self.assertEqual(set(data),{'content','menu_id','theme','pricing','revision'})
        self.assertEqual(self.client.get('/api/admin/menu').json['pricing'],value)
        with self.client.session_transaction() as session:session['csrf']='changed'
        self.assertEqual(self.post('/api/admin/system/pricing',{}).status_code,403)

    def test_employee_cannot_change_currency_but_can_fetch_sample_draft(self):
        self.store.manage_user(self.admin,'staff','create','synthetic-staff',role='editor')
        with self.client.session_transaction() as session:
            staff=self.store.user('staff');session['username']='staff';session['token']=staff['token']
        self.assertEqual(self.client.get('/api/admin/system/pricing').status_code,403)
        self.assertEqual(self.post('/api/admin/system/pricing',{'pricing':DEFAULT_PRICING,'revision':self.store.pricing()['revision']}).status_code,403)
        before=self.store.menu()
        self.assertEqual(self.client.get('/api/admin/menu/sample/screen4').status_code,200)
        self.assertEqual(self.client.get('/api/admin/menu/sample/screen5').status_code,200)
        self.assertEqual(self.client.get('/api/admin/menu/sample/screen1').status_code,400)
        self.assertEqual(self.store.menu(),before)

    def test_system_backup_preserves_currency_and_three_columns(self):
        selected={'currency':'JPY','locale':'ja-JP'}
        self.store.set_pricing(selected,self.store.pricing()['revision'],self.admin)
        backup=backups.export_system(self.store,self.admin,{'ssid':'ExampleWiFi','password':''})
        self.store.set_pricing(DEFAULT_PRICING,self.store.pricing()['revision'],self.admin)
        backups.restore_system(self.store,backup,self.admin,backups.revision(self.store))
        self.assertEqual(Store(self.root).pricing()['pricing'],selected)
        self.assertEqual(backups.menu_file(backup['state']['menu'])['menu'],self.store.menu()['menu'])
        # Existing RC2 backups have no pricing key and must still restore as USD.
        del backup['state']['settings']['pricing'];backup['app_version']='1.0.0-rc2'
        backups.restore_system(self.store,backup,self.admin,backups.revision(self.store))
        self.assertEqual(self.store.pricing()['pricing'],DEFAULT_PRICING)

    def test_upgrade_does_not_populate_empty_or_overwrite_existing_menus(self):
        state=self.store.state();state['menu']['screens'][3]['items']=[]
        state['menu']['screens'][4]['items'][1]['price']='7.25'
        atomic_json(self.root/'menu-state.json',state);atomic_json(self.root/'menu.json',state['menu'])
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        new=Store(self.root)
        for name,data in before.items():self.assertEqual((self.root/name).read_bytes(),data)
        self.assertEqual(new.menu()['menu']['screens'][3]['items'],[])
        self.assertEqual(new.menu()['menu']['screens'][4]['items'][1]['price'],'7.25')


if __name__=='__main__':unittest.main()
