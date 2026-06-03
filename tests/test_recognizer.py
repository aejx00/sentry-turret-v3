"""Tests for FaceRecognizer."""
import sys
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
import os
import tempfile


@pytest.fixture
def recognizer(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.config.FACE_DATA_DIR", str(tmp_path / "face_data"))
    monkeypatch.setattr("src.vision.recognizer.FACE_DATA_DIR", str(tmp_path / "face_data"))
    monkeypatch.setattr("src.vision.recognizer.MODEL_FILE", str(tmp_path / "model.yml"))
    monkeypatch.setattr("src.vision.recognizer.LABELS_FILE", str(tmp_path / "labels.pkl"))

    from src.vision.recognizer import FaceRecognizer
    r = FaceRecognizer()
    r.start()
    return r


def _sample():
    return np.zeros((100, 100), dtype=np.uint8)


def test_predict_returns_none_when_untrained(recognizer):
    name, conf = recognizer.predict(_sample())
    assert name is None
    assert conf > 100


def test_enroll_adds_profile(recognizer):
    recognizer.enroll("Alice", [_sample(), _sample()])
    assert "Alice" in recognizer.list_profiles()


def test_enroll_and_predict_known(recognizer):
    cv2 = sys.modules["cv2"]
    lbph = cv2.face.LBPHFaceRecognizer_create.return_value
    # id 1 will be Alice
    lbph.predict.return_value = (1, 40.0)
    recognizer.enroll("Alice", [_sample(), _sample()])
    recognizer._name_map["Alice"] = 1
    recognizer._label_map[1] = "Alice"
    name, conf = recognizer.predict(_sample())
    assert name == "Alice"
    assert conf == pytest.approx(40.0)


def test_predict_hostile_above_threshold(recognizer):
    cv2 = sys.modules["cv2"]
    lbph = cv2.face.LBPHFaceRecognizer_create.return_value
    lbph.predict.return_value = (1, 90.0)
    recognizer.enroll("Bob", [_sample()])
    recognizer._trained = True
    name, conf = recognizer.predict(_sample())
    assert name is None


def test_delete_profile(recognizer):
    recognizer.enroll("Carol", [_sample()])
    assert recognizer.delete_profile("Carol") is True
    assert "Carol" not in recognizer.list_profiles()


def test_delete_missing_profile(recognizer):
    assert recognizer.delete_profile("Nobody") is False


def test_is_safe_true_for_known(recognizer):
    assert recognizer.is_safe("Alice") is True


def test_is_safe_false_for_none(recognizer):
    assert recognizer.is_safe(None) is False
