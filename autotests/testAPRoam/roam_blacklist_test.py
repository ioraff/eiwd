#!/usr/bin/python3

import unittest
import sys

sys.path.append('../util')
import iwd
from iwd import IWD, IWD_CONFIG_DIR
from iwd import NetworkType

from hostapd import HostapdCLI
from hwsim import Hwsim

class Test(unittest.TestCase):
    def validate_connected(self, hostapd):
        ordered_network = self.device.get_ordered_network('TestAPRoam')

        self.assertEqual(ordered_network.type, NetworkType.psk)

        condition = 'not obj.connected'
        self.wd.wait_for_object_condition(ordered_network.network_object, condition)

        self.device.connect_bssid(hostapd.bssid)

        condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_condition(self.device, condition)

        hostapd.wait_for_event('AP-STA-CONNECTED')

    def validate_ap_roamed(self, from_hostapd, to_hostapd):
        from_hostapd.send_bss_transition(
            self.device.address, self.neighbor_list, disassoc_imminent=True
        )

        from_condition = 'obj.state == DeviceState.roaming'
        to_condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_change(self.device, from_condition, to_condition)

        to_hostapd.wait_for_event('AP-STA-CONNECTED %s' % self.device.address)

        self.device.wait_for_event("ap-roam-blacklist-added")

    def test_roam_to_optimal_candidates(self):
        # In this test IWD will naturally transition down the list after each
        # BSS gets roam blacklisted. All BSS's are above the RSSI thresholds.
        self.rule_ssid1.signal = -5000
        self.rule_ssid2.signal = -6500
        self.rule_ssid3.signal = -6900

        # Connect to BSS0
        self.validate_connected(self.bss_hostapd[0])

        # AP directed roam to BSS1
        self.validate_ap_roamed(self.bss_hostapd[0], self.bss_hostapd[1])

        # AP directed roam to BSS2
        self.validate_ap_roamed(self.bss_hostapd[1], self.bss_hostapd[2])

    def test_avoiding_under_threshold_bss(self):
        # In this test IWD will blacklist BSS0, then roam the BSS1. BSS1 will
        # then tell IWD to roam, but it should go back to BSS0 since the only
        # non-blacklisted BSS is under the roam threshold.
        self.rule_ssid1.signal = -5000
        self.rule_ssid2.signal = -6500
        self.rule_ssid3.signal = -7300

        # Connect to BSS0
        self.validate_connected(self.bss_hostapd[0])

        # AP directed roam to BSS1
        self.validate_ap_roamed(self.bss_hostapd[0], self.bss_hostapd[1])

        # AP directed roam, but IWD should choose BSS0 since BSS2 is -73dB
        self.validate_ap_roamed(self.bss_hostapd[1], self.bss_hostapd[0])

    def test_connect_to_roam_blacklisted_bss(self):
        # In this test a BSS will be roam blacklisted, but all other options are
        # below the RSSI threshold so IWD should roam back to the blacklisted
        # BSS.
        self.rule_ssid1.signal = -5000
        self.rule_ssid2.signal = -8000
        self.rule_ssid3.signal = -8500

        # Connect to BSS0
        self.validate_connected(self.bss_hostapd[0])

        # AP directed roam, should connect to BSS1 as its the next best
        self.validate_ap_roamed(self.bss_hostapd[0], self.bss_hostapd[1])

        # Connected to BSS1, but the signal is bad, so IWD should try to roam
        # again. BSS0 is still blacklisted, but its the only reasonable option
        # since both BSS1 and BSS2 are below the set RSSI threshold (-72dB)

        from_condition = 'obj.state == DeviceState.roaming'
        to_condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_change(self.device, from_condition, to_condition)

        # IWD should have connected to BSS0, even though its roam blacklisted
        self.bss_hostapd[0].wait_for_event('AP-STA-CONNECTED %s' % self.device.address)

    def test_blacklist_during_roam_scan(self):
        # Tests that an AP roam request mid-roam results in the AP still being
        # blacklisted even though the request itself doesn't directly trigger
        # a roam.
        self.rule_ssid1.signal = -7300
        self.rule_ssid2.signal = -7500
        self.rule_ssid3.signal = -8500

        # Connect to BSS0 under the roam threshold so IWD will immediately try
        # roaming elsewhere
        self.validate_connected(self.bss_hostapd[0])

        self.device.wait_for_event("roam-scan-triggered")

        self.bss_hostapd[0].send_bss_transition(
            self.device.address, self.neighbor_list, disassoc_imminent=True
        )
        self.device.wait_for_event("ap-roam-blacklist-added")

        # BSS0 should have gotten blacklisted even though IWD was mid-roam,
        # causing IWD to choose BSS1 when it gets is results.

        from_condition = 'obj.state == DeviceState.roaming'
        to_condition = 'obj.state == DeviceState.connected'
        self.wd.wait_for_object_change(self.device, from_condition, to_condition)

        self.bss_hostapd[1].wait_for_event('AP-STA-CONNECTED %s' % self.device.address)

    def setUp(self):
        self.wd = IWD(True)

        devices = self.wd.list_devices(1)
        self.device = devices[0]


    def tearDown(self):
        self.wd = None
        self.device = None


    @classmethod
    def setUpClass(cls):
        IWD.copy_to_storage("main.conf.roaming", IWD_CONFIG_DIR, "main.conf")
        IWD.copy_to_storage('TestAPRoam.psk')
        hwsim = Hwsim()

        cls.bss_hostapd = [ HostapdCLI(config='ssid1.conf'),
                            HostapdCLI(config='ssid2.conf'),
                            HostapdCLI(config='ssid3.conf') ]
        HostapdCLI.group_neighbors(*cls.bss_hostapd)

        rad0 = hwsim.get_radio('rad0')
        rad1 = hwsim.get_radio('rad1')
        rad2 = hwsim.get_radio('rad2')

        cls.neighbor_list = [
            (cls.bss_hostapd[0].bssid, "8f0000005101060603000000"),
            (cls.bss_hostapd[1].bssid, "8f0000005102060603000000"),
            (cls.bss_hostapd[2].bssid, "8f0000005103060603000000"),
        ]


        cls.rule_ssid1 = hwsim.rules.create()
        cls.rule_ssid1.source = rad0.addresses[0]
        cls.rule_ssid1.bidirectional = True
        cls.rule_ssid1.enabled = True

        cls.rule_ssid2 = hwsim.rules.create()
        cls.rule_ssid2.source = rad1.addresses[0]
        cls.rule_ssid2.bidirectional = True
        cls.rule_ssid2.enabled = True

        cls.rule_ssid3 = hwsim.rules.create()
        cls.rule_ssid3.source = rad2.addresses[0]
        cls.rule_ssid3.bidirectional = True
        cls.rule_ssid3.enabled = True

    @classmethod
    def tearDownClass(cls):
        IWD.clear_storage()

if __name__ == '__main__':
    unittest.main(exit=True)
