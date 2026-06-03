# Software Architecture

## Module Map

```
sentry-turret-v3/
├── main.py                     # Entry point — wires all components, starts web server
├── src/
│   ├── config.py               # All tunable constants (PWM range, PID gains, paths…)
│   ├── hardware/
│   │   ├── camera.py           # IMX477 via OpenCV — threaded capture loop
│   │   ├── servo.py            # PCA9685 pan/tilt — thread-safe, clamped PWM
│   │   ├── relay.py            # GPIO 21 firing relay — input/output toggle workaround
│   │   └── audio.py            # AudioPlayer — non-blocking WAV via subprocess aplay
│   ├── vision/
│   │   ├── detector.py         # Haar cascade face detection
│   │   ├── recognizer.py       # LBPH recognition, enrollment, persistence
│   │   └── tracker.py          # PID face tracker → servo deltas
│   ├── control/
│   │   ├── state.py            # SystemState — thread-safe shared state
│   │   ├── fire_control.py     # FireController — mediates safety/ammo/relay
│   │   └── autonomous.py       # AutonomousController — main engagement loop
│   ├── utils/
│   │   └── logging_config.py   # Structured logging, LOG_LEVEL env var
│   └── web/
│       ├── app.py              # FastAPI app factory
│       ├── stream.py           # MJPEG generator with HUD overlay
│       └── templates/          # Jinja2 HTML templates
└── tests/                      # pytest suite — all hardware mocked in conftest.py
```

## Key Design Decisions

### Dependency Injection for Testability
All hardware classes accept optional mock arguments in their constructors (`gpio_module`, `i2c_bus`).  The `conftest.py` stubs out `RPi.GPIO`, `cv2`, `adafruit_pca9685`, and `board` at import time — no hardware required for `pytest`.

### Thread Model
| Thread | Purpose |
|--------|---------|
| `camera-capture` | Continuously reads frames into `_latest_frame`; other threads call `get_frame()` |
| `autonomous` | 15 Hz detect/track/fire loop; only runs when mode = AUTONOMOUS |
| `audio-<state>` | Daemon thread per clip — fire-and-forget, no blocking |
| `uvicorn` (main) | HTTP server; async handlers read shared state |

### SystemState as Single Source of Truth
`SystemState` is the only mutable shared object.  Every attribute access is protected by a `threading.Lock()`.  FastAPI handlers and the autonomous loop both read/write exclusively through this object.

### PCA9685 PWM Range
The safe servo range is **PWM 150–600** (out of 4096).  Values are clamped in `ServoController._clamp()` before being written to the driver.  Any out-of-range command is logged as a warning and silently clamped rather than raising an exception, to avoid interrupting an active engagement.
