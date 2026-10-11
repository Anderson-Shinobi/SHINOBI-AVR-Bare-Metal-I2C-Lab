/*
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Anderson Nogueira
 * SHINOBI AVR Bare-Metal I2C/TWI Lab — ATmega328P @ 16 MHz.
 * DS1307 register read using START, repeated START, address/data ACK and NACK.
 * Register-level driver; no Wire, Serial, or Arduino GPIO API.
 */
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#include <avr/io.h>
#include <util/delay.h>
#include <stdint.h>

namespace {
constexpr uint8_t kDs1307Address = 0x68;
constexpr uint8_t kSecondsRegister = 0x00;
constexpr uint16_t kUartUBRR = 103;
constexpr uint16_t kTwiPollLimit = 60000;
constexpr uint8_t kTW_STATUS_MASK = 0xF8;
constexpr uint8_t kSTART = 0x08;
constexpr uint8_t kREPEATED_START = 0x10;
constexpr uint8_t kSLA_W_ACK = 0x18;
constexpr uint8_t kSLA_W_NACK = 0x20;
constexpr uint8_t kDATA_W_ACK = 0x28;
constexpr uint8_t kSLA_R_ACK = 0x40;
constexpr uint8_t kDATA_R_NACK = 0x58;

void uart_init() {
  UCSR0A = 0;
  UBRR0H = static_cast<uint8_t>(kUartUBRR >> 8);
  UBRR0L = static_cast<uint8_t>(kUartUBRR);
  UCSR0B = _BV(TXEN0);
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
}
void uart_char(char c) { while (!(UCSR0A & _BV(UDRE0))) {} UDR0 = static_cast<uint8_t>(c); }
void uart_text(const char* s) { while (*s) uart_char(*s++); }
void uart_hex(uint8_t v) {
  const char hex[] = "0123456789ABCDEF";
  uart_char(hex[v >> 4]); uart_char(hex[v & 0x0F]);
}
void uart_dec(uint8_t v) {
  if (v >= 100) uart_char(static_cast<char>('0' + v / 100));
  if (v >= 10) uart_char(static_cast<char>('0' + (v / 10) % 10));
  uart_char(static_cast<char>('0' + (v % 10)));
}
void twi_init() {
  TWSR &= static_cast<uint8_t>(~(_BV(TWPS0) | _BV(TWPS1)));
  TWBR = 72;
  TWCR = _BV(TWEN);
}
uint8_t twi_status() { return TWSR & kTW_STATUS_MASK; }
bool twi_wait() {
  for (uint16_t n = 0; n < kTwiPollLimit; ++n) {
    if (TWCR & _BV(TWINT)) return true;
  }
  return false;
}
// STOP is asynchronous. TWSTO returns to zero when the bus STOP completes.
bool twi_wait_stop_completion() {
  for (uint16_t n = 0; n < kTwiPollLimit; ++n) {
    if (!(TWCR & _BV(TWSTO))) return true;
  }
  return false;
}
bool twi_start(uint8_t expected) {
  // Never overwrite TWCR with a new START while a prior STOP is pending.
  if (!twi_wait_stop_completion()) return false;
  TWCR = _BV(TWINT) | _BV(TWSTA) | _BV(TWEN);
  return twi_wait() && twi_status() == expected;
}
bool twi_write(uint8_t byte, uint8_t expected) {
  TWDR = byte;
  TWCR = _BV(TWINT) | _BV(TWEN);
  return twi_wait() && twi_status() == expected;
}
bool twi_read_nack(uint8_t& output) {
  TWCR = _BV(TWINT) | _BV(TWEN);
  if (!twi_wait() || twi_status() != kDATA_R_NACK) return false;
  output = TWDR;
  return true;
}
bool twi_stop() {
  TWCR = _BV(TWINT) | _BV(TWEN) | _BV(TWSTO);
  return twi_wait_stop_completion();
}
bool ds1307_read_seconds(uint8_t& seconds) {
  bool ok = twi_start(kSTART);
  if (ok) ok = twi_write(static_cast<uint8_t>((kDs1307Address << 1) | 0), kSLA_W_ACK);
  if (ok) ok = twi_write(kSecondsRegister, kDATA_W_ACK);
  if (ok) ok = twi_start(kREPEATED_START);
  if (ok) ok = twi_write(static_cast<uint8_t>((kDs1307Address << 1) | 1), kSLA_R_ACK);
  if (ok) ok = twi_read_nack(seconds);
  const bool stop_ok = twi_stop();
  if (!stop_ok) uart_text("DS1307 STOP_TIMEOUT\r\n");
  return ok && stop_ok;
}
void probe_unused_address() {
  if (!twi_start(kSTART)) {
    // Release the bus BEFORE potentially slow UART formatting.
    const bool stop_ok = twi_stop();
    uart_text("probe START failed\r\n");
    if (!stop_ok) uart_text("probe STOP_TIMEOUT\r\n");
    return;
  }
  TWDR = static_cast<uint8_t>(0x69 << 1);
  TWCR = _BV(TWINT) | _BV(TWEN);
  const bool completed = twi_wait();
  // Snapshot TWSR before STOP may change the last peripheral status.
  const uint8_t status = completed ? twi_status() : 0xFF;
  // The previous VCD showed ~47.77ms SCL LOW because UART was sent
  // before STOP. Close the TWI transaction before writing diagnostics.
  const bool stop_ok = twi_stop();
  if (completed) {
    uart_text("probe 0x69 status=0x"); uart_hex(status);
    uart_text(status == kSLA_W_NACK ? " EXPECTED_ADDRESS_NACK\r\n" : " CHECK_BUS\r\n");
  } else {
    uart_text("probe timeout\r\n");
  }
  if (!stop_ok) uart_text("probe STOP_TIMEOUT\r\n");
}
}

void setup() {
  uart_init(); twi_init();
  uart_text("SHINOBI AVR TWI / DS1307 0x68 / 100 kHz\r\n");
}
void loop() {
  uint8_t bcd = 0;
  if (ds1307_read_seconds(bcd)) {
    const uint8_t raw_seconds = bcd & 0x7F;
    const uint8_t seconds = static_cast<uint8_t>((raw_seconds >> 4) * 10 + (raw_seconds & 0x0F));
    uart_text("DS1307 seconds BCD=0x"); uart_hex(raw_seconds);
    uart_text(" decimal="); uart_dec(seconds);
    uart_text(" READ_PASS\r\n");
  } else {
    uart_text("DS1307 READ_FAIL (last TWSR=0x"); uart_hex(twi_status()); uart_text(")\r\n");
  }
  probe_unused_address();
  _delay_ms(1000);
}
