# LAB 03 — Wokwi I²C/TWI validation plan

**Hardware under test:** Arduino Uno R3 / ATmega328P 16 MHz, integrated TWI controller (no Wire/Arduino API), DS1307 RTC at 7-bit address `0x68`, two independent 4.7 kΩ pull-ups to +5 V, logic analyzer on SDA and SCL.

**Status:** compiled by AVR-GCC; both [baseline](../evidence/I2C_VCD_VALIDATION.md) and [post-fix](../evidence/I2C_POSTFIX_VCD_VALIDATION.md) Wokwi VCDs decoded. Protocol frames and active 100 kHz SCL measured; the baseline ~47.77-ms SCL-low hold is absent in the post-fix trace, where the address probe takes only 108.875 µs. UART Serial Monitor output and physical hardware are still pending.

## How to run

**[Open the author's saved LAB 03 I²C/TWI project](https://wokwi.com/projects/477548989078745089).** Two captured versions have now been measured and documented. If you edit the simulation, verify its firmware revision before comparing new measurements.

1. Open the [saved Wokwi project](https://wokwi.com/projects/477548989078745089). Keep the SPI LAB 02 project untouched.
2. Confirm the saved `sketch.ino` and `diagram.json` correspond to the current repository [firmware](../sketch.ino) and [circuit](../diagram.json). If they differ, update or create a copy rather than assuming the saved project uses the latest code.
3. Confirm `wokwi-ds1307` is visible with SDA on **A4** and SCL on **A5**, 5V, shared GND, and the logic analyzer connected **D0=SDA**, **D1=SCL**. The two 4.7 kΩ pull-up resistors must connect each bus line to 5V.
4. Run for at least **5 seconds** and check the serial monitor. Look for `READ_PASS` and `EXPECTED_ADDRESS_NACK` but **do not assert them until observed**.
5. Press **Stop** to generate the analyzer capture `shinobi-i2c-ds1307.vcd`. Save and upload the VCD (and optionally a screenshot or copy of Serial Monitor).
6. Do not assign a verified SCL rate or protocol compliance from compilation alone. Decode transitions from the VCD.

## Target I²C transaction

```text
START
  0xD0  ACK     DS1307 address 0x68, WRITE
  0x00  ACK     DS1307 seconds register pointer
REPEATED START
  0xD1  ACK     DS1307 address 0x68, READ
  DATA  NACK    One BCD seconds byte; master finishes reception with NACK
STOP
[wait until hardware TWSTO clears]
START
  0xD2  NACK    Probe absent address 0x69, WRITE
STOP
```

The TWI controller's expected status codes are `0x08` START, `0x10` repeated START, `0x18` SLA+W ACK, `0x28` data ACK, `0x40` SLA+R ACK, `0x58` data read followed by NACK, and `0x20` SLA+W NACK for the absent address. **The 0xD0/0xD1/0xD2 values include the R/W bit; 0x68/0x69 are seven-bit addresses.**

For a 16 MHz AVR clock, prescaler 1 and `TWBR=72`, nominal bus rate is:

```text
f_SCL = F_CPU / (16 + 2*TWBR*prescaler)
      = 16,000,000 / (16 + 2*72) = 100,000 Hz
```

Bus timing must be **measured** from the new VCD, including any clock stretching.

## STOP/START regression

The original sketch did not wait for STOP to finish before sending the next START (RTC read then the 0x69 probe). The firmware now polls `TWSTO` until hardware clears it, within a bounded retry count, before issuing a new START; failure produces a STOP timeout message and prevents a premature START. This follows AVR TWI semantics and is **not a substitute for a live simulation run**.

## Validation acceptance checklist

- [ ] Wokwi schematic loads without invalid pin/wiring warnings.
- [x] Repeated START is visible without an intervening STOP (first VCD).
- [x] DS1307 acknowledges `0xD0`, `0x00`, and `0xD1` (first VCD).
- [x] Final seconds byte is followed by a master NACK, then STOP (first VCD).
- [x] New `0xD2` probe occurs only after the prior STOP and receives NACK (first VCD).
- [ ] Serial Monitor reports `READ_PASS` and `EXPECTED_ADDRESS_NACK`.
- [x] Active SCL median period 10 µs (100 kHz) in both VCDs; the original probe's ~47.77-ms SCL-low hold disappears in the post-fix VCD (no LOW period over 1 ms).
- [x] Original abnormal observation and source diagnosis documented; post-fix source now issues STOP before UART, and the measured probe START→STOP interval fell to 108.875 µs.
- [ ] Hardware behavior remains **untested on a physical board**.

## Expected evidence

- Public Wokwi project URL (received): [LAB 03 saved simulation](https://wokwi.com/projects/477548989078745089).
- Both original pre-fix and post-fix VCDs preserved without editing, with SHA-256 hashes.
- UART Serial Monitor output.
- Reproducible decoding report (timestamps and address ACK/NACK).
- Later, physical Arduino Uno and actual DS1307 testing.

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
