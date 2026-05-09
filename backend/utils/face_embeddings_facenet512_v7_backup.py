import numpy as np
from io import BytesIO
from PIL import Image

_mtcnn_detector = None

EMBED_DIM = 512  # Facenet512 produces 512-dim embeddings (same dim as ArcFace,
                 # so no DB schema change is needed when swapping models)

# Minimum short-side dimension for reliable MTCNN face detection.
# Images smaller than this are upscaled before detection/embedding.
_MIN_DIM = 320

# Reject MTCNN detections below this confidence. Real faces in our test set
# scored 0.84-1.00; the landscape false-positive was 0.97 only when CLAHE was
# applied, and produces 0 detections without it. 0.80 is inclusive of harder
# real faces while still leaving headroom over typical garbage detections.
_MIN_FACE_CONFIDENCE = 0.80


def _get_mtcnn():
    global _mtcnn_detector
    if _mtcnn_detector is None:
        from mtcnn import MTCNN
        _mtcnn_detector = MTCNN()
    return _mtcnn_detector


def _normalize(embedding: list) -> list[float]:
    arr = np.array(embedding, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def _preprocess(img_array: np.ndarray) -> np.ndarray:
    """Upscale small images for reliable MTCNN detection.

    No CLAHE: it amplifies non-face textures into face-like features and was
    producing high-confidence false detections on landscapes.
    """
    h, w = img_array.shape[:2]
    if min(h, w) < _MIN_DIM:
        scale = _MIN_DIM / min(h, w)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img_array = np.array(
            Image.fromarray(img_array).resize((new_w, new_h), Image.LANCZOS)
        )
    return img_array


def _detect_largest_face(img_array: np.ndarray) -> dict | None:
    """Return the largest detection from the standalone MTCNN, or None.

    Filters out low-confidence detections to avoid embedding bogus crops.
    """
    faces = _get_mtcnn().detect_faces(img_array)
    faces = [f for f in faces if f.get("confidence", 0.0) >= _MIN_FACE_CONFIDENCE]
    if not faces:
        return None
    return max(faces, key=lambda f: f["box"][2] * f["box"][3])


def _crop(img_array: np.ndarray, box: dict, pad: float = 0.25) -> np.ndarray:
    # 0.25 padding chosen via ablation: pad=0.25 gave gap -0.058 vs pad=0.35
    # gap -0.161 on the test_imgs set. Tighter crops (0.15-0.20) regressed
    # because background context still helps Facenet512 disambiguate.
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    ih, iw = img_array.shape[:2]
    p = int(min(w, h) * pad)
    return img_array[max(0, y - p):min(ih, y + h + p),
                     max(0, x - p):min(iw, x + w + p)]


def _embed(img_array: np.ndarray) -> list[float]:
    """Detect with our standalone MTCNN, crop, then embed with Facenet512.

    DeepFace's bundled MTCNN raises a TF shape error on some inputs and
    silently falls back to embedding the whole image when enforce_detection
    is False — both produce degenerate vectors that cluster falsely. We
    detect+crop with the standalone `mtcnn` package and feed the crop to
    DeepFace with detector_backend="skip" so it just runs the embedder.

    Facenet512 was chosen over ArcFace after measurements: on cross-pose
    same-person pairs, ArcFace gave a negative same/different gap
    (same=0.57, different=0.61), making the search return wrong winners.
    Facenet512 puts different identities at negative cos-sim while keeping
    same identities at 0.45-0.51, producing a wide, usable gap.

    Alignment is intentionally not performed: 2/5-point alignment with
    DeepFace's weights produced lower same-person similarity than a
    simple padded crop in our test set.
    """
    from deepface import DeepFace
    img_array = _preprocess(img_array)
    face = _detect_largest_face(img_array)
    if face is None:
        raise ValueError("no face found")
    box = {
        "x": face["box"][0], "y": face["box"][1],
        "width": face["box"][2], "height": face["box"][3],
    }
    crop = _crop(img_array, box)
    if crop.size == 0:
        raise ValueError("invalid face crop")
    reps = DeepFace.represent(
        crop,
        model_name="Facenet512",
        detector_backend="skip",
        enforce_detection=False,
        align=False,
    )
    if not reps:
        raise ValueError("Facenet512 produced no embedding")
    return _normalize(reps[0]["embedding"])


def detect_faces(image_bytes: bytes) -> list[dict]:
    """Detect faces and return bounding boxes in original image coordinates.

    Upscales internally when the image is too small for reliable detection,
    then maps coordinates back to the original pixel space so the frontend
    overlay stays accurate. Filters by confidence to avoid false positives.
    """
    orig = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
    h, w = orig.shape[:2]
    scale = 1.0
    img = orig
    if min(h, w) < _MIN_DIM:
        scale = _MIN_DIM / min(h, w)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = np.array(Image.fromarray(orig).resize((new_w, new_h), Image.LANCZOS))
    results = _get_mtcnn().detect_faces(img)
    return [
        {
            "box": {
                "x": max(0, int(r["box"][0] / scale)),
                "y": max(0, int(r["box"][1] / scale)),
                "width": max(1, int(r["box"][2] / scale)),
                "height": max(1, int(r["box"][3] / scale)),
            },
            "confidence": float(r["confidence"]),
        }
        for r in results
        if r.get("confidence", 0.0) >= _MIN_FACE_CONFIDENCE
    ]


def extract_single_embedding(image_bytes: bytes) -> tuple[list[float] | None, int]:
    """Extract an embedding from an image that contains exactly one face."""
    faces = detect_faces(image_bytes)
    if len(faces) != 1:
        return None, len(faces)
    img_array = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
    try:
        return _embed(img_array), 1
    except Exception:
        return None, 1


def extract_embedding_for_profile(image_bytes: bytes) -> list[float] | None:
    """Extract an embedding from a contact profile picture."""
    img_array = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
    try:
        return _embed(img_array)
    except Exception:
        return None


def extract_group_embeddings(image_bytes: bytes) -> list[dict]:
    """Detect all faces in a group photo and return embeddings + bounding boxes.

    Standalone MTCNN for detection (with confidence filter), then ArcFace via
    DeepFace with detector_backend="skip". Bounding boxes are mapped back to
    original image space.
    """
    from deepface import DeepFace
    img_array = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
    orig_h, orig_w = img_array.shape[:2]

    preprocessed = _preprocess(img_array.copy())
    prep_h, prep_w = preprocessed.shape[:2]
    sx = orig_w / prep_w
    sy = orig_h / prep_h

    faces = [
        f for f in _get_mtcnn().detect_faces(preprocessed)
        if f.get("confidence", 0.0) >= _MIN_FACE_CONFIDENCE
    ]
    result: list[dict] = []
    for i, face in enumerate(faces):
        x, y, w, h = face["box"]
        crop = _crop(preprocessed, {"x": x, "y": y, "width": w, "height": h})
        if crop.size == 0:
            continue
        try:
            reps = DeepFace.represent(
                crop,
                model_name="Facenet512",
                detector_backend="skip",
                enforce_detection=False,
                align=False,
            )
        except Exception:
            continue
        if not reps:
            continue
        result.append({
            "face_index": i,
            "box": {
                "x": max(0, int(x * sx)),
                "y": max(0, int(y * sy)),
                "width": max(1, int(w * sx)),
                "height": max(1, int(h * sy)),
            },
            "detection_confidence": float(face.get("confidence", 1.0)),
            "embedding": _normalize(reps[0]["embedding"]),
        })
    return result
