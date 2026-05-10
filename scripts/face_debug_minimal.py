"""Test the actual hypothesis:
- Does CLAHE create false-positive faces in landscapes?
- Does the alignment+crop ordering destroy same-person similarity?

Compares 4 variants on the 4 test images:
  A. raw upscale (no CLAHE), no alignment
  B. raw upscale (no CLAHE), align (current broken code)
  C. CLAHE + no alignment
  D. CLAHE + align (current pipeline)
For each, prints MTCNN confidence and pairwise cos-sim Ronaldo1 vs Ronaldo2.
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import numpy as np
from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")

from utils.face_embeddings import _get_mtcnn, _normalize  # noqa: E402

MIN_DIM = 320


def upscale(img):
    h, w = img.shape[:2]
    if min(h, w) < MIN_DIM:
        s = MIN_DIM / min(h, w)
        img = np.array(Image.fromarray(img).resize(
            (max(1, int(w*s)), max(1, int(h*s))), Image.LANCZOS))
    return img


def clahe(img):
    import cv2
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = cl.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def crop_box(img, box, pad=0.35):
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    ih, iw = img.shape[:2]
    p = int(min(w, h) * pad)
    return img[max(0, y - p):min(ih, y + h + p),
               max(0, x - p):min(iw, x + w + p)]


def align_then_crop(img, face):
    """My current broken approach: rotate the whole image, then crop with the
    pre-rotation bbox."""
    import cv2
    kp = face.get("keypoints", {})
    le, re = kp.get("left_eye"), kp.get("right_eye")
    aligned = img
    if le and re:
        angle = float(np.degrees(np.arctan2(re[1]-le[1], re[0]-le[0])))
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
        aligned = cv2.warpAffine(img, M, (w, h),
                                  flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE)
    x, y, w, h = face["box"]
    return crop_box(aligned, {"x": x, "y": y, "width": w, "height": h})


def crop_then_align(img, face):
    """Better: crop first (face is centered in the crop), then rotate around
    the eye midpoint."""
    import cv2
    x, y, w, h = face["box"]
    pad = int(min(w, h) * 0.35)
    x0 = max(0, x - pad); y0 = max(0, y - pad)
    crop = img[y0:min(img.shape[0], y + h + pad),
               x0:min(img.shape[1], x + w + pad)].copy()
    kp = face.get("keypoints", {})
    le, re = kp.get("left_eye"), kp.get("right_eye")
    if not le or not re or crop.size == 0:
        return crop
    le_c = (le[0] - x0, le[1] - y0)
    re_c = (re[0] - x0, re[1] - y0)
    angle = float(np.degrees(np.arctan2(re_c[1]-le_c[1], re_c[0]-le_c[0])))
    eye_mid = ((le_c[0] + re_c[0]) / 2, (le_c[1] + re_c[1]) / 2)
    M = cv2.getRotationMatrix2D(eye_mid, angle, 1.0)
    return cv2.warpAffine(crop, M, (crop.shape[1], crop.shape[0]),
                          flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REPLICATE)


def embed(crop):
    if crop.size == 0:
        return None
    from deepface import DeepFace
    try:
        reps = DeepFace.represent(
            crop, model_name="ArcFace",
            detector_backend="skip", enforce_detection=False, align=False,
        )
    except Exception:
        return None
    if not reps:
        return None
    return np.asarray(_normalize(reps[0]["embedding"]))


def cos(a, b):
    if a is None or b is None:
        return None
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


ARC_REF = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041],
], dtype=np.float32)


def arcface_align(img, face):
    """5-point similarity alignment to canonical ArcFace 112x112."""
    import cv2
    kp = face.get("keypoints", {})
    needed = ("left_eye", "right_eye", "nose", "mouth_left", "mouth_right")
    if not all(k in kp for k in needed):
        return None
    src = np.array([kp[k] for k in needed], dtype=np.float32)
    M, _ = cv2.estimateAffinePartial2D(src, ARC_REF, method=cv2.LMEDS)
    if M is None:
        return None
    return cv2.warpAffine(img, M, (112, 112), borderValue=0.0)


def embed_with_deepface_pipeline(crop):
    """Run DeepFace's own align + ArcFace on the crop."""
    if crop.size == 0:
        return None
    from deepface import DeepFace
    try:
        reps = DeepFace.represent(
            crop, model_name="ArcFace",
            detector_backend="mtcnn", enforce_detection=False, align=True,
        )
    except Exception as e:
        return None
    if not reps:
        return None
    return np.asarray(_normalize(reps[0]["embedding"]))


