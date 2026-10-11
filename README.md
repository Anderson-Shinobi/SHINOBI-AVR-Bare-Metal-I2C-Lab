# SHINOBI AVR Bare-Metal I²C/TWI Lab

**From Physics to Firmware | Arduino Uno R3 / ATmega328P | MIT License**

> **Status:** AVR-GCC compilation and static checks are automated in GitHub Actions. A bounded STOP-completion handshake was added before reusing the TWI bus. **Wokwi run/VCD capture and physical Uno validation are still pending.**

This is an **independent repository** linked from the [SHINOBI Engineering portfolio](https://anderson-shinobi.github.io/). The firmware uses AVR peripheral registers directly; `setup()` and `loop()` are invoked by Wokwi's standard Arduino start-up scaffold. No `SPI.h`, `Wire.h`, `Serial`, or Arduino high-level pin APIs are used.

## Experiment

Hardware TWI master; TWBR/TWSR/TWCR/TWDR; 100 kHz at 16 MHz MCU; DS1307 RTC slave 0x68; START/repeated START/STOP, ACK and final-byte NACK.

## Run in Wokwi

See the full [LAB 03 Wokwi protocol and measurement checklist](docs/WOKWI_VALIDATION.md) before claiming any signal or protocol validation.

1. Open [Wokwi Arduino Uno](https://wokwi.com/projects/new/arduino-uno).
2. Replace **sketch.ino** and **diagram.json** in that project with the same files from this repository.
3. Start the simulation; inspect the serial monitor and the logic analyzer.
4. Stop and download the **VCD** capture. Send the VCD for quantitative timing and protocol decoding.
5. Keep captured, measured and calculated results separate in the report.

Wiring: A4=SDA to DS1307 SDA and analyzer D0; A5=SCL to DS1307 SCL and analyzer D1; 5V→RTC VCC and SDA/SCL through separate 4.7 kΩ pull-ups; shared GND. **Target UART** (not yet measured in Wokwi): DS1307 seconds … READ_PASS and probe 0x69 … EXPECTED_ADDRESS_NACK. The new `twi_stop()` waits for `TWSTO` to clear before the following START; a timeout is reported if STOP does not complete.

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

**Next:** run Wokwi → collect UART output and VCD → decode START/repeated START/ACK/NACK/STOP and measure SCL → repeat on an actual Arduino Uno → compare traces.

**SHINOBI Engineering — Don't just write drivers. Measure the bus.**
