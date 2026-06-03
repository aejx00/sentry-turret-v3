"""LBPH face recognizer — enroll safe individuals, treat unknowns as hostile."""
from __future__ import annotations

import os
import pickle
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.config import FACE_DATA_DIR, LBPH_CONFIDENCE_THRESHOLD
from src.utils.logging_config import get_logger

log = get_logger(__name__)

LABELS_FILE = os.path.join(FACE_DATA_DIR, "labels.pkl")
MODEL_FILE = os.path.join(FACE_DATA_DIR, "lbph_model.yml")
META_FILE = os.path.join(FACE_DATA_DIR, "profile_meta.pkl")

# Default metadata applied to every new profile
_DEFAULT_META = {
    "classification": "safe",   # "safe" or "hostile"
    "fire_mode": None,          # None = don't override; or "semi"/"burst"/"full_auto"
    "detect_sound": None,       # None = use "targeting"; or any AUDIO_STATE_DIRS key
}


class FaceRecognizer:
    """LBPH-based recognizer.  label_id=0 is always UNKNOWN/hostile."""

    def __init__(self) -> None:
        self._recognizer = None
        self._label_map: Dict[int, str] = {}
        self._name_map: Dict[str, int] = {}
        self._next_id = 1
        self._trained = False
        self._profile_meta: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        import cv2

        self._recognizer = cv2.face.LBPHFaceRecognizer_create()
        os.makedirs(FACE_DATA_DIR, exist_ok=True)
        if os.path.exists(MODEL_FILE) and os.path.exists(LABELS_FILE):
            self._load()
        else:
            log.info("No existing model — recognizer not trained yet")

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def predict(self, roi_gray: np.ndarray) -> Tuple[Optional[str], float]:
        """Return (name_or_None, confidence).  None means unknown/hostile."""
        if not self._trained or self._recognizer is None:
            return None, 999.0
        label_id, confidence = self._recognizer.predict(roi_gray)
        if confidence > LBPH_CONFIDENCE_THRESHOLD:
            log.debug("Face not recognised (conf=%.1f > threshold %.1f)", confidence, LBPH_CONFIDENCE_THRESHOLD)
            return None, confidence
        name = self._label_map.get(label_id, "UNKNOWN")
        log.debug("Recognised '%s' (conf=%.1f)", name, confidence)
        return name, confidence

    def is_safe(self, name: Optional[str]) -> bool:
        """Enrolled profiles default to safe; explicitly classified hostile profiles are not."""
        if name is None:
            return False
        meta = self._profile_meta.get(name, _DEFAULT_META)
        return meta.get("classification", "safe") == "safe"

    # ------------------------------------------------------------------
    # Profile metadata
    # ------------------------------------------------------------------

    def get_profile_meta(self, name: str) -> dict:
        return dict(self._profile_meta.get(name, _DEFAULT_META))

    def set_profile_meta(self, name: str, classification: str, fire_mode: Optional[str], detect_sound: Optional[str]) -> None:
        self._profile_meta[name] = {
            "classification": classification,
            "fire_mode": fire_mode or None,
            "detect_sound": detect_sound or None,
        }
        self._save()
        log.info("Updated meta for '%s': class=%s fm=%s sound=%s", name, classification, fire_mode, detect_sound)

    def get_fire_mode(self, name: Optional[str]) -> Optional[str]:
        if name is None:
            return None
        return self._profile_meta.get(name, {}).get("fire_mode")

    def get_detect_sound(self, name: Optional[str]) -> Optional[str]:
        if name is None:
            return None
        return self._profile_meta.get(name, {}).get("detect_sound")

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------

    def enroll(self, name: str, samples: List[np.ndarray]) -> None:
        if name not in self._name_map:
            label_id = self._next_id
            self._next_id += 1
            self._name_map[name] = label_id
            self._label_map[label_id] = name
            if name not in self._profile_meta:
                self._profile_meta[name] = dict(_DEFAULT_META)
            log.info("Enrolling new person '%s' as label_id=%d", name, label_id)
        else:
            label_id = self._name_map[name]
            log.info("Updating existing person '%s' (label_id=%d)", name, label_id)

        images, labels = self._load_training_data()
        for sample in samples:
            images.append(sample)
            labels.append(label_id)
        self._retrain(images, labels)
        self._save()

    def list_profiles(self) -> List[str]:
        return list(self._name_map.keys())

    def delete_profile(self, name: str) -> bool:
        if name not in self._name_map:
            return False
        label_id = self._name_map.pop(name)
        self._label_map.pop(label_id, None)
        self._profile_meta.pop(name, None)
        log.info("Deleted profile '%s'", name)
        images, labels = self._load_training_data()
        filtered = [(img, lbl) for img, lbl in zip(images, labels) if lbl != label_id]
        if filtered:
            imgs, lbls = zip(*filtered)
            self._retrain(list(imgs), list(lbls))
        else:
            self._trained = False
        self._save()
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_training_data(self) -> Tuple[List[np.ndarray], List[int]]:
        images: List[np.ndarray] = []
        labels: List[int] = []
        for name, label_id in self._name_map.items():
            person_dir = os.path.join(FACE_DATA_DIR, name)
            if not os.path.isdir(person_dir):
                continue
            import cv2
            for fname in os.listdir(person_dir):
                if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                    img = cv2.imread(os.path.join(person_dir, fname), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        images.append(img)
                        labels.append(label_id)
        return images, labels

    def _retrain(self, images: List[np.ndarray], labels: List[int]) -> None:
        if not images:
            return
        self._recognizer.train(images, np.array(labels))
        self._trained = True
        log.info("LBPH model trained on %d samples across %d identities", len(images), len(self._label_map))

    def _save(self) -> None:
        if self._trained:
            self._recognizer.save(MODEL_FILE)
        with open(LABELS_FILE, "wb") as f:
            pickle.dump({
                "label_map": self._label_map,
                "name_map": self._name_map,
                "next_id": self._next_id,
            }, f)
        with open(META_FILE, "wb") as f:
            pickle.dump(self._profile_meta, f)
        log.debug("Model, labels and meta saved")

    def _load(self) -> None:
        self._recognizer.read(MODEL_FILE)
        with open(LABELS_FILE, "rb") as f:
            data = pickle.load(f)
        self._label_map = data["label_map"]
        self._name_map = data["name_map"]
        self._next_id = data["next_id"]
        self._trained = True
        if os.path.exists(META_FILE):
            with open(META_FILE, "rb") as f:
                self._profile_meta = pickle.load(f)
        log.info("Loaded LBPH model with %d profiles: %s", len(self._name_map), list(self._name_map.keys()))
