"""FastAPI web application — UI, MJPEG stream, REST control endpoints."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.control.state import FireMode, OperatingMode, SystemState
from src.utils.logging_config import get_logger
from src.web.stream import mjpeg_generator

log = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(
    state: SystemState,
    camera,
    servo,
    detector,
    recognizer,
    fire_ctrl,
    audio,
    engagement_log=None,
) -> FastAPI:
    app = FastAPI(title="Sentry Turret V3", version="3.0.0")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request, "index.html", {"profiles": recognizer.list_profiles()}
        )

    @app.get("/register", response_class=HTMLResponse)
    async def register_page(request: Request):
        return templates.TemplateResponse(
            request, "register.html", {"profiles": recognizer.list_profiles()}
        )

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    @app.get("/stream")
    async def video_stream():
        return StreamingResponse(
            mjpeg_generator(camera, state, detector),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @app.get("/api/status")
    async def get_status():
        snap = state.snapshot()
        snap["muted"] = audio.muted
        return JSONResponse(snap)

    # ------------------------------------------------------------------
    # Audio mute
    # ------------------------------------------------------------------

    @app.post("/api/mute/toggle")
    async def toggle_mute():
        muted = audio.toggle_mute()
        return JSONResponse({"muted": muted})

    # ------------------------------------------------------------------
    # Mode control
    # ------------------------------------------------------------------

    @app.post("/api/mode")
    async def set_mode(mode: str = Form(...)):
        try:
            new_mode = OperatingMode(mode)
        except ValueError:
            return JSONResponse({"error": f"Invalid mode: {mode}"}, status_code=400)
        state.mode = new_mode
        log.info("Mode → %s", new_mode.value)
        return JSONResponse({"mode": new_mode.value})

    @app.post("/api/fire_mode")
    async def set_fire_mode(fire_mode: str = Form(...)):
        try:
            new_fm = FireMode(fire_mode)
        except ValueError:
            return JSONResponse({"error": f"Invalid fire mode: {fire_mode}"}, status_code=400)
        state.fire_mode = new_fm
        log.info("Fire mode → %s", new_fm.value)
        return JSONResponse({"fire_mode": new_fm.value})

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    @app.post("/api/arm")
    async def arm():
        state.armed = True
        audio.play("armed")
        log.info("SAFETY ARMED")
        return JSONResponse({"armed": True})

    @app.post("/api/disarm")
    async def disarm():
        state.armed = False
        audio.play("disarmed")
        log.info("Safety disarmed")
        return JSONResponse({"armed": False})

    # ------------------------------------------------------------------
    # Manual pan/tilt
    # ------------------------------------------------------------------

    @app.post("/api/pan_tilt")
    async def manual_pan_tilt(pan: int = Form(...), tilt: int = Form(...)):
        servo.set_pan(pan)
        servo.set_tilt(tilt)
        state.pan = pan
        state.tilt = tilt
        return JSONResponse({"pan": pan, "tilt": tilt})

    @app.post("/api/pan_tilt/delta")
    async def pan_tilt_delta(pan_delta: int = Form(default=0), tilt_delta: int = Form(default=0)):
        servo.move(pan_delta, tilt_delta)
        pan, tilt = servo.position
        state.pan = pan
        state.tilt = tilt
        return JSONResponse({"pan": pan, "tilt": tilt})

    # ------------------------------------------------------------------
    # Fire
    # ------------------------------------------------------------------

    @app.post("/api/fire")
    async def fire():
        fired = fire_ctrl.attempt_fire()
        return JSONResponse({"fired": fired, "ammo": state.ammo})

    # ------------------------------------------------------------------
    # Ammo
    # ------------------------------------------------------------------

    @app.post("/api/reload")
    async def reload():
        state.reload()
        log.info("Magazine reloaded — ammo=%d", state.ammo)
        return JSONResponse({"ammo": state.ammo})

    # ------------------------------------------------------------------
    # Engagement log
    # ------------------------------------------------------------------

    @app.get("/api/log")
    async def get_log():
        if engagement_log is None:
            return JSONResponse([])
        return JSONResponse(engagement_log.to_list())

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @app.post("/api/register/snapshot")
    async def capture_snapshot(name: str = Form(...)):
        from src.config import FACE_DATA_DIR
        import cv2

        frame = camera.get_frame()
        if frame is None:
            return JSONResponse({"error": "No camera frame available"}, status_code=503)

        person_dir = os.path.join(FACE_DATA_DIR, name)
        os.makedirs(person_dir, exist_ok=True)
        existing = [f for f in os.listdir(person_dir) if f.endswith(".png")]
        idx = len(existing)
        path = os.path.join(person_dir, f"{idx:04d}.png")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(path, gray)
        log.info("Captured snapshot %s for '%s'", path, name)
        return JSONResponse({"saved": path, "count": idx + 1})

    @app.post("/api/register/train")
    async def train_profile(name: str = Form(...)):
        from src.config import FACE_DATA_DIR
        import cv2

        person_dir = os.path.join(FACE_DATA_DIR, name)
        if not os.path.isdir(person_dir):
            return JSONResponse({"error": f"No samples for '{name}'"}, status_code=404)
        images = []
        for fname in os.listdir(person_dir):
            if fname.endswith(".png"):
                img = cv2.imread(os.path.join(person_dir, fname), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    images.append(img)
        if not images:
            return JSONResponse({"error": "No valid images"}, status_code=400)
        recognizer.enroll(name, images)
        log.info("Enrolled '%s' with %d samples", name, len(images))
        return JSONResponse({"name": name, "samples": len(images)})

    @app.delete("/api/register/{name}")
    async def delete_profile(name: str):
        from src.config import FACE_DATA_DIR
        ok = recognizer.delete_profile(name)
        if not ok:
            return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)
        person_dir = os.path.join(FACE_DATA_DIR, name)
        if os.path.isdir(person_dir):
            shutil.rmtree(person_dir)
            log.info("Deleted photo directory for '%s'", name)
        return JSONResponse({"deleted": name})

    @app.get("/api/register/{name}/meta")
    async def get_profile_meta(name: str):
        meta = recognizer.get_profile_meta(name)
        return JSONResponse({"name": name, **meta})

    @app.post("/api/register/{name}/meta")
    async def set_profile_meta(
        name: str,
        classification: str = Form(default="safe"),
        fire_mode: str = Form(default=""),
        detect_sound: str = Form(default=""),
    ):
        recognizer.set_profile_meta(
            name,
            classification=classification,
            fire_mode=fire_mode or None,
            detect_sound=detect_sound or None,
        )
        return JSONResponse({"name": name, "classification": classification,
                             "fire_mode": fire_mode or None, "detect_sound": detect_sound or None})

    return app
