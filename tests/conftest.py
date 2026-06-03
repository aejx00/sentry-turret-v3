"""Shared fixtures — all hardware mocked for CI-safe testing."""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

# ---------------------------------------------------------------------------
# Stub out hardware libraries before any src import
# ---------------------------------------------------------------------------

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# RPi.GPIO
_gpio = _make_stub("RPi")
_gpio_gpio = _make_stub("RPi.GPIO")
_gpio_gpio.BCM = 11
_gpio_gpio.IN = 1
_gpio_gpio.OUT = 0
_gpio_gpio.setmode = MagicMock()
_gpio_gpio.setup = MagicMock()
_gpio_gpio.cleanup = MagicMock()
_gpio.GPIO = _gpio_gpio

# board / busio
_board = _make_stub("board")
_board.SCL = MagicMock()
_board.SDA = MagicMock()
_busio = _make_stub("busio")
_busio.I2C = MagicMock(return_value=MagicMock())

# adafruit_pca9685
_pca_mod = _make_stub("adafruit_pca9685")
_MockPCA = MagicMock()
_pca_mod.PCA9685 = _MockPCA

# cv2 (minimal stub with what we need)
_cv2 = _make_stub("cv2")
_cv2.COLOR_BGR2GRAY = 6
_cv2.COLOR_GRAY2BGR = 8
_cv2.CASCADE_SCALE_IMAGE = 2
_cv2.CAP_V4L2 = 200
_cv2.CAP_PROP_FRAME_WIDTH  = 3
_cv2.CAP_PROP_FRAME_HEIGHT = 4
_cv2.CAP_PROP_FPS          = 5
_cv2.IMWRITE_JPEG_QUALITY  = 1
_cv2.FONT_HERSHEY_SIMPLEX  = 0
_cv2.cvtColor = MagicMock(return_value=np.zeros((480, 640), dtype=np.uint8))
_cv2.equalizeHist = MagicMock(return_value=np.zeros((480, 640), dtype=np.uint8))
_cv2.rectangle = MagicMock()
_cv2.putText = MagicMock()
_cv2.imencode = MagicMock(return_value=(True, np.zeros(100, dtype=np.uint8)))
_cv2.imread = MagicMock(return_value=np.zeros((100, 100), dtype=np.uint8))
_cv2.imwrite = MagicMock(return_value=True)

_mock_cascade = MagicMock()
_mock_cascade.empty.return_value = False
_mock_cascade.detectMultiScale.return_value = np.array([[100, 100, 80, 80]])
_cv2.CascadeClassifier = MagicMock(return_value=_mock_cascade)

# cv2.face
_cv2_face = types.ModuleType("cv2.face")
_MockLBPH = MagicMock()
_MockLBPH.return_value.predict.return_value = (1, 45.0)
_cv2_face.LBPHFaceRecognizer_create = _MockLBPH
_cv2.face = _cv2_face
sys.modules["cv2.face"] = _cv2_face

# VideoCapture
_mock_cap = MagicMock()
_mock_cap.isOpened.return_value = True
_mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
_cv2.VideoCapture = MagicMock(return_value=_mock_cap)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_gpio():
    return _gpio_gpio


@pytest.fixture
def mock_pca():
    pca_instance = MagicMock()
    _MockPCA.return_value = pca_instance
    return pca_instance


@pytest.fixture
def blank_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)
