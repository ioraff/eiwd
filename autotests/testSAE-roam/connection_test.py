#! /usr/bin/python3

import unittest
import sys, os

sys.path.append('../util')
import iwd
from iwd import IWD
from iwd import PSKAgent
from iwd import NetworkType
from hostapd import HostapdCLI
import testutil
from config import ctx

class Test(unittest.TestCase):
    def connect(self, wd, device, hapd):
        # This won't guarantee all BSS's are found, but at least ensures that
        # at least one will be.
        device.get_ordered_network('TestFT', full_scan=True)

        self.assertFalse(hapd.list_sta())

        device.connect_bssid(hapd.bssid)

        condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_condition(device, condition)

        hapd.wait_for_event('AP-STA-CONNECTED %s' % device.address)

        self.assertFalse(self.bss_hostapd[1].list_sta())

        testutil.test_iface_operstate(device.name)
        testutil.test_ifaces_connected(hapd.ifname, device.name)

    def roam(self, wd, device, hapd_from, hapd_to):
        device.roam(hapd_to.bssid)

        # Check that iwd is on hapd_to once out of roaming state and doesn't
        # go through 'disconnected', 'autoconnect', 'connecting' in between
        from_condition = 'obj.state == DeviceState.roaming'
        to_condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_change(device, from_condition, to_condition)

        hapd_to.wait_for_event('AP-STA-CONNECTED %s' % device.address)

        testutil.test_iface_operstate(device.name)
        testutil.test_ifaces_connected(hapd_to.ifname, device.name)
        self.assertRaises(Exception, testutil.test_ifaces_connected,
                          (hapd_from.ifname, device.name, True, True))


    def validate_connection(self, wd, ft=True, check_used_pmksa=False):
        device = wd.list_devices(1)[0]

        self.connect(wd, device, self.bss_hostapd[0])

        # If PMKSA was used, hostapd should not include the sae_group key in
        # its status for the station.
        sta_status = self.bss_hostapd[0].sta_status(device.address)
        if check_used_pmksa:
            self.assertNotIn("sae_group", sta_status.keys())
        else:
            self.assertIn("sae_group", sta_status.keys())

        self.roam(wd, device, self.bss_hostapd[0], self.bss_hostapd[1])

        if not ft:
            return

        self.roam(wd, device, self.bss_hostapd[1], self.bss_hostapd[2])

    def test_ft_roam_success(self):
        wd = IWD(True)

        self.bss_hostapd[0].set_value('wpa_key_mgmt', 'FT-SAE SAE')
        self.bss_hostapd[0].reload()
        self.bss_hostapd[0].wait_for_event("AP-ENABLED")
        self.bss_hostapd[1].set_value('wpa_key_mgmt', 'FT-SAE SAE')
        self.bss_hostapd[1].reload()
        self.bss_hostapd[1].wait_for_event("AP-ENABLED")
        self.bss_hostapd[2].set_value('wpa_key_mgmt', 'FT-PSK')
        self.bss_hostapd[2].reload()
        self.bss_hostapd[2].wait_for_event("AP-ENABLED")

        self.validate_connection(wd, True)

    def test_ft_roam_pmksa(self):
        wd = IWD(True)

        self.bss_hostapd[0].set_value('wpa_key_mgmt', 'FT-SAE SAE')
        self.bss_hostapd[0].reload()
        self.bss_hostapd[0].wait_for_event("AP-ENABLED")
        self.bss_hostapd[1].set_value('wpa_key_mgmt', 'FT-SAE SAE')
        self.bss_hostapd[1].reload()
        self.bss_hostapd[1].wait_for_event("AP-ENABLED")
        self.bss_hostapd[2].set_value('wpa_key_mgmt', 'FT-PSK')
        self.bss_hostapd[2].reload()
        self.bss_hostapd[2].wait_for_event("AP-ENABLED")

        self.validate_connection(wd, True)

        device = wd.list_devices(1)[0]
        device.disconnect()

        for hapd in self.bss_hostapd:
            hapd.deauthenticate(device.address)

        wd.wait(5)

        self.validate_connection(wd, True, check_used_pmksa=True)

    def test_ft_roam_with_pmksa(self):
        wd = IWD(True)

        self.bss_hostapd[0].set_value('wpa_key_mgmt', 'FT-SAE SAE')
        self.bss_hostapd[0].reload()
        self.bss_hostapd[0].wait_for_event("AP-ENABLED")
        self.bss_hostapd[1].set_value('wpa_key_mgmt', 'FT-SAE SAE')
        self.bss_hostapd[1].reload()
        self.bss_hostapd[1].wait_for_event("AP-ENABLED")
        self.bss_hostapd[2].set_value('wpa_key_mgmt', 'FT-PSK')
        self.bss_hostapd[2].reload()
        self.bss_hostapd[2].wait_for_event("AP-ENABLED")

        device = wd.list_devices(1)[0]

        self.connect(wd, device, self.bss_hostapd[0])

        self.roam(wd, device, self.bss_hostapd[0], self.bss_hostapd[1])
        self.roam(wd, device, self.bss_hostapd[1], self.bss_hostapd[0])

    def test_reassociate_roam_success(self):
        wd = IWD(True)

        self.bss_hostapd[0].set_value('wpa_key_mgmt', 'SAE')
        self.bss_hostapd[0].reload()
        self.bss_hostapd[0].wait_for_event("AP-ENABLED")
        self.bss_hostapd[1].set_value('wpa_key_mgmt', 'SAE')
        self.bss_hostapd[1].reload()
        self.bss_hostapd[1].wait_for_event("AP-ENABLED")
        self.bss_hostapd[2].set_value('wpa_key_mgmt', 'WPA-PSK')
        self.bss_hostapd[2].reload()
        self.bss_hostapd[2].wait_for_event("AP-ENABLED")

        self.validate_connection(wd, False)

    def test_reassociate_roam_pmksa(self):
        wd = IWD(True)

        self.bss_hostapd[0].set_value('wpa_key_mgmt', 'SAE')
        self.bss_hostapd[0].reload()
        self.bss_hostapd[0].wait_for_event("AP-ENABLED")
        self.bss_hostapd[1].set_value('wpa_key_mgmt', 'SAE')
        self.bss_hostapd[1].reload()
        self.bss_hostapd[1].wait_for_event("AP-ENABLED")
        self.bss_hostapd[2].set_value('wpa_key_mgmt', 'WPA-PSK')
        self.bss_hostapd[2].reload()
        self.bss_hostapd[2].wait_for_event("AP-ENABLED")

        self.validate_connection(wd, False)

        device = wd.list_devices(1)[0]
        device.disconnect()

        for hapd in self.bss_hostapd:
            hapd.deauthenticate(device.address)

        wd.wait(5)

        self.validate_connection(wd, False, check_used_pmksa=True)

    def tearDown(self):
        os.system('ip link set "' + self.bss_hostapd[0].ifname + '" down')
        os.system('ip link set "' + self.bss_hostapd[1].ifname + '" down')
        os.system('ip link set "' + self.bss_hostapd[2].ifname + '" down')
        os.system('ip link set "' + self.bss_hostapd[0].ifname + '" up')
        os.system('ip link set "' + self.bss_hostapd[1].ifname + '" up')
        os.system('ip link set "' + self.bss_hostapd[2].ifname + '" up')

    @classmethod
    def setUpClass(cls):
        cls.bss_hostapd = [ HostapdCLI(config='ft-sae-1.conf'),
                            HostapdCLI(config='ft-sae-2.conf'),
                            HostapdCLI(config='ft-psk-3.conf') ]

        cls.bss_hostapd[0].set_address('12:00:00:00:00:01')
        cls.bss_hostapd[1].set_address('12:00:00:00:00:02')
        cls.bss_hostapd[2].set_address('12:00:00:00:00:03')

        HostapdCLI.group_neighbors(*cls.bss_hostapd)

        IWD.copy_to_storage('TestFT.psk')

    @classmethod
    def tearDownClass(cls):
        IWD.clear_storage()

        cls.bss_hostapd = None

if __name__ == '__main__':
    unittest.main(exit=True)
