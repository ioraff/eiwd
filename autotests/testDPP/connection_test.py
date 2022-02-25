#!/usr/bin/python3

import unittest
import sys

sys.path.append('../util')
from iwd import IWD
from wpas import Wpas
from hostapd import HostapdCLI
from hwsim import Hwsim

class Test(unittest.TestCase):
    def test_iwd_as_enrollee(self):
        self.device.autoconnect = True
        self.hapd.reload()

        uri = self.device.dpp_start_enrollee()

        self.wpas.dpp_configurator_create(uri)
        self.wpas.dpp_configurator_start('ssidCCMP', 'secret123')

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

    def test_iwd_as_enrollee_channel_switch(self):
        self.device.autoconnect = True
        self.hapd.reload()

        uri = self.device.dpp_start_enrollee()

        self.wpas.dpp_configurator_create(uri)
        self.wpas.dpp_configurator_start('ssidCCMP', 'secret123', freq=2462)

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

    def test_iwd_as_enrollee_scan_after(self):
        self.wpas.disconnect()
        uri = self.device.dpp_start_enrollee()

        self.wpas.dpp_configurator_create(uri)
        self.wpas.dpp_configurator_start('ssidCCMP', 'secret123')

        self.hapd.reload()

        with self.assertRaises(Exception):
            self.device.get_ordered_network('ssidCCMP', scan_if_needed=False)

        self.hapd.wait_for_event('AP-ENABLED')

        self.device.autoconnect = True

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

    def test_iwd_as_enrollee_no_ack(self):
        self.rule0.enabled = True
        self.device.autoconnect = True
        self.hapd.reload()

        uri = self.device.dpp_start_enrollee()

        self.wpas.dpp_configurator_create(uri)
        self.wpas.dpp_configurator_start('ssidCCMP', 'secret123')

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

    def test_iwd_as_configurator(self):
        self.hapd.reload()
        self.hapd.wait_for_event('AP-ENABLED')

        IWD.copy_to_storage('ssidCCMP.psk')
        self.device.autoconnect = True

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

        uri = self.device.dpp_start_configurator()

        self.wpas.dpp_enrollee_start(uri)

        self.wpas.wait_for_event('DPP-CONF-RECEIVED')

    def test_iwd_as_configurator_initiator(self):
        self.hapd.reload()
        self.hapd.wait_for_event('AP-ENABLED')

        IWD.copy_to_storage('ssidCCMP.psk')
        self.device.autoconnect = True

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

        uri = self.wpas.dpp_enrollee_start(oper_and_channel='81/2')

        self.device.dpp_start_configurator(uri)

        self.hapd.wait_for_event('AP-STA-CONNECTED 42:00:00:00:00:00')

    def setUp(self):
        self.wd = IWD(True)
        self.device = self.wd.list_devices(1)[0]
        self.wpas = Wpas('wpas.conf')
        self.hapd = HostapdCLI('hostapd.conf')
        self.hapd.disable()
        self.hwsim = Hwsim()

        self.rule0 = self.hwsim.rules.create()
        self.rule0.prefix = 'd0'
        self.rule0.match_offset = 24
        self.rule0.match = '04 09 50 6f 9a 1a 01 01'
        self.rule0.match_times = 1
        self.rule0.drop = True

    def tearDown(self):
        print("calling Disconnect()")
        self.device.disconnect()
        self.device.dpp_stop()
        self.wpas.dpp_configurator_remove()

        self.wd = None
        self.device = None
        self.wpas = None
        self.hapd = None
        self.rule0 = None
        IWD.clear_storage()

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

if __name__ == '__main__':
    unittest.main(exit=True)
