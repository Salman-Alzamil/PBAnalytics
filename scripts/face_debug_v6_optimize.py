"""Run all 4 investigation tests in one pass:
  Test 1 — save crops to disk
  Test 2 — padding ablation
  Test 3 — landmark alignment on/off
  Test 4 — Facenet512 vs ArcFace vs VGG-Face

Pairs evaluated:
  SAME-RONALDO: every pair from {images, images(1), download.*1-4*}
  DIFFERENT  : Ronaldo-canonical vs {download(5), saudi-arabesque, want-portrait, Ahmed pfp}

Reports: same-min, same-max, diff-max, gap.
"""
from __future__ import annotations
import os, sys, itertools
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

from utils.face_embeddings import _get_mtcnn, _normalize, _MIN_DIM, _MIN_FACE_CONFIDENCE  # noqa: E402

OUT = ROOT / "scripts" / "_v6_crops"
OUT.mkdir(exist_ok=True)


def upscale(img):
    h, w = img.shape[:2]
    if min(h, w) < _MIN_DIM:
        s = _MIN_DIM / min(h, w)
        img = np.array(Image.fromarray(img).resize(
            (max(1, int(w*s)), max(1, int(h*s))), Image.LANCZOS))
    return img


def crop_box(img, box, pad):
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    ih, iw = img.shape[:2]
    p = int(min(w, h) * pad)
    return img[max(0, y - p):min(ih, y + h + p),
               max(0, x - p):min(iw, x + w + p)]


def align_with_landmarks(img, face_dict):
    import cv2
    kp = face_dict["keypoints"]
    le = np.array(kp["left_eye"], dtype=np.float64)
    re = np.array(kp["right_eye"], dtype=np.float64)
    angle = float(np.degrees(np.arctan2(re[1]-le[1], re[0]-le[0])))
    eye_center = ((le[0]+re[0])/2.0, (le[1]+re[1])/2.0)
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LANCZOS4,
                          borderMode=cv2.BORDER_REPLICATE)


def cos(a, b):
    if a is None or b is None: return None
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


_emb_cache: dict = {}


def get_emb(img_bytes_id, raw_bytes, *, model, pad, align, resize_native):
    key = (img_bytes_id, model, pad, align, resize_native)
    if key in _emb_cache:
        return _emb_cache[key]
    from deepface import DeepFace

    arr = upscale(np.array(Image.open(BytesIO(raw_bytes)).convert("RGB")))
    faces = [f for f in _get_mtcnn().detect_faces(arr)
             if f.get("confidence", 0) >= _MIN_FACE_CONFIDENCE]
    if not faces:
        _emb_cache[key] = None
        return None
    face = max(faces, key=lambda f: f["box"][2] * f["box"][3])

    work = align_with_landmarks(arr, face) if align else arr
    crop = crop_box(work, {"x": face["box"][0], "y": face["box"][1],
                            "width": face["box"][2], "height": face["box"][3]}, pad=pad)
    if crop.size == 0:
        _emb_cache[key] = None
        return None

    if resize_native:
        target = {"Facenet512": 160, "ArcFace": 112, "VGG-Face": 224}.get(model, 160)
        crop = np.array(Image.fromarray(crop).resize((target, target), Image.LANCZOS))

    try:
        reps = DeepFace.represent(
            crop, model_name=model, detector_backend="skip",
            enforce_detection=False, align=False,
        )
    except Exception:
        _emb_cache[key] = None
        return None
    if not reps:
        _emb_cache[key] = None
        return None
    out = np.asarray(_normalize(reps[0]["embedding"]))
    _emb_cache[key] = out
    return out


