# Sentry Turret V3

An autonomous face-tracking sentry turret built on a **Raspberry Pi 4 Model B** running Debian Bookworm.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (no hardware required)
pytest

# Launch the turret
python main.py

# Open web UI
http://<pi-ip>:8080
```

## System Overview

| Component | Detail |
|-----------|--------|
| Platform  | Raspberry Pi 4 Model B, Debian Bookworm |
| Camera    | IMX477 HQ via libcamera/OpenCV |
| Servos    | PCA9685 @ I2C 0x40, 60 Hz — ch0=pan, ch1=tilt |
| Relay     | GPIO 21 (BCM), input/output toggle |
| Audio     | USB Speaker GEMBIRD HK-5002, WAV via `aplay` |
| Ammo      | 6-dart magazine |
| Web UI    | FastAPI + Jinja2, port 8080 |

## Operating Modes

- **Autonomous** — detects, tracks, and engages hostile (unregistered) faces automatically.
- **Manual** — web UI joystick controls servo position and fire button; safety arm still required.
- **Registration** — capture face snapshots and train LBPH model for safe individuals.

## Safety

A **safety arm toggle** in the web UI must be explicitly enabled before any firing can occur regardless of mode.
