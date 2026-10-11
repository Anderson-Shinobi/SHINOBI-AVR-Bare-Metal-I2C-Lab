"""Decode the original Wokwi LAB 03 SDA/SCL VCD.

Wokwi digital waveform validation is not physical-board certification.
The last SCL rising edge before STOP/repeated START releases the bus HIGH;
it is NOT an extra 9-bit data clock.
"""
import hashlib
import unittest
from bisect import bisect_right
from pathlib import Path
from statistics import median

VCD = Path(__file__).resolve().parents[1] / "evidence/shinobi-i2c-ds1307-2026-10-11.vcd"
SHA256 = "3267e41d96c1905b2a069203f273a2356408b519362d313c1874bf6ba05a40fd"


def parse():
    timestamp = 0
    names = {}
    signals = {}
    levels = {}
    for line in VCD.read_text(encoding="utf-8").splitlines():
        if line.startswith("$var "):
            fields = line.split()
            names[fields[3]] = fields[4]
            signals[fields[4]] = []
        elif line.startswith("#"):
            timestamp = int(line[1:])
        elif len(line) > 1 and line[0] in "01" and line[1:] in names:
            name = names[line[1:]]
            v = int(line[0])
            prior = levels.get(name)
            signals[name].append((timestamp, prior, v))
            levels[name] = v
    return signals


def sample(events, t):
    idx = bisect_right([v[0] for v in events], t) - 1
    return None if idx < 0 else events[idx][2]


def decode():
    signals = parse()
    sda, scl = signals["SDA"], signals["SCL"]
    scl_times = {t for t, _, _ in scl}
    boundaries = []
    for t, before, after in sda:
        if before is None or before == after or t in scl_times:
            continue
        if sample(scl, t - 1) == sample(scl, t + 1) == 1:
            boundaries.append((t, "START" if after == 0 else "STOP"))
    boundaries.sort()
    segments = []
    for i, (start, kind) in enumerate(boundaries[:-1]):
        if kind != "START":
            continue
        end, closing = boundaries[i + 1]
        rises = [t for t, was, v in scl if was == 0 and v == 1 and start < t < end]
        if len(rises) not in (10, 19):
            raise AssertionError("Wrong SCL clocks in START segment: " + str(len(rises)))
        data_rises = rises[:-1]  # Last rise prepares RESTART or STOP.
        values = []
        for offset in range(0, len(data_rises), 9):
            sample_times = data_rises[offset:offset + 9]
            if len(sample_times) != 9:
                raise AssertionError("Incomplete 9-bit frame")
            bits = [sample(sda, t + 200) for t in sample_times]
            value = int("".join(str(bit) for bit in bits[:8]), 2)
            values.append((value, bits[8]))
        segments.append((start, end, closing, values, rises))
    return signals, boundaries, segments


class TestI2CVcd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signals, cls.boundaries, cls.segments = decode()

    def test_integrity_and_channels(self):
        self.assertEqual(VCD.stat().st_size, 10319)
        self.assertEqual(hashlib.sha256(VCD.read_bytes()).hexdigest(), SHA256)
        self.assertEqual(set(self.signals), {"SDA", "SCL"})

    def test_start_repeated_start_and_stop(self):
        self.assertEqual([kind for _, kind in self.boundaries],
                         ["START", "START", "STOP", "START", "STOP"] * 5)

    def test_five_rtc_reads_and_address_nacks(self):
        self.assertEqual(len(self.segments), 15)
        for i in range(5):
            write, read, probe = self.segments[3 * i:3 * i + 3]
            self.assertEqual((write[2], read[2], probe[2]),
                             ("START", "STOP", "STOP"))
            self.assertEqual(write[3], [(0xD0, 0), (0x00, 0)])
            self.assertEqual(read[3], [(0xD1, 0), (i, 1)])
            self.assertEqual(probe[3], [(0xD2, 1)])
            self.assertLess(read[1], probe[0])
            self.assertTrue(47_000_000 < probe[1] - probe[0] < 49_000_000)

    def test_100khz_scl_bit_clock(self):
        periods = []
        for _, _, _, _, rises in self.segments:
            for start, end in zip(rises[:-2], rises[1:-1]):
                if end - start <= 20_000:
                    periods.append(end - start)
        self.assertEqual(median(periods), 10_000)
        self.assertGreaterEqual(sum(value == 10_000 for value in periods), 150)

    def test_five_extended_scl_low_holds(self):
        scl = self.signals["SCL"]
        holds = [(b - a) / 1e6
                 for (a, _, value), (b, _, _) in zip(scl, scl[1:])
                 if value == 0 and b - a > 1_000_000]
        self.assertEqual(len(holds), 5)
        self.assertTrue(all(47.5 <= v <= 48.0 for v in holds))


if __name__ == "__main__":
    unittest.main()
