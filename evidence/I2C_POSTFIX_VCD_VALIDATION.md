# LAB 03 — Post-fix I²C/TWI VCD validation

**Result: PASS in Wokwi digital simulation.** The extended ~47.77 ms SCL LOW hold observed in the original `0x69` address-probe transaction is absent after the [STOP-before-UART source change](../sketch.ino). RTC reads, repeated START, ACK/NACK handling and 100 kHz SCL remain correct in this capture.

This is a **new, independent waveform recording** after the firmware change, not an edited copy of the original evidence. Physical Arduino Uno R3/DS1307 hardware and UART output have **not** been verified here.

## Artifact provenance

| Field | Post-fix capture |
|---|---|
| Original author-supplied filename | `shinobi-i2c-ds1307.vcd.vcd` |
| Preserved source | [shinobi-i2c-ds1307-postfix-2026-10-11.vcd](shinobi-i2c-ds1307-postfix-2026-10-11.vcd) |
| Original SHA-256 | `97aebe95e824677da0bdce820cb22ca08878669f1d31a57efee7706d2630eff1` |
| Git blob SHA-1 | `840c23b69851a91db3786565d9ca069d22e15acb` |
| Wokwi header timestamp | `Sun, 11 Oct 2026 02:44:31 GMT` |
| Timescale / captured span | **1 ns / 10.467227250 s** |
| Size | **20,518 bytes / 2,756 lines** |
| Channels | D0=SDA / D1=SCL |

## Decoded bus transactions

- **30 START conditions**, including **10 repeated STARTs**; **20 STOP conditions**.
- **10 complete RTC seconds reads** from 7-bit DS1307 address `0x68`.
- **10 address probes** to non-present 7-bit address `0x69`, all acknowledged with **NACK**, as expected.
- Seconds returned on the data bus: BCD `0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09`.
- Every RTC read preserves the repeated START without an intervening STOP.
- Each transaction follows the same decoded pattern:

```text
START
  0xD0  ACK    (0x68, WRITE)
  0x00  ACK    (DS1307 seconds register)
REPEATED START
  0xD1  ACK    (0x68, READ)
  0x00..0x09  NACK    (one seconds byte, master NACKs)
STOP
START
  0xD2  NACK   (0x69, WRITE; no slave present)
STOP
```

Decoder samples SDA 200 ns after SCL rising transitions; the last rising transition of each START-delimited region releases SCL before the next START or STOP and is not counted as a ninth data clock. Each 8-data-plus-ACK/NACK frame was recovered from actual scalar timestamp transitions.

## Before vs. after (measured)

| Quantity | Original VCD (before fix) | New VCD (after fix) |
|---|---:|---:|
| Duration of capture | 5.397543562 s | 10.467227250 s |
| DS1307 reads decoded | 5 | **10** |
| 0x69 probes decoded | 5 | **10** |
| Probe START→STOP median | **47,869.5 µs (47.8695 ms)** | **108.875 µs (0.108875 ms)** |
| Longest probe-associated SCL LOW | **47.767563 ms** | **8.938 µs** (maximum low interval anywhere in new trace) |
| SCL LOW intervals longer than 1 ms | **5** | **0** |
| SCL active bit-clock median period | 10,000 ns | **10,000 ns** |
| Derived active bit-clock rate | 100 kHz | **100 kHz** |
| Expected DS1307 ACK / final-byte NACK | 5 of 5 | **10 of 10** |
| Expected unused-address NACK | 5 of 5 | **10 of 10** |

**Result:** the median `0x69` probe is **439.67× shorter** and the transaction duration decreased by **99.77%**. No software-caused long SCL-low hold was observed in the new capture. Both captures are separately preserved: do not overwrite the pre-fix VCD.

## Source attribution and limits

The original code delayed TWI STOP until after `uart_text()` printed status at 9600 bps. The revised code samples `TWSR`, completes STOP by awaiting `TWSTO` clear, and only then formats UART status. The disappearance of the long hold is **consistent with that code correction** and demonstrates its effect on the simulated SDA/SCL waveforms.

This comparison does **not** establish analogue bus rise times, pull-up adequacy with a physical load, compatibility with multiple slaves, hardware electrical conformity, RTC oscillator calibration, or Wokwi UART status output. Only digital bus signals appear in the attached VCD; additional Serial Monitor content would be separate evidence.

## Reproducibility / pass criteria

- [x] Original and post-fix VCD archived with integrity hash.
- [x] SDA/SCL channels and transaction boundaries parsed.
- [x] Full `0x68` write-pointer/repeated-start/read sequence decoded with ACK, NACK, STOP.
- [x] `0x69` probe receives NACK on all ten cycles.
- [x] Active SCL bit clock measured at 100 kHz (median 10 µs).
- [x] No SCL-low hold over 1 ms in the post-fix file.
- [x] Baseline anomalous probe duration and corrected probe duration compared.
- [ ] UART Serial Monitor transcript checked.
- [ ] Physical ATmega328P + DS1307 validated with logic analyzer.

**Overall LAB 03 status: Wokwi digital protocol + post-fix timing validation PASS; real-hardware validation PENDING.**

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
