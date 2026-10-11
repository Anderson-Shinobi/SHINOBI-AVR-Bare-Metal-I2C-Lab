# SHINOBI AVR Bare-Metal I²C/TWI Lab

**From Physics to Firmware | Arduino Uno R3 / ATmega328P | MIT License**

> **Status:** AVR-GCC and static checks PASS. **Two Wokwi VCD measurements PASS:** first capture exposed a ~47.77 ms SCL-low hold in the absent-address probe; **post-fix capture confirms its removal** (probe median 108.875 µs), with 10 correct DS1307 reads, repeated START/ACK/NACK/STOP and measured 100 kHz SCL. Physical Uno and UART transcript remain untested.

This is an **independent repository** linked from the [SHINOBI Engineering portfolio](https://anderson-shinobi.github.io/). The firmware uses AVR peripheral registers directly; `setup()` and `loop()` are invoked by Wokwi's standard Arduino start-up scaffold. No `SPI.h`, `Wire.h`, `Serial`, or Arduino high-level pin APIs are used.

## Experiment

Hardware TWI master; TWBR/TWSR/TWCR/TWDR; 100 kHz at 16 MHz MCU; DS1307 RTC slave 0x68; START/repeated START/STOP, ACK and final-byte NACK.

## Run in Wokwi

**[▶ Open the author's saved I²C/TWI laboratory in Wokwi](https://wokwi.com/projects/477548989078745089)**

The saved Wokwi project has now yielded a measurable SDA/SCL capture with protocol-level evidence. **Physical Uno validation and the UART transcript remain pending.** Wokwi projects can be edited independently of the GitHub source; compare the saved sketch against the version used for each VCD before reproducing measurements.

See the full [LAB 03 Wokwi protocol and measurement checklist](docs/WOKWI_VALIDATION.md) before claiming any signal or protocol validation.

1. Open the [saved I²C/TWI Wokwi project](https://wokwi.com/projects/477548989078745089) and confirm its `sketch.ino` and `diagram.json` match the current repository revisions.
2. Start the simulation; inspect the Serial Monitor and the logic analyzer.
3. Run for at least 5 seconds, then press **Stop** to export the **VCD** capture.
4. Send the VCD and the Serial Monitor output for quantitative timing and protocol decoding.
5. Keep captured, measured and calculated results separate in the report.

Wiring: A4=SDA to DS1307 SDA and analyzer D0; A5=SCL to DS1307 SCL and analyzer D1; 5V→RTC VCC and SDA/SCL through separate 4.7 kΩ pull-ups; shared GND. **Target UART** (not yet measured in Wokwi): DS1307 seconds … READ_PASS and probe 0x69 … EXPECTED_ADDRESS_NACK. The new `twi_stop()` waits for `TWSTO` to clear before the following START; a timeout is reported if STOP does not complete.

## First measured Wokwi capture

- [Logic analyzer report — first I²C VCD](evidence/I2C_VCD_VALIDATION.md)
- [Original VCD archived](evidence/shinobi-i2c-ds1307-2026-10-11.vcd)
- [Executable VCD regression tests](tests/test_i2c_vcd.py)
- **Observed:** all five full DS1307 reads `0xD0 ACK → 0x00 ACK → repeated START → 0xD1 ACK → seconds NACK → STOP`, followed by address probe `0xD2 NACK → STOP`.
- **Measured:** SCL **100 kHz** inside active byte-clock bursts; returned seconds 00–04 BCD.
- **Identified in original VCD:** the `0x69` probe held SCL LOW for **~47.77 ms** before STOP; firmware was changed to complete STOP before printing UART diagnostics. **The [post-fix VCD](evidence/I2C_POSTFIX_VCD_VALIDATION.md) now confirms this anomaly is gone in the Wokwi digital capture.**

## Second measured Wokwi capture — STOP-before-UART improvement confirmed

- [Post-fix waveform validation and before/after comparison](evidence/I2C_POSTFIX_VCD_VALIDATION.md)
- [Post-fix original VCD preserved without editing](evidence/shinobi-i2c-ds1307-postfix-2026-10-11.vcd)
- [Repeatable pre/post regression tests](tests/test_i2c_postfix_vcd.py)
- **10 of 10 DS1307 register reads** and **10 of 10 expected address NACKs**; BCD seconds `0x00` through `0x09`.
- **SCL:** median active clock period **10 µs (100 kHz)**, no low interval longer than 1 ms.
- **Probe duration:** original median **47.8695 ms** → revised median **0.108875 ms**, approximately **440× shorter**.
- **Still pending:** UART Serial Monitor evidence and physical Arduino Uno/DS1307 validation.

## Measurement acceptance criteria

Decode I²C: START, 0xD0+ACK, register 0x00+ACK, repeated START, 0xD1+ACK, seconds data+NACK, STOP. Probe 0x69 must NACK. Measure SCL, do not claim 100 kHz without VCD.

The waveform and physical board still require independent validation. The AVR-GCC workflow compiles only an object (`.o`) and does not itself prove that the firmware works in the simulator or silicon.

## Build on Linux Mint

```bash
sudo apt-get install -y gcc-avr avr-libc
avr-g++ -std=gnu++11 -Os -Wall -Wextra -Werror -mmcu=atmega328p -DF_CPU=16000000UL -x c++ -c sketch.ino -o /tmp/shinobi-lab.o
python3 -m unittest discover -s tests -v
```

## Repository files

- [sketch.ino](sketch.ino) — firmware implemented through peripheral registers
- [diagram.json](diagram.json) — Wokwi circuit and analyzer connections
- [.github/workflows/ci.yml](.github/workflows/ci.yml) — AVR compile and static tests
- [tests/test_lab.py](tests/test_lab.py) — static structure and wiring assertions
- [tests/test_stop_handshake.py](tests/test_stop_handshake.py) — STOP/START synchronization checks
- [docs/WOKWI_VALIDATION.md](docs/WOKWI_VALIDATION.md) — protocol test plan and evidence acceptance criteria
- [LICENSE](LICENSE) — MIT © 2026 Anderson Nogueira

## Roadmap

**Next:** optionally archive the Wokwi Serial Monitor transcript → test the revised firmware on a physical Arduino Uno with DS1307 and a logic analyzer → compare timing, pull-up behavior and START/STOP/ACK/NACK. Both before/after simulated VCD captures are already archived.

**SHINOBI Engineering — Don't just write drivers. Measure the bus.**
