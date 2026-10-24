import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from network_service import Controller, NM, write_json

HOME = '11111111-1111-1111-1111-111111111111'
AP = '22222222-2222-2222-2222-222222222222'


class FakeNM:
    def __init__(self):
        self.current = HOME
        self.settings={'enabled':True}
        self.ssid='TestMenu'
        self.failure = None
        self.preferences = []
        self.configured = False
        self.saved_password = ''

    def capabilities(self):
        return {'wifi_control':True,'hotspot_supported':True,'ethernet_interfaces':[],'hotspot_reason':''}

    def wired_info(self):
        return []

    def profiles(self):
        return [{'uuid':HOME,'name':'shop-wifi','mode':'infrastructure'},
                {'uuid':AP,'name':'maxs-menu-hotspot','mode':'ap'}]

    def active(self):
        return self.current

    def addresses(self):
        return ['192.168.50.1' if self.current==AP else '192.168.1.20']

    def configure(self, uuid, password, ssid):
        self.ssid=ssid
        self.configured = True
        self.saved_password = password
        return AP

    def password(self, uuid):
        return self.saved_password

    def activate(self, uuid):
        if uuid==self.failure:
            raise ValueError('Activation failed')
        self.current = uuid

    def preference(self, uuid, enabled):
        self.preferences.append((uuid,enabled))


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'state.json'
        self.nm = FakeNM()
        self.now = 1000
        self.queue = []
        self.controller = Controller(self.nm,self.path,lambda:self.now,self.queue.append)
        self.controller.state = {'internet':HOME}
        self.controller.save()

    def tearDown(self):
        self.temp.cleanup()

    def configure(self):
        self.controller.dispatch({'action':'configure','ssid':'TestMenu','password':'trial-password'})

    def switch(self,mode='hotspot'):
        return self.controller.dispatch({'action':'switch','mode':mode,'profile':'' if mode=='hotspot' else HOME})

    def run_queue(self):
        self.queue.pop(0)()

    def test_configuration_leaves_current_network_and_hides_password(self):
        self.configure()
        self.assertEqual(self.nm.current,HOME)
        self.assertNotIn('trial-password',self.path.read_text())
        self.assertNotIn('trial-password',json.dumps(self.controller.status()))
        self.assertTrue(self.controller.status()['hotspot_ready'])

    def test_saved_password_only_returned_on_explicit_credentials_request(self):
        self.assertEqual(self.controller.dispatch({'action':'credentials'}),{'password':'','ssid':'TestMenu'})
        self.configure()
        self.assertEqual(self.controller.dispatch({'action':'credentials'}),{'password':'trial-password','ssid':'TestMenu'})
        self.assertNotIn('trial-password',json.dumps(self.controller.status()))

    def test_confirmed_mode_retried_after_temporary_startup_failure(self):
        self.configure()
        self.controller.state['confirmed']=AP
        self.nm.failure=AP
        self.controller.tick()
        self.assertEqual(self.nm.current,HOME)
        self.nm.failure=None
        self.now+=31
        self.controller.tick()
        self.assertEqual(self.nm.current,AP)

    def test_switch_is_deferred_confirmed_and_restored_at_boot(self):
        self.configure();self.switch()
        self.assertEqual(self.nm.current,HOME)
        self.assertTrue(self.controller.busy)
        self.run_queue();self.assertEqual(self.nm.current,AP)
        pending=self.controller.status()['pending']
        self.assertTrue(pending['active'])
        self.controller.dispatch({'action':'confirm','id':pending['id']})
        self.assertNotIn('pending',self.controller.state)
        self.assertEqual(self.controller.state['confirmed'],AP)
        self.nm.current=HOME
        restarted=Controller(self.nm,self.path)
        restarted.recover_startup()
        self.assertEqual(self.nm.current,AP)

    def test_expiry_restores_previous_network(self):
        self.configure();self.switch();self.run_queue();self.now+=181
        self.controller.tick()
        self.assertEqual(self.nm.current,HOME)
        self.assertNotIn('pending',self.controller.state)

    def test_failed_target_immediately_rolls_back(self):
        self.configure();self.nm.failure=AP;self.switch();self.run_queue()
        self.assertEqual(self.nm.current,HOME)
        self.assertNotIn('pending',self.controller.state)

    def test_restart_during_trial_rolls_back_even_before_deadline(self):
        self.configure();self.switch();self.run_queue()
        restarted=Controller(self.nm,self.path)
        restarted.recover_startup()
        self.assertEqual(self.nm.current,HOME)
        self.assertNotIn('pending',restarted.state)

    def test_cancel_is_deferred_and_recovers(self):
        self.configure();self.switch();self.run_queue()
        self.controller.dispatch({'action':'cancel','id':self.controller.state['pending']['id']})
        self.assertEqual(self.nm.current,AP)
        self.run_queue();self.assertEqual(self.nm.current,HOME)

    def test_failed_rollback_is_retained_and_retried(self):
        self.configure();self.switch();self.run_queue();self.nm.failure=HOME;self.now+=181
        self.controller.tick();self.assertIn('pending',self.controller.state)
        self.nm.failure=None;self.controller.tick()
        self.assertEqual(self.nm.current,HOME)
        self.assertNotIn('pending',self.controller.state)

    def test_cannot_confirm_before_target_or_after_expiry(self):
        self.configure();self.switch();pending=self.controller.state['pending']
        self.controller.busy=False
        with self.assertRaises(ValueError):self.controller.dispatch({'action':'confirm','id':pending['id']})
        self.run_queue();self.now+=181
        with self.assertRaises(ValueError):self.controller.dispatch({'action':'confirm','id':pending['id']})
        self.controller.tick()

    def test_reject_arbitrary_commands_profiles_and_invalid_passwords(self):
        for body in [{'action':'shell','command':'reboot'}, {'action':'configure','ssid':'TestMenu','password':'short'},
                     {'action':'configure','ssid':'TestMenu','password':'password\nsecret'}, {'action':'configure','ssid':'TestMenu','password':'a'*64},
                     {'action':'status','command':'whoami'}, {'action':'switch','mode':'internet','profile':'unrelated'}]:
            with self.assertRaises(ValueError):self.controller.dispatch(body)
        self.assertEqual(self.nm.current,HOME)

    def test_cannot_reconfigure_active_hotspot_or_start_overlapping_trial(self):
        self.configure();self.switch();self.run_queue()
        with self.assertRaises(ValueError):self.configure()
        with self.assertRaises(ValueError):self.switch('internet')

    def test_switch_back_to_saved_internet(self):
        self.configure();self.switch();self.run_queue()
        self.controller.dispatch({'action':'confirm','id':self.controller.state['pending']['id']})
        self.switch('internet');self.run_queue()
        self.controller.dispatch({'action':'confirm','id':self.controller.state['pending']['id']})
        self.assertEqual(self.nm.current,HOME)
        self.assertEqual(self.controller.state['confirmed'],HOME)

    def test_nm_uses_argument_arrays_and_redacts_command_errors(self):
        class Result:
            returncode=1
            stdout=''
            stderr='sensitive password'
        with patch('network_service.subprocess.run',return_value=Result()) as run:
            with self.assertRaises(ValueError) as error:NM({'enabled':True}).run('connection','modify','uuid',AP,'wifi-sec.psk','sensitive password')
            self.assertNotIn('sensitive password',str(error.exception))
            self.assertIsInstance(run.call_args.args[0],list)
            self.assertNotIn('shell',run.call_args.kwargs)

    def test_local_socket_client_round_trip_and_service_errors(self):
        import socket
        import threading
        from network_client import request_network
        path=str(Path(self.temp.name)/'control.sock')
        try:
            probe=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            probe.close()
        except PermissionError:
            self.skipTest('This runtime blocks Unix domain sockets; run this check on the Pi.')
        for response in [{'mode':'internet'},{'error':'Trial already pending'}]:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
                listener.bind(path);listener.listen(1)
                received=[]
                def server():
                    connection,_=listener.accept()
                    with connection:
                        stream=connection.makefile('rb')
                        received.append(json.loads(stream.readline()))
                        stream.close()
                        connection.sendall(json.dumps(response).encode()+b'\n')
                thread=threading.Thread(target=server);thread.start()
                with patch('network_client.SOCKET',path):
                    if 'error' in response:
                        with self.assertRaises(ValueError):request_network({'action':'status'})
                    else:self.assertEqual(request_network({'action':'status'}),response)
                thread.join(timeout=2)
                self.assertEqual(received,[{'action':'status'}])
            Path(path).unlink()


if __name__=='__main__':unittest.main()
