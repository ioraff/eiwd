import unittest
import sys
import os

sys.path.append('../util')
from iwd import IWD
from iwd import PSKAgent
from iwd import NetworkType

class Test(unittest.TestCase):
    def connect_failure(self, ex):
        self.failure_triggered = True

    def test_netconfig_timeout(self):
        IWD.copy_to_storage('autoconnect.psk', name='ap-ns1.psk')

        wd = IWD(True)

        psk_agent = PSKAgent("secret123")
        wd.register_psk_agent(psk_agent)

        devices = wd.list_devices(1)
        device = devices[0]

        ordered_network = device.get_ordered_network('ap-ns1')

        self.assertEqual(ordered_network.type, NetworkType.psk)

        condition = 'not obj.connected'
        wd.wait_for_object_condition(ordered_network.network_object, condition)

        self.failure_triggered = False

        # Set our error handler here so we can check if it fails
        ordered_network.network_object.connect(
            wait=False,
            timeout=1000,
            error_handler=self.connect_failure
        )

        # IWD should attempt to try both BSS's with both failing netconfig.
        # Then the autoconnect list should be exhausted, and IWD should
        # transition to a disconnected state, then proceed to full autoconnect.
        device.wait_for_event("netconfig-failed", timeout=1000)
        device.wait_for_event("netconfig-failed", timeout=1000)
        device.wait_for_event("disconnected")

        device.wait_for_event("autoconnect_full")

        # The connect call should have failed
        self.assertTrue(self.failure_triggered)

        condition = "obj.scanning"
        wd.wait_for_object_condition(device, condition)
        condition = "not obj.scanning"
        wd.wait_for_object_condition(device, condition)

        # IWD should attempt to connect, but it will of course fail again.
        device.wait_for_event("netconfig-failed", timeout=1000)

        device.disconnect()
        condition = 'obj.state == DeviceState.disconnected'
        wd.wait_for_object_condition(device, condition)

    @classmethod
    def setUpClass(cls):
        cls.orig_path = os.environ['PATH']
        os.environ['PATH'] = '/tmp/test-bin:' + os.environ['PATH']
        IWD.copy_to_storage('resolvconf', '/tmp/test-bin')

    @classmethod
    def tearDownClass(cls):
        IWD.clear_storage()
        os.system('rm -rf /tmp/radvd.conf /tmp/resolvconf.log /tmp/test-bin')
        os.environ['PATH'] = cls.orig_path

if __name__ == '__main__':
    unittest.main(exit=True)
