#!/usr/bin/python3

import unittest
import sys

sys.path.append('../util')
from iwd import IWD
from iwd import PSKAgent
from iwd import NetworkType
from hostapd import HostapdCLI
import testutil

class Test(unittest.TestCase):

    def validate_connection(self, wd, ssid, hostapd, expected_group):
        psk_agent = PSKAgent("secret123")
        wd.register_psk_agent(psk_agent)

        devices = wd.list_devices(1)
        self.assertIsNotNone(devices)
        device = devices[0]

        device.disconnect()

        network = device.get_ordered_network(ssid, full_scan=True)

        self.assertEqual(network.type, NetworkType.psk)

        network.network_object.connect()

        condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_condition(device, condition)

        wd.wait(2)

        testutil.test_iface_operstate(intf=device.name)
        testutil.test_ifaces_connected(if0=device.name, if1=hostapd.ifname)

        # Initial connection PMKSA should not be used. So we should see the
        # SAE group set.
        sta_status = hostapd.sta_status(device.address)
        self.assertEqual(int(sta_status["sae_group"]), expected_group)

        device.disconnect()

        condition = 'not obj.connected'
        wd.wait_for_object_condition(network.network_object, condition)

        wd.unregister_psk_agent(psk_agent)

        network.network_object.connect(wait=False)

        condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_condition(device, condition)

        wd.wait(2)

        testutil.test_iface_operstate(intf=device.name)
        testutil.test_ifaces_connected(if0=device.name, if1=hostapd.ifname)

        # Having connected once prior we should have a PMKSA and SAE should not
        # have been used.
        sta_status = hostapd.sta_status(device.address)
        self.assertNotIn("sae_group", sta_status.keys())

        device.disconnect()

        condition = 'not obj.connected'
        wd.wait_for_object_condition(network.network_object, condition)

        hostapd.pmksa_flush()

        wd.wait(5)

        network.network_object.connect()

        device.wait_for_event("pmksa-invalid-pmkid")

        condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_condition(device, condition)

        wd.wait(2)

        testutil.test_iface_operstate(intf=device.name)
        testutil.test_ifaces_connected(if0=device.name, if1=hostapd.ifname)

        # Manually flushing the PMKSA from the AP then reconnecting we should
        # have failed (INVALID_PMKID) then retried the same BSS with SAE, not
        # PMKSA.
        sta_status = hostapd.sta_status(device.address)
        self.assertEqual(int(sta_status["sae_group"]), expected_group)

    def test_pmksa_sae(self):
        self.hostapd.wait_for_event("AP-ENABLED")
        self.validate_connection(self.wd, "ssidSAE", self.hostapd, 19)

    def setUp(self):
        self.hostapd.default()
        self.wd = IWD(True)

    def tearDown(self):
        self.wd.clear_storage()
        self.wd = None

    @classmethod
    def setUpClass(cls):
        cls.hostapd = HostapdCLI(config='ssidSAE.conf')

    @classmethod
    def tearDownClass(cls):
        pass

if __name__ == '__main__':
    unittest.main(exit=True)
