# Sentry Turret V3

Autonomous face-tracking sentry turret built on a Raspberry Pi 4 Model B. Detects faces via Haar cascades, identifies enrolled individuals via LBPH recognition, tracks hostile targets with PID-controlled pan/tilt servos, and engages with a dart firing relay — all managed through a FastAPI web UI.

---

## Hardware

| Component    | Detail                                              |
| ------------ | --------------------------------------------------- |
| Platform     | Raspberry Pi 4 Model B — Debian Bookworm            |
| Camera       | IMX477 HQ via libcamera / OpenCV V4L2               |
| Servo driver | PCA9685 @ I2C `0x40`, 60 Hz — ch0 = pan, ch1 = tilt |
| Firing relay | GPIO 21 (BCM), input/output toggle (not HIGH/LOW)   |
| Audio        | GEMBIRD HK-5002 USB speaker via `aplay`             |
| Magazine     | 6-dart capacity                                     |

---

## Features

- **Autonomous mode** — detect → track → acquire → fire on unrecognised faces
- **Manual mode** — web joystick for pan/tilt and direct fire button
- **Registration mode** — enroll safe individuals via webcam snapshots, train LBPH model in-browser
- **Safety arm toggle** — must be explicitly armed in the UI before any firing is possible
- **Fire modes** — semi-auto, burst (3-round), full-auto
- **Ammo counter** — tracks remaining darts, plays clip on empty, reload button in UI
- **MJPEG live stream** — annotated with face boxes, mode, arm status, and ammo count
- **State-mapped audio** — random WAV clip played on init, targeting, engaging, armed, disarmed, shutdown, mission complete, and out of ammo
- **Graceful shutdown** — servos centre, GPIO cleanup, shutdown sound on SIGINT/SIGTERM

---

## Quick Start

```bash
git clone https://github.com/aejx00/sentry-turret-v3.git
cd sentry-turret-v3

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py
```

Web UI: `http://<pi-ip>:8080`

---

## Running Tests

No hardware required — all GPIO, PCA9685, and camera dependencies are mocked in `conftest.py`.

```bash
pip install pytest httpx fastapi jinja2 python-multipart numpy
pytest
```

---

## Project Structure

```
sentry-turret-v3/
├── main.py                        # Single entry point
├── src/
│   ├── config.py                  # All tunable constants
│   ├── hardware/
│   │   ├── camera.py              # IMX477 threaded capture
│   │   ├── servo.py               # PCA9685 pan/tilt, PWM clamped 150–600
│   │   ├── relay.py               # GPIO 21 input/output toggle relay
│   │   └── audio.py               # Non-blocking WAV playback via aplay
│   ├── vision/
│   │   ├── detector.py            # Haar cascade face detection
│   │   ├── recognizer.py          # LBPH recognition + enrollment
│   │   └── tracker.py             # Dual-axis PID tracker
│   ├── control/
│   │   ├── state.py               # Thread-safe shared system state
│   │   ├── fire_control.py        # Safety / ammo gate before relay
│   │   └── autonomous.py          # 15 Hz engagement loop
│   └── web/
│       ├── app.py                 # FastAPI app factory + all routes
│       ├── stream.py              # MJPEG generator with HUD overlay
│       └── templates/             # Jinja2 HTML (base, ops, register)
├── tests/                         # pytest suite — hardware-free
│   ├── conftest.py                # Hardware stubs (cv2, RPi.GPIO, PCA9685)
│   ├── test_servo.py
│   ├── test_relay.py
│   ├── test_detector.py
│   ├── test_tracker.py
│   ├── test_recognizer.py
│   ├── test_state.py
│   ├── test_fire_control.py
│   └── test_web.py
├── docs/                          # MkDocs source
├── mkdocs.yml
└── requirements.txt
```

---

## Configuration

All tunable constants live in `src/config.py`:

| Constant                    | Default              | Description                   |
| --------------------------- | -------------------- | ----------------------------- |
| `SERVO_CENTER`              | `375`                | PWM centre position           |
| `SERVO_MIN / MAX`           | `150 / 600`          | Safe PWM range                |
| `PID_KP / KI / KD`          | `0.25 / 0.01 / 0.05` | PID gains                     |
| `LBPH_CONFIDENCE_THRESHOLD` | `80.0`               | Below = safe; above = hostile |
| `MAGAZINE_CAPACITY`         | `6`                  | Dart count                    |
| `BURST_COUNT`               | `3`                  | Rounds per burst              |
| `WEB_PORT`                  | `8080`               | HTTP server port              |

Set `LOG_LEVEL=DEBUG` for verbose hardware output.

---

## Face Enrollment

1. Switch to **Registration** mode in the web UI.
2. Go to the **Register** page, enter a name, and click **Capture Snapshot** ≥ 20 times (vary angle and expression).
3. Click **Train Model**.
4. Switch back to **Autonomous** — that person is now recognised as safe.

Enrolled face data is stored in `~/Documents/FacialRecognitionProject/face_data/`.

---

## Audio Clips

[dreadnought_clips.zip - Google Drive](https://drive.google.com/file/d/1kI1ts4uIpsv4WAZLSyxmC3jy6SUEvGn9/view?usp=sharing)

Place `.wav` files in subdirectories under `~/Documents/FacialRecognitionProject/dreadnought_clips/`:

```
dreadnought_clips/
├── init/
├── targeting/
├── engaging/
├── armed/
├── disarmed/
├── shutdown/
├── mission_complete/
└── out_of_ammo/
```

A random clip is selected each time an event fires.

---

## Documentation

Full MkDocs documentation (architecture, logic flow, wiring guide, setup guide):

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

---

## Tech Stack

Python 3.10+ · OpenCV (Haar + LBPH) · Adafruit PCA9685 · RPi.GPIO · FastAPI · Jinja2 · uvicorn · pytest · MkDocs
