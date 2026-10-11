"""Check TWI STOP synchronization and declared Wokwi wiring.

Structural checks do not execute Wokwi or validate bus timing.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestTwiStop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (ROOT / "sketch.ino").read_text(encoding="utf-8")

    def test_stop_completion_wait_is_bounded(self):
        self.assertIn("bool twi_wait_stop_completion()", self.code)
        self.assertIn("for (uint16_t n = 0; n < kTwiPollLimit; ++n)", self.code)
        self.assertIn("if (!(TWCR & _BV(TWSTO))) return true;", self.code)
        self.assertIn("return false;", self.code)

    def test_new_start_waits_for_pending_stop(self):
        start = self.code.split("bool twi_start(uint8_t expected) {", 1)[1].split("bool twi_write", 1)[0]
        self.assertLess(start.index("if (!twi_wait_stop_completion()) return false;"),
                        start.index("TWCR = _BV(TWINT) | _BV(TWSTA) | _BV(TWEN);"))

    def test_stop_is_awaited_and_checked(self):
        stop = self.code.split("bool twi_stop() {", 1)[1].split("bool ds1307_read_seconds", 1)[0]
        self.assertIn("TWCR = _BV(TWINT) | _BV(TWEN) | _BV(TWSTO);", stop)
        self.assertIn("return twi_wait_stop_completion();", stop)

        read = self.code.split("bool ds1307_read_seconds", 1)[1].split("void probe_unused_address", 1)[0]
        self.assertIn("const bool stop_ok = twi_stop();", read)
        self.assertIn("return ok && stop_ok;", read)

        probe = self.code.split("void probe_unused_address() {", 1)[1].split("void setup()", 1)[0]
        self.assertIn("const bool stop_ok = twi_stop();", probe)
        self.assertIn('if (!stop_ok) uart_text("probe STOP_TIMEOUT', probe)
        self.assertIn("0x69 << 1", probe)
        # Capture the completed state and TWSR code BEFORE issuing STOP.
        self.assertIn("const bool completed = twi_wait();", probe)
        self.assertIn("const uint8_t status = completed ? twi_status() : 0xFF;", probe)
        self.assertLess(probe.index("const uint8_t status"),
                        probe.rindex("const bool stop_ok = twi_stop();"))
        self.assertLess(probe.rindex("const bool stop_ok = twi_stop();"),
                        probe.index('uart_text("probe 0x69 status=0x")'))

    def test_rtc_address_and_clock_unchanged(self):
        self.assertIn("kDs1307Address = 0x68", self.code)
        self.assertIn("TWBR = 72", self.code)
        self.assertIn("kREPEATED_START", self.code)
        self.assertIn("kDATA_R_NACK", self.code)
        self.assertIn("EXPECTED_ADDRESS_NACK", self.code)


if __name__ == "__main__":
    unittest.main()
