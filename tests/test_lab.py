"""Static checks are not live I²C measurements."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TestTWI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (ROOT / "sketch.ino").read_text()
        cls.diagram = json.loads((ROOT / "diagram.json").read_text())

    def test_registers_states(self):
        for token in ("TWBR", "TWCR", "TWSR", "TWDR", "TWSTA", "TWSTO",
                      "TWINT", "0x08", "0x10", "0x18", "0x20", "0x28",
                      "0x40", "0x58", "kDs1307Address = 0x68", "TWBR = 72"):
            self.assertIn(token, self.code)

    def test_ds1307_and_analyzer(self):
        parts = {p["id"]: p for p in self.diagram["parts"]}
        self.assertEqual(parts["rtc1"]["type"], "wokwi-ds1307")
        self.assertEqual(parts["rSDA"]["attrs"]["value"], "4700")
        self.assertEqual(parts["rSCL"]["attrs"]["value"], "4700")
        pairs = {(x[0], x[1]) for x in self.diagram["connections"]}
        for pair in (("uno:A4", "rtc1:SDA"), ("uno:A5", "rtc1:SCL"),
                     ("uno:A4", "logic1:D0"), ("uno:A5", "logic1:D1"),
                     ("uno:GND.3", "logic1:GND")):
            self.assertIn(pair, pairs)

    def test_license(self):
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())
        self.assertIn("SPDX-License-Identifier: MIT", self.code)
