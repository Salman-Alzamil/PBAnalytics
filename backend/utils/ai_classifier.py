<<<<<<< HEAD
from ultralytics import YOLO
from io import BytesIO
from PIL import Image
import os

_model = None

def _get_model():
    global _model
    if _model is None:
        model_path = 'model/best.pt'
        if not os.path.exists(model_path):
            raise RuntimeError(f"Model file not found: {model_path}")
        _model = YOLO(model_path)
    return _model

def classify_image_bytes(image_bytes: bytes) -> dict:
    """
    Takes raw image bytes, runs YOLO classification,
    returns prediction and confidence as a dict.
    """
    model = _get_model()
=======
import json
import os
from io import BytesIO
from PIL import Image
from ultralytics import YOLO

_CONFIG_PATH = "model/active_model.json"
_DEFAULT_PATH = "model/best.pt"

_model: YOLO | None = None
_loaded_path: str | None = None


def _read_config() -> dict:
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    return {"version": "v1.0", "checkpoint": "best", "path": _DEFAULT_PATH}


def _get_model() -> tuple[YOLO, dict]:
    global _model, _loaded_path
    config = _read_config()
    model_path = config.get("path", _DEFAULT_PATH)
    if _model is None or _loaded_path != model_path:
        if not os.path.exists(model_path):
            raise RuntimeError(f"Model file not found: {model_path}")
        _model = YOLO(model_path)
        _loaded_path = model_path
    return _model, config


def reload_model() -> dict:
    """Force the next call to re-read active_model.json and load fresh weights."""
    global _model, _loaded_path
    _model = None
    _loaded_path = None
    _, config = _get_model()
    return config


def get_model_info() -> dict:
    """Return metadata about the currently loaded model."""
    _, config = _get_model()
    return {**config, "loaded_path": _loaded_path}


def classify_image_bytes(image_bytes: bytes) -> dict:
    model, _ = _get_model()
>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    result = model.predict(img, verbose=False)
    predicted_class = result[0].names[result[0].probs.top1]
    confidence = float(result[0].probs.top1conf) * 100
    all_probs = {
        result[0].names[i]: round(float(result[0].probs.data[i]) * 100, 2)
        for i in range(len(result[0].names))
    }
    return {
        "prediction": predicted_class,
        "confidence": round(confidence, 2),
<<<<<<< HEAD
        "all_classes": all_probs
=======
        "all_classes": all_probs,
>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0
    }
