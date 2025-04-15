#!/usr/bin/python3

import unittest
import sys

sys.path.append('../util')
import iwd
from iwd import IWD
from iwd import NetworkType

from hostapd import HostapdCLI

class Test(unittest.TestCase):
    def initial_connection(self):
        ordered_network = self.device.get_ordered_network('TestAPRoam')

        self.assertEqual(ordered_network.type, NetworkType.psk)

        condition = 'not obj.connected'
        self.wd.wait_for_object_condition(ordered_network.network_object, condition)

        self.device.connect_bssid(self.bss_hostapd[0].bssid)

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

        self.bss_hostapd[0].wait_for_event('AP-STA-CONNECTED')

        self.assertFalse(self.bss_hostapd[1].list_sta())

    def validate_roam(self, from_bss, to_bss, expect_roam=True):
        from_bss.send_bss_transition(self.device.address,
                self.neighbor_list,
                disassoc_imminent=expect_roam)

        if expect_roam:
            from_condition = 'obj.state == DeviceState.roaming'
            to_condition = 'obj.state == DeviceState.connected'
            self.wd.wait_for_object_change(self.device, from_condition, to_condition)

            to_bss.wait_for_event('AP-STA-CONNECTED %s' % self.device.address)
        else:
            self.device.wait_for_event("no-roam-candidates")

    def test_disassoc_imminent(self):
        self.initial_connection()
        self.validate_roam(self.bss_hostapd[0], self.bss_hostapd[1])

    def test_no_candidates(self):
        self.initial_connection()
        # We now have BSS0 roam blacklisted
        self.validate_roam(self.bss_hostapd[0], self.bss_hostapd[1])
        # Try and trigger another roam back, which shouldn't happen since now
        # both BSS's are roam blacklisted
        self.validate_roam(self.bss_hostapd[1], self.bss_hostapd[0], expect_roam=False)

    def setUp(self):
        self.wd = IWD(True)

        devices = self.wd.list_devices(1)
        self.device = devices[0]

    def tearDown(self):
        self.wd = None
        self.device = None

    @classmethod
    def setUpClass(cls):
        IWD.copy_to_storage('TestAPRoam.psk')

        cls.bss_hostapd = [ HostapdCLI(config='ssid1.conf'),
                            HostapdCLI(config='ssid2.conf'),
                            HostapdCLI(config='ssid3.conf') ]
        cls.neighbor_list = [
            (cls.bss_hostapd[0].bssid, "8f0000005101060603000000"),
            (cls.bss_hostapd[1].bssid, "8f0000005102060603000000"),
        ]

    @classmethod
    def tearDownClass(cls):
        IWD.clear_storage()

if __name__ == '__main__':
    unittest.main(exit=True)
