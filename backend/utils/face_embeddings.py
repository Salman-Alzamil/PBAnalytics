import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from insightface.app import FaceAnalysis

EMBED_DIM = 512
# RetinaFace (buffalo_l detector) scores are calibrated lower than MTCNN's:
# the test set produced det_score 0.68–0.89 on real faces, with the reference
# image at 0.684. The InsightFace default is 0.50; staying at 0.50 catches all
# real faces in our set while still rejecting low-quality false positives.
_MIN_FACE_CONFIDENCE = 0.50
_app = None


def _get_app():
    global _app
    if _app is None:
        _app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _app.prepare(ctx_id=-1, det_size=(640, 640))
    return _app


def _pil_to_bgr(image_bytes: bytes) -> np.ndarray:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def detect_faces(image_bytes: bytes) -> list[dict]:
    img_bgr = _pil_to_bgr(image_bytes)
    faces = _get_app().get(img_bgr)
    return [
        {
            "box": {
                "x": max(0, int(f.bbox[0])),
                "y": max(0, int(f.bbox[1])),
                "width": max(1, int(f.bbox[2] - f.bbox[0])),
                "height": max(1, int(f.bbox[3] - f.bbox[1])),
            },
            "confidence": float(f.det_score),
        }
        for f in faces
        if f.det_score >= _MIN_FACE_CONFIDENCE
    ]


def extract_single_embedding(image_bytes: bytes) -> tuple[list[float] | None, int]:
    img_bgr = _pil_to_bgr(image_bytes)
    faces = [f for f in _get_app().get(img_bgr) if f.det_score >= _MIN_FACE_CONFIDENCE]
    if len(faces) != 1:
        return None, len(faces)
    return faces[0].normed_embedding.tolist(), 1


def extract_embedding_for_profile(image_bytes: bytes) -> list[float] | None:
    img_bgr = _pil_to_bgr(image_bytes)
    faces = [f for f in _get_app().get(img_bgr) if f.det_score >= _MIN_FACE_CONFIDENCE]
    if not faces:
        return None
    best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return best.normed_embedding.tolist()


def extract_group_embeddings(image_bytes: bytes) -> list[dict]:
    img_bgr = _pil_to_bgr(image_bytes)
    faces = [f for f in _get_app().get(img_bgr) if f.det_score >= _MIN_FACE_CONFIDENCE]
    return [
        {
            "face_index": i,
            "box": {
                "x": max(0, int(f.bbox[0])),
                "y": max(0, int(f.bbox[1])),
                "width": max(1, int(f.bbox[2] - f.bbox[0])),
                "height": max(1, int(f.bbox[3] - f.bbox[1])),
            },
            "detection_confidence": float(f.det_score),
            "embedding": f.normed_embedding.tolist(),
        }
        for i, f in enumerate(faces)
    ]
