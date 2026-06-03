"""MJPEG stream generator with HUD annotation and logo overlay."""
from __future__ import annotations

import os
from typing import AsyncGenerator, Optional, Tuple
import numpy as np

from src.config import MJPEG_QUALITY, OVERLAY_IMAGE_PATH, OVERLAY_SIZE
from src.utils.logging_config import get_logger

log = get_logger(__name__)

_BOUNDARY     = b"--frame"
_CONTENT_TYPE = b"Content-Type: image/jpeg\r\n\r\n"

# Cached overlay — loaded once on first use
_overlay_cache: Optional[np.ndarray] = None
_overlay_checked = False

# Box colours (BGR)
_COL_SAFE     = (0, 255, 0)    # green   — safe or general detection
_COL_ACQUIRED = (0, 165, 255)  # orange  — hostile target locked
_COL_FIRING   = (0, 0, 255)    # red     — currently firing


def _load_overlay() -> Optional[np.ndarray]:
    global _overlay_cache, _overlay_checked
    if _overlay_checked:
        return _overlay_cache
    _overlay_checked = True
    import cv2

    if not os.path.exists(OVERLAY_IMAGE_PATH):
        log.debug("No overlay image at %s — skipping", OVERLAY_IMAGE_PATH)
        return None
    img = cv2.imread(OVERLAY_IMAGE_PATH, cv2.IMREAD_UNCHANGED)
    if img is None:
        log.warning("Failed to load overlay image: %s", OVERLAY_IMAGE_PATH)
        return None
    _overlay_cache = cv2.resize(img, (OVERLAY_SIZE, OVERLAY_SIZE), interpolation=cv2.INTER_AREA)
    log.info("Overlay loaded: %s (%dpx)", OVERLAY_IMAGE_PATH, OVERLAY_SIZE)
    return _overlay_cache


def _apply_overlay(frame: np.ndarray, overlay: np.ndarray) -> None:
    """Blend overlay PNG into the top-right corner of frame (in-place)."""
    h, w = overlay.shape[:2]
    fh, fw = frame.shape[:2]
    x, y = fw - w - 10, 10
    roi = frame[y:y + h, x:x + w]
    if overlay.ndim == 3 and overlay.shape[2] == 4:
        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        rgb   = overlay[:, :, :3].astype(np.float32)
        roi[:] = (alpha * rgb + (1.0 - alpha) * roi.astype(np.float32)).astype(np.uint8)
    else:
        roi[:] = overlay[:, :, :3] if overlay.ndim == 3 and overlay.shape[2] >= 3 else overlay


def _rects_match(r1: Optional[Tuple], r2: Optional[Tuple], tolerance: int = 40) -> bool:
    """True when both rects have centres within tolerance pixels of each other."""
    if r1 is None or r2 is None:
        return False
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2
    return abs((x1 + w1 // 2) - (x2 + w2 // 2)) < tolerance and \
           abs((y1 + h1 // 2) - (y2 + h2 // 2)) < tolerance


async def mjpeg_generator(camera, state, detector) -> AsyncGenerator[bytes, None]:
    """Yields MJPEG frames for StreamingResponse."""
    import cv2
    import asyncio

    overlay = _load_overlay()

    while True:
        frame = camera.get_frame()
        if frame is None:
            await asyncio.sleep(0.05)
            continue

        annotated = frame.copy()
        faces = detector.detect(frame) if state.mode.value in ("autonomous", "manual", "patrol") else []

        snap = state.snapshot()
        target_rect = state.target_rect
        is_firing = snap.get("is_firing", False)
        target_acquired = snap.get("target_acquired", False)

        for rect in faces:
            if _rects_match(rect, target_rect):
                colour = _COL_FIRING if is_firing else (_COL_ACQUIRED if target_acquired else _COL_SAFE)
            else:
                colour = _COL_SAFE
            x, y, w, h = rect
            cv2.rectangle(annotated, (x, y), (x + w, y + h), colour, 2)

        _draw_hud(annotated, snap)

        if overlay is not None:
            _apply_overlay(annotated, overlay)

        ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY])
        if not ok:
            continue

        yield _BOUNDARY + b"\r\n" + _CONTENT_TYPE + buf.tobytes() + b"\r\n"
        await asyncio.sleep(1 / 30)


def _draw_hud(frame: np.ndarray, snap: dict) -> None:
    import cv2

    colour  = (0, 0, 255) if snap["armed"] else (0, 200, 0)
    arm_txt = "ARMED" if snap["armed"] else "SAFE"
    cv2.putText(frame, f"{arm_txt} | {snap['mode'].upper()} | AMMO:{snap['ammo']}",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)

    if snap["tracking"] and snap["target"]:
        cv2.putText(frame, f"ID: {snap['target']}", (8, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)

    cooldown = snap.get("cooldown_remaining", 0.0)
    if cooldown > 0.0:
        cv2.putText(frame, f"COOLDOWN: {cooldown:.1f}s",
                    (8, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

    if snap.get("muted"):
        cv2.putText(frame, "MUTED", (8, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
