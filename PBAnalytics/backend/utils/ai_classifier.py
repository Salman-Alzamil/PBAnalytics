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
        "all_classes": all_probs
    }
