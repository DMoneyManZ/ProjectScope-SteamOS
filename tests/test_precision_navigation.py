import unittest
from projectscope.precision import options,step_for,remember
from projectscope.gamescope.controller import AxisDirection
class Fake:
    value='{}'
    def get_string(self,key): return self.value
    def set_string(self,key,value): self.value=value
class PrecisionTests(unittest.TestCase):
    def test_legacy_step_retained_and_field_independent(self):
        cfg=Fake();self.assertIn(.05,options(.05))
        remember(cfg,'dot.radius',.1)
        self.assertEqual(step_for(cfg,'dot.radius',.5),.1)
        self.assertEqual(step_for(cfg,'lines.thickness',.5),.5)
    def test_corrupt_setting_falls_back(self):
        cfg=Fake();cfg.value='[]';self.assertEqual(step_for(cfg,'scale',.25),.25)
class AxisTests(unittest.TestCase):
    def test_unsigned_stick_and_hysteresis(self):
        axis=AxisDirection(0,65535)
        self.assertEqual(axis.event(32768),0)
        self.assertEqual(axis.event(60000),1)
        self.assertEqual(axis.event(61000),0)
        self.assertEqual(axis.event(48000),0)
        self.assertEqual(axis.event(32768),0)
        self.assertEqual(axis.event(0),-1)
    def test_signed_stick_and_invalid_range(self):
        axis=AxisDirection(-32768,32767)
        self.assertEqual(axis.event(-30000),-1)
        self.assertEqual(axis.event(0),0)
        self.assertEqual(axis.event(30000),1)
        self.assertEqual(AxisDirection(0,0).event(42),0)
