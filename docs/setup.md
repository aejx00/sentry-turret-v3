# Setup Guide

## Prerequisites

- Raspberry Pi 4 Model B running Debian Bookworm (64-bit recommended)
- Python 3.10+
- I2C enabled (`raspi-config` → Interface Options → I2C)
- Camera enabled (`raspi-config` → Interface Options → Camera)
- `aplay` available (`sudo apt install alsa-utils`)

## 1. Clone the Repository

```bash
git clone http://192.168.0.90:673/hermes/sentry-turret-v3.git
cd sentry-turret-v3
```

## 2. Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

!!! note "OpenCV on Pi"
    `opencv-contrib-python` includes the `cv2.face` module needed for LBPH.  If pip install is slow, use the system package:
    ```bash
    sudo apt install python3-opencv
    pip install opencv-contrib-python --no-binary :all:
    ```

## 3. Audio Clips

Place WAV files in the following directory structure:

```
~/Documents/FacialRecognitionProject/dreadnought_clips/
├── init/
├── targeting/
├── engaging/
├── armed/
├── disarmed/
├── shutdown/
├── mission_complete/
└── out_of_ammo/
```

Each subdirectory should contain one or more `.wav` files.  A random clip is selected each time the event fires.

## 4. Environment Variables

| Variable  | Default | Description |
|-----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose hardware output |

```bash
export LOG_LEVEL=DEBUG
```

## 5. Stream Overlay Image (optional)

Save a PNG (transparency supported) to:
```
~/Documents/FacialRecognitionProject/overlay.png
```

It will be rendered at 80×80 px in the top-right corner of the live stream. Without the file, the overlay is silently skipped.

## 6. Run

```bash
python main.py
```

The web UI is available at `http://<pi-ip>:8080`.

## 6. Run Tests (CI / development machine)

Tests mock all hardware and can run on any machine with Python 3.10+:

```bash
pip install pytest httpx fastapi jinja2 python-multipart numpy
pytest
```

## 7. Build Documentation

```bash
pip install mkdocs mkdocs-material
mkdocs serve    # development server at http://127.0.0.1:8000
mkdocs build    # outputs to site/
```

## 8. First-Time Face Enrollment

1. Open the web UI and switch to **Registration** mode.
2. Navigate to the **Register** page.
3. Enter the person's name and click **Capture Snapshot** at least 20 times (varying angles/expressions).
4. Click **Train Model**.
5. Switch back to **Autonomous** mode — the person is now recognised as safe.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Camera not found | Run `v4l2-ctl --list-devices`; check ribbon cable seating |
| Servos jitter | Check 6V supply capacity; reduce PID_KP in `config.py` |
| No audio | Run `aplay -l`; set default in `~/.asoundrc` |
| I2C device not found | Run `i2cdetect -y 1`; confirm 0x40 appears |
| Relay fires continuously | Check input/output toggle logic; do NOT use HIGH/LOW |
