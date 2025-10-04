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

    def test_full_scan(self):
        """
            Tests that IWD first tries a limited scan, then a full scan after
            an AP directed roam. After the full scan yields no results IWD
            should stop trying to roam.
        """
        self.initial_connection()

        # Disable other APs, so the scans come up empty
        self.bss_hostapd[1].disable()
        self.bss_hostapd[2].disable()

        # Send a bad candidate list with the BSS TM request which contains a
        # channel with no AP operating on it.
        self.bss_hostapd[0].send_bss_transition(
            self.device.address,
            [(self.bss_hostapd[1].bssid, "8f0000005105060603000000")]
        )
        self.device.wait_for_event("roam-scan-triggered")
        self.device.wait_for_event("no-roam-candidates")
        # IWD should then trigger a full scan
        self.device.wait_for_event("full-roam-scan")
        self.device.wait_for_event("no-roam-candidates", timeout=30)

        # IWD should not trigger a roam again after the above 2 failures.
        with self.assertRaises(TimeoutError):
            self.device.wait_for_event("roam-scan-triggered", timeout=60)

    def test_bad_candidate_list(self):
        """
            Tests behavior when the AP sends a candidate list but the scan
            finds no BSS's. IWD should fall back to a full scan after.
        """
        self.initial_connection()

        # Send a bad candidate list with the BSS TM request which contains a
        # channel with no AP operating on it.
        self.bss_hostapd[0].send_bss_transition(
            self.device.address,
            [(self.bss_hostapd[1].bssid, "8f0000005105060603000000")]
        )
        self.device.wait_for_event("roam-scan-triggered")
        self.device.wait_for_event("no-roam-candidates")
        # IWD should then trigger a full scan
        self.device.wait_for_event("full-roam-scan")
        self.device.wait_for_event("roaming", timeout=30)
        self.device.wait_for_event("connected")

    def test_bad_neighbor_report(self):
        """
            Tests behavior when the AP sends no candidate list. IWD should
            request a neighbor report. If the limited scan yields no BSS's IWD
            should fall back to a full scan.
        """

        # Set a bad neighbor (channel that no AP is on) to force the limited
        # roam scan to fail
        self.bss_hostapd[0].set_neighbor(
            self.bss_hostapd[1].bssid,
            "TestAPRoam",
            '%s8f000000%s%s060603000000' % (self.bss_hostapd[1].bssid.replace(':', ''), "51", "0b")
        )

        self.initial_connection()

        self.bss_hostapd[0].send_bss_transition(self.device.address, [])
        self.device.wait_for_event("roam-scan-triggered")
        # The AP will have sent a neighbor report with a single BSS but on
        # channel 11 which no AP is on. This should result in a limited scan
        # picking up no candidates.
        self.device.wait_for_event("no-roam-candidates", timeout=30)
        # IWD should then trigger a full scan
        self.device.wait_for_event("full-roam-scan")
        self.device.wait_for_event("roaming", timeout=30)
        self.device.wait_for_event("connected")

    def test_ignore_candidate_list_quirk(self):
        """
            Tests that IWD ignores the candidate list sent by the AP since its
            OUI indicates it should be ignored.
        """

        # Set the OUI so the candidate list should be ignored
        for hapd in self.bss_hostapd:
            hapd.set_value('vendor_elements', 'dd0400180a01')

        self.initial_connection()

        # Send with a candidate list (should be ignored)
        self.bss_hostapd[0].send_bss_transition(
            self.device.address,
            [(self.bss_hostapd[1].bssid, "8f0000005105060603000000")]
        )
        # IWD should ignore the list and trigger a full scan since we have not
        # set any neighbors
        self.device.wait_for_event("full-roam-scan")
        self.device.wait_for_event("roaming", timeout=30)
        self.device.wait_for_event("connected")

    def setUp(self):
        self.wd = IWD(True)

        devices = self.wd.list_devices(1)
        self.device = devices[0]

    def tearDown(self):
        self.wd = None
        self.device = None

        for hapd in self.bss_hostapd:
            hapd.reload()

    @classmethod
    def setUpClass(cls):
        IWD.copy_to_storage('TestAPRoam.psk')

        cls.bss_hostapd = [ HostapdCLI(config='ssid1.conf'),
                            HostapdCLI(config='ssid2.conf'),
                            HostapdCLI(config='ssid3.conf') ]

    @classmethod
    def tearDownClass(cls):
        IWD.clear_storage()

if __name__ == '__main__':
    unittest.main(exit=True)