def load_test_set():
    """Returns (samples_dict, same_pairs, diff_pairs).

    User has confirmed: download.*, images*.webp, download(1-4).jfif are Ronaldo.
    download(5).jfif is NOT Ronaldo. saudi-arabesque, want-portrait, Ahmed are different people.
    """
    test_dir = ROOT / "test_imgs"
    samples = {f.name: f.read_bytes() for f in sorted(test_dir.iterdir())}

    # Pull Ahmed pfp from DB to use as a different-person reference
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    rows = db.execute(text("""
        SELECT c.first_name, ui.image_bytes
        FROM contacts c JOIN uploaded_images ui ON ui.id=c.profile_picture_id
        WHERE c.first_name='Ahmed' LIMIT 1
    """)).fetchall()
    if rows:
        samples["[ahmed pfp]"] = bytes(rows[0].image_bytes)

    ronaldo = [
        "images.webp", "images (1).webp",
        "download.jfif", "download (1).jfif", "download (2).jfif",
        "download (3).jfif", "download (4).jfif",
    ]
    different = [
        "download (5).jfif",
        "saudi-arabesque-saudi-men-traditional-dress.jpg",
        "want-portrait-image-plain-dark-260nw-2521853183.webp",
        "[ahmed pfp]",
    ]
    same_pairs = list(itertools.combinations(ronaldo, 2))
    # cross-identity: every Ronaldo vs every non-Ronaldo
    diff_pairs = [(r, d) for r in ronaldo for d in different]
    return samples, same_pairs, diff_pairs


def evaluate(samples, same_pairs, diff_pairs, *, model, pad, align, resize_native, label):
    same_sims, diff_sims = [], []
    failures = []
    for a, b in same_pairs:
        ea = get_emb(a, samples[a], model=model, pad=pad, align=align, resize_native=resize_native)
        eb = get_emb(b, samples[b], model=model, pad=pad, align=align, resize_native=resize_native)
        s = cos(ea, eb)
        if s is None:
            failures.append((a, b, "embed-failed"))
            continue
        same_sims.append(((a, b), s))
    for a, b in diff_pairs:
        ea = get_emb(a, samples[a], model=model, pad=pad, align=align, resize_native=resize_native)
        eb = get_emb(b, samples[b], model=model, pad=pad, align=align, resize_native=resize_native)
        s = cos(ea, eb)
        if s is None: continue
        diff_sims.append(((a, b), s))

    if not same_sims or not diff_sims:
        print(f"{label:<55} | (insufficient data)")
        return None

    s_min = min(s for _, s in same_sims)
    s_med = float(np.median([s for _, s in same_sims]))
    s_max = max(s for _, s in same_sims)
    d_max = max(s for _, s in diff_sims)
    d_med = float(np.median([s for _, s in diff_sims]))
    gap = s_min - d_max
    print(f"{label:<55} | same min/med/max = {s_min:.3f}/{s_med:.3f}/{s_max:.3f} "
          f"| diff med/max = {d_med:.3f}/{d_max:.3f} | gap = {gap:+.3f}")
    return {"label": label, "model": model, "pad": pad, "align": align,
            "resize": resize_native, "same_min": s_min, "same_med": s_med,
            "same_max": s_max, "diff_max": d_max, "gap": gap,
            "worst_same": min(same_sims, key=lambda x: x[1]),
            "worst_diff": max(diff_sims, key=lambda x: x[1])}


def save_crops_for_inspection(samples):
    """Test 1 — save crops to OUT for visual review."""
    print(f"\n[Test 1] Saving crops to {OUT}/")
    from PIL import Image as PILImage
    for name, ib in samples.items():
        if name == "[ahmed pfp]":
            continue
        arr = upscale(np.array(Image.open(BytesIO(ib)).convert("RGB")))
        faces = [f for f in _get_mtcnn().detect_faces(arr)
                 if f.get("confidence", 0) >= _MIN_FACE_CONFIDENCE]
        if not faces:
            print(f"  {name}: NO FACE")
            continue
        face = max(faces, key=lambda f: f["box"][2] * f["box"][3])
        x, y, w, h = face["box"]
        for pad in (0.15, 0.35):
            crop = crop_box(arr, {"x": x, "y": y, "width": w, "height": h}, pad=pad)
            if crop.size == 0: continue
            safe = name.replace(" ", "_").replace("(", "").replace(")", "")
            PILImage.fromarray(crop).save(OUT / f"{safe}__pad{int(pad*100)}.png")
        print(f"  {name}: {w}x{h} face, conf={face['confidence']:.3f}, "
              f"keypoints={'YES' if face.get('keypoints') else 'NO'}")


