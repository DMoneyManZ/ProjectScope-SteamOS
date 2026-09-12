import unittest
from projectscope.gamescope.hotkey import HotkeyLatch

class HotkeyLatchTests(unittest.TestCase):
    def test_repeated_keypress_does_not_toggle_twice(self):
        latch=HotkeyLatch()
        self.assertTrue(latch.event(True))
        self.assertFalse(latch.event(True))
        self.assertFalse(latch.event(True))
        self.assertFalse(latch.event(False))
        self.assertTrue(latch.event(True))
