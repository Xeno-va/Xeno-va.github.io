---
title: "Embedded microfluidics — platform development log"
slug: embedded-microfluidics-platform
date: 2025-05-11
kind: Lab notes
status: Active
summary: >-
  A modular, low-cost embedded microfluidics platform automating enzyme
  evolution workflows on off-the-shelf microcontrollers and laser-cut chips.
---

## Goal

A modular, low-cost embedded microfluidics platform capable of automating enzyme
evolution workflows — droplet sorting, incubation, and optical analysis — all
using off-the-shelf microcontrollers and custom-fabricated chips.

## Hardware architecture

| Subsystem | Choice |
|---|---|
| Microcontroller | ESP32-S3, native USB and camera support |
| Control interface | A4988 stepper drivers, 5 V / 12 V MOSFET banks, GPIO breakout |
| Pumps | Custom syringe and peristaltic modules with motor feedback |
| Imaging | OV2640 + 850 nm LED for fluorescence; USB/UART for live logging |
| Display / UI | 0.96″ OLED with rotary encoder for standalone debug |
| Power | 12 V main rail, 5 V / 3.3 V regulation, optional Li-ion and solar input |

### Notes

- The ESP32's dual cores let us separate UI from real-time control loops.
- Isolation diodes are needed between MOSFETs and the shared power rail.
- Image acquisition latency is ~200 ms at 320×240 — acceptable for endpoint assays.

## Microfluidic chip fabrication

- **Material:** PMMA (acrylic), 1.5 mm base, 1 mm channel layer
- **Method:** CO₂ laser rastering for channels, solvent-bonded with ethanol + UV
- **Channel specs:** 0.5 mm width, 1 mm depth routed, Y-junctions and incubation loops
- **Hydrophobic treatment:** vapor-phase HMDS post-bonding

### Lessons learned

- Melt-over from laser cutting introduces edge deformation — DCM polishing helps.
- HMDS vapor passivation lasts about a week before wetting increases noticeably.
- Clamping during UV bonding is critical to avoid microchannel deformation.

## Software stack

- **Firmware:** PlatformIO (ESP-IDF), FreeRTOS split tasks
- **Command protocol:** serial JSON over USB/UART
- **UI:** knob navigation, debug output to OLED and USB
- **Control loops:** PID flow regulation from motor encoder feedback
- **Logging:** external SD card, or Wi-Fi upload in batch mode

## Next steps

- Fabricate V3 of the chip with an integrated droplet trap zone.
- Finish tuning PID for consistent 1–10 µL injection pulses.
- Implement high-speed capture for droplet count per flow event.
- Integrate magnet-based sorting and validate on fluorescent droplet batches.
