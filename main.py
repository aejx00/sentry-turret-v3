#!/usr/bin/env python3
"""Sentry Turret V3 — single entry point."""
import signal
import sys
import threading
import uvicorn

from src.config import WEB_HOST, WEB_PORT
from src.control.autonomous import AutonomousController
from src.control.engagement_log import EngagementLog
from src.control.fire_control import FireController
from src.control.state import SystemState
from src.hardware.audio import AudioPlayer
from src.hardware.camera import Camera
from src.hardware.relay import FiringRelay
from src.hardware.servo import ServoController
from src.utils.logging_config import get_logger, setup_logging
from src.vision.detector import FaceDetector
from src.vision.recognizer import FaceRecognizer
from src.vision.tracker import FaceTracker
from src.web.app import create_app

setup_logging()
log = get_logger("main")


def main() -> None:
    log.info("=" * 60)
    log.info("Sentry Turret V3 — starting up")
    log.info("=" * 60)

    state        = SystemState()
    audio        = AudioPlayer()
    camera       = Camera()
    servo        = ServoController()
    relay        = FiringRelay()
    detector     = FaceDetector()
    recognizer   = FaceRecognizer()
    tracker      = FaceTracker()
    engage_log   = EngagementLog()
    fire_ctrl    = FireController(state, relay, audio, engagement_log=engage_log)
    autonomous   = AutonomousController(state, camera, servo, detector, recognizer, tracker, fire_ctrl, audio)

    # Restore ammo count from previous run
    state.load_ammo()

    # ------------------------------------------------------------------
    # Graceful shutdown
    # ------------------------------------------------------------------

    def shutdown(signum=None, frame=None) -> None:
        log.info("Shutdown signal received — cleaning up")
        autonomous.stop()
        state.save_ammo()
        audio.play("shutdown")
        servo.stop()
        relay.stop()
        camera.stop()
        log.info("Shutdown complete")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ------------------------------------------------------------------
    # Hardware init
    # ------------------------------------------------------------------

    try:
        camera.start()
        servo.start()
        relay.start()
        detector.start()
        recognizer.start()
    except Exception as exc:
        log.error("Hardware init failed: %s", exc)
        shutdown()
        return

    audio.play("init")
    autonomous.start()

    # ------------------------------------------------------------------
    # Web server
    # ------------------------------------------------------------------

    app = create_app(state, camera, servo, detector, recognizer, fire_ctrl, audio,
                     engagement_log=engage_log)
    log.info("Web UI available at http://%s:%d", WEB_HOST, WEB_PORT)
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT, log_level="warning")


if __name__ == "__main__":
    main()
