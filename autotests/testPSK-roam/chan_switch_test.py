#! /usr/bin/python3

import unittest
import sys, os

sys.path.append('../util')
from iwd import IWD
from iwd import NetworkType
from hostapd import HostapdCLI
from packaging import version
from subprocess import run
import re
import testutil

#
# The CSA handling was added in kernel 6.8, so for any earlier kernel this test
# won't pass.
#
def kernel_is_newer(min_version="6.8"):
    proc = run(["uname",  "-r"], capture_output=True)

    version_str = proc.stdout.decode("utf-8")
    match = re.match(r"(\d+\.\d+)", version_str)
    if not match:
        return False

    return version.parse(match.group(1)) >= version.parse(min_version)

class Test(unittest.TestCase):
    def test_channel_switch_during_roam(self):
        wd = self.wd

        device = wd.list_devices(1)[0]

        ordered_network = device.get_ordered_network('TestFT', full_scan=True)

        self.assertEqual(ordered_network.type, NetworkType.psk)

        condition = 'not obj.connected'
        wd.wait_for_object_condition(ordered_network.network_object, condition)

        self.assertFalse(self.bss_hostapd[0].list_sta())
        self.assertFalse(self.bss_hostapd[1].list_sta())

        device.connect_bssid(self.bss_hostapd[0].bssid)

        condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_condition(device, condition)

        self.bss_hostapd[0].wait_for_event('AP-STA-CONNECTED %s' % device.address)

        testutil.test_iface_operstate(device.name)
        testutil.test_ifaces_connected(self.bss_hostapd[0].ifname, device.name)
        self.assertRaises(Exception, testutil.test_ifaces_connected,
                          (self.bss_hostapd[1].ifname, device.name, True, True))

        # Start a channel switch and wait for it to begin
        self.bss_hostapd[1].chan_switch(6, wait=False)
        self.bss_hostapd[1].wait_for_event("CTRL-EVENT-STARTED-CHANNEL-SWITCH")
        # Initiate a roam immediately which should get rejected by the kernel
        device.roam(self.bss_hostapd[1].bssid)

        # IWD should authenticate, then proceed to association
        device.wait_for_event("ft-authenticating")
        device.wait_for_event("ft-roaming")

        # The kernel should reject the association, which should trigger a
        # disconnect
        condition = 'obj.state == DeviceState.disconnected'
        wd.wait_for_object_condition(device, condition)

        condition = 'obj.state == DeviceState.connected'
        wd.wait_for_object_condition(device, condition)


    def tearDown(self):
        os.system('ip link set "' + self.bss_hostapd[0].ifname + '" down')
        os.system('ip link set "' + self.bss_hostapd[1].ifname + '" down')
        os.system('ip link set "' + self.bss_hostapd[0].ifname + '" up')
        os.system('ip link set "' + self.bss_hostapd[1].ifname + '" up')

        for hapd in self.bss_hostapd:
            hapd.default()

        self.wd.stop()
        self.wd = None

    def setUp(self):
        self.wd = IWD(True)

    @classmethod
    def setUpClass(cls):
        if not kernel_is_newer():
            raise unittest.SkipTest()

        IWD.copy_to_storage('TestFT.psk')

        cls.bss_hostapd = [ HostapdCLI(config='ft-psk-ccmp-1.conf'),
                            HostapdCLI(config='ft-psk-ccmp-2.conf'),
                            HostapdCLI(config='ft-psk-ccmp-3.conf') ]

        unused = HostapdCLI(config='ft-psk-ccmp-3.conf')
        unused.disable()

        cls.bss_hostapd[0].set_address('12:00:00:00:00:01')
        cls.bss_hostapd[1].set_address('12:00:00:00:00:02')
        cls.bss_hostapd[2].set_address('12:00:00:00:00:03')

        HostapdCLI.group_neighbors(*cls.bss_hostapd)

    @classmethod
    def tearDownClass(cls):
        IWD.clear_storage()
        cls.bss_hostapd = None