def main():
    samples, same_pairs, diff_pairs = load_test_set()
    save_crops_for_inspection(samples)

    print(f"\n{len(same_pairs)} same-person pairs, {len(diff_pairs)} different-person pairs\n")

    print("=" * 100)
    print("BASELINE  (current production: Facenet512, pad 0.35, no align, no native-resize)")
    print("=" * 100)
    base = evaluate(samples, same_pairs, diff_pairs,
                    model="Facenet512", pad=0.35, align=False, resize_native=False,
                    label="Facenet512 pad=0.35 align=F resize=F")

    print("\n" + "=" * 100)
    print("TEST 2 — padding ablation  (Facenet512, no align, no resize)")
    print("=" * 100)
    test2 = []
    for pad in (0.15, 0.20, 0.25, 0.35):
        r = evaluate(samples, same_pairs, diff_pairs,
                     model="Facenet512", pad=pad, align=False, resize_native=False,
                     label=f"Facenet512 pad={pad:.2f}")
        if r: test2.append(r)

    print("\n" + "=" * 100)
    print("TEST 3 — landmark alignment  (Facenet512, best pad TBD, no resize)")
    print("=" * 100)
    best_pad = max(test2, key=lambda r: r["gap"])["pad"] if test2 else 0.35
    print(f"  using best padding from Test 2: {best_pad}")
    align_no = evaluate(samples, same_pairs, diff_pairs,
                        model="Facenet512", pad=best_pad, align=False, resize_native=False,
                        label=f"Facenet512 pad={best_pad:.2f} align=False")
    align_yes = evaluate(samples, same_pairs, diff_pairs,
                         model="Facenet512", pad=best_pad, align=True, resize_native=False,
                         label=f"Facenet512 pad={best_pad:.2f} align=True")

    print("\n" + "=" * 100)
    print("FIX D — resize crop to model native size before embedding")
    print("=" * 100)
    resize_test = evaluate(samples, same_pairs, diff_pairs,
                           model="Facenet512", pad=best_pad, align=False, resize_native=True,
                           label=f"Facenet512 pad={best_pad:.2f} align=F resize=160")

    print("\n" + "=" * 100)
    print("TEST 4 — model comparison  (best pad, align as best from Test 3)")
    print("=" * 100)
    best_align = align_yes and align_no and (align_yes["gap"] >= align_no["gap"] + 0.05)
    print(f"  using align={best_align}, pad={best_pad}, resize_native=True")
    test4 = []
    for model in ("Facenet512", "ArcFace", "VGG-Face"):
        r = evaluate(samples, same_pairs, diff_pairs,
                     model=model, pad=best_pad, align=best_align, resize_native=True,
                     label=f"{model} pad={best_pad:.2f} align={best_align} resize=native")
        if r: test4.append(r)

    print("\n" + "=" * 100)
    print("SUMMARY  (sorted by gap, best first)")
    print("=" * 100)
    every = ([base] if base else []) + test2 + ([align_no, align_yes, resize_test] if all([align_no, align_yes, resize_test]) else []) + test4
    every = [e for e in every if e is not None]
    every.sort(key=lambda r: -r["gap"])
    for r in every[:10]:
        print(f"  {r['label']:<55} | same_min={r['same_min']:.3f} diff_max={r['diff_max']:.3f} gap={r['gap']:+.3f}")
        ws = r["worst_same"]
        print(f"      worst-same: {ws[0][0]} <-> {ws[0][1]} = {ws[1]:.3f}")
        wd = r["worst_diff"]
        print(f"      worst-diff: {wd[0][0]} <-> {wd[0][1]} = {wd[1]:.3f}")


if __name__ == "__main__":
    main()