def main():
    print("\nDEEPFACE-ON-CROP TEST (crop-with-our-MTCNN, then DeepFace align+embed)")
    print(f"{'pipeline':<60} | cos-sim")
    print("-" * 75)
    a_bytes = (ROOT / "test_imgs" / "images.webp").read_bytes()
    b_bytes = (ROOT / "test_imgs" / "images (1).webp").read_bytes()
    a_arr = np.array(Image.open(BytesIO(a_bytes)).convert("RGB"))
    b_arr = np.array(Image.open(BytesIO(b_bytes)).convert("RGB"))

    for pad in (0.20, 0.35, 0.50, 0.80):
        ap, bp = upscale(a_arr.copy()), upscale(b_arr.copy())
        af = max(_get_mtcnn().detect_faces(ap), key=lambda x: x["box"][2]*x["box"][3])
        bf = max(_get_mtcnn().detect_faces(bp), key=lambda x: x["box"][2]*x["box"][3])
        ac = crop_box(ap, {"x":af["box"][0],"y":af["box"][1],
                            "width":af["box"][2],"height":af["box"][3]}, pad=pad)
        bc = crop_box(bp, {"x":bf["box"][0],"y":bf["box"][1],
                            "width":bf["box"][2],"height":bf["box"][3]}, pad=pad)
        ea = embed_with_deepface_pipeline(ac)
        eb = embed_with_deepface_pipeline(bc)
        s = cos(ea, eb)
        if s is None:
            print(f"crop pad={pad:.2f} -> DeepFace align+embed                    | (no embed)")
        else:
            print(f"crop pad={pad:.2f} -> DeepFace align+embed                    | {s:>7.4f}")

    print("\n5-POINT SIMILARITY ALIGNMENT TEST  (proper ArcFace pipeline)")
    print(f"{'pipeline':<60} | cos-sim")
    print("-" * 75)
    a_bytes = (ROOT / "test_imgs" / "images.webp").read_bytes()
    b_bytes = (ROOT / "test_imgs" / "images (1).webp").read_bytes()
    a_arr = np.array(Image.open(BytesIO(a_bytes)).convert("RGB"))
    b_arr = np.array(Image.open(BytesIO(b_bytes)).convert("RGB"))
    for name, prep in [
        ("upscale + 5pt-align + ArcFace 112x112",      upscale),
        ("upscale+CLAHE + 5pt-align + ArcFace 112x112", lambda i: clahe(upscale(i))),
    ]:
        ap, bp = prep(a_arr.copy()), prep(b_arr.copy())
        af = _get_mtcnn().detect_faces(ap)
        bf = _get_mtcnn().detect_faces(bp)
        af_best = max(af, key=lambda x: x["box"][2]*x["box"][3])
        bf_best = max(bf, key=lambda x: x["box"][2]*x["box"][3])
        ac = arcface_align(ap, af_best)
        bc = arcface_align(bp, bf_best)
        ea, eb = embed(ac), embed(bc)
        s = cos(ea, eb)
        print(f"{name:<55} | {s:>7.4f}")
    print()
    _orig_main()


