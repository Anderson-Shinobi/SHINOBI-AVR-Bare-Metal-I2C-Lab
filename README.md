# SHINOBI AVR Bare-Metal I²C/TWI Lab

**From Physics to Firmware | Arduino Uno R3 / ATmega328P | MIT License**

> **Status:** implementation prepared and local structural checks performed. AVR-GCC build on GitHub Actions and execution/measurement in Wokwi must be checked before claiming the protocol was validated.

This is an **independent repository** linked from the [SHINOBI Engineering portfolio](https://anderson-shinobi.github.io/). The firmware uses AVR peripheral registers directly; `setup()` and `loop()` are invoked by Wokwi's standard Arduino start-up scaffold. No `SPI.h`, `Wire.h`, `Serial`, or Arduino high-level pin APIs are used.

## Experiment

Hardware TWI master; TWBR/TWSR/TWCR/TWDR; 100 kHz at 16 MHz MCU; DS1307 RTC slave 0x68; START/repeated START/STOP, ACK and final-byte NACK.

## Run in Wokwi

1. Open [Wokwi Arduino Uno](https://wokwi.com/projects/new/arduino-uno).
2. Replace **sketch.ino** and **diagram.json** in that project with the same files from this repository.
3. Start the simulation; inspect the serial monitor and the logic analyzer.
4. Stop and download the **VCD** capture. Send the VCD for quantitative timing and protocol decoding.
5. Keep captured, measured and calculated results separate in the report.

Wiring: A4=SDA to DS1307 SDA and analyzer D0; A5=SCL to DS1307 SCL and analyzer D1; 5V→RTC VCC and SDA/SCL through separate 4.7 kΩ pull-ups; shared GND. Expected UART: DS1307 seconds … READ_PASS and probe 0x69 … EXPECTED_ADDRESS_NACK.

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
- [LICENSE](LICENSE) — MIT © 2026 Anderson Nogueira

## Roadmap

**Next:** pass GitHub CI → run Wokwi → collect VCD → inspect timing, protocol and error cases → repeat on an actual Arduino Uno → compare traces.

**SHINOBI Engineering — Don't just write drivers. Measure the bus.**
