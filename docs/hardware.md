# Hardware Wiring Guide

## Raspberry Pi 4 GPIO Pinout (BCM)

```
                  Pi 4 GPIO Header
                  ┌──────────────┐
  3.3V        1 ──┤ ●          ●├── 2   5V
  SDA (I2C)   3 ──┤ ●          ●├── 4   5V
  SCL (I2C)   5 ──┤ ●          ●├── 6   GND
              7 ──┤             ├── 8
  GND         9 ──┤ ●          ●├── 10
             11 ──┤             ├── 12
             13 ──┤             ├── 14  GND
             15 ──┤             ├── 16
  3.3V       17 ──┤             ├── 18
             19 ──┤             ├── 20  GND
             21 ──┤ ● RELAY     ├── 22
             ...
```

## PCA9685 Connections (I2C @ 0x40)

| PCA9685 Pin | Pi Header Pin | Signal |
|-------------|---------------|--------|
| VCC         | Pin 2 (5V)    | Power  |
| GND         | Pin 6 (GND)   | Ground |
| SDA         | Pin 3 (GPIO2) | I2C Data |
| SCL         | Pin 5 (GPIO3) | I2C Clock |
| V+          | Servo supply (6V recommended) | Servo power rail |

| PCA9685 Channel | Function |
|-----------------|----------|
| Channel 0       | Pan servo |
| Channel 1       | Tilt servo |

**PWM Settings:** 60 Hz, center = 375, safe range = 150–600 (out of 4096).

## Firing Relay

| Connection | Detail |
|------------|--------|
| GPIO pin   | BCM 21 (physical pin 40) |
| Logic      | **Input/Output toggle** — set pin as OUTPUT to fire, INPUT to idle |
| Wiring     | Relay COM/NO between dart pusher motor and motor supply |

!!! warning "Hardware Quirk"
    This relay module does not respond correctly to HIGH/LOW logic.  The firmware uses `GPIO.setup(pin, GPIO.OUT)` to assert fire and `GPIO.setup(pin, GPIO.IN)` to release.  Do not change this to a standard HIGH/LOW pattern.

## IMX477 HQ Camera

Connect the CSI ribbon cable to the Pi's camera port.  Enable the camera in `raspi-config` or `/boot/config.txt`:

```
camera_auto_detect=1
```

The application uses OpenCV with the V4L2 backend (`cv2.CAP_V4L2`).

## USB Speaker (GEMBIRD HK-5002)

Plug into any USB port.  Audio is played via `aplay` (ALSA).  Verify the device is visible:

```bash
aplay -l
```

Set it as the default ALSA output if needed via `~/.asoundrc`.

## Bill of Materials

| Item | Qty |
|------|-----|
| Raspberry Pi 4 Model B | 1 |
| IMX477 HQ Camera | 1 |
| PCA9685 16-channel PWM driver | 1 |
| Pan/tilt servo bracket + 2× MG90S servos | 1 set |
| Nerf-compatible dart blaster mechanism | 1 |
| Relay module (5V coil, 10A contacts) | 1 |
| GEMBIRD HK-5002 USB speaker | 1 |
| 5V/3A USB-C PSU (Pi) | 1 |
| 6V servo power supply | 1 |
| Jumper wires | assorted |
