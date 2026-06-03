# Original Project Brief

> This page preserves the original specification that defined this project.

---

**Sentry Turret V3**

Create a Python 3.10+ autonomous sentry turret project called **"Sentry Turret V3"** hosted on a self-hosted Gitea instance at `http://192.168.0.90:673/`. The system runs on a **Raspberry Pi 4 Model B (Debian Bookworm)**.

**Hardware:**

- IMX477 HQ Camera via libcamera/OpenCV
- PCA9685 PWM driver at I2C `0x40`, 60Hz — channel 0 = pan, channel 1 = tilt. Center = PWM 375, safe range 150–600
- GPIO 21 (BCM) firing relay — uses input/output toggle workaround (not HIGH/LOW) due to hardware quirk
- USB Speaker (GEMBIRD HK-5002) for WAV playback
- 6-dart magazine with semi-auto and full-auto fire modes

**Face Detection & Tracking:**

- OpenCV Haar cascades + LBPH recognizer only — no external face_recognition library; optimise for Pi 4 performance
- Active pan/tilt tracking using PID-style error correction to centre detected faces in frame
- PWM output clamped to safe range 150–600; reset to centre (375) if limits exceeded
- Frame resolution 640×480

**Registration & Fire Control:**

- Enroll "safe" individuals via webcam snapshot through the web UI; unknown faces are treated as hostile
- Fire behaviour (semi-auto / burst / full-auto) is configurable per-profile and per-mode
- A **safety arm toggle** must be enabled in the web UI before any firing can occur

**Operating Modes:**

- **Autonomous** — detect → track → acquire → fire on unknown targets
- **Manual** — web UI controls for pan/tilt and fire; safety toggle still required to fire
- **Registration** — capture and label faces to enroll as safe

**Web Application (FastAPI + Jinja2):**

- Live MJPEG camera stream
- Mode switcher (Autonomous / Manual / Registration)
- Safety arm toggle (must be armed before firing is permitted)
- Manual pan/tilt joystick and fire controls
- Ammo counter with reload button
- System status and active mode display
- Registration UI: capture snapshot, enter name, save profile

**Sound Effects:**

- Play a random WAV from `~/Documents/FacialRecognitionProject/dreadnought_clips/` subdirectories mapped to system states:
  - `init/` — on system startup
  - `targeting/` — on face acquisition
  - `engaging/` — on fire
  - `armed/` — on safety arm
  - `disarmed/` — on safety disarm
  - `shutdown/` — on system exit
  - `mission_complete/` — on target lost after engagement
  - `out_of_ammo/` — when ammo reaches zero

**Engineering Requirements:**

- Red/green TDD with `pytest`; all hardware (GPIO, PCA9685, camera) must be mockable for CI-safe tests
- MkDocs documentation including: this original prompt, software architecture overview, logic flow, hardware wiring guide, and setup guide
- Verbose structured logging via Python `logging` module; DEBUG level toggled via `LOG_LEVEL` env var
- Manually launched via single entry point `main.py` — no systemd
- Graceful shutdown handler: servos centre, GPIO cleanup, cease fire, play shutdown sound

**Tech Stack:** Python 3.10+, OpenCV, Adafruit PCA9685, RPi.GPIO, FastAPI, Jinja2, pytest, MkDocs. Version control via Gitea at `http://192.168.0.90:673/`.
