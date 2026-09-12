import unittest
from projectscope.gamescope.controller import MenuChord

class MenuChordTests(unittest.TestCase):
    def test_requires_both_buttons_and_hold(self):
        chord=MenuChord();chord.button(308,1,0)
        chord.button(310,1,0);self.assertFalse(chord.ready(2))
        chord.button(311,1,2);self.assertFalse(chord.ready(2.59))
        self.assertTrue(chord.ready(2.61));self.assertFalse(chord.ready(5))

    def test_release_cancels_short_press(self):
        chord=MenuChord();chord.button(308,1,0);chord.button(310,1,0);chord.button(311,1,0)
        chord.button(310,0,.2);self.assertFalse(chord.ready(1))

    def test_repeats_do_not_rearm_until_both_released(self):
        chord=MenuChord();chord.button(308,1,0);chord.button(310,1,0);chord.button(311,1,0)
        self.assertTrue(chord.ready(.7))
        chord.button(310,0,.8);chord.button(310,1,.9)
        self.assertFalse(chord.ready(2))
        chord.button(310,0,2);chord.button(311,0,2);chord.button(308,0,2)
        chord.button(308,1,3);chord.button(311,1,3);chord.button(310,1,3)
        self.assertTrue(chord.ready(3.7))

    def test_disconnect_or_dropped_events_clear_pending_chord(self):
        chord=MenuChord();chord.button(308,1,0);chord.button(310,1,0);chord.button(311,1,0)
        chord.reset();self.assertFalse(chord.ready(5))

    def test_other_buttons_cannot_open_menu(self):
        chord=MenuChord();chord.button(308,1,0);chord.button(304,1,0);chord.button(305,1,0)
        self.assertFalse(chord.ready(2))

class ChordGroupTests(unittest.TestCase):
    def test_mirrored_physical_and_virtual_devices_open_once(self):
        from projectscope.gamescope.controller import ChordGroup
        group=ChordGroup();pads={'physical':MenuChord(),'virtual':MenuChord()}
        for pad in pads.values(): pad.button(308,1,0)
        for pad in pads.values(): pad.button(310,1,0);pad.button(311,1,0)
        self.assertEqual(group.poll(pads,.7),'physical')
        self.assertIsNone(group.poll(pads,.8))
        self.assertEqual(group.source,'physical')

    def test_delayed_duplicate_cannot_close_menu_before_release(self):
        from projectscope.gamescope.controller import ChordGroup
        group=ChordGroup();pads={'physical':MenuChord(),'virtual':MenuChord()}
        for pad in pads.values(): pad.button(308,1,0)
        pads['physical'].button(310,1,0);pads['physical'].button(311,1,0)
        self.assertEqual(group.poll(pads,.7),'physical')
        pads['virtual'].button(310,1,.3);pads['virtual'].button(311,1,.3)
        self.assertIsNone(group.poll(pads,1))
        for pad in pads.values(): pad.button(310,0,2);pad.button(311,0,2);pad.button(308,0,2)
        self.assertIsNone(group.poll(pads,2))
        pads['virtual'].button(308,1,3);pads['virtual'].button(310,1,3);pads['virtual'].button(311,1,3)
        self.assertEqual(group.poll(pads,3.7),'virtual')

    def test_release_observed_inside_batched_events_rearms(self):
        from projectscope.gamescope.controller import ChordGroup
        group=ChordGroup();pad=MenuChord();pad.button(308,1,0);pads={'pad':pad}
        pad.button(310,1,0);pad.button(311,1,0)
        self.assertEqual(group.poll(pads,.7),'pad')
        # All six transitions can arrive in one read; no activation polls between them.
        for code,value in [(310,0),(311,0),(308,0),(308,1),(310,1),(311,1)]:
            pad.button(code,value,1)
            group.observe_release(pads)
        self.assertEqual(group.poll(pads,1.7),'pad')


class ObsoleteChordTests(unittest.TestCase):
    def test_select_start_no_longer_opens_menu(self):
        chord=MenuChord();chord.button(314,1,0);chord.button(315,1,0)
        self.assertFalse(chord.ready(2))
    def test_bumpers_without_y_do_not_open_menu(self):
        chord=MenuChord();chord.button(310,1,0);chord.button(311,1,0)
        self.assertFalse(chord.ready(2))
