"""Compare immutable pre-/post-fix Wokwi I²C bus captures.

Tests reproduce digital timing only, not physical I²C electrical conformity.
"""
import hashlib
import unittest
from pathlib import Path
from bisect import bisect_right
from statistics import median

ROOT = Path(__file__).resolve().parents[1] / "evidence"
PRE = ROOT / "shinobi-i2c-ds1307-2026-10-11.vcd"
POST = ROOT / "shinobi-i2c-ds1307-postfix-2026-10-11.vcd"
SHA_PRE = "3267e41d96c1905b2a069203f273a2356408b519362d313c1874bf6ba05a40fd"
SHA_POST = "97aebe95e824677da0bdce820cb22ca08878669f1d31a57efee7706d2630eff1"


def parse(path):
    channels, names = {}, {}
    t = 0
    for row in path.read_text(encoding="utf-8").splitlines():
        if row.startswith("$var "):
            fields = row.split()
            names[fields[3]] = fields[4]
            channels[fields[4]] = []
        elif row.startswith("#"):
            t = int(row[1:])
        elif len(row) > 1 and row[0] in "01" and row[1:] in names:
            events = channels[names[row[1:]]]
            value = int(row[0])
            events.append((t, events[-1][2] if events else None, value))
    return channels


def at(events, t):
    ts = [row[0] for row in events]
    i = bisect_right(ts, t) - 1
    return None if i < 0 else events[i][2]


def decode(channels):
    sda, scl = channels["SDA"], channels["SCL"]
    scl_timestamps = {t for t, _, _ in scl}
    boundaries = []
    for t, before, after in sda:
        if before is None or before == after or t in scl_timestamps:
            continue
        if at(scl, t - 1) == at(scl, t + 1) == 1:
            boundaries.append((t, "START" if after == 0 else "STOP"))
    segments = []
    periods = []
    for i, (start, kind) in enumerate(boundaries[:-1]):
        if kind != "START":
            continue
        end, following = boundaries[i + 1]
        rises = [t for t, was, now in scl
                 if was == 0 and now == 1 and start < t < end]
        if len(rises) not in (10, 19):
            raise AssertionError(f"Unexpected clocks: {len(rises)}")
        data_rises = rises[:-1]  # Last SCL high prepares the next START/STOP.
        values = []
        for offset in range(0, len(data_rises), 9):
            times = data_rises[offset:offset + 9]
            if len(times) != 9:
                raise AssertionError("Incomplete 9-bit transfer")
            bits = [at(sda, t + 200) for t in times]
            values.append((sum(bit << (7-i) for i, bit in enumerate(bits[:8])), bits[8]))
        periods.extend((b - a) for a, b in zip(rises[:-2], rises[1:-1]) if b - a <= 20000)
        segments.append((start, end, following, values))
    low_spans = [b - a for (a, _, v), (b, _, _) in zip(scl, scl[1:]) if v == 0]
    return boundaries, segments, periods, low_spans


class TestI2CPostFixVCD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = decode(parse(PRE))
        cls.post = decode(parse(POST))

    def test_source_integrity(self):
        self.assertEqual(PRE.stat().st_size, 10319)
        self.assertEqual(POST.stat().st_size, 20518)
        self.assertEqual(hashlib.sha256(PRE.read_bytes()).hexdigest(), SHA_PRE)
        self.assertEqual(hashlib.sha256(POST.read_bytes()).hexdigest(), SHA_POST)

    def test_ten_full_rtc_and_probe_cycles(self):
        boundaries, segments, periods, lows = self.post
        self.assertEqual([x[1] for x in boundaries],
                         ["START", "START", "STOP", "START", "STOP"] * 10)
        self.assertEqual(len(segments), 30)
        for cycle in range(10):
            write, read, probe = segments[cycle * 3:cycle * 3 + 3]
            self.assertEqual([s[2] for s in (write, read, probe)],
                             ["START", "STOP", "STOP"])
            self.assertEqual(write[3], [(0xD0, 0), (0x00, 0)])
            self.assertEqual(read[3], [(0xD1, 0), (cycle, 1)])
            self.assertEqual(probe[3], [(0xD2, 1)])
            self.assertLess(read[1], probe[0])
            self.assertEqual(probe[1] - probe[0], 108875)

    def test_100khz_and_no_extended_scl_low(self):
        self.assertEqual(median(self.post[2]), 10000)
        self.assertGreaterEqual(self.post[2].count(10000), 400)
        self.assertLess(max(self.post[3]), 9000)
        self.assertFalse(any(v > 1000000 for v in self.post[3]))

    def test_probe_regression_before_after(self):
        baseline = [v[1]-v[0] for v in self.baseline[1][2::3]]
        post = [v[1]-v[0] for v in self.post[1][2::3]]
        self.assertEqual(len(baseline), 5)
        self.assertEqual(len(post), 10)
        self.assertEqual(median(baseline), 47869500)
        self.assertEqual(median(post), 108875)
        self.assertGreater(median(baseline) / median(post), 439)
        self.assertEqual(sum(v > 1000000 for v in self.baseline[3]), 5)
        self.assertEqual(sum(v > 1000000 for v in self.post[3]), 0)


if __name__ == "__main__":
    unittest.main()