def _orig_main():
    files = sorted((ROOT / "test_imgs").iterdir())
    contact_imgs = []
    # Also pull the 3 stored profile images via DB
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    rows = db.execute(text("""
        SELECT c.id, c.first_name, ui.image_bytes
        FROM contacts c JOIN uploaded_images ui ON ui.id=c.profile_picture_id
        WHERE c.profile_picture_id IS NOT NULL ORDER BY c.id
    """)).fetchall()
    contact_imgs = [(f"c{r.id}_{r.first_name}", bytes(r.image_bytes)) for r in rows]
    test_imgs = [(f"t_{f.name}", f.read_bytes()) for f in files]

    samples = test_imgs + contact_imgs

    print(f"\n{'sample':<48} | mode             | n_faces | top_conf")
    print("-" * 95)
    for label, ib in samples:
        arr = np.array(Image.open(BytesIO(ib)).convert("RGB"))
        for mode, prep in [("upscale-only", upscale),
                            ("upscale+CLAHE", lambda i: clahe(upscale(i)))]:
            try:
                pre = prep(arr.copy())
                faces = _get_mtcnn().detect_faces(pre)
                n = len(faces)
                top = max((f["confidence"] for f in faces), default=0.0)
                print(f"{label[:48]:<48} | {mode:<16} | {n:>7} | {top:.4f}")
            except Exception as e:
                print(f"{label[:48]:<48} | {mode:<16} | ERROR {e}")

    # Same-person Ronaldo similarity test under each pipeline variant.
    print("\nSAME-PERSON RONALDO  (test_images.webp  vs  test_images (1).webp)")
    print(f"{'pipeline':<55} | cos-sim | conf-A | conf-B")
    print("-" * 90)
    a_bytes = (ROOT / "test_imgs" / "images.webp").read_bytes()
    b_bytes = (ROOT / "test_imgs" / "images (1).webp").read_bytes()
    a_arr = np.array(Image.open(BytesIO(a_bytes)).convert("RGB"))
    b_arr = np.array(Image.open(BytesIO(b_bytes)).convert("RGB"))

    pipelines = [
        ("A. upscale,            crop only",       upscale,                       crop_box),
        ("B. upscale,            align-then-crop", upscale,                       align_then_crop),
        ("C. upscale,            crop-then-align", upscale,                       crop_then_align),
        ("D. upscale+CLAHE,      crop only",       lambda i: clahe(upscale(i)),   crop_box),
        ("E. upscale+CLAHE,      align-then-crop", lambda i: clahe(upscale(i)),   align_then_crop),
        ("F. upscale+CLAHE,      crop-then-align", lambda i: clahe(upscale(i)),   crop_then_align),
    ]
    for name, prep, cropper in pipelines:
        try:
            ap, bp = prep(a_arr.copy()), prep(b_arr.copy())
            af = _get_mtcnn().detect_faces(ap)
            bf = _get_mtcnn().detect_faces(bp)
            if not af or not bf:
                print(f"{name:<55} | (no face)")
                continue
            af_best = max(af, key=lambda x: x["box"][2]*x["box"][3])
            bf_best = max(bf, key=lambda x: x["box"][2]*x["box"][3])
            if cropper is crop_box:
                ac = cropper(ap, {"x":af_best["box"][0],"y":af_best["box"][1],
                                  "width":af_best["box"][2],"height":af_best["box"][3]})
                bc = cropper(bp, {"x":bf_best["box"][0],"y":bf_best["box"][1],
                                  "width":bf_best["box"][2],"height":bf_best["box"][3]})
            else:
                ac = cropper(ap, af_best)
                bc = cropper(bp, bf_best)
            ea, eb = embed(ac), embed(bc)
            s = cos(ea, eb)
            print(f"{name:<55} | {s:>7.4f} | {af_best['confidence']:.3f} | {bf_best['confidence']:.3f}")
        except Exception as e:
            print(f"{name:<55} | ERROR {e}")

    # And: confidence of MTCNN's "face" in Abdullah's landscape
    print("\nLANDSCAPE FALSE-POSITIVE INSPECTION (Abdullah's pfp)")
    abdullah_row = next((r for r in rows if r.first_name == "Abdullah"), None)
    if abdullah_row:
        arr = np.array(Image.open(BytesIO(bytes(abdullah_row.image_bytes))).convert("RGB"))
        for mode, prep in [("upscale-only", upscale),
                            ("upscale+CLAHE", lambda i: clahe(upscale(i)))]:
            faces = _get_mtcnn().detect_faces(prep(arr.copy()))
            print(f"  {mode}: detected {len(faces)} face(s)")
            for f in faces:
                print(f"     box={f['box']}  confidence={f['confidence']:.4f}")


if __name__ == "__main__":
    main()
