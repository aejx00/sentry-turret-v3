"""Central configuration for Sentry Turret V3."""
import os

# Camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_FPS = 30

# PCA9685 servo driver
PCA9685_ADDRESS = 0x40
PCA9685_FREQUENCY = 60
SERVO_PAN_CHANNEL = 0
SERVO_TILT_CHANNEL = 1
SERVO_CENTER = 375
SERVO_MIN = 150
SERVO_MAX = 600

# GPIO
RELAY_PIN = 21  # BCM

# Firing
MAGAZINE_CAPACITY = 6
BURST_COUNT = 3
SEMI_AUTO_DELAY = 0.15   # seconds between shots
FULL_AUTO_DELAY = 0.12

# Face recognition
FACE_SCALE_FACTOR = 1.1
FACE_MIN_NEIGHBORS = 5
FACE_MIN_SIZE = (60, 60)
LBPH_CONFIDENCE_THRESHOLD = 80.0  # below = recognised; above = unknown/hostile

# PID tracking
PID_KP = 0.10
PID_KI = 0.01
PID_KD = 0.05

# Audio clips base directory
AUDIO_BASE_DIR = os.path.expanduser("~/Documents/FacialRecognitionProject/dreadnought_clips")
AUDIO_STATE_DIRS = {
    "init":             "init",
    "targeting":        "targeting",
    "engaging":         "engaging",
    "armed":            "armed",
    "disarmed":         "disarmed",
    "shutdown":         "shutdown",
    "mission_complete": "mission_complete",
    "out_of_ammo":      "out_of_ammo",
}

# Face data storage
FACE_DATA_DIR = os.path.expanduser("~/Documents/FacialRecognitionProject/face_data")
HAAR_CASCADE_PATH = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"

# Stream overlay image (PNG with transparency recommended)
OVERLAY_IMAGE_PATH = os.path.expanduser("~/Documents/FacialRecognitionProject/overlay.png")
OVERLAY_SIZE = 80  # pixels — square, top-right corner

# Patrol mode
PATROL_PAN_MIN = 200
PATROL_PAN_MAX = 550
PATROL_TILT_CENTER = 375
PATROL_STEP = 4  # servo units per tick (~0.5 deg)

# Fire cooldown
FIRE_COOLDOWN = 2.0  # seconds between engagements

# Ammo persistence
AMMO_PERSIST_PATH = os.path.expanduser("~/Documents/FacialRecognitionProject/ammo_state.json")

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080
MJPEG_QUALITY = 70
