# LAB 03 — First Wokwi I²C/TWI + DS1307 logic-analyzer validation

> **Status: SIMULATED PROTOCOL PASS for the captured RTC read and expected address NACK; physical hardware and UART evidence still pending.** The capture also reveals a ~47.77-ms SCL-low hold during the unused-address probe. This is an avoidable timing issue in the captured firmware, not a claim that the RTC read failed.

## Capture provenance

- Saved simulation: [SHINOBI AVR I²C/TWI laboratory](https://wokwi.com/projects/477548989078745089)
- **Unmodified user-provided VCD:** [shinobi-i2c-ds1307-2026-10-11.vcd](shinobi-i2c-ds1307-2026-10-11.vcd)
- Header timestamp: `Sun, 11 Oct 2026 02:24:17 GMT`
- Time scale **1 ns**; captured span **5.397543562 s**
- Original size **10,319 bytes**; **1,396 lines**
- Original SHA-256: `3267e41d96c1905b2a069203f273a2356408b519362d313c1874bf6ba05a40fd`
- Git blob SHA: `eddc96437f1075d0616829a9b082349cd016e380`
- Analyzer channels: D0=**SDA** (Arduino Uno A4), D1=**SCL** (A5)
- Device: DS1307, seven-bit address `0x68`, simulated. Probe: no device at `0x69`.

## Protocol decoder methodology

Identify **START** when SDA falls while SCL remains HIGH; **STOP** when SDA rises while SCL remains HIGH. Exclude SDA changes simultaneous with SCL falls (regular data-bit changes). Sample SDA 200 ns after each SCL rising edge. Read each 9-bit byte frame as **8 MSB-first data bits + the ACK/NACK bit**.

Within each START-delimited region, the VCD shows 19 SCL rises for 2-byte transfers and 10 rises for the 1-byte address probe. The *last* rise in each region is the SCL HIGH release that sets up the subsequent repeated START or STOP, **not an additional data bit**. Sample the 18 or 9 data/ACK clocks preceding that release.

## Decoded I²C events

There are **15 START events**, including **5 repeated START conditions**, and **10 STOP events**. Five complete cycles have the following frames:

| Event | 8-bit value | Meaning | Ninth bit | Observed |
|---|---|---|---|---|
| START, address write | `0xD0` | `0x68 << 1 | 0` | 0 | Slave **ACK** |
| Register pointer | `0x00` | Seconds register | 0 | Slave **ACK** |
| **Repeated START**, address read | `0xD1` | `0x68 << 1 | 1` | 0 | Slave **ACK** |
| One data byte | `0x00`–`0x04` | BCD seconds | 1 | Master **NACK** |
| STOP | — | End RTC reading | — | Observed |
| START, unused address | `0xD2` | `0x69 << 1 | 0` | 1 | **NACK** |
| STOP | — | End address probe | — | Observed |

| RTC cycle | Returned seconds byte (BCD) | Decimal seconds | `0x69` address probe |
|---:|---|---:|---|
| 1 | `0x00` | 0 | NACK |
| 2 | `0x01` | 1 | NACK |
| 3 | `0x02` | 2 | NACK |
| 4 | `0x03` | 3 | NACK |
| 5 | `0x04` | 4 | NACK |

No STOP was observed between the register write and the subsequent read phase: the repeated START sequence is correct in this digital capture. All five reads completed with the expected master final-byte NACK; all five absent-address probes received NACK.

### Representative timing

- SCL clock period during the active byte bursts: **median 10,000 ns = 100 kHz**
- Regular SCL HIGH and LOW half-periods: **5,000 ns each** (typical captured pulses; additional inter-byte setup/release time occurs)
- RTC write section (START to repeated START): **~204.813 µs**.
- RTC read section (repeated START to STOP): **~202.125 µs**.
- Probe section (START to STOP): **~47.867 ms**, dominated by an extended low period.
- Five anomalously long SCL LOW intervals in probes: **47.763–47.768 ms**, median **47.767187 ms**.
- Each RTC read STOP precedes the subsequent address-probe START; no overlapping STOP/START is seen.

**Important:** 100 kHz is the measured nominal *bit-clock frequency within active bursts*, **not** a statement that the bus remained at 100 kHz throughout the probe's 47-ms low hold.

## Engineering finding — serial logging while the I²C transaction remains active

Reviewing the committed `probe_unused_address()` firmware shows it obtains the NACK status, **prints the status to UART at 9600 bps while the TWI transaction is still open**, and only then calls `twi_stop()`. That source order is consistent with the five ~47.77-ms SCL-low holds captured after `0xD2` NACK and before STOP.

**Measured:** SCL stays LOW for ~47.77 ms in each probe before STOP. **Reasoned from firmware structure:** UART output is delaying STOP while the controller awaits software. **Not proven:** whether an independent, physical DS1307, TWI hardware timeout, or another I²C device would tolerate the prolonged hold. This is not evidence of clock stretching by the DS1307.

**Recommended firmware change:** latch `TWSR` while the TWI operation is complete, issue STOP and await its completion, and **then** format and print the UART status. Keep START/STOP timeout reporting, and capture a new VCD to confirm the 47-ms low hold disappears. The archived original VCD is a pre-fix baseline and must not be presented as validation of any subsequent firmware revision.

## Acceptance criteria status

| Gate | Result |
|---|---|
| Slave address `0x68`, WRITE + ACK | **PASS in Wokwi VCD** |
| Register pointer `0x00` + ACK | **PASS in Wokwi VCD** |
| Repeated START with no STOP | **PASS in Wokwi VCD** |
| Slave address `0x68`, READ + ACK | **PASS in Wokwi VCD** |
| Read seconds byte, master final-byte NACK | **PASS in Wokwi VCD** |
| STOP completed before new probe START | **PASS in Wokwi VCD** |
| Absent address `0x69` returns NACK | **PASS in Wokwi VCD** |
| 100 kHz during active bit clocks | **PASS in Wokwi VCD** |
| No long hold while probe active | **OPEN — ~47.77 ms hold measured** |
| UART Serial Monitor `READ_PASS` and `EXPECTED_ADDRESS_NACK` | **NOT CHECKED — UART log not supplied** |
| Physical Uno/DS1307 or analog waveforms | **NOT TESTED** |

The [VCD regression decoder](../tests/test_i2c_vcd.py) reproduces the byte-level findings and documents the long clock-low interval. **Follow-up now completed:** a separate [post-fix VCD report](I2C_POSTFIX_VCD_VALIDATION.md) demonstrates the probe duration fell from ~47.87 ms to 108.875 µs after the STOP-before-UART change, while protocol frames continued to pass. This document and its original VCD remain the immutable *pre-fix* baseline. This source-backed, measured report is narrower than full I²C electrical compliance or physical-hardware validation.

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
